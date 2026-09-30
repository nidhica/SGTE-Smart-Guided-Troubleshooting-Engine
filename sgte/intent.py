"""Deterministic action intent: operation + target, not polarity alone."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from sgte.lexical import normalize, token_list
from sgte.polarity import mask_negated_turn_on

_OPS = (
    ("disable", re.compile(r"\b(disable|disabled|turn off|turns off|turned off|deactivate|deactivated|switch off|block|hide)\b", re.I)),
    ("enable", re.compile(r"\b(enable|enabled|turn on|turns on|turned on|activate|activated|switch on|allow|show)\b", re.I)),
    ("increase", re.compile(r"\b(increase|raise|turn up|higher)\b", re.I)),
    ("decrease", re.compile(r"\b(decrease|lower|turn down|reduce)\b", re.I)),
    ("update", re.compile(r"\b(change|set|update|adjust|configure)\b", re.I)),
    ("open", re.compile(r"\b(open|view|navigate to|access|go to)\b", re.I)),
)

# Leading primary enable/disable. Optional "How do I" prefix for NL paraphrases.
# Disable is checked before enable so "turn off" / "Disable Allow ..." win.
_HOWTO_PREFIX = re.compile(r"^\s*(?:how\s+do\s+i\s+)?", re.IGNORECASE)
_PRIMARY_DISABLE = re.compile(
    r"^(disable|disables|disabled|turn\s+off|switch\s+off|deactivate|deactivated)\b",
    re.IGNORECASE,
)
_PRIMARY_ENABLE = re.compile(
    r"^(enable|enables|enabled|turn\s+on|switch\s+on|activate|activated|allow)\b",
    re.IGNORECASE,
)
# Second primary action in another clause — keep multi-op ambiguity as unknown.
_CONFLICTING_PRIMARY_CLAUSE = re.compile(
    r"\b(?:and|then|also|but)\s+"
    r"(?:enable|enables|enabled|disable|disables|disabled|"
    r"turn\s+on|turn\s+off|switch\s+on|switch\s+off|"
    r"activate|activated|deactivate|deactivated|allow)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ActionIntent:
    operation: str
    target: str
    object: str
    context: str
    raw: str


def _strip_ops(text: str) -> str:
    out = text or ""
    for _, pattern in _OPS:
        out = pattern.sub(" ", out)
    return normalize(out)


def _primary_enable_disable(raw: str) -> Optional[str]:
    """Return enable/disable when the query has a clear leading primary operation.

    Incidental words in the target (view, access, allow, embedded turn off) must
    not cancel that primary. Coordinated multi-action clauses still return None
    so the caller can keep operation=unknown.
    """
    body = _HOWTO_PREFIX.sub("", raw or "", count=1).strip()
    if not body:
        return None
    if _CONFLICTING_PRIMARY_CLAUSE.search(body):
        return None
    if _PRIMARY_DISABLE.match(body):
        return "disable"
    if _PRIMARY_ENABLE.match(body):
        return "enable"
    return None


def extract_intent(text: str) -> ActionIntent:
    raw = text or ""
    # Ignore negated failure "turn on" when scanning for enable ops.
    scan = mask_negated_turn_on(raw)
    primary = _primary_enable_disable(scan)
    if primary is not None:
        operation = primary
    else:
        found = []
        for name, pattern in _OPS:
            if pattern.search(scan):
                found.append(name)
        operation = found[0] if len(found) == 1 else "unknown"
    target = _strip_ops(raw)
    tokens = token_list(target, min_len=3)
    obj = " ".join(tokens[:6])
    return ActionIntent(operation=operation, target=target, object=obj, context=raw, raw=raw)


def candidate_target(message: str, description: str, qna: str) -> str:
    # Prefer message: descriptions repeat "device Settings on the device".
    primary = _strip_ops(message or "")
    extra = _strip_ops(f"{description or ''} {qna or ''}")
    return f"{primary} {extra}".strip()


def candidate_target(message: str, description: str, qna: str) -> str:
    # Prefer message: descriptions repeat "device Settings on the device".
    primary = _strip_ops(message or "")
    extra = _strip_ops(f"{description or ''} {qna or ''}")
    return f"{primary} {extra}".strip()
