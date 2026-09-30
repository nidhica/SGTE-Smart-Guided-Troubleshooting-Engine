"""Lightweight canonical query representation for cache similarity only.

Patterns use words already in the user string. No Samsung procedure knowledge.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Tuple

from sgte.compatibility import domains
from sgte.intent import extract_intent
from sgte.query.intent_boundary import boundary_intent_label, intent_boundaries
from sgte.query.normalize import normalize_query

# Generic symptom collocations — only fire when those tokens are present.
_INTENT_HINTS: Tuple[Tuple[FrozenSet[str], str], ...] = (
    (frozenset({"battery", "drain"}), "battery_drain"),
    (frozenset({"battery", "drains"}), "battery_drain"),
    (frozenset({"screen", "blank"}), "blank_screen"),
    (frozenset({"screen", "black"}), "blank_screen"),
    (frozenset({"display", "blank"}), "blank_screen"),
    (frozenset({"screen", "flicker"}), "flicker_display"),
    (frozenset({"screen", "flickers"}), "flicker_display"),
    (frozenset({"touch", "lag"}), "touch_lag"),
    (frozenset({"touch", "delayed"}), "touch_lag"),
    (frozenset({"touch", "sensitivity"}), "touch_sensitivity"),
    (frozenset({"fast", "charging"}), "fast_charging"),
    (frozenset({"full", "screen"}), "app_fullscreen"),
    (frozenset({"cracked"}), "physical_damage"),
    (frozenset({"crack"}), "physical_damage"),
    (frozenset({"floating", "circle"}), "overlay_shortcut"),
    (frozenset({"adaptive", "brightness"}), "adaptive_brightness"),
    (frozenset({"mouse", "keys"}), "mouse_keys"),
    (frozenset({"time", "format"}), "time_format"),
    (frozenset({"back", "up"}), "backup_data"),
    (frozenset({"gmail", "notification"}), "app_notification"),
    (frozenset({"gmail", "notifications"}), "app_notification"),
)


@dataclass(frozen=True)
class CanonicalQuery:
    original: str
    normalized: str
    operation: str
    domain: str
    intent: str
    semantic_key: str
    tokens: Tuple[str, ...]
    boundaries: Tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "original": self.original,
            "normalized": self.normalized,
            "operation": self.operation,
            "domain": self.domain,
            "intent": self.intent,
            "semantic_key": self.semantic_key,
            "tokens": list(self.tokens),
            "boundaries": list(self.boundaries),
        }


def _intent_label(token_set: FrozenSet[str]) -> str:
    for needed, label in _INTENT_HINTS:
        if needed <= token_set:
            return label
    if token_set:
        return "user_query"
    return "unknown"


def canonicalize(query: str) -> CanonicalQuery:
    original = query or ""
    normalized = normalize_query(original)
    action = extract_intent(original)
    operation = action.operation if action.operation != "unknown" else "troubleshoot"
    # "open an email" is not a settings-open intent; keep troubleshoot unless polarity.
    if operation == "open" and action.operation == "open":
        if not any(w in normalized.split() for w in ("settings", "menu", "page")):
            operation = "troubleshoot"
    found_domains = sorted(domains(original) | domains(normalized))
    domain = "+".join(found_domains) if found_domains else "general"
    token_tuple = tuple(normalized.split())
    from sgte.query.understand import understand_query

    understood = understand_query(original)
    bounds = intent_boundaries(understood)
    # Prefer structured intent-boundary labels for cache isolation.
    intent = boundary_intent_label(bounds)
    if intent == "user_query":
        intent = _intent_label(frozenset(token_tuple))
        if understood.intent not in {"troubleshoot", "user_query"}:
            intent = understood.intent
    issue_bit = "+".join(i.target for i in understood.issues)
    op_bit = understood.operations[0] if understood.operations else operation
    bound_bit = "+".join(sorted(bounds)) if bounds else "none"
    semantic_key = (
        f"operation_{op_bit} domain_{domain.replace('+', '_')} "
        f"intent_{intent} bounds_{bound_bit} issues_{issue_bit} "
        f"{' '.join(sorted(set(token_tuple)))}"
    )
    return CanonicalQuery(
        original=original,
        normalized=normalized,
        operation=op_bit if op_bit in {"enable", "disable", "increase", "decrease"} else operation,
        domain=domain,
        intent=intent,
        semantic_key=semantic_key,
        tokens=token_tuple,
        boundaries=tuple(sorted(bounds)),
    )
