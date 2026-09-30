"""Confidence-gate head-evidence hardening. Precision/safety only."""

from __future__ import annotations

from sgte.pipeline import retrieval_is_confident
from sgte.query.understand import understand_query
from sgte.siis_reranker import retrieve_siis
from sgte.siis_repo import SiisRepository


def _top(query: str):
    sq = understand_query(query)
    hits = retrieve_siis(SiisRepository.from_file(), query, sq, top_k=3)
    assert hits, f"expected at least one SIIS hit for {query!r}"
    return hits[0], sq


def test_black_screen_remains_confident():
    query = "My phone screen is completely black"
    top, sq = _top(query)
    assert "blank" in top.title.lower() or "black" in top.title.lower()
    assert retrieval_is_confident(top, query=query, structured=sq) is True


def test_cracked_screen_remains_confident():
    query = "My screen is cracked"
    top, sq = _top(query)
    assert "crack" in top.title.lower()
    assert retrieval_is_confident(top, query=query, structured=sq) is True


def test_battery_drain_blank_display_not_confident():
    query = "My phone battery is draining quickly"
    top, sq = _top(query)
    assert "blank" in top.title.lower() or "black" in top.title.lower()
    assert float(top.score_breakdown.get("lexical_score", top.score)) >= 0.22
    assert retrieval_is_confident(top, query=query, structured=sq) is False


def test_brightness_mirroring_not_confident():
    query = "The screen brightness keeps changing"
    top, sq = _top(query)
    assert "mirror" in top.title.lower()
    assert float(top.score_breakdown.get("lexical_score", top.score)) >= 0.22
    assert retrieval_is_confident(top, query=query, structured=sq) is False


def test_touchscreen_not_responding_still_non_confident():
    query = "My touchscreen is not responding"
    top, sq = _top(query)
    assert "touch" in top.title.lower()
    # Pre-existing: lexical below gate; must not become confident.
    assert retrieval_is_confident(top, query=query, structured=sq) is False
