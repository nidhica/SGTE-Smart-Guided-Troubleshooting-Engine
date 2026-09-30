"""Split SIIS articles into evidence sections and keep query-relevant ones only."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from sgte.extractor import split_sections
from sgte.lexical import tokens, weighted_overlap
from sgte.loaders import SiisRecord
from sgte.query.understand import StructuredQuery, understand_query

# Topic tags from heading/body words — not a Samsung procedure list.
_OFFTOPIC = {
    "fingerprint": frozenset({"fingerprint", "fingerprints", "biometric"}),
    "kids_pin": frozenset({"kids", "pin"}),
    "lock_security": frozenset({"locked", "security", "google", "frp"}),
    "third_party_keyboard": frozenset({"keyboard", "lock"}),
}


@dataclass(frozen=True)
class EvidenceSection:
    evidence_id: str
    heading: str
    body: str
    score: float
    keep: bool
    reject_reason: str = ""

    @property
    def text(self) -> str:
        return f"{self.heading}\n{self.body}".strip()


def sectionize(record: SiisRecord) -> List[EvidenceSection]:
    out: List[EvidenceSection] = []
    for i, (heading, body) in enumerate(split_sections(record.content)):
        out.append(
            EvidenceSection(
                evidence_id=f"{record.id}.section_{i}",
                heading=heading or "",
                body=body or "",
                score=0.0,
                keep=True,
            )
        )
    return out


def _query_bag(sq: StructuredQuery) -> frozenset:
    parts = [sq.original, sq.target, " ".join(sq.symptoms), " ".join(sq.context)]
    for issue in sq.issues:
        parts.append(issue.target)
        parts.extend(issue.symptoms)
        parts.extend(issue.context)
    return tokens(" ".join(parts), min_len=3)


def _offtopic_penalty(heading: str, body: str, qbag: frozenset) -> Tuple[float, str]:
    hbag = tokens(heading, min_len=3)
    for name, vocab in _OFFTOPIC.items():
        if hbag & vocab and not (qbag & vocab):
            return 0.55, f"unrelated topic {name}"
    return 0.0, ""


def _contradiction_penalty(heading: str, body: str, sq: StructuredQuery) -> Tuple[float, str]:
    blob = f"{heading} {body}".lower()
    if sq.device_state.get("phone_powers_on") and (
        "won't turn on" in blob
        or "will not turn on" in blob
        or "does not power" in blob
        or "device not turning on" in blob
        or "not turning on" in blob
    ):
        return 0.7, "contradicts device_powers_on"
    if sq.device_state.get("physical_damage") is False and "physical damage" in blob:
        return 0.35, "user stated no physical damage"
    if sq.device_state.get("physical_damage") is True and any(
        w in blob for w in ("brightness", "rotation", "adaptive display", "font size")
    ):
        return 0.6, "software setting vs physical damage"
    # Touch failure ≠ invisible display.
    if sq.target == "touchscreen" and sq.device_state.get("display_visible") is not False:
        if "nothing is visible" in blob or "blank or black" in blob:
            return 0.75, "invisible-display section vs touch failure"
    # Display flicker ≠ camera/video shutter troubleshooting.
    symptoms = set(sq.symptoms)
    flick = bool(symptoms & {"flicker", "flickers", "flickering"})
    camera_ctx = sq.target == "camera" or bool(set(sq.context) & {"camera", "video"})
    if flick and not camera_ctx and any(
        w in blob for w in ("shutter", "super steady", "video flickering", "pro video")
    ):
        return 0.75, "camera/video section vs display flicker"
    # Smart Switch + blank: reject transfer-only steps that ignore blank display.
    if (
        ("smart_switch" in sq.context or sq.target == "smart_switch")
        and (sq.device_state.get("display_visible") is False or bool(symptoms & {"blank", "black", "dark"}))
        and any(w in blob for w in ("open smart switch", "select transfer", "transfer method"))
        and not any(w in blob for w in ("blank", "black", "visible", "restart", "mouse", "keyboard"))
    ):
        return 0.65, "smart-switch transfer ignores blank display"
    # Distortion ≠ rotation/orientation troubleshooting (unless user asked about rotation).
    distorted = "distorted" in symptoms or bool(
        re.search(r"\bdistort", sq.original or "", re.I)
    )
    q_low = (sq.original or "").lower()
    asks_rotation = any(
        w in q_low for w in ("rotate", "rotation", "orientation", "auto rotate", "autorotate")
    )
    if distorted and not asks_rotation:
        head = (heading or "").lower()
        if any(w in head for w in ("orientation", "rotation", "rotate", "portrait", "landscape")):
            return 0.75, "rotation section vs screen distortion"
        if any(
            w in blob
            for w in (
                "adjust screen orientation",
                "test app rotation",
                "auto rotate",
                "autorotate",
            )
        ):
            return 0.75, "rotation section vs screen distortion"
    if sq.target == "time_format" and not any(
        w in blob for w in ("time", "clock", "24-hour", "hour format")
    ):
        return 0.8, "unrelated to time format"
    return 0.0, ""


def score_section(section: EvidenceSection, sq: StructuredQuery) -> EvidenceSection:
    qbag = _query_bag(sq)
    sbag = tokens(section.text, min_len=3)
    overlap = (len(qbag & sbag) / len(qbag)) if qbag else 0.0
    lex = weighted_overlap(sq.original, section.text)
    target_hit = 0.0
    for issue in sq.issues:
        if issue.target != "general" and issue.target in section.text.lower():
            target_hit = max(target_hit, 0.35)
        if any(s in section.text.lower() for s in issue.symptoms):
            target_hit = max(target_hit, 0.4)
    if sq.target != "general" and sq.target.replace("_", " ") in section.text.lower():
        target_hit = max(target_hit, 0.3)
    if sq.target in {"display", "touchscreen"} or "display" in sq.intent:
        if any(w in section.text.lower() for w in ("restart", "charge", "power on", "blank", "black", "display", "screen")):
            target_hit = max(target_hit, 0.55)
    off_p_extra = 0.0
    off_r_extra = ""
    if sq.target == "floating_shortcut":
        blob = (section.heading or "").lower() or section.text.lower()[:240]
        if not any(w in blob for w in ("edge", "shortcut", "floating", "circle")):
            off_p_extra = 0.55
            off_r_extra = "unrelated to floating shortcut"
    if "email" in sq.context or "gmail" in sq.context:
        if any(w in section.text.lower() for w in ("email", "gmail", "cache", "account")):
            target_hit = max(target_hit, 0.45)
    if "smart_switch" in sq.context or sq.target == "smart_switch":
        if "smart switch" in section.text.lower() or "transfer" in section.text.lower():
            target_hit = max(target_hit, 0.45)
    if sq.target == "touchscreen" or "touch" in sq.intent:
        if any(w in section.text.lower() for w in ("touch", "unresponsive", "respond")):
            target_hit = max(target_hit, 0.5)
        if "brightness" in section.text.lower() and "touch" not in section.text.lower():
            target_hit = min(target_hit, 0.15)
    off_p, off_r = _offtopic_penalty(section.heading, section.body, qbag)
    off_p += off_p_extra
    off_r = off_r or off_r_extra
    con_p, con_r = _contradiction_penalty(section.heading, section.body, sq)
    score = 0.40 * overlap + 0.25 * lex + 0.35 * target_hit - off_p - con_p
    reason = off_r or con_r
    keep = score >= 0.18 and off_p < 0.5
    if not section.heading and overlap >= 0.08:
        keep = keep or (off_p < 0.5)
        score = max(score, 0.2)
    return EvidenceSection(
        evidence_id=section.evidence_id,
        heading=section.heading,
        body=section.body,
        score=score,
        keep=keep,
        reject_reason="" if keep else (reason or f"weak section relevance ({score:.3f})"),
    )


def filter_record_sections(record: SiisRecord, query: str, sq: Optional[StructuredQuery] = None) -> Tuple[List[EvidenceSection], List[EvidenceSection], SiisRecord]:
    sq = sq or understand_query(query)
    scored = [score_section(sec, sq) for sec in sectionize(record)]
    kept = [s for s in scored if s.keep]
    rejected = [s for s in scored if not s.keep]
    if not kept:
        # Keep the single best non-offtopic section rather than leaking the whole article.
        ranked = sorted(scored, key=lambda s: -s.score)
        for cand in ranked:
            if "unrelated topic" not in cand.reject_reason:
                kept = [
                    EvidenceSection(
                        evidence_id=cand.evidence_id,
                        heading=cand.heading,
                        body=cand.body,
                        score=cand.score,
                        keep=True,
                        reject_reason="",
                    )
                ]
                rejected = [s for s in scored if s.evidence_id != cand.evidence_id]
                break
    parts: List[str] = []
    for sec in kept:
        if sec.heading:
            parts.append(f"## {sec.heading}\n{sec.body}")
        else:
            parts.append(sec.body)
    filtered = SiisRecord(
        id=record.id,
        original_query=record.original_query,
        title=record.title,
        content="\n\n".join(parts),
        siis_response={"title": record.title, "content": "\n\n".join(parts)},
        raw=record.raw,
    )
    return kept, rejected, filtered
