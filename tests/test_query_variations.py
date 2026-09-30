"""Official Theme 2 query_variations: 8–10 distinct register-aware paraphrases."""

from __future__ import annotations

import re

from sgte.query.enrich import enrich_query, generate_query_variations
from sgte.query.normalize import normalize_query
from sgte.url_leak import url_leak_reasons

_REQUIRED_REGISTERS = ("formal", "casual", "keyword-only", "frustrated", "typo-inclusive")


def _assert_variation_list(variations: list[str]) -> None:
    assert 8 <= len(variations) <= 10, variations
    assert all(isinstance(v, str) and v.strip() for v in variations)
    keys = [re.sub(r"\s+", " ", v.lower().strip()) for v in variations]
    assert len(keys) == len(set(keys)), variations
    joined = " ".join(variations).lower()
    assert "bixby://" not in joined
    assert "http://" not in joined
    assert "https://" not in joined
    for v in variations:
        assert not url_leak_reasons(v)


def _has_register_signals(variations: list[str], original: str) -> dict[str, bool]:
    """Heuristic presence checks for required registers (not a production classifier)."""
    lows = [v.lower() for v in variations]
    orig = original.lower().strip()
    formal = any(
        (
            v[:1].isupper()
            and (
                v.endswith(".")
                or v.startswith("The ")
                or v.startswith("One ")
                or "does one" in v.lower()
                or "not visible" in v.lower()
            )
        )
        or (v[:1].isupper() and "cannot" in v.lower())
        for v in variations
    )
    casual = any(
        v == original
        or v.lower() == orig
        or v.startswith("My ")
        or v.startswith("how do i ")
        or "can't" in v.lower()
        for v in variations
    )
    keyword = any(len(v.split()) <= max(3, len(original.split()) - 1) and "why" not in v.lower() and not v.endswith("?") for v in variations[1:])
    frustrated = any(v.startswith("Why") or "frustrating" in v.lower() or "why is this happening" in v.lower() for v in variations)
    typo = any(
        any(t in v.lower() for t in ("phne", "scren", "blak", "batery", "canot", "acess", "gmal", "swtich", "bred", "sourdogh", "disply", "flickrs", "tranfer"))
        or (normalize_query(v) != normalize_query(original) and sum(1 for a, b in zip(v.lower(), orig) if a != b) >= 1 and len(v.split()) == len(original.split()))
        for v in variations
    )
    return {
        "formal": formal,
        "casual": casual,
        "keyword-only": keyword,
        "frustrated": frustrated,
        "typo-inclusive": typo,
    }


def test_short_black_screen_has_8_to_10_variations():
    q = "my phone screen is black"
    variations = generate_query_variations(q)
    _assert_variation_list(variations)
    assert variations[0].lower() == q.lower() or q.lower() in {v.lower() for v in variations}
    signals = _has_register_signals(variations, q)
    for name in _REQUIRED_REGISTERS:
        assert signals[name], f"missing register {name}: {variations}"


def test_multi_issue_preserves_both_issues():
    q = "my phone screen flickers and the battery drains quickly"
    variations = generate_query_variations(q)
    _assert_variation_list(variations)
    for v in variations:
        low = v.lower()
        assert "flicker" in low
        assert "battery" in low or "drain" in low


def test_smart_switch_context_preserved():
    q = "I cannot transfer my phone using Smart Switch"
    variations = generate_query_variations(q)
    _assert_variation_list(variations)
    for v in variations:
        assert "smart" in v.lower() and "switch" in v.lower() or "swtich" in v.lower()


def test_gmail_context_preserved():
    q = "I cannot access my Gmail"
    variations = generate_query_variations(q)
    _assert_variation_list(variations)
    for v in variations:
        assert "gmail" in v.lower() or "gmal" in v.lower()


def test_unsupported_sourdough_no_phone_injection():
    q = "how to bake sourdough bread"
    variations = generate_query_variations(q)
    _assert_variation_list(variations)
    banned = ("samsung", "galaxy", "phone", "tablet", "screen", "display", "battery", "deeplink", "bixby")
    for v in variations:
        low = v.lower()
        for word in banned:
            assert word not in low, v
        assert "sourdough" in low or "sourdogh" in low
        assert "bread" in low or "bred" in low


def test_enrich_query_deterministic_and_bounded():
    q = "my phone screen is black"
    a = enrich_query(q)["query_variations"]
    b = enrich_query(q)["query_variations"]
    assert a == b
    _assert_variation_list(a)


def test_required_registers_present_on_representative_queries():
    queries = [
        "my phone screen is black",
        "my phone screen flickers and the battery drains quickly",
        "I cannot transfer my phone using Smart Switch",
        "I cannot access my Gmail",
        "how to bake sourdough bread",
    ]
    for q in queries:
        variations = generate_query_variations(q)
        _assert_variation_list(variations)
        signals = _has_register_signals(variations, q)
        for name in _REQUIRED_REGISTERS:
            assert signals[name], f"{q!r} missing {name}: {variations}"
