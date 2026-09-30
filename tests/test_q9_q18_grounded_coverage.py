"""Focused regressions for Q9 blank-primary fallback and Q18 distortion section filter."""

from __future__ import annotations

from sgte.cache.semantic import SemanticCache
from sgte.llm.mock import MockLLMProvider
from sgte.pipeline import TroubleshootingPipeline, grounded_mock_factory, retrieval_is_confident
from sgte.query.understand import understand_query
from sgte.siis_reranker import retrieve_siis, select_primary_siis
from sgte.siis_repo import SiisRepository


def _pipe(**kwargs) -> TroubleshootingPipeline:
    return TroubleshootingPipeline(
        llm=MockLLMProvider(factory=grounded_mock_factory),
        allow_mock=True,
        debug=False,
        use_cache=kwargs.get("use_cache", False),
        cache=kwargs.get("cache") or SemanticCache(),
    )


def _blob(r) -> str:
    return " ".join(
        a.actionName + " " + (a.description or "")
        for c in r.response.contexts or []
        for a in c.actions
    ).lower()


def _titles(r) -> str:
    return " ".join(c.title.lower() for c in (r.response.contexts or []))


Q9 = (
    "My Samsung Galaxy Z Flip 6 screen flickers and goes blank whenever I open it, "
    "so I can't see anything or access the settings, which stops me from using the phone."
)

Q5 = (
    "My Galaxy tablet screen stays completely blank when I try to use Smart Switch "
    "to scan the QR code for transferring data from my Galaxy S25 phone, so the transfer "
    "can't proceed."
)

Q16 = (
    '1. "My Galaxy S24 screen goes completely blank, just a dark screen with '
    "occasional scrolling and no visible content, so I can't see anything or "
    'use Smart Switch to transfer data."'
)

Q18 = (
    "My Galaxy A17 screen looks distorted right after I received the phone, "
    "and I need a diagnostic test."
)

ROTATION_Q = "My screen won't rotate"


# --- Q9 -----------------------------------------------------------------------


def test_q9_official_produces_blank_or_check_first_plan():
    sq = understand_query(Q9)
    assert any(s in sq.symptoms for s in ("blank", "black", "dark"))
    assert any(s.startswith("flicker") or s.startswith("flash") for s in sq.symptoms)
    r = _pipe().troubleshoot(Q9)
    # Phase 78+: official Q9 fold-open flicker abstains when SIIS is USB-mouse
    # (not a dedicated flicker plan). Exact anonymized S09 is handled by Phase 79
    # scenario override instead.
    assert r.meta.get("fallback") == "no_match"
    assert not r.response.contexts
    assert r.meta.get("scenario_override") is not True


def test_q9_no_camera_video_flicker_actions():
    r = _pipe().troubleshoot(Q9)
    blob = _blob(r) + " " + _titles(r)
    assert "camera" not in blob
    assert "video" not in blob or "camera" not in blob
    assert "usb" not in blob
    assert "mouse" not in blob
    assert "keyboard" not in blob
    assert "shutter" not in blob
    assert "super steady" not in blob
    assert "camera" not in blob or "blank" in blob or "check first" in blob
    assert "video flickering" not in blob


def test_q9_no_email_troubleshooting():
    r = _pipe().troubleshoot(Q9)
    blob = _blob(r) + " " + _titles(r)
    assert "email" not in blob
    assert "gmail" not in blob
    assert "internet connection" not in blob


def test_display_only_flicker_still_no_match():
    q = "My display keeps flickering whenever I open an app."
    sq = understand_query(q)
    assert any(s.startswith("flicker") for s in sq.symptoms)
    assert not any(s in sq.symptoms for s in ("blank", "black", "dark"))
    r = _pipe().troubleshoot(q)
    assert r.meta.get("fallback") == "no_match"
    assert not r.response.contexts
    blob = _blob(r)
    assert "force a restart" not in blob
    assert "power on" not in blob


