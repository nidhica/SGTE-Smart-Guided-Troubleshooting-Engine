"""Extract candidate troubleshooting instructions from official SIIS text only."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Sequence

from sgte.loaders import SiisRecord
from sgte.url_leak import url_leak_reasons

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
_STEP_PREFIX = re.compile(r"^(?:step\s+\d+\s*[:.-]\s*|\d+\.\s*)", re.IGNORECASE)
_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")
_IMPERATIVE = re.compile(
    r"^(?:please\s+)?"
    r"(tap|go|open|swipe|press|touch|select|navigate|restart|contact|visit|"
    r"connect|disable|enable|increase|adjust|ensure|check|try|clear|remove|"
    r"turn|hold|insert|locate|switch|set|follow|use|schedule|inspect|"
    r"uninstall|re-?add|wipe|charge|force|back\s+up|access)\b",
    re.IGNORECASE,
)
_SETTINGS_HINT = re.compile(r"\b(settings|quick settings|tap|swipe|go to)\b", re.IGNORECASE)

# Headings that are explanations, not instruction blocks (from SIIS structure).
_SKIP_HEADING = re.compile(
    r"^(understanding|glossary|what is|tips for|requirements|note:|"
    r"factors affecting|useful app pairing)",
    re.IGNORECASE,
)

_BOILERPLATE = re.compile(
    r"^(smartphone|tablet|mobile accessories|others mobile)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CandidateStep:
    text: str
    source_row_id: str
    source_section: Optional[str]
    evidence_text: str


@dataclass(frozen=True)
class CandidateAction:
    heading: str
    source_row_id: str
    source_section: str
    evidence_text: str
    steps: Sequence[CandidateStep]
    body: str


def _sentences(text: str) -> List[str]:
    parts = [p.strip() for p in _SENTENCE.split(text or "") if p and p.strip()]
    cleaned: List[str] = []
    for part in parts:
        part = re.sub(r"\s+", " ", part).strip(" -*\t")
        if not part:
            continue
        if _BOILERPLATE.match(part):
            continue
        cleaned.append(part)
    return cleaned


def _is_instruction(sentence: str) -> bool:
    if len(sentence) < 12:
        return False
    if url_leak_reasons(sentence):
        return False
    if _IMPERATIVE.match(sentence):
        return True
    if _SETTINGS_HINT.search(sentence) and len(sentence) <= 240:
        return True
    return False


def split_sections(content: str) -> List[tuple[str, str]]:
    matches = list(_HEADING.finditer(content or ""))
    if not matches:
        return [("", content or "")]
    sections: List[tuple[str, str]] = []
    preamble = content[: matches[0].start()].strip()
    if preamble:
        sections.append(("", preamble))
    for i, match in enumerate(matches):
        heading = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        sections.append((heading, content[start:end].strip()))
    return sections


def extract_candidate_actions(record: SiisRecord) -> List[CandidateAction]:
    """Pull instruction-bearing sections from SIIS markdown. Does not invent text."""
    actions: List[CandidateAction] = []
    for heading, body in split_sections(record.content):
        if heading and _SKIP_HEADING.match(heading):
            continue
        display = _STEP_PREFIX.sub("", heading).strip() if heading else record.title
        if not display:
            continue
        evidence_sentences = _sentences(body)
        instruction_texts = [s for s in evidence_sentences if _is_instruction(s)]
        if not instruction_texts:
            continue
        steps = [
            CandidateStep(
                text=text,
                source_row_id=record.id,
                source_section=display,
                evidence_text=text,
            )
            for text in instruction_texts
        ]
        actions.append(
            CandidateAction(
                heading=display,
                source_row_id=record.id,
                source_section=display,
                evidence_text=" ".join(instruction_texts),
                steps=steps,
                body=body,
            )
        )
    return actions
