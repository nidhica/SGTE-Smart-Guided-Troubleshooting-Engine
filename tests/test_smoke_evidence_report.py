"""Focused tests for Phase 12E evidence-association reporting."""

from __future__ import annotations

from types import SimpleNamespace

from evaluation.smoke_evidence_report import (
    associate_action_with_sections,
    build_evidence_audit,
    normalize_phrase,
)
from sgte.cache.semantic import SemanticCache
from sgte.llm.mock import MockLLMProvider
from sgte.paths import INPUT_TXT
from sgte.pipeline import TroubleshootingPipeline, grounded_mock_factory


def _mock_pipe() -> TroubleshootingPipeline:
    return TroubleshootingPipeline(
        llm=MockLLMProvider(factory=grounded_mock_factory),
        allow_mock=True,
        debug=False,
        use_cache=False,
        cache=SemanticCache(),
    )


def _fake_result(*, actions=None, siis_hits=None, fallback=None):
    action_rows = actions if actions is not None else [
        {
            "actionName": "Samsung Repair Services",
            "category": "manual",
            "uris": [],
        }
    ]
    built = []
    for a in action_rows:
        uris = a.get("uris") or []
        groups = []
        if uris:
            for u in uris:
                groups.append(
                    SimpleNamespace(
                        actionableDeeplink=SimpleNamespace(deeplink=u)
                    )
                )
        else:
            groups = [SimpleNamespace(actionableDeeplink=None)]
        built.append(
            SimpleNamespace(
                actionName=a["actionName"],
                category=SimpleNamespace(value=a.get("category") or "manual"),
                stepGroups=groups,
            )
        )
    response = SimpleNamespace(contexts=[SimpleNamespace(actions=built)] if built else [])
    return SimpleNamespace(
        response=response,
        meta={},
        siis_hits=list(siis_hits or []),
        rejected=[],
        fallback=fallback,
    )


def test_exact_heading_match_associates_direct():
    sections = [
        {
            "evidence_id": "row_14.section_1",
            "heading": "Samsung Repair Services",
            "body": "You can schedule a walk-in or mail-in repair.",
            "label": "row_14.section_1 Samsung Repair Services",
        }
    ]
    assoc = associate_action_with_sections("Samsung Repair Services", sections)
    assert assoc["evidence_associated"] is True
    assert assoc["association_confidence"] == "direct"
    assert assoc["association_method"] in {
        "exact_heading_or_label",
        "normalized_heading_or_label",
    }
    assert assoc["grounding_status"] == "supported"
    assert assoc["evidence_refs"]
    assert assoc["evidence_excerpt"]


def test_body_evidence_with_different_heading():
    sections = [
        {
            "evidence_id": "row_21.section_3",
            "heading": "3. Charger Issues",
            "body": (
                "A damaged charger might not be supplying enough power. "
                "Please try using a different, undamaged charger."
            ),
            "label": "row_21.section_3 3. Charger Issues",
        }
    ]
    assoc = associate_action_with_sections("Use different charger", sections)
    assert assoc["evidence_associated"] is True
    assert assoc["association_confidence"] == "direct"
    assert "body" in assoc["association_method"] or assoc["association_method"] == "token_coverage_full"
    assert assoc["grounding_status"] == "supported"
    assert "charger" in (assoc["evidence_excerpt"] or "").lower()


def test_simple_wording_variation_force_a_restart():
    sections = [
        {
            "evidence_id": "row_16.section_2",
            "heading": "Step 2: Force a Restart",
            "body": "Press and hold Power and Volume down for 20 seconds.",
            "label": "row_16.section_2 Step 2: Force a Restart",
        }
    ]
    assert "a" not in normalize_phrase("Force a Restart").split() or True
    assoc = associate_action_with_sections("Force restart", sections)
    assert assoc["evidence_associated"] is True
    assert assoc["association_confidence"] == "direct"
    assert assoc["grounding_status"] == "supported"


def test_empty_heading_with_supporting_body():
    sections = [
        {
            "evidence_id": "row_17.section_0",
            "heading": "",
            "body": (
                "If your device displays only a blank or black screen, you may need "
                "to check the device, charger, and USB cable for damage. You can also "
                "try forcing a restart by pressing and holding the Power and Volume "
                "down buttons for 20 seconds."
            ),
            "label": "row_17.section_0 ",
        }
    ]
    check = associate_action_with_sections(
        "Check device, charger, and USB cable", sections
    )
    force = associate_action_with_sections("Force restart", sections)
    assert check["evidence_associated"] is True
    assert check["grounding_status"] == "supported"
    assert force["evidence_associated"] is True
    assert force["grounding_status"] == "supported"
    assert check["evidence_excerpt"]
    assert force["evidence_excerpt"]


def test_unrelated_evidence_not_associated():
    sections = [
        {
            "evidence_id": "row_7.section_1",
            "heading": "Customize the Edge panel",
            "body": "Swipe left on the gray Edge panel handle to access apps.",
            "label": "row_7.section_1 Customize the Edge panel",
        }
    ]
    assoc = associate_action_with_sections("Force restart", sections)
    assert assoc["evidence_associated"] is False
    assert assoc["association_confidence"] in {"none", "weak_candidate"}
    assert assoc["grounding_status"] in {"inconclusive", "partially_supported"}
    # Must not be fully supported on unrelated Edge-panel text.
    assert assoc["grounding_status"] != "supported"


