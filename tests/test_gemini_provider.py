"""Offline Gemini provider tests — mocked HTTP only; no live API requests."""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest
import urllib.error

from sgte.cache.semantic import SemanticCache
from sgte.llm.base import LLMError, LLMHTTPError, MissingCredentialsError
from sgte.llm.factory import build_llm_provider
from sgte.llm.gemini_provider import (
    GeminiProvider,
    classify_gemini_http_error,
    extract_gemini_text,
    parse_structured_json,
)
from sgte.llm.openai_provider import OpenAICompatibleProvider
from sgte.paths import INPUT_TXT
from sgte.pipeline import TroubleshootingPipeline
from sgte.settings import Settings


def _http_error(code: int, body: Dict[str, Any], reason: str = "Error") -> urllib.error.HTTPError:
    raw = json.dumps(body).encode("utf-8")
    return urllib.error.HTTPError(
        url="https://generativelanguage.googleapis.com/v1beta/models/x:generateContent",
        code=code,
        msg=reason,
        hdrs=None,  # type: ignore[arg-type]
        fp=BytesIO(raw),
    )


def _gemini_success_payload(obj: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": json.dumps(obj)}],
                    "role": "model",
                },
                "finishReason": "STOP",
            }
        ],
        "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5},
    }


class _Resp:
    def __init__(self, payload: Dict[str, Any]):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


def test_gemini_requires_api_key():
    with pytest.raises(MissingCredentialsError):
        GeminiProvider(api_key="", model="gemini-2.0-flash")


def test_settings_reads_gemini_api_key(monkeypatch):
    monkeypatch.setenv("SGTE_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-test-not-real")
    monkeypatch.delenv("SGTE_LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("SGTE_LLM_MODEL", raising=False)
    s = Settings.from_env()
    assert s.llm_provider == "gemini"
    assert s.llm_api_key == "AIza-test-not-real"
    assert s.llm_model == "gemini-2.0-flash"
    assert "generativelanguage.googleapis.com" in s.llm_base_url


def test_factory_builds_gemini(monkeypatch):
    monkeypatch.setenv("SGTE_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-test-not-real")
    s = Settings.from_env()
    llm = build_llm_provider(s)
    assert isinstance(llm, GeminiProvider)
    assert llm.provider_name == "gemini"


def test_factory_openai_unchanged(monkeypatch):
    monkeypatch.setenv("SGTE_LLM_PROVIDER", "openai")
    monkeypatch.setenv("SGTE_LLM_API_KEY", "sk-test-not-real")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    s = Settings.from_env()
    llm = build_llm_provider(s)
    assert isinstance(llm, OpenAICompatibleProvider)
    assert llm.provider_name == "openai"


def test_factory_production_none_no_silent_mock():
    with pytest.raises(MissingCredentialsError):
        build_llm_provider(
            Settings(
                llm_provider="none",
                llm_model="gemini-2.0-flash",
                llm_api_key="",
                llm_base_url="https://generativelanguage.googleapis.com/v1beta",
                llm_mode="production",
                embedding_provider="hashing",
                index_dir=Path(".sgte_index"),
                debug=False,
                cache_enabled=True,
                cache_threshold=0.58,
                prewarm_on_startup=False,
            )
        )


def test_gemini_successful_structured_json():
    provider = GeminiProvider(api_key="AIza-test-not-real", model="gemini-2.0-flash")
    payload = _gemini_success_payload(
        {
            "actions": [
                {
                    "actionName": "Touch Sensitivity Setting",
                    "description": "enable the Touch sensitivity option",
                    "steps": ["enable the Touch sensitivity option"],
                }
            ]
        }
    )
    with patch("urllib.request.urlopen", return_value=_Resp(payload)):
        out = provider.generate_structured_response("prompt", system="Return JSON only.")
    assert "actions" in out
    assert out["actions"][0]["actionName"] == "Touch Sensitivity Setting"
    # Key must never appear in stringified output
    assert "AIza-test-not-real" not in json.dumps(out)


def test_gemini_malformed_json_raises():
    provider = GeminiProvider(api_key="AIza-test-not-real", model="gemini-2.0-flash")
    payload = {
        "candidates": [{"content": {"parts": [{"text": "not-json{"}]}}],
    }
    with patch("urllib.request.urlopen", return_value=_Resp(payload)):
        with pytest.raises(LLMError) as ei:
            provider.generate_structured_response("prompt")
    assert ei.value.kind == "malformed_response"


def test_gemini_empty_candidates_raises():
    provider = GeminiProvider(api_key="AIza-test-not-real", model="gemini-2.0-flash")
    with patch("urllib.request.urlopen", return_value=_Resp({"candidates": []})):
        with pytest.raises(LLMError) as ei:
            provider.generate_structured_response("prompt")
    assert ei.value.kind == "malformed_response"


def test_gemini_http_auth_error():
    provider = GeminiProvider(api_key="AIza-test-not-real", model="gemini-2.0-flash")
    body = {"error": {"code": 401, "message": "API key not valid", "status": "UNAUTHENTICATED"}}
    with patch("urllib.request.urlopen", side_effect=_http_error(401, body, "Unauthorized")):
        with pytest.raises(LLMHTTPError) as ei:
            provider.generate_structured_response("prompt")
    assert ei.value.kind == "authentication"
    assert "AIza-test-not-real" not in str(ei.value)


def test_gemini_http_429_and_server():
    provider = GeminiProvider(api_key="AIza-test-not-real", model="gemini-2.0-flash")
    body_429 = {"error": {"code": 429, "message": "Resource exhausted", "status": "RESOURCE_EXHAUSTED"}}
    with patch("urllib.request.urlopen", side_effect=_http_error(429, body_429, "Too Many Requests")):
        with pytest.raises(LLMHTTPError) as ei:
            provider.generate_structured_response("prompt")
    assert ei.value.kind == "rate_limit_or_quota_unspecified"

    body_500 = {"error": {"code": 500, "message": "boom", "status": "INTERNAL"}}
    with patch("urllib.request.urlopen", side_effect=_http_error(500, body_500, "Internal Server Error")):
        with pytest.raises(LLMHTTPError) as ei2:
            provider.generate_structured_response("prompt")
    assert ei2.value.kind == "server_error"


def test_gemini_timeout_raises():
    provider = GeminiProvider(api_key="AIza-test-not-real", model="gemini-2.0-flash")
    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.URLError("timed out"),
    ):
        with pytest.raises(LLMError) as ei:
            provider.generate_structured_response("prompt")
    assert ei.value.kind == "timeout"


