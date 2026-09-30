"""Lexical contraction / short-entity / confidence precision regressions."""

from __future__ import annotations

from sgte.lexical import expand_contractions, normalize, token_list
from sgte.llm.mock import MockLLMProvider
from sgte.pipeline import (
    TroubleshootingPipeline,
    distinctive_issue_tokens,
    grounded_mock_factory,
    retrieval_is_confident,
)
from sgte.polarity import polarity
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


def _plan_titles(query: str) -> list[str]:
    result = _pipe().troubleshoot(query)
    return [c.title for c in result.response.contexts]


def _action_count(query: str) -> int:
    result = _pipe().troubleshoot(query)
    return sum(len(c.actions) for c in result.response.contexts)


# --- Part 1: contractions -------------------------------------------------


def test_wont_does_not_produce_won_token():
    assert "won" not in token_list("My phone won't connect to my TV")
    assert "won" not in distinctive_issue_tokens("My phone won't connect to my TV")
    assert "won" not in normalize("won't turn on").split()


def test_doesnt_does_not_produce_doesn_token():
    toks = token_list("My phone doesn't turn on")
    assert "doesn" not in toks
    assert "turn" in toks


def test_contraction_expansion_forms():
    assert "will not" in expand_contractions("won't").lower()
    for raw, needle in [
        ("can't", "cannot"),
        ("doesn't", "does not"),
        ("isn't", "is not"),
        ("aren't", "are not"),
        ("don't", "do not"),
        ("didn't", "did not"),
        ("couldn't", "could not"),
        ("wouldn't", "would not"),
        ("shouldn't", "should not"),
    ]:
        assert needle in expand_contractions(raw).lower()


# --- Part 2: short entities -----------------------------------------------


def test_tv_uppercase_acronym_preserved():
    toks = token_list("My phone won't connect to my TV")
    assert "tv" in toks
    assert "to" not in toks
    assert "on" not in toks


def test_wifi_hyphen_and_compact():
    assert "wifi" in token_list("My phone won't connect to Wi-Fi")
    assert "wifi" in token_list("Enable WiFi")
    assert "wi" not in token_list("Wi-Fi")
    assert "fi" not in token_list("Wi-Fi")


def test_bluetooth_unchanged():
    assert "bluetooth" in token_list("My phone won't connect to Bluetooth")


def test_stopwords_not_promoted_as_short_tokens():
    toks = token_list("Turn ON the display TO fix it IN Settings OF the phone")
    assert "to" not in toks
    assert "on" not in toks
    assert "in" not in toks
    assert "of" not in toks


# --- Part 3 / A–L behavior ------------------------------------------------


def test_a_tv_connect_not_black_screen_plan():
    q = "My phone won't connect to my TV"
    assert "won" not in distinctive_issue_tokens(q)
    assert "tv" in distinctive_issue_tokens(q)
    assert "connect" in distinctive_issue_tokens(q)
    titles = _plan_titles(q)
    assert not any("black" in (t or "").lower() for t in titles)
    sq = understand_query(q)
    hits = retrieve_siis(SiisRepository.from_file(), q, sq, top_k=3)
    if hits:
        assert retrieval_is_confident(hits[0], query=q, structured=sq) is False or (
            "mirror" in (hits[0].title or "").lower() or "tv" in (hits[0].title or "").lower()
        )


def test_b_wont_turn_on_not_enable_and_not_won():
    q = "My phone won't turn on"
    assert polarity(q) != "enable"
    assert "enable" not in understand_query(q).operations
    assert "won" not in distinctive_issue_tokens(q)
    assert "turn" in distinctive_issue_tokens(q)


def test_c_wont_charge_not_blank_via_won():
    q = "My phone won't charge"
    assert "won" not in distinctive_issue_tokens(q)
    assert "charge" in distinctive_issue_tokens(q)
    sq = understand_query(q)
    hits = retrieve_siis(SiisRepository.from_file(), q, sq, top_k=1)
    if hits and "blank" in (hits[0].title or "").lower():
        assert retrieval_is_confident(hits[0], query=q, structured=sq) is False


def test_d_wont_rotate_prefers_rotation_when_confident():
    q = "My screen won't rotate"
    assert "won" not in distinctive_issue_tokens(q)
    assert "rotate" in distinctive_issue_tokens(q)
    sq = understand_query(q)
    hits = retrieve_siis(SiisRepository.from_file(), q, sq, top_k=3)
    assert hits
    # Rotation article should beat blank/black for this wording after contraction fix.
    assert "rotate" in (hits[0].title or "").lower()
    assert retrieval_is_confident(hits[0], query=q, structured=sq) is True


def test_e_bluetooth_connect_not_via_won():
    q = "My phone won't connect to Bluetooth"
    assert "won" not in distinctive_issue_tokens(q)
    assert "bluetooth" in distinctive_issue_tokens(q)
    titles = _plan_titles(q)
    assert not any("black" in (t or "").lower() for t in titles)


def test_f_wifi_identity_preserved():
    q = "My phone won't connect to Wi-Fi"
    core = distinctive_issue_tokens(q)
    assert "won" not in core
    assert "wifi" in core
    titles = _plan_titles(q)
    assert not any("black" in (t or "").lower() for t in titles)


def test_g_doesnt_turn_on_no_doesn():
    q = "My phone doesn't turn on"
    assert "doesn" not in token_list(q)
    assert "doesn" not in distinctive_issue_tokens(q)
    assert polarity(q) != "enable"


def test_h_cant_connect_tv_preserves_channel():
    q = "My phone can't connect to my TV"
    core = distinctive_issue_tokens(q)
    assert "tv" in core
    assert "connect" in core
    assert "won" not in core


def test_i_black_screen_still_works():
    q = "My phone screen is completely black"
    assert _action_count(q) >= 2
    sq = understand_query(q)
    hits = retrieve_siis(SiisRepository.from_file(), q, sq, top_k=1)
    assert hits
    assert retrieval_is_confident(hits[0], query=q, structured=sq) is True


def test_j_cracked_still_confident_retrieval():
    q = "My screen is cracked"
    sq = understand_query(q)
    hits = retrieve_siis(SiisRepository.from_file(), q, sq, top_k=1)
    assert hits
    assert "crack" in (hits[0].title or "").lower()
    assert retrieval_is_confident(hits[0], query=q, structured=sq) is True


def test_k_wont_turn_on_and_wifi_disabled_not_enable_only():
    q = "My phone won't turn on and Wi-Fi is disabled"
    sq = understand_query(q)
    assert sq.operations != ("enable",)
    assert polarity(q) != "enable"


def test_l_genuine_enable_requests():
    for q in (
        "Turn on my display",
        "How do I turn on the display?",
        "Enable Wi-Fi",
        "How do I enable Wi-Fi?",
    ):
        assert polarity(q) == "enable"
        assert understand_query(q).operations == ("enable",)
