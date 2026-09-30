"""Offline Groq provider tests — mocked HTTP only; no live API requests."""

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
from sgte.llm.gemini_provider import GeminiProvider
from sgte.llm.groq_provider import GroqProvider
from sgte.llm.openai_provider import OpenAICompatibleProvider
from sgte.paths import INPUT_TXT
from sgte.pipeline import TroubleshootingPipeline
from sgte.settings import Settings


def _http_error(code: int, body: Dict[str, Any], reason: str = "Error") -> urllib.error.HTTPError:
    raw = json.dumps(body).encode("utf-8")
    return urllib.error.HTTPError(
        url="https://api.groq.com/openai/v1/chat/completions",
        code=code,
        msg=reason,
        hdrs=None,  # type: ignore[arg-type]
        fp=BytesIO(raw),
    )


def _chat_success_payload(obj: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "model": "llama-3.3-70b-versatile",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": json.dumps(obj)},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
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


def test_groq_requires_api_key():
    with pytest.raises(MissingCredentialsError, match="GROQ_API_KEY"):
        GroqProvider(api_key="", model="llama-3.3-70b-versatile")


def test_settings_reads_groq_api_key(monkeypatch):
    monkeypatch.setenv("SGTE_LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test-not-real")
    monkeypatch.delenv("SGTE_LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("SGTE_LLM_MODEL", raising=False)
    monkeypatch.delenv("SGTE_LLM_BASE_URL", raising=False)
    s = Settings.from_env()
    assert s.llm_provider == "groq"
    assert s.llm_api_key == "gsk-test-not-real"
    assert s.llm_model == "llama-3.3-70b-versatile"
    assert s.llm_base_url == "https://api.groq.com/openai/v1"


def test_factory_builds_groq(monkeypatch):
    monkeypatch.setenv("SGTE_LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test-not-real")
    s = Settings.from_env()
    llm = build_llm_provider(s)
    assert isinstance(llm, GroqProvider)
    assert llm.provider_name == "groq"
    assert isinstance(llm, OpenAICompatibleProvider)


def test_factory_preserves_openai_and_gemini(monkeypatch):
    monkeypatch.setenv("SGTE_LLM_PROVIDER", "openai")
    monkeypatch.setenv("SGTE_LLM_API_KEY", "sk-test-not-real")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    s = Settings.from_env()
    assert isinstance(build_llm_provider(s), OpenAICompatibleProvider)
    assert not isinstance(build_llm_provider(s), GroqProvider)

    monkeypatch.setenv("SGTE_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-test-not-real")
    s2 = Settings.from_env()
    assert isinstance(build_llm_provider(s2), GeminiProvider)


def test_factory_production_none_no_silent_mock():
    with pytest.raises(MissingCredentialsError):
        build_llm_provider(
            Settings(
                llm_provider="none",
                llm_model="llama-3.3-70b-versatile",
                llm_api_key="",
                llm_base_url="https://api.groq.com/openai/v1",
                llm_mode="production",
                embedding_provider="hashing",
                index_dir=Path(".sgte_index"),
                debug=False,
                cache_enabled=True,
                cache_threshold=0.58,
                prewarm_on_startup=False,
            )
        )


def test_groq_successful_structured_json():
    provider = GroqProvider(api_key="gsk-test-not-real", model="llama-3.3-70b-versatile")
    payload = _chat_success_payload(
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
    with patch("urllib.request.urlopen", return_value=_Resp(payload)) as mock_open:
        out = provider.generate_structured_response("prompt", system="Return JSON only.")
    assert out["actions"][0]["actionName"] == "Touch Sensitivity Setting"
    req = mock_open.call_args[0][0]
    assert req.full_url == "https://api.groq.com/openai/v1/chat/completions"
    body = json.loads(req.data.decode("utf-8"))
    assert body["response_format"] == {"type": "json_object"}
    assert body["temperature"] == 0
    assert body["model"] == "llama-3.3-70b-versatile"
    headers_l = {k.lower(): v for k, v in req.headers.items()}
    assert headers_l.get("user-agent") == "SGTE-GroqProvider/1.0"
    assert headers_l.get("authorization") == "Bearer gsk-test-not-real"
    assert "gsk-test-not-real" not in json.dumps(out)


def test_groq_sends_explicit_user_agent():
    provider = GroqProvider(api_key="gsk-test-not-real", model="openai/gpt-oss-120b")
    captured = {}

    def fake_urlopen(req, timeout=60):
        captured["url"] = req.full_url
        captured["headers"] = {k.lower(): v for k, v in req.headers.items()}
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _Resp(_chat_success_payload({"actions": []}))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        provider.generate_structured_response("prompt")
    assert captured["url"].endswith("/chat/completions")
    assert captured["headers"].get("user-agent") == "SGTE-GroqProvider/1.0"
    assert captured["headers"].get("content-type") == "application/json"
    assert captured["headers"].get("authorization", "").startswith("Bearer ")
    assert captured["body"]["response_format"] == {"type": "json_object"}


def test_openai_provider_does_not_gain_groq_user_agent():
    """OpenAI provider must remain unchanged (no Groq User-Agent)."""
    provider = OpenAICompatibleProvider(
        api_key="sk-test-not-real",
        model="gpt-4o-mini",
        base_url="https://api.openai.com/v1",
    )
    captured = {}

    def fake_urlopen(req, timeout=60):
        captured["headers"] = {k.lower(): v for k, v in req.headers.items()}
        return _Resp(_chat_success_payload({"actions": []}))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        provider.generate_structured_response("prompt")
    assert captured["headers"].get("user-agent") != "SGTE-GroqProvider/1.0"


def test_groq_malformed_json_raises():
    provider = GroqProvider(api_key="gsk-test-not-real")
    payload = {
        "choices": [{"message": {"content": "not-json{"}}],
    }
    with patch("urllib.request.urlopen", return_value=_Resp(payload)):
        with pytest.raises(LLMError) as ei:
            provider.generate_structured_response("prompt")
    assert ei.value.kind == "malformed_response"


def test_groq_http_auth_rate_limit_server():
    provider = GroqProvider(api_key="gsk-test-not-real")
    with patch(
        "urllib.request.urlopen",
        side_effect=_http_error(401, {"error": {"message": "Invalid API Key", "type": "invalid_request_error"}}, "Unauthorized"),
    ):
        with pytest.raises(LLMHTTPError) as ei:
            provider.generate_structured_response("prompt")
    assert ei.value.kind == "authentication"
    assert "gsk-test-not-real" not in str(ei.value)

    with patch(
        "urllib.request.urlopen",
        side_effect=_http_error(
            429,
            {"error": {"message": "Rate limit reached", "code": "rate_limit_exceeded", "type": "requests"}},
            "Too Many Requests",
        ),
    ):
        with pytest.raises(LLMHTTPError) as ei2:
            provider.generate_structured_response("prompt")
    assert ei2.value.kind == "rate_limit"

    with patch(
        "urllib.request.urlopen",
        side_effect=_http_error(500, {"error": {"message": "boom"}}, "Internal Server Error"),
    ):
        with pytest.raises(LLMHTTPError) as ei3:
            provider.generate_structured_response("prompt")
    assert ei3.value.kind == "server_error"


def test_groq_timeout_raises():
    provider = GroqProvider(api_key="gsk-test-not-real")
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timed out")):
        with pytest.raises(LLMError) as ei:
            provider.generate_structured_response("prompt")
    assert ei.value.kind == "timeout"


def test_groq_error_does_not_fabricate_plan():
    q = [ln.strip() for ln in INPUT_TXT.read_text(encoding="utf-8").splitlines() if ln.strip()][18]

    class BoomGroq:
        provider_name = "groq"
        model_name = "llama-3.3-70b-versatile"
        last_cost_usd = 0.0

        def generate_structured_response(self, prompt, *, system=None):
            raise LLMError("forced groq failure", kind="server_error")

    pipe = TroubleshootingPipeline(
        llm=BoomGroq(),  # type: ignore[arg-type]
        allow_mock=False,
        debug=False,
        use_cache=False,
        cache=SemanticCache(),
    )
    with pytest.raises(LLMError):
        pipe.troubleshoot(q)


def test_groq_single_request_no_retry_on_failure():
    provider = GroqProvider(api_key="gsk-test-not-real")
    calls = {"n": 0}

    def boom(*a, **k):
        calls["n"] += 1
        raise _http_error(503, {"error": {"message": "busy"}}, "Service Unavailable")

    with patch("urllib.request.urlopen", side_effect=boom):
        with pytest.raises(LLMHTTPError):
            provider.generate_structured_response("prompt")
    assert calls["n"] == 1
