"""Official Theme 2 output-contract checks for Goal.title / Goal.goal / Action.description."""

from __future__ import annotations

import re

from sgte.builder import format_action_description, format_goal_statement, format_goal_title
from sgte.extractor import CandidateAction, CandidateStep
from sgte.llm.mock import MockLLMProvider
from sgte.pipeline import TroubleshootingPipeline, grounded_mock_factory
from sgte.query.understand import understand_query


def _pipe() -> TroubleshootingPipeline:
    return TroubleshootingPipeline(
        llm=MockLLMProvider(factory=grounded_mock_factory),
        allow_mock=True,
        debug=False,
    )


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[A-Za-z0-9']+", text)]


def _is_sentence_case(title: str) -> bool:
    words = title.split()
    if not words:
        return False
    if not words[0][:1].isupper():
        return False
    # Reject ALL-CAPS titles and full Title Case of every word (except known proper nouns).
    if title.isupper() and len(title) > 3:
        return False
    proper = {"gmail", "smart", "switch", "bixby", "qr", "usb", "apps", "edge"}
    titled = 0
    for w in words[1:]:
        if w[:1].isupper() and w.lower() not in proper and w != "Switch":
            titled += 1
    return titled == 0 or (len(words) == 2 and words[0] == "Smart" and words[1] == "Switch")


def test_goal_title_is_two_or_three_words_sentence_case():
    cases = [
        ("my phone screen is completely black", "Black screen"),
        ("My S22 touch inputs are delayed and laggy", "Touchscreen lag"),
        ("my battery drains very quickly", "Battery drain"),
        ("screen goes black when opening Gmail", "Gmail display"),
        ("The screen is completely cracked and I can't use the device", "Cracked screen"),
        ("disable the floating circle on my screen", "Floating shortcut"),
        ("screen is blank while trying Smart Switch", "Black screen"),
    ]
    for query, expected in cases:
        sq = understand_query(query)
        title = format_goal_title(query=query, structured=sq)
        words = title.split()
        assert len(words) in {2, 3}, f"{query!r} -> {title!r}"
        assert _is_sentence_case(title), title
        assert title == expected, f"{query!r}: got {title!r}, want {expected!r}"


def test_goal_statement_matches_required_syntax():
    sq = understand_query("my phone screen is completely black")
    title = format_goal_title(query=sq.original, structured=sq)
    goal = format_goal_statement(title, sq)
    assert goal.startswith("Follow these steps to perform this ")
    assert goal.endswith(" Troubleshooting") or goal.endswith(" Configuration")
    assert re.match(
        r"^Follow these steps to perform this .+ (Troubleshooting|Configuration)$",
        goal,
    )


def test_configuration_kind_for_enable_disable_intent():
    sq = understand_query("disable the floating circle on my screen")
    title = format_goal_title(query=sq.original, structured=sq)
    goal = format_goal_statement(title, sq)
    assert goal.endswith(" Configuration")
    assert "Floating Shortcut" in goal or "Floating shortcut" in goal.replace("Shortcut", "shortcut")


def test_action_description_starts_with_it_will_and_has_5_to_7_words():
    samples = [
        CandidateAction(
            heading="Force a Restart",
            source_row_id="row_2",
            source_section="Force a Restart",
            evidence_text="Force a Restart by holding the keys.",
            steps=[CandidateStep("Force a Restart by holding the keys.", "row_2", "Force a Restart", "Force a Restart")],
            body="Force a Restart by holding the keys.",
        ),
        CandidateAction(
            heading="Check for Physical Damage and Liquid Exposure",
            source_row_id="row_2",
            source_section="Check for Physical Damage",
            evidence_text="Check for Physical Damage and Liquid Exposure.",
            steps=[CandidateStep("Check for Physical Damage and Liquid Exposure.", "row_2", None, "Check")],
            body="Check for Physical Damage and Liquid Exposure.",
        ),
        CandidateAction(
            heading="Remove shortcuts from Apps Edge",
            source_row_id="row_12",
            source_section="Remove shortcuts from Apps Edge",
            evidence_text="Remove shortcuts from Apps Edge.",
            steps=[CandidateStep("Remove shortcuts from Apps Edge.", "row_12", None, "Remove")],
            body="Remove shortcuts from Apps Edge.",
        ),
    ]
    for action in samples:
        desc = format_action_description(action)
        assert desc.startswith("It will "), desc
        n = len(_words(desc))
        assert 5 <= n <= 7, f"{desc!r} has {n} words"


def test_action_description_preserves_action_meaning():
    restart = format_action_description(
        CandidateAction(
            heading="Force a Restart",
            source_row_id="row_2",
            source_section="Force a Restart",
            evidence_text="Force a Restart",
            steps=[CandidateStep("Force a Restart", "row_2", None, "Force a Restart")],
            body="Force a Restart",
        )
    )
    assert "restart" in restart.lower()
    assert restart.startswith("It will ")

    remove = format_action_description(
        CandidateAction(
            heading="Remove shortcuts from Apps Edge",
            source_row_id="row_12",
            source_section="Remove shortcuts from Apps Edge",
            evidence_text="Remove shortcuts from Apps Edge",
            steps=[CandidateStep("Remove shortcuts from Apps Edge", "row_12", None, "Remove")],
            body="Remove shortcuts from Apps Edge",
        )
    )
    assert "remove" in remove.lower()
    assert "shortcut" in remove.lower() or "apps" in remove.lower() or "edge" in remove.lower()


def test_pipeline_output_contract_on_matched_query():
    result = _pipe().troubleshoot("My phone screen is black")
    assert result.response.contexts
    goal = result.response.contexts[0]
    title_words = goal.title.split()
    assert len(title_words) in {2, 3}
    assert _is_sentence_case(goal.title)
    assert goal.goal.startswith("Follow these steps to perform this ")
    assert goal.goal.endswith(" Troubleshooting") or goal.goal.endswith(" Configuration")
    for action in goal.actions:
        assert action.description.startswith("It will ")
        n = len(_words(action.description))
        assert 5 <= n <= 7, action.description


def test_unsupported_query_still_no_match():
    result = _pipe().troubleshoot("How do I bake sourdough bread in a home oven")
    assert result.response.model_dump() == {"contexts": []}
    assert result.matched is False


def test_physical_damage_and_powers_on_still_recorded():
    cracked = understand_query("The screen is completely cracked and I can't use the device")
    assert cracked.device_state.get("physical_damage") is True
    powers = understand_query("My S24 Ultra screen is black but the phone powers on and rings")
    assert powers.device_state.get("phone_powers_on") is True