def test_gemini_error_does_not_fabricate_plan():
    q = [ln.strip() for ln in INPUT_TXT.read_text(encoding="utf-8").splitlines() if ln.strip()][18]

    class BoomGemini:
        provider_name = "gemini"
        model_name = "gemini-2.0-flash"
        last_cost_usd = 0.0

        def generate_structured_response(self, prompt, *, system=None):
            raise LLMError("forced gemini failure", kind="server_error")

    pipe = TroubleshootingPipeline(
        llm=BoomGemini(),  # type: ignore[arg-type]
        allow_mock=False,
        debug=False,
        use_cache=False,
        cache=SemanticCache(),
    )
    with pytest.raises(LLMError):
        pipe.troubleshoot(q)


def test_classify_gemini_quota_language():
    c = classify_gemini_http_error(
        429,
        json.dumps({"error": {"code": 429, "message": "You exceeded your quota", "status": "RESOURCE_EXHAUSTED"}}),
        reason="Too Many Requests",
    )
    assert c["kind"] == "insufficient_quota"


def test_parse_structured_json_strips_fences():
    obj = parse_structured_json("```json\n{\"actions\": []}\n```")
    assert obj == {"actions": []}


def test_extract_gemini_text():
    text = extract_gemini_text(_gemini_success_payload({"goal": "x"}))
    assert json.loads(text)["goal"] == "x"


def test_gemini_request_uses_header_not_query_key():
    provider = GeminiProvider(api_key="AIza-test-not-real", model="gemini-2.0-flash")
    captured = {}

    def fake_urlopen(req, timeout=60):
        captured["url"] = req.full_url
        captured["headers"] = dict(req.headers)
        return _Resp(_gemini_success_payload({"actions": []}))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        provider.generate_structured_response("prompt")
    assert "key=" not in captured["url"]
    # urllib may title-case headers
    headers_l = {k.lower(): v for k, v in captured["headers"].items()}
    assert headers_l.get("x-goog-api-key") == "AIza-test-not-real"
