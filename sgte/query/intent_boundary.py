"""Intent-boundary fingerprints for semantic-cache isolation (not ranking weights).

Hard semantic families that must not share cache entries when conflicting.
"""

from __future__ import annotations

from typing import FrozenSet, Iterable, Set

from sgte.query.understand import StructuredQuery

# Mutually exclusive primary issue families for cache matching.
_PRIMARY = frozenset(
    {
        "blank_display",
        "physical_damage",
        "touch_failure",
        "display_flicker",
        "camera_flicker",
        "time_format",
        "fast_charging",
        "slow_charging",
        "touch_sensitivity",
        "app_fullscreen",
    }
)

_CONFLICT_PAIRS = frozenset(
    {
        frozenset({"blank_display", "physical_damage"}),
        frozenset({"blank_display", "touch_failure"}),
        frozenset({"physical_damage", "touch_failure"}),
        frozenset({"display_flicker", "camera_flicker"}),
        frozenset({"time_format", "blank_display"}),
        frozenset({"time_format", "display_flicker"}),
        frozenset({"time_format", "camera_flicker"}),
        frozenset({"time_format", "touch_failure"}),
        frozenset({"time_format", "physical_damage"}),
        frozenset({"fast_charging", "blank_display"}),
        frozenset({"fast_charging", "physical_damage"}),
        frozenset({"touch_sensitivity", "touch_failure"}),
        frozenset({"app_fullscreen", "blank_display"}),
    }
)

_VIS = frozenset({"blank", "black", "dark"})
_FLICK = frozenset({"flicker", "flickers", "flickering", "flashes", "flash"})
_CRACK = frozenset({"crack", "cracks", "cracked"})


def intent_boundaries(sq: StructuredQuery) -> FrozenSet[str]:
    """Derive hard semantic boundary tags from a structured query."""
    bounds: Set[str] = set()
    symptoms = set(sq.symptoms)
    for issue in sq.issues:
        symptoms.update(issue.symptoms)
    ctx = set(sq.context)
    for issue in sq.issues:
        ctx.update(issue.context)
    dstate = sq.device_state or {}

    if sq.target == "time_format" or "time_format" in (sq.intent or ""):
        bounds.add("time_format")
    if sq.target == "fast_charging" or "fast_charging" in (sq.intent or ""):
        bounds.add("fast_charging")
    if sq.target == "slow_charging" or "slow_charging" in (sq.intent or ""):
        bounds.add("slow_charging")
    if sq.target == "touch_sensitivity" or "touch_sensitivity" in (sq.intent or ""):
        bounds.add("touch_sensitivity")
    if sq.target == "app_fullscreen" or "app_fullscreen" in (sq.intent or ""):
        bounds.add("app_fullscreen")

    if dstate.get("physical_damage") is True or (symptoms & _CRACK):
        bounds.add("physical_damage")

    if sq.target == "touchscreen" or dstate.get("touch_responsive") is False:
        bounds.add("touch_failure")

    cameraish = bool(ctx & {"camera", "video", "recording"}) or sq.target == "camera"
    if symptoms & _FLICK:
        if cameraish:
            bounds.add("camera_flicker")
        else:
            bounds.add("display_flicker")

    # Blank/black/dark visibility — subordinate to physical_damage for cache identity
    # when the primary complaint is a cracked screen (may also "barely see").
    if (
        dstate.get("display_visible") is False or (symptoms & _VIS)
    ) and "physical_damage" not in bounds:
        bounds.add("blank_display")

    if "smart_switch" in ctx or sq.target == "smart_switch":
        bounds.add("smart_switch")

    if sq.target == "email" or ctx & {"gmail", "email"}:
        bounds.add("email")

    if sq.target == "battery" or symptoms & {"drain", "drains", "dies"}:
        bounds.add("battery")

    return frozenset(bounds)


def boundaries_compatible(a: Iterable[str], b: Iterable[str]) -> bool:
    """False when structured intents have material semantic conflicts."""
    sa, sb = frozenset(a or ()), frozenset(b or ())
    if not sa and not sb:
        return True
    for pair in _CONFLICT_PAIRS:
        if pair <= (sa | sb) and (pair & sa) and (pair & sb):
            # both sides contribute different members of a conflict pair
            if (pair & sa) != (pair & sb):
                return False
    pa, pb = sa & _PRIMARY, sb & _PRIMARY
    if pa and pb and pa != pb:
        return False
    # Smart Switch + blank must not share with blank-only or SS-only
    if ("smart_switch" in sa) != ("smart_switch" in sb):
        if "blank_display" in sa or "blank_display" in sb:
            return False
    # Multi-symptom flicker+blank must not reuse blank-only cache
    if ("display_flicker" in sa) != ("display_flicker" in sb):
        if "blank_display" in sa or "blank_display" in sb:
            return False
    return True


def boundary_intent_label(bounds: FrozenSet[str]) -> str:
    """Stable cache intent label from boundary tags (most specific first)."""
    order = (
        "time_format",
        "fast_charging",
        "slow_charging",
        "touch_sensitivity",
        "app_fullscreen",
        "physical_damage",
        "touch_failure",
        "camera_flicker",
        "display_flicker",
        "blank_display",
        "smart_switch",
        "email",
        "battery",
    )
    for name in order:
        if name in bounds:
            return name
    return "user_query"