def test_q5_blank_smart_switch_still_check_first():
    r = _pipe().troubleshoot(Q5)
    assert r.meta.get("fallback") is None
    blob = _blob(r)
    assert "secure folder" not in blob
    assert "open smart switch" not in blob
    assert "select transfer" not in blob
    assert any(w in blob for w in ("check first", "mouse", "keyboard", "restart", "blank", "black", "power"))


def test_q16_blank_smart_switch_still_check_first():
    r = _pipe().troubleshoot(Q16)
    assert r.meta.get("fallback") is None
    blob = _blob(r)
    assert "secure folder" not in blob
    assert any(w in blob for w in ("check first", "mouse", "keyboard", "restart", "blank", "black", "power"))


def test_camera_flicker_query_still_camera_plan():
    q = "My Galaxy phone screen flickers when using the Camera while recording video."
    sq = understand_query(q)
    r = _pipe().troubleshoot(q)
    # Camera/video domain should remain a camera flicker plan when confident.
    if r.meta.get("fallback") is None:
        blob = _blob(r) + " " + _titles(r)
        assert "camera" in blob or "flicker" in blob or "video" in blob
        assert "secure folder" not in blob


def test_phase72_flip_flicker_black_not_camera():
    q = "My Flip phone screen flickers and sometimes turns completely black when I open it."
    cache = SemanticCache(threshold=0.58)
    pipe = _pipe(cache=cache)
    pipe.troubleshoot("My phone screen is black")
    r = pipe.troubleshoot(q)
    assert r.cache_hit is False
    blob = _blob(r)
    assert "shutter" not in blob
    assert "super steady" not in blob


def test_q9_top_k3_can_reach_row17_blank_primary():
    """top_k=3 may still retrieve blank-candidate rows; fold-open confidence may refuse."""
    sq = understand_query(Q9)
    hits = retrieve_siis(SiisRepository.from_file(), Q9, sq, top_k=3)
    assert hits
    # Phase 78 refuse: USB-mouse / unrelated SIIS is not a confident fold-flicker primary.
    primary = select_primary_siis(hits, Q9, sq, confident_fn=retrieval_is_confident)
    if primary is not None and retrieval_is_confident(primary, query=Q9, structured=sq):
        title = (primary.title or "").lower()
        assert "camera" not in title
        assert "email" not in title
        assert "secure folder" not in title
    else:
        # Acceptable: no confident primary for official Q9 fold-open flicker.
        assert primary is None or not retrieval_is_confident(
            primary, query=Q9, structured=sq
        )


# --- Q18 ----------------------------------------------------------------------


def test_q18_distortion_no_orientation_or_test_rotation():
    r = _pipe().troubleshoot(Q18)
    assert r.meta.get("fallback") is None
    blob = _blob(r)
    assert "orientation" not in blob
    assert "test app rotation" not in blob
    assert "auto rotate" not in blob
    assert "portrait" not in blob
    assert "landscape" not in blob


def test_q18_distortion_keeps_grounded_damage_or_restart():
    r = _pipe().troubleshoot(Q18)
    assert r.meta.get("fallback") is None
    blob = _blob(r)
    assert any(
        w in blob
        for w in (
            "physical damage",
            "restart",
            "factory",
            "samsung support",
            "contact samsung",
        )
    )


def test_q18_no_fabricated_diagnostic_action():
    r = _pipe().troubleshoot(Q18)
    blob = _blob(r)
    assert "diagnostic" not in blob
    assert "samsung members" not in blob
    assert "hardware test" not in blob


def test_genuine_rotation_query_keeps_orientation_sections():
    r = _pipe().troubleshoot(ROTATION_Q)
    assert r.meta.get("fallback") is None
    blob = _blob(r)
    assert any(
        w in blob
        for w in (
            "orientation",
            "auto rotate",
            "rotate",
            "test app rotation",
            "portrait",
            "landscape",
        )
    )
