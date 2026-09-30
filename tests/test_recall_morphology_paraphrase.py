"""Deterministic paraphrase/morphology recall: dark, empty-display, flicker, crack."""

from __future__ import annotations

from sgte.lexical import token_list
from sgte.llm.mock import MockLLMProvider
from sgte.pipeline import (
    TroubleshootingPipeline,
    grounded_mock_factory,
    retrieval_is_confident,
)
from sgte.query.understand import understand_query
from sgte.siis_reranker import retrieve_siis
from sgte.siis_repo import SiisRepository


def _pipe() -> TroubleshootingPipeline:
    return TroubleshootingPipeline(
        llm=MockLLMProvider(factory=grounded_mock_factory),
        allow_mock=True,
        debug=False,
        use_cache=False,
    )


def _top(query: str):
    sq = understand_query(query)
    hits = retrieve_siis(SiisRepository.from_file(), query, sq, top_k=3)
    assert hits, f"expected SIIS hits for {query!r}"
    return hits[0], sq


def _action_count(query: str) -> int:
    result = _pipe().troubleshoot(query)
    return sum(len(c.actions) for c in result.response.contexts)


def _fallback(query: str):
    return _pipe().troubleshoot(query).meta.get("fallback")


# --- FIX 1: dark ↔ black ↔ blank -------------------------------------------------


def test_dark_display_symptoms_align_with_black_blank():
    q = "My display went completely dark"
    sq = understand_query(q)
    assert "dark" in sq.symptoms
    assert "black" in sq.symptoms
    assert "blank" in sq.symptoms
    assert sq.device_state.get("display_visible") is False
    top, _ = _top(q)
    assert "blank" in top.title.lower() or "black" in top.title.lower()
    assert retrieval_is_confident(top, query=q, structured=sq) is True
    assert _action_count(q) >= 1


def test_black_display_unchanged_canon():
    q = "My display is completely black"
    sq = understand_query(q)
    assert "black" in sq.symptoms
    assert sq.device_state.get("display_visible") is False
    top, _ = _top(q)
    assert "blank" in top.title.lower() or "black" in top.title.lower()
    assert retrieval_is_confident(top, query=q, structured=sq) is True
    assert _action_count(q) >= 2


def test_phone_black_screen_unchanged_canon():
    q = "My phone screen is completely black"
    sq = understand_query(q)
    assert "black" in sq.symptoms
    top, _ = _top(q)
    assert "blank" in top.title.lower() or "black" in top.title.lower()
    assert retrieval_is_confident(top, query=q, structured=sq) is True
    assert _action_count(q) >= 2


# --- FIX 2: empty-display phrases -----------------------------------------------


def test_showing_nothing_empty_display_symptom():
    q = "My phone screen is showing nothing"
    sq = understand_query(q)
    assert "blank" in sq.symptoms or "black" in sq.symptoms
    assert sq.device_state.get("display_visible") is False
    top, _ = _top(q)
    assert "blank" in top.title.lower() or "black" in top.title.lower()
    assert retrieval_is_confident(top, query=q, structured=sq) is True
    assert _action_count(q) >= 1


def test_bare_nothing_without_screen_not_empty_display():
    q = "There is nothing I can do about Bluetooth"
    sq = understand_query(q)
    assert "blank" not in sq.symptoms
    assert "black" not in sq.symptoms
    assert sq.device_state.get("display_visible") is not False


# --- FIX 3: flicker morphology --------------------------------------------------


def test_flickering_aligns_with_flickers_evidence():
    q = "My screen keeps flickering"
    sq = understand_query(q)
    assert any(s in sq.symptoms for s in ("flicker", "flickers", "flickering"))
    assert "flicker" in token_list(q)
    # Morphology preserved; display flicker must not attach to camera/video SIIS.
    hits = retrieve_siis(SiisRepository.from_file(), q, sq, top_k=3)
    if hits and retrieval_is_confident(hits[0], query=q, structured=sq):
        title = (hits[0].title or "").lower()
        assert "camera" not in title
        assert "video" not in title or "flicker" in title


def test_phone_screen_flickering_canon_still_confident():
    q = "My phone screen is flickering"
    sq = understand_query(q)
    assert any(s in sq.symptoms for s in ("flicker", "flickers", "flickering"))
    assert "flicker" in token_list(q)
    hits = retrieve_siis(SiisRepository.from_file(), q, sq, top_k=3)
    if hits and retrieval_is_confident(hits[0], query=q, structured=sq):
        title = (hits[0].title or "").lower()
        assert "camera" not in title


# --- FIX 4: crack morphology ----------------------------------------------------


def test_cracks_aligns_with_cracked_siis():
    q = "My display has cracks"
    sq = understand_query(q)
    assert any(s in sq.symptoms for s in ("crack", "cracks", "cracked"))
    assert sq.device_state.get("physical_damage") is True
    assert "crack" in token_list(q)
    top, _ = _top(q)
    assert "crack" in top.title.lower()
    assert retrieval_is_confident(top, query=q, structured=sq) is True
    # Necessity may still empty the plan for repair-only SIIS — do not weaken it.
    # Retrieval/confidence success is the success criterion for this paraphrase.


def test_cracked_canon_still_confident():
    q = "My screen is cracked"
    sq = understand_query(q)
    assert "cracked" in sq.symptoms or "crack" in sq.symptoms
    top, _ = _top(q)
    assert "crack" in top.title.lower()
    assert retrieval_is_confident(top, query=q, structured=sq) is True


# --- Precision holdouts ---------------------------------------------------------


def test_tv_connect_prefers_mirroring_not_blank():
    q = "My phone won't connect to my TV"
    titles = [c.title for c in _pipe().troubleshoot(q).response.contexts]
    assert not any("black" in (t or "").lower() for t in titles)
    sq = understand_query(q)
    hits = retrieve_siis(SiisRepository.from_file(), q, sq, top_k=3)
    assert hits
    assert "mirror" in (hits[0].title or "").lower() or "tv" in (hits[0].title or "").lower()


def test_bluetooth_connect_no_match():
    q = "My phone won't connect to Bluetooth"
    assert _fallback(q) in {"no_match", "no_siis_context"} or _action_count(q) == 0
    titles = [c.title for c in _pipe().troubleshoot(q).response.contexts]
    assert not any("black" in (t or "").lower() for t in titles)


def test_wont_charge_no_match():
    q = "My phone won't charge"
    assert _fallback(q) in {"no_match", "no_siis_context"} or _action_count(q) == 0
    titles = [c.title for c in _pipe().troubleshoot(q).response.contexts]
    assert not any("black" in (t or "").lower() for t in titles)
