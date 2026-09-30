"""FastAPI layer. Delegates to TroubleshootingPipeline.troubleshoot()."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from sgte.cache.prewarm import prewarm_cache
from sgte.cache.semantic import LOGIC_VERSION, SemanticCache
from sgte.llm.mock import MockLLMProvider
from sgte.paths import INPUT_TXT
from sgte.pipeline import TroubleshootingPipeline, grounded_mock_factory
from sgte.query.enrich import enrich_query
from sgte.settings import Settings
from sgte.url_leak import url_leak_reasons

LOCALHOST_ORIGIN_REGEX = r"https?://(localhost|127\.0\.0\.1)(:\d+)?$"
_LOG = logging.getLogger("sgte.api")


class TroubleshootRequest(BaseModel):
    query: str
    siis_response: Optional[str] = None

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value: str) -> str:
        if value is None or not str(value).strip():
            raise ValueError("query must be a non-empty string")
        return value


class MetaOut(BaseModel):
    latency_ms: float
    cache_hit: bool
    model: str
    cost_usd: float
    # Official Theme 2 envelope metadata (not schema.py). Only present on empty plans.
    fallback: Optional[str] = None
    # Demo/review labeling — MOCK vs LIVE; does not imply production authorization.
    execution_mode: Optional[str] = None

    model_config = {"extra": "ignore"}


class TroubleshootResponse(BaseModel):
    query: str
    query_variations: List[str]
    response: Dict[str, Any]
    meta: MetaOut

    def model_dump(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(*args, **kwargs)


def _http_urls_in(obj: Any) -> List[str]:
    found: List[str] = []
    if isinstance(obj, str):
        if url_leak_reasons(obj) or "http://" in obj.lower() or "https://" in obj.lower():
            if "http://" in obj.lower() or "https://" in obj.lower():
                found.append(obj[:120])
        return found
    if isinstance(obj, dict):
        for value in obj.values():
            found.extend(_http_urls_in(value))
    elif isinstance(obj, list):
        for value in obj:
            found.extend(_http_urls_in(value))
    return found


def load_prewarm_queries() -> List[str]:
    """Official Theme 2 input.txt lines used for startup prewarm."""
    if not INPUT_TXT.exists():
        return []
    return [
        line.strip()
        for line in INPUT_TXT.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def create_pipeline(settings: Optional[Settings] = None) -> TroubleshootingPipeline:
    settings = settings or Settings.from_env()
    allow_mock = settings.llm_provider in {"", "none", "mock"}
    llm = None
    if allow_mock:
        llm = MockLLMProvider(factory=grounded_mock_factory)
    return TroubleshootingPipeline(
        settings=settings,
        llm=llm,
        allow_mock=allow_mock,
        debug=False,
        cache=SemanticCache(threshold=settings.cache_threshold),
    )


def _run_startup_prewarm(pipe: TroubleshootingPipeline, queries: List[str]) -> Dict[str, Any]:
    """Synchronous prewarm body (runs off the event loop)."""
    _LOG.info("STARTUP: cache prewarm begin (%d seed queries)", len(queries))
    t0 = time.perf_counter()
    if pipe.use_cache and pipe.cache is not None and queries:
        report = prewarm_cache(pipe, queries, include_variations=True)
    else:
        report = {
            "entries_attempted": 0,
            "entries_successfully_cached": 0,
            "failures": [],
            "failure_count": 0,
            "cache_size": pipe.cache.stats()["size"] if pipe.cache else 0,
            "skipped": True,
        }
    report["elapsed_ms"] = (time.perf_counter() - t0) * 1000.0
    _LOG.info(
        "STARTUP: cache prewarm complete attempted=%s cached=%s elapsed_ms=%.0f",
        report.get("entries_attempted"),
        report.get("entries_successfully_cached"),
        report["elapsed_ms"],
    )
    return report


def create_app(
    pipeline: Optional[TroubleshootingPipeline] = None,
    *,
    prewarm: Optional[bool] = None,
) -> FastAPI:
    """Create the API app.

    Startup prewarm uses existing ``prewarm_cache()`` once. Default:
    - ``prewarm=True`` when the app boots its own pipeline (production ``app``)
    - ``prewarm=False`` when a pipeline is injected (unit tests stay fast / predictable)
    Override with the ``prewarm=`` argument or ``SGTE_PREWARM_ON_STARTUP``.

    Prewarm runs in a background thread *after* the app is ready to accept traffic so
    uvicorn can reach \"Application startup complete\" without waiting for ~100+ cold
    pipeline runs (Phase 8 made each seed+variation pass multi-second).
    """
    settings = Settings.from_env()
    if prewarm is None:
        if pipeline is not None:
            do_prewarm = False
        else:
            do_prewarm = bool(settings.prewarm_on_startup and settings.cache_enabled)
    else:
        do_prewarm = bool(prewarm)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        prewarm_task: Optional[asyncio.Task] = None
        _LOG.info("STARTUP: lifespan begin")
        # Boot pipeline before accepting traffic (SIIS + catalogue index). Fast.
        pipe = app.state.pipeline
        if pipe is None:
            _LOG.info("STARTUP: loading pipeline (SIIS + catalogue index)")
            t0 = time.perf_counter()
            pipe = create_pipeline(settings)
            app.state.pipeline = pipe
            _LOG.info("STARTUP: pipeline ready (%.2fs)", time.perf_counter() - t0)
        else:
            _LOG.info("STARTUP: using injected pipeline")

        app.state.prewarm_invocations = int(getattr(app.state, "prewarm_invocations", 0) or 0)
        app.state.prewarm_running = False

        async def _background_prewarm() -> None:
            app.state.prewarm_running = True
            try:
                queries = load_prewarm_queries()
                report = await asyncio.to_thread(_run_startup_prewarm, pipe, queries)
                app.state.prewarm_report = report
            except Exception as exc:  # noqa: BLE001 — startup must stay up
                _LOG.exception("STARTUP: cache prewarm failed: %s", exc)
                app.state.prewarm_report = {
                    "entries_attempted": 0,
                    "entries_successfully_cached": 0,
                    "failures": [f"{type(exc).__name__}:{exc}"],
                    "failure_count": 1,
                    "cache_size": pipe.cache.stats()["size"] if pipe.cache else 0,
                    "error": str(exc),
                }
            finally:
                app.state.prewarm_done = True
                app.state.prewarm_running = False
                _LOG.info("STARTUP: startup complete")

        if do_prewarm and not getattr(app.state, "prewarm_done", False):
            app.state.prewarm_invocations += 1
            prewarm_task = asyncio.create_task(_background_prewarm())
        else:
            app.state.prewarm_done = True
            _LOG.info("STARTUP: prewarm skipped; startup complete")

        _LOG.info("STARTUP: accepting traffic")
        yield

        if prewarm_task is not None and not prewarm_task.done():
            prewarm_task.cancel()
            try:
                await prewarm_task
            except asyncio.CancelledError:
                pass

    app = FastAPI(
        title="SGTE Troubleshooting API",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=LOCALHOST_ORIGIN_REGEX,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.pipeline = pipeline
    app.state.prewarm_done = False
    app.state.prewarm_invocations = 0
    app.state.prewarm_enabled = do_prewarm
    app.state.prewarm_running = False

    def pipeline_or_boot() -> TroubleshootingPipeline:
        if app.state.pipeline is None:
            app.state.pipeline = create_pipeline(settings)
        return app.state.pipeline

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "validation_error", "message": "Invalid request"}},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        # Match the frontend ApiError envelope ({error: {code, message}}).
        # FastAPI's default would return {"detail": ...}, which the UI does not parse.
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": "http_error", "message": str(exc.detail)}},
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": "Request failed"}},
        )

    @app.get("/health")
    def health() -> Dict[str, Any]:
        pipe = pipeline_or_boot()
        cache_state = "ready" if pipe.cache is not None else "unavailable"
        catalogue = "loaded" if len(pipe.deeplinks) else "empty"
        siis = "loaded" if len(pipe.siis.inner) else "empty"
        provider = (settings.llm_provider or "none").lower()
        # MOCK when mock provider or empty/none with allow_mock boot path
        if provider in {"mock", "", "none"}:
            execution_mode = "MOCK"
        else:
            execution_mode = "LIVE"
        demo_offline = os.environ.get("SGTE_DEMO_OFFLINE", "").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        cache_stats = pipe.cache.stats() if pipe.cache is not None else {}
        return {
            "status": "ok",
            "cache": cache_state,
            "cache_logic_version": LOGIC_VERSION,
            "cache_size": cache_stats.get("size"),
            "catalogue": catalogue,
            "siis": siis,
            "execution_mode": execution_mode,
            "llm_provider": provider or "none",
            "demo_offline": demo_offline or execution_mode == "MOCK",
            "production_authorized": False,
            "implementation_gate_satisfied": False,
        }

    @app.post("/v1/cache/clear")
    def clear_cache() -> Dict[str, Any]:
        """Drop in-memory semantic cache entries (demo/ops). Does not disable caching."""
        pipe = pipeline_or_boot()
        if pipe.cache is None:
            raise HTTPException(status_code=503, detail="Cache unavailable")
        before = pipe.cache.stats()["size"]
        pipe.cache.clear()
        return {
            "status": "ok",
            "cleared": before,
            "cache_size": pipe.cache.stats()["size"],
            "cache_logic_version": LOGIC_VERSION,
        }

    @app.post("/v1/troubleshoot", response_model_exclude_none=True)
    def troubleshoot(body: TroubleshootRequest) -> TroubleshootResponse:
        t0 = time.perf_counter()
        pipe = pipeline_or_boot()
        result = pipe.troubleshoot(body.query, siis_response=body.siis_response)
        if result.validation is None or not result.validation.ok:
            raise HTTPException(status_code=500, detail="Response failed schema validation")
        payload = result.response.model_dump(mode="json")
        meta: Dict[str, Any] = {
            "latency_ms": (time.perf_counter() - t0) * 1000.0,
            "cache_hit": bool(result.cache_hit),
            "model": result.model,
            "cost_usd": float(result.cost_usd),
            "execution_mode": (
                "MOCK"
                if (settings.llm_provider or "").lower() in {"mock", "", "none"}
                or str(result.model or "").startswith("mock")
                or str(getattr(result, "llm_provider", "") or "") == "mock"
                else "LIVE"
            ),
        }
        fallback = result.fallback or (result.meta or {}).get("fallback")
        if fallback:
            meta["fallback"] = fallback
        envelope = {
            "query": body.query,
            "query_variations": enrich_query(body.query)["query_variations"],
            "response": payload,
            "meta": meta,
        }
        checked = pipe.validator.validate(payload)
        if not checked.ok:
            raise HTTPException(status_code=500, detail="Response failed schema validation")
        if _http_urls_in(envelope):
            raise HTTPException(status_code=500, detail="Response failed schema validation")
        return TroubleshootResponse.model_validate(envelope)

    return app


app = create_app()
