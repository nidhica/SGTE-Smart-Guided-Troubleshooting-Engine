"""Turn LLM JSON into CandidateAction rows, then drop anything not grounded in SIIS."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from sgte.evidence import grounded_steps, is_supported, looks_like_invented_path, multi_screen_name
from sgte.extractor import CandidateAction, CandidateStep
from sgte.loaders import SiisRecord
from sgte.url_leak import url_leak_reasons


def llm_payload_to_candidates(
    payload: Dict[str, Any],
    record: SiisRecord,
) -> Tuple[List[CandidateAction], List[str]]:
    source = f"{record.title}\n{record.content}"
    rejected: List[str] = []
    actions: List[CandidateAction] = []
    raw_actions = payload.get("actions")
    if not isinstance(raw_actions, list):
        return [], ["LLM JSON missing actions list"]

    for index, item in enumerate(raw_actions):
        if not isinstance(item, dict):
            rejected.append(f"action[{index}] not an object")
            continue
        name = str(item.get("actionName") or "").strip()
        description = str(item.get("description") or "").strip()
        steps_raw = item.get("steps") or []
        if not name:
            rejected.append(f"action[{index}] missing actionName")
            continue
        if "bixby://" in name.lower() or "bixby://" in description.lower():
            # LLM must never emit catalogue URIs in free text; mapper attaches URIs only.
            rejected.append(f"action[{index}] forbidden bixby:// in name/description")
            continue
        if multi_screen_name(name):
            rejected.append(f"action[{index}] violates one-action-one-screen: {name!r}")
            continue
        if url_leak_reasons(name) or url_leak_reasons(description):
            rejected.append(f"action[{index}] URL leak in name/description")
            continue
        if looks_like_invented_path(name, source) or (
            description and looks_like_invented_path(description, source)
        ):
            rejected.append(f"action[{index}] hallucinated Settings path")
            continue
        if description and not is_supported(description, source):
            rejected.append(f"action[{index}] description unsupported by SIIS")
            continue
        if not isinstance(steps_raw, list):
            rejected.append(f"action[{index}] steps not a list")
            continue
        step_strings = [str(s).strip() for s in steps_raw if str(s).strip()]
        if any("bixby://" in s.lower() for s in step_strings):
            rejected.append(f"action[{index}] forbidden bixby:// in steps")
            continue
        kept, dropped = grounded_steps(step_strings, source)
        for drop in dropped:
            rejected.append(f"action[{index}] rejected step: {drop[:80]}")
        if not kept:
            rejected.append(f"action[{index}] no grounded steps")
            continue
        evidence = item.get("evidence")
        evidence_text = " ".join(str(x) for x in evidence) if isinstance(evidence, list) else " ".join(kept)
        if evidence_text and not is_supported(evidence_text, source, min_coverage=0.5):
            evidence_text = " ".join(kept)
        cand_steps = [
            CandidateStep(
                text=step,
                source_row_id=record.id,
                source_section=name,
                evidence_text=step,
            )
            for step in kept
        ]
        actions.append(
            CandidateAction(
                heading=name,
                source_row_id=record.id,
                source_section=name,
                evidence_text=evidence_text,
                steps=cand_steps,
                body=description or " ".join(kept),
            )
        )
    return actions, rejected
