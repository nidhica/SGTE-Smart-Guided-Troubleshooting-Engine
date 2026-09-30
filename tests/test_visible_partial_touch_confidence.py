"""Visible display + partial-area touch: narrow confidence bypass for row_21."""

from __future__ import annotations

from sgte.cache.semantic import SemanticCache
from sgte.llm.mock import MockLLMProvider
from sgte.pipeline import TroubleshootingPipeline, grounded_mock_factory, retrieval_is_confident
from sgte.query.understand import understand_query
from sgte.siis_reranker import retrieve_siis
from sgte.siis_repo import SiisRepository


def _pipe() -> TroubleshootingPipeline:
    return TroubleshootingPipeline(
        llm=MockLLMProvider(factory=grounded_mock_factory),
        allow_mock=True,
        debug=False,
        use_cache=False,
        cache=SemanticCache(),
    )


def _top(query: str):
    sq = understand_query(query)
    hits = retrieve_siis(SiisRepository.from_file(), query, sq, top_k=3)
    assert hits
    return hits[0], sq


def test_visible_partial_touch_uses_touchscreen_plan():
    q = "My screen is visible but some areas don't respond to touch."
    sq = understand_query(q)
    assert sq.target == "touchscreen"
    assert sq.device_state.get("display_visible") is True
    assert sq.device_state.get("touch_responsive") is False
    top, _ = _top(q)
    assert "touchscreen" in (top.title or "").lower()
    assert float(top.score_breakdown.get("lexical_score", top.score)) < 0.22
    assert retrieval_is_confident(top, query=q, structured=sq) is True
    r = _pipe().troubleshoot(q)
    assert r.meta.get("fallback") is None
    assert r.response.contexts
    titles = " ".join(c.title.lower() for c in r.response.contexts)
    assert "touch" in titles
    blob = " ".join(
        a.actionName.lower()
        for c in r.response.contexts
        for a in c.actions
    )
    assert any(
        w in blob
        for w in ("restart", "safe mode", "touch sensitivity", "gesture", "factors")
    )


def test_areas_dont_respond_still_touchscreen_plan():
    q = "Some areas of my screen don't respond when I touch them."
    top, sq = _top(q)
    assert sq.target == "touchscreen"
    assert "touchscreen" in (top.title or "").lower()
    assert retrieval_is_confident(top, query=q, structured=sq) is True
    r = _pipe().troubleshoot(q)
    assert r.meta.get("fallback") is None
    assert r.response.contexts


def test_bare_touchscreen_not_responding_remains_no_match():
    q = "My touchscreen is not responding"
    top, sq = _top(q)
    assert "touch" in (top.title or "").lower()
    assert retrieval_is_confident(top, query=q, structured=sq) is False
    r = _pipe().troubleshoot(q)
    assert r.meta.get("fallback") == "no_match"
    assert not r.response.contexts


def test_cracked_and_touch_does_not_use_partial_touch_bypass():
    q = "My screen is cracked and touch doesn't work in some areas."
    sq = understand_query(q)
    hits = retrieve_siis(SiisRepository.from_file(), q, sq, top_k=3)
    assert hits
    # Bypass requires touchscreen title; cracked article must not become confident via it.
    for h in hits:
        if "crack" in (h.title or "").lower():
            assert retrieval_is_confident(h, query=q, structured=sq) is False or (
                sq.target != "touchscreen"
                or sq.device_state.get("display_visible") is not True
            )
        if "touchscreen" in (h.title or "").lower() and sq.target != "touchscreen":
            assert retrieval_is_confident(h, query=q, structured=sq) is False
    r = _pipe().troubleshoot(q)
    if r.meta.get("fallback") is None:
        blob = " ".join(
            c.title.lower() + " " + " ".join(a.actionName.lower() for a in c.actions)
            for c in r.response.contexts
        )
        # Prefer repair/crack family when cracked, not a bypass-only touchscreen plan.
        assert "crack" in blob or "repair" in blob or "bleed" in blob or "premium" in blob


def test_camera_video_flicker_unchanged():
    q = "My camera video is flickering."
    r = _pipe().troubleshoot(q)
    assert r.meta.get("fallback") is None
    titles = [c.title.lower() for c in r.response.contexts]
    assert any("flicker" in t or "video" in t or "camera" in t for t in titles)


def test_blank_black_display_unchanged():
    q = "My phone screen is completely black."
    top, sq = _top(q)
    assert any(w in (top.title or "").lower() for w in ("blank", "black"))
    assert retrieval_is_confident(top, query=q, structured=sq) is True
    r = _pipe().troubleshoot(q)
    assert r.meta.get("fallback") is None
    assert r.response.contexts