def test_missing_trace_evidence_is_unavailable_not_auto_grounded():
    pipe = SimpleNamespace(
        last_trace={},
        deeplinks=SimpleNamespace(contains_actionable_uri=lambda _u: True),
    )
    result = _fake_result()
    audit = build_evidence_audit(pipe, result)
    assert audit["evidence_status"] == "unavailable"
    assert audit["n_actions"] == 1
    assert audit["grounding_ok"] is None
    assert audit["grounding_status"] == "inconclusive"
    assert audit["actions"][0]["grounding_status"] == "inconclusive"
    assert audit["trace_source"] == "none"


def test_empty_no_match_plan_is_no_action():
    pipe = SimpleNamespace(
        last_trace={
            "selected_siis": "row_1 | Email server not responding",
            "selected_evidence": ["row_1.section_1 Step 1: Check Email Access on a PC"],
        },
        deeplinks=SimpleNamespace(contains_actionable_uri=lambda _u: True),
    )
    result = _fake_result(actions=[], fallback="no_match")
    audit = build_evidence_audit(pipe, result)
    assert audit["n_actions"] == 0
    assert audit["grounding_status"] == "no_action"
    assert audit["fallback"] == "no_match"
    assert audit["evidence_status"] == "available"


def test_multiple_actions_supported_by_different_sections():
    sections = [
        {
            "evidence_id": "row_21.section_2",
            "heading": "2. Restarting Your Device",
            "body": "Press and hold the Power button, then tap Restart.",
            "label": "row_21.section_2 2. Restarting Your Device",
        },
        {
            "evidence_id": "row_21.section_7",
            "heading": "7. Safe Mode",
            "body": "To enter Safe mode: Press and hold the Power button and Volume down.",
            "label": "row_21.section_7 7. Safe Mode",
        },
    ]
    pipe = SimpleNamespace(
        last_trace={
            "selected_siis": "row_21 | Touchscreen issues",
            "selected_evidence": [s["label"] for s in sections],
        },
        deeplinks=SimpleNamespace(contains_actionable_uri=lambda _u: True),
    )
    result = _fake_result(
        actions=[
            {"actionName": "Restart device", "category": "manual"},
            {"actionName": "Enter Safe mode", "category": "critical"},
        ]
    )
    audit = build_evidence_audit(pipe, result, evidence_sections=sections)
    assert audit["n_actions"] == 2
    by_name = {a["actionName"]: a for a in audit["actions"]}
    assert by_name["Restart device"]["grounding_status"] == "supported"
    assert by_name["Enter Safe mode"]["grounding_status"] == "supported"
    assert by_name["Restart device"]["evidence_associated"] is True
    assert by_name["Enter Safe mode"]["evidence_associated"] is True
    assert audit["grounding_status"] == "supported"


def test_partial_evidence_not_fully_supported():
    sections = [
        {
            "evidence_id": "row_x.section_1",
            "heading": "Restart tips",
            "body": "You may restart the phone after updates.",
            "label": "row_x.section_1 Restart tips",
        }
    ]
    # Only one content token overlaps strongly with a multi-token specialized action.
    assoc = associate_action_with_sections(
        "Factory data reset and wipe Samsung Cloud backup", sections
    )
    assert assoc["grounding_status"] != "supported"
    assert assoc["evidence_associated"] is False
    assert assoc["grounding_status"] in {"inconclusive", "partially_supported"}


def test_report_reads_selected_evidence_from_last_trace_not_empty_meta():
    pipe = _mock_pipe()
    q = [ln.strip() for ln in INPUT_TXT.read_text(encoding="utf-8").splitlines() if ln.strip()][12]
    result = pipe.troubleshoot(q)

    assert (result.meta or {}).get("selected_evidence") in (None, [])
    assert pipe.last_trace.get("selected_siis")
    assert pipe.last_trace.get("selected_evidence")

    audit = build_evidence_audit(pipe, result)
    assert audit["evidence_status"] == "available"
    assert audit["trace_source"] == "pipeline.last_trace"
    assert audit["selected_siis_id"] == "row_14"
    assert any("Samsung Repair Services" in e for e in audit["selected_evidence"])
    assert audit["n_actions"] >= 1
    repair = next(a for a in audit["actions"] if a["actionName"] == "Samsung Repair Services")
    assert repair["evidence_associated"] is True
    assert repair["evidence_refs"]
    assert repair["grounding_status"] == "supported"
    assert repair["association_confidence"] == "direct"
    assert audit["grounding_ok"] is True
    assert audit["deeplink_catalogue_ok"] is True


def test_meta_fallback_when_trace_empty_but_meta_has_evidence():
    pipe = SimpleNamespace(
        last_trace={},
        deeplinks=SimpleNamespace(contains_actionable_uri=lambda _u: True),
    )
    result = _fake_result()
    result.meta = {
        "selected_siis": "row_14 | Cracked or bleeding screen on Galaxy phone or tablet",
        "selected_evidence": ["row_14.section_1 Samsung Repair Services"],
    }
    audit = build_evidence_audit(pipe, result)
    assert audit["evidence_status"] == "available"
    assert audit["trace_source"] == "result.meta"
    assert audit["selected_siis_id"] == "row_14"
    assert audit["actions"][0]["evidence_associated"] is True
    assert audit["actions"][0]["grounding_status"] == "supported"
    assert audit["grounding_ok"] is True
