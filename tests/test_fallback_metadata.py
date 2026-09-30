"""Theme 2 fallback metadata: meta.fallback = no_match | no_siis_context."""

from __future__ import annotations

from fastapi.testclient import TestClient

from sgte.api import create_app
from sgte.cache.semantic import SemanticCache
from sgte.engine import TroubleshootingEngine
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


def _client(pipe=None) -> TestClient:
    return TestClient(create_app(pipeline=pipe or _pipe()), raise_server_exceptions=False)


def _official() -> str:
    return INPUT_TXT.read_text(encoding="utf-8").splitlines()[0]


def test_unsupported_query_emits_no_match_fallback():
    result = _pipe().troubleshoot("how to bake sourdough bread")
    assert result.response.model_dump() == {"contexts": []}
    assert result.fallback == "no_match"
    assert result.meta.get("fallback") == "no_match"
    assert result.matched is False


def test_missing_siis_context_emits_no_siis_context_fallback():
    # Explicit blank SIIS text (key present, unusable content) — not the same as omission.
    result = _pipe().troubleshoot("my phone screen is black", siis_response="   ")
    assert result.response.model_dump() == {"contexts": []}
    assert result.fallback == "no_siis_context"
    assert result.meta.get("fallback") == "no_siis_context"


def test_supplied_empty_plan_is_no_match_not_no_siis_context():
    # Usable SIIS text that yields no grounded actions → no_match.
    result = _pipe().troubleshoot(
        "my phone screen is black",
        siis_response="This article has no troubleshooting steps at all.",
    )
    assert result.response.contexts == [] or result.extraction_empty or result.fallback == "no_match"
    if not result.response.contexts:
        assert result.fallback == "no_match"
        assert result.fallback != "no_siis_context"


def test_successful_query_has_no_fallback_metadata():
    result = _pipe().troubleshoot("My phone screen is black")
    assert result.response.contexts
    assert result.fallback is None
    assert "fallback" not in result.meta


def test_api_unsupported_includes_meta_fallback_no_match():
    body = _client().post("/v1/troubleshoot", json={"query": "how to bake sourdough bread"}).json()
    assert body["response"]["contexts"] == []
    assert body["meta"]["fallback"] == "no_match"
    assert "query_variations" in body


def test_api_missing_siis_context_fallback():
    body = _client().post(
        "/v1/troubleshoot",
        json={"query": "my phone screen is black", "siis_response": ""},
    ).json()
    assert body["response"]["contexts"] == []
    assert body["meta"]["fallback"] == "no_siis_context"


def test_api_success_omits_fallback_key():
    body = _client().post("/v1/troubleshoot", json={"query": "My phone screen is black"}).json()
    assert body["response"]["contexts"]
    assert "fallback" not in body["meta"]
    from sgte.deeplink_repo import DeeplinkRepository

    checked = ResponseValidator(DeeplinkRepository.from_file()).validate(body["response"])
    assert checked.ok, checked.errors


def test_engine_no_match_sets_fallback():
    engine = TroubleshootingEngine()
    result = engine.respond("zzzzqxqwy unique-nonoverlap-token-xyzzy")
    assert result.response.contexts == []
    assert result.fallback == "no_match"


def test_phase7_unsupported_still_empty_contexts():
    result = _pipe().troubleshoot("How do I bake sourdough bread in a home oven")
    assert result.response.model_dump() == {"contexts": []}
    assert result.matched is False
    assert result.fallback == "no_match"
