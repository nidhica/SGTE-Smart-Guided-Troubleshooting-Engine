"""Negated 'turn on' must not be treated as an enable operation."""

from __future__ import annotations

from sgte.intent import extract_intent
from sgte.llm.mock import MockLLMProvider
from sgte.pipeline import TroubleshootingPipeline, grounded_mock_factory
from sgte.polarity import polarity
from sgte.query.understand import understand_query


def _ops(query: str):
    return understand_query(query).operations


def test_wont_turn_on_not_enable():
    q = "My phone won't turn on"
    assert polarity(q) != "enable"
    assert "enable" not in _ops(q)
    assert extract_intent(q).operation != "enable"


def test_doesnt_turn_on_not_enable():
    q = "My phone doesn't turn on"
    assert polarity(q) != "enable"
    assert "enable" not in _ops(q)


def test_cant_turn_on_not_enable():
    q = "My phone can't turn on"
    assert polarity(q) != "enable"
    assert "enable" not in _ops(q)


def test_not_turning_on_not_enable():
    q = "My screen is not turning on"
    assert polarity(q) != "enable"
    assert "enable" not in _ops(q)


def test_unable_to_turn_on_not_enable():
    q = "My phone is unable to turn on"
    assert polarity(q) != "enable"
    assert "enable" not in _ops(q)


def test_turn_on_display_is_enable():
    q = "Turn on my display"
    assert polarity(q) == "enable"
    assert _ops(q) == ("enable",)


def test_how_do_i_turn_on_display_is_enable():
    q = "How do I turn on the display?"
    assert polarity(q) == "enable"
    assert _ops(q) == ("enable",)


def test_enable_wifi_is_enable():
    q = "Enable Wi-Fi"
    assert polarity(q) == "enable"
    assert _ops(q) == ("enable",)


def test_how_do_i_enable_wifi_is_enable():
    q = "How do I enable Wi-Fi?"
    assert polarity(q) == "enable"
    assert _ops(q) == ("enable",)


def test_enable_and_disable_stays_non_enable_only():
    q = "Enable Wi-Fi and disable Bluetooth"
    # Existing multi-op behavior: no single enable-only commitment.
    assert polarity(q) is None
    assert extract_intent(q).operation == "unknown"
    assert "enable" not in _ops(q) or _ops(q) != ("enable",)
    assert _ops(q) != ("enable",)


def test_black_screen_wont_turn_on_not_enable_display():
    q = "My Samsung phone screen suddenly went completely black and won't turn on"
    sq = understand_query(q)
    assert "enable" not in sq.operations
    assert sq.intent != "enable_display"
    assert sq.target == "display"
    assert "black" in sq.symptoms
    assert sq.intent == "display_troubleshooting"


def test_black_screen_paraphrase_keeps_multi_actions():
    pipe = TroubleshootingPipeline(
        llm=MockLLMProvider(factory=grounded_mock_factory),
        allow_mock=True,
        debug=False,
        use_cache=False,
    )
    short = pipe.troubleshoot("My phone screen is completely black")
    paraphrase = pipe.troubleshoot(
        "My Samsung phone screen suddenly went completely black and won't turn on"
    )
    assert short.fallback is None
    assert paraphrase.fallback is None
    short_n = sum(len(c.actions) for c in short.response.contexts)
    para_n = sum(len(c.actions) for c in paraphrase.response.contexts)
    assert short_n >= 3
    # Must not collapse to restart-only due to false enable polarity.
    assert para_n >= 3
    names = {a.actionName for c in paraphrase.response.contexts for a in c.actions}
    assert "Force a Restart" in names
    assert "Attempt to Power On" in names or "Check for Physical Damage and Liquid Exposure" in names


def test_wont_turn_on_with_disabled_wifi_not_generic_enable():
    q = "My phone won't turn on and Wi-Fi is disabled"
    assert polarity(q) != "enable"
    assert _ops(q) != ("enable",)
