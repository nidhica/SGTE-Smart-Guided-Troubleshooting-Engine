"""Focused tests for startup prewarm + cache safety. Does not alter production scoring."""

from __future__ import annotations

from fastapi.testclient import TestClient

from sgte.api import create_app, load_prewarm_queries
from sgte.cache.prewarm import prewarm_cache
from sgte.cache.semantic import SemanticCache
from sgte.llm.mock import MockLLMProvider
from sgte.paths import INPUT_TXT
from sgte.pipeline import TroubleshootingPipeline, grounded_mock_factory
from sgte.validator import ResponseValidator


def _pipe() -> TroubleshootingPipeline:
    return TroubleshootingPipeline(
        llm=MockLLMProvider(factory=grounded_mock_factory),
        allow_mock=True,
        debug=False,
        cache=SemanticCache(threshold=0.58),
        use_cache=True,
    )


def test_prewarm_cache_populates_expected_entries():
    pipe = _pipe()
    queries = load_prewarm_queries()[:2]
    assert queries
    before = pipe.cache.stats()["size"]
    report = prewarm_cache(pipe, queries, include_variations=True)
    after = pipe.cache.stats()["size"]
    assert after > before
    assert report["entries_successfully_cached"] > 0
    assert report["cache_size"] == after
    # Known seed must hit after prewarm.
    hit = pipe.troubleshoot(queries[0])
    assert hit.cache_hit is True
    assert hit.cost_usd == 0.0


def test_prewarm_twice_does_not_duplicate_cache_state():
    pipe = _pipe()
    queries = load_prewarm_queries()[:1]
    first = prewarm_cache(pipe, queries, include_variations=True)
    size_after_first = pipe.cache.stats()["size"]
    second = prewarm_cache(pipe, queries, include_variations=True)
    size_after_second = pipe.cache.stats()["size"]
    assert size_after_second == size_after_first
    assert second["cache_size"] == first["cache_size"]
    # Second pass should mostly be hits, not new writes.
    assert second["entries_successfully_cached"] >= 1


def test_startup_invokes_prewarming_exactly_once():
    pipe = _pipe()
    seeds = load_prewarm_queries()[:1]

    def _seeds():
        return seeds

    # Patch loader so startup prewarm stays fast.
    import time

    import sgte.api as api_mod

    original = api_mod.load_prewarm_queries
    api_mod.load_prewarm_queries = _seeds  # type: ignore[assignment]
    try:
        app = create_app(pipeline=pipe, prewarm=True)
        with TestClient(app) as client:
            assert app.state.prewarm_invocations == 1
            # Prewarm runs in a background thread after traffic is accepted.
            deadline = time.time() + 60.0
            while not app.state.prewarm_done and time.time() < deadline:
                time.sleep(0.05)
            assert app.state.prewarm_done is True
            assert pipe.cache.stats()["size"] >= 1
            health = client.get("/health")
            assert health.status_code == 200
            # Lifespan must not re-run prewarm on subsequent requests.
            client.get("/health")
            assert app.state.prewarm_invocations == 1
            warm = client.post("/v1/troubleshoot", json={"query": seeds[0]})
            assert warm.status_code == 200
            assert warm.json()["meta"]["cache_hit"] is True
            assert warm.json()["meta"]["cost_usd"] == 0.0
    finally:
        api_mod.load_prewarm_queries = original  # type: ignore[assignment]


def test_normal_cache_hit_still_works_without_startup_prewarm():
    client = TestClient(create_app(pipeline=_pipe(), prewarm=False))
    q = INPUT_TXT.read_text(encoding="utf-8").splitlines()[0]
    first = client.post("/v1/troubleshoot", json={"query": q})
    second = client.post("/v1/troubleshoot", json={"query": q})
    assert first.status_code == 200
    assert first.json()["meta"]["cache_hit"] is False
    assert second.status_code == 200
    assert second.json()["meta"]["cache_hit"] is True
    assert second.json()["meta"]["cost_usd"] == 0.0


def test_unseen_request_still_works_after_prewarm():
    pipe = _pipe()
    prewarm_cache(pipe, load_prewarm_queries()[:1], include_variations=False)
    size = pipe.cache.stats()["size"]
    result = pipe.troubleshoot("How do I bake sourdough bread in a home oven")
    assert result.cache_hit is False
    assert result.validation is not None and result.validation.ok
    # Unrelated miss may write a no-match entry; that is normal cold-path behavior.
    assert pipe.cache.stats()["size"] >= size


def test_fallback_behavior_unchanged_with_blank_siis(deeplink_repo):
    pipe = _pipe()
    result = pipe.troubleshoot("my phone screen is black", siis_response="   ")
    assert result.cache_hit is False
    assert result.fallback == "no_siis_context"
    assert result.response.contexts == []
    assert result.meta.get("fallback") == "no_siis_context"


def test_api_schema_unchanged_with_prewarm_flag(deeplink_repo):
    client = TestClient(create_app(pipeline=_pipe(), prewarm=False))
    body = client.post(
        "/v1/troubleshoot",
        json={"query": "my phone screen is black"},
    ).json()
    assert set(body.keys()) == {"query", "query_variations", "response", "meta"}
    assert "contexts" in body["response"]
    assert {"latency_ms", "cache_hit", "model", "cost_usd"} <= set(body["meta"].keys())
    checked = ResponseValidator(deeplink_repo).validate(body["response"])
    assert checked.ok, checked.errors
