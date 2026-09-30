"""Small extensible domain tags + target overlap. Not a Samsung feature encyclopedia."""

from __future__ import annotations

from typing import FrozenSet, Optional

from sgte.intent import ActionIntent
from sgte.lexical import tokens
from sgte.loaders import DeeplinkRecord
from sgte.polarity import original_type_polarity, polarity

# Tiny generic expansions, not a Samsung settings encyclopedia.
_SYNONYMS = {
    "brightness": "display",
    "backup": "cloud",
    "navbar": "navigation",
}

# Generic UI/device domains — a handful of buckets, not per-setting rules.
DOMAIN_TERMS = {
    "power": frozenset({"charger", "charging", "charge", "battery", "powered", "restart", "reboot", "power"}),
    "gesture": frozenset({"double", "tap", "palm", "gesture", "gestures"}),
    "timeout": frozenset({"timeout", "sleep"}),
    "navigation": frozenset({"navigation", "navbar", "gestural"}),
    "input": frozenset({"keyboard", "mouse", "keys", "keypad"}),
    "backup": frozenset({"backup", "cloud", "restore"}),
    "display": frozenset({"brightness", "adaptive", "display", "font", "dark", "blue", "light"}),
    "network": frozenset({"wifi", "bluetooth", "network", "connections"}),
    "time": frozenset({"time", "format", "clock", "hour"}),
    "lock": frozenset({"lock", "unlock", "fingerprint", "pin", "password"}),
}


def domains(text: str) -> FrozenSet[str]:
    bag = tokens(text or "", min_len=3)
    hit = set()
    for name, vocab in DOMAIN_TERMS.items():
        if bag & vocab:
            hit.add(name)
    return frozenset(hit)


def _expand(bag: FrozenSet[str]) -> FrozenSet[str]:
    extra = set(bag)
    for token in bag:
        if token in _SYNONYMS:
            extra.add(_SYNONYMS[token])
    return frozenset(extra)


def target_compatibility(action_target: str, cand_target: str) -> float:
    a = _expand(tokens(action_target, min_len=3))
    b = _expand(tokens(cand_target, min_len=3))
    if not a or not b:
        return 0.0
    return len(a & b) / len(a)


def operation_compatibility(operation: str, row: DeeplinkRecord) -> float:
    msg_p = polarity(row.message or "")
    desc_p = polarity(f"{row.message} {row.description} {row.qna_description or ''}")
    type_p = original_type_polarity(row.originalType)
    row_p = msg_p or desc_p or type_p
    if operation in {"enable", "disable"}:
        if row_p and row_p != operation:
            return 0.0
        if row_p == operation:
            return 1.0
        return 0.45
    if operation in {"increase", "decrease", "update"} and row.originalType == "updateURL":
        return 0.85
    if operation == "open" and row.originalType in {"onClickURL", None}:
        return 0.7
    return 0.55


def context_compatibility(action_text: str, row: DeeplinkRecord) -> float:
    a = domains(action_text)
    c = domains(f"{row.message} {row.qna_description or ''}")
    if not a or not c:
        return 0.5
    if a & c:
        return 1.0
    return 0.15


def mismatch_penalty(action_text: str, row: DeeplinkRecord, intent: ActionIntent) -> float:
    a = domains(action_text)
    c = domains(f"{row.message} {row.qna_description or ''}")
    if "power" in a and "gesture" in c and "gesture" not in a:
        return 0.55
    if "power" in a and "navigation" in c and "navigation" not in a:
        return 0.45
    if "power" in a and "input" in c and "input" not in a:
        return 0.4
    if a and c and not (a & c):
        return 0.35
    return 0.0


def polarity_allows(intent: ActionIntent, row: DeeplinkRecord) -> bool:
    if intent.operation not in {"enable", "disable"}:
        return True
    msg = f"{row.message} {row.description} {row.qna_description or ''}"
    msg_p = polarity(row.message or "") or polarity(msg) or original_type_polarity(row.originalType)
    if msg_p is None:
        return True
    return msg_p == intent.operation
