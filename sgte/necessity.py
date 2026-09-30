"""Deterministic action necessity, contradiction, and duplicate merge."""

from __future__ import annotations

import re
from typing import List, Sequence, Tuple

from sgte.extractor import CandidateAction
from sgte.intent import extract_intent
from sgte.lexical import normalize, tokens
from sgte.polarity import polarity
from sgte.query.understand import StructuredQuery
from sgte.siis_sections import EvidenceSection

_OFFTOPIC_ACTION = re.compile(
    r"\b(fingerprint|kids pin|samsung kids|third-party keyboard|frp|google account)\b",
    re.I,
)
_POWER_OFF_ASSUME = re.compile(
    r"\b(won't turn on|will not turn on|does not power|device is off|powered off completely)\b",
    re.I,
)
_POWER_FAILURE_ACTION = re.compile(
    r"\b("
    r"attempt to power on|"
    r"charge the device|"
    r"device not turning on|"
    r"won't turn on|will not turn on|"
    r"troubleshooting steps for device not turning on|"
    r"check for physical damage and liquid exposure"
    r")\b",
    re.I,
)
_ENABLE_TOUCH_SENS = re.compile(
    r"\benable\s+touch\s+sensitivity\b|\btouch\s+sensitivity\b.{0,40}\benable",
    re.I,
)
_DISABLE_TOUCH_SENS = re.compile(
    r"\bdisable\s+touch\s+sensitivity\b|\btouch\s+sensitivity\b.{0,40}\bdisable",
    re.I,
)
_SOFTWARE_SETTING = re.compile(
    r"\b(brightness|rotation|adaptive display|font size|dark mode|blue light)\b",
    re.I,
)


def contradicts_device_state(text: str, sq: StructuredQuery) -> str:
    if sq.device_state.get("phone_powers_on") and (
        _POWER_OFF_ASSUME.search(text or "") or _POWER_FAILURE_ACTION.search(text or "")
    ):
        return "contradicts phone_powers_on"
    if sq.device_state.get("physical_damage") is True and _SOFTWARE_SETTING.search(text or ""):
        return "software setting does not address physical damage"
    return ""


def _touch_sensitivity_polarity(action: CandidateAction) -> str:
    """Return 'enable', 'disable', or '' for Touch sensitivity actions."""
    heading = (action.heading or "").strip().lower()
    if heading.startswith("enable touch sensitivity"):
        return "enable"
    if heading.startswith("disable touch sensitivity"):
        return "disable"
    blob = f"{action.heading} {action.evidence_text} {action.body}"
    en = bool(_ENABLE_TOUCH_SENS.search(blob))
    dis = bool(_DISABLE_TOUCH_SENS.search(blob))
    if en and not dis:
        return "enable"
    if dis and not en:
        return "disable"
    return ""


def _filter_touch_sensitivity_contradictions(
    kept: List[CandidateAction],
    sq: StructuredQuery,
    rejected: List[str],
) -> List[CandidateAction]:
    """Never emit both Enable and Disable Touch sensitivity in one plan.

    Explicit query polarity wins. When direction is ambiguous, keep Enable only if
    evidence text supports enabling; otherwise drop both. Never invent a direction.
    """
    enable_idxs: List[int] = []
    disable_idxs: List[int] = []
    for i, action in enumerate(kept):
        pol = _touch_sensitivity_polarity(action)
        if pol == "enable":
            enable_idxs.append(i)
        elif pol == "disable":
            disable_idxs.append(i)
    if not enable_idxs or not disable_idxs:
        return kept

    ops = set(sq.operations or ())
    drop: set[int] = set()
    if "disable" in ops and "enable" not in ops:
        drop.update(enable_idxs)
        for i in enable_idxs:
            rejected.append(
                f"{kept[i].heading}: contradictory touch sensitivity polarity "
                "(query requests disable)"
            )
    elif "enable" in ops and "disable" not in ops:
        drop.update(disable_idxs)
        for i in disable_idxs:
            rejected.append(
                f"{kept[i].heading}: contradictory touch sensitivity polarity "
                "(query requests enable)"
            )
    else:
        evidence_supports_enable = any(
            "enabl" in (kept[i].evidence_text or "").lower()
            and "touch sensitivity" in (kept[i].evidence_text or "").lower()
            for i in enable_idxs
        )
        if evidence_supports_enable:
            drop.update(disable_idxs)
            for i in disable_idxs:
                rejected.append(
                    f"{kept[i].heading}: contradictory touch sensitivity polarity "
                    "(disable unsupported alongside enable)"
                )
        else:
            drop.update(enable_idxs)
            drop.update(disable_idxs)
            for i in sorted(drop):
                rejected.append(
                    f"{kept[i].heading}: ambiguous touch sensitivity direction; "
                    "abstaining from opposing Enable/Disable pair"
                )
    return [a for i, a in enumerate(kept) if i not in drop]


def polarity_conflict(action_text: str, sq: StructuredQuery) -> str:
    act = polarity(action_text) or extract_intent(action_text).operation
    if not sq.operations:
        return ""
    qop = sq.operations[0]
    opposites = {("enable", "disable"), ("disable", "enable"), ("increase", "decrease"), ("decrease", "increase")}
    if act in {"enable", "disable", "increase", "decrease"} and (qop, act) in opposites:
        return f"polarity conflict query {qop} vs action {act}"
    return ""


def action_is_necessary(action: CandidateAction, sq: StructuredQuery) -> str:
    blob = f"{action.heading} {action.evidence_text} {action.body}"
    low = blob.lower()
    contra = contradicts_device_state(blob, sq) or polarity_conflict(blob, sq)
    if contra:
        return contra
    if _OFFTOPIC_ACTION.search(f"{action.heading} {action.evidence_text}"):
        q = normalize(sq.original)
        if not any(w in q for w in ("fingerprint", "kids", "pin", "keyboard", "google", "frp")):
            return "action does not address identified symptoms"
    symptoms = set(sq.symptoms)
    for issue in sq.issues:
        symptoms.update(issue.symptoms)
    # Touch failure must not accept invisible-display actions.
    if sq.target == "touchscreen" and sq.device_state.get("display_visible") is not False:
        if "nothing is visible" in low or "blank or black" in low:
            return "action addresses invisible display, not touch failure"
        # Full-screen gesture tip is SIIS-conditional (gesture misinterpretation).
        # For unresponsive touch (not lag/delay), it is not a primary grounded fix and
        # maps to View Navigation bar rather than Disable Gesture Controls.
        if sq.device_state.get("touch_responsive") is False:
            laggy = bool(symptoms & {"laggy", "lag", "delayed", "delay"})
            if not laggy and any(
                w in low
                for w in (
                    "full screen gesture",
                    "fullscreen gesture",
                    "navigation bar",
                    "gesture function",
                )
            ):
                return "action addresses gesture navigation, not unresponsive touch"
    # Display flicker must not accept camera/video shutter actions.
    flick = bool(symptoms & {"flicker", "flickers", "flickering"})
    camera_ctx = sq.target == "camera" or bool(set(sq.context) & {"camera", "video"})
    if flick and not camera_ctx and any(
        w in low for w in ("shutter", "super steady", "pro video", "video flickering")
    ):
        return "action addresses camera/video, not display flicker"
    # Smart Switch + blank: reject transfer openers that ignore blank display.
    if (
        ("smart_switch" in sq.context or sq.target == "smart_switch")
        and (sq.device_state.get("display_visible") is False or bool(symptoms & {"blank", "black", "dark"}))
        and any(w in low for w in ("open smart switch", "select transfer", "transfer method"))
        and not any(w in low for w in ("blank", "black", "restart", "mouse", "keyboard", "visible"))
    ):
        return "action ignores blank-display constraint during Smart Switch"
    # Distortion ≠ orientation/rotation actions unless the user asked about rotation.
    if ("distorted" in symptoms or re.search(r"\bdistort", sq.original or "", re.I)) and not any(
        w in normalize(sq.original)
        for w in ("rotate", "rotation", "orientation", "auto rotate", "autorotate")
    ):
        if any(
            w in low
            for w in (
                "orientation",
                "auto rotate",
                "autorotate",
                "test app rotation",
                "portrait mode",
                "landscape mode",
                "screen orientation",
            )
        ):
            return "action addresses rotation, not screen distortion"
    if sq.target == "time_format":
        if not any(w in low for w in ("time", "clock", "24-hour", "24 hour", "hour format", "format")):
            return "action does not address time format"
        if any(w in low for w in ("multi window", "apps edge", "edge panel", "mirroring")):
            return "action does not address time format"
    if sq.target == "fast_charging":
        if "fast charg" not in low and "fast-charg" not in low:
            return "action does not address fast charging"
        ops = set(sq.operations)
        if "disable" in ops and any(w in low for w in ("enable fast", "turn on fast")):
            return "action polarity does not match requested fast charging setting"
        if "enable" in ops and any(w in low for w in ("disable fast", "turn off fast")):
            return "action polarity does not match requested fast charging setting"
    if sq.target == "slow_charging":
        # Offline corpus has no grounded slow-charging plan; reject opportunistic actions.
        return "no grounded slow-charging action in available evidence"
    if sq.target == "touch_sensitivity":
        if "touch sensitivity" not in low and "touch-sensitivity" not in low:
            return "action does not address touch sensitivity"
        ops = set(sq.operations)
        if "disable" in ops and re.search(r"\benable\s+touch\s+sensitivity\b", low):
            return "action polarity does not match requested touch sensitivity setting"
        if "enable" in ops and re.search(r"\bdisable\s+touch\s+sensitivity\b", low):
            return "action polarity does not match requested touch sensitivity setting"
    if sq.target == "floating_shortcut":
        from sgte.query.understand import floating_feature_identified

        if not floating_feature_identified(sq.original):
            return "floating overlay identity not established"
        head = (action.heading or "").lower()
        if not any(w in head for w in ("edge", "shortcut", "floating", "circle", "remove")):
            return "action does not address floating shortcut"
        return ""
    if sq.target == "app_fullscreen":
        if any(w in low for w in ("mirror", "smart view", "smartview", "cast to")):
            return "action addresses mirroring, not app fullscreen"
        if "full screen" not in low and "fullscreen" not in low:
            return "action does not address app fullscreen"
    qbag = tokens(sq.original, min_len=3) | tokens(" ".join(sq.symptoms), min_len=3)
    for issue in sq.issues:
        qbag |= tokens(issue.target, min_len=3)
        qbag |= tokens(" ".join(issue.symptoms), min_len=3)
    abag = tokens(blob, min_len=3)
    # Restart/charge/power-on / input-access remain relevant to display failures.
    if sq.target in {"display", "touchscreen"} and any(
        w in low
        for w in (
            "restart",
            "charge",
            "power",
            "blank",
            "black",
            "screen",
            "display",
            "touch",
            "mouse",
            "keyboard",
            "usb",
            "monitor",
            "check first",
            "access",
            "data",
        )
    ):
        return ""
    # Blank + Smart Switch: USB mouse/keyboard / check-first evidence is on-topic.
    if (
        ("smart_switch" in sq.context or sq.target == "smart_switch")
        and (sq.device_state.get("display_visible") is False or bool(symptoms & {"blank", "black", "dark"}))
        and any(w in low for w in ("mouse", "keyboard", "usb", "monitor", "check first", "restart", "charge"))
    ):
        return ""
    # Repair/service remains valid for physical damage when evidence supports it.
    if sq.device_state.get("physical_damage") is True and any(
        w in low for w in ("repair", "service", "cracked", "damage", "premium care")
    ):
        return ""
    if qbag and abag and not (qbag & abag):
        if sq.target != "general" and sq.target.replace("_", "") not in normalize(blob).replace(" ", ""):
            return "action does not address identified symptoms"
    return ""


def verify_actions(
    actions: Sequence[CandidateAction],
    sq: StructuredQuery,
    kept_sections: Sequence[EvidenceSection],
) -> Tuple[List[CandidateAction], List[str]]:
    source = "\n".join(s.text for s in kept_sections)
    kept: List[CandidateAction] = []
    rejected: List[str] = []
    seen = set()
    for action in actions:
        reason = action_is_necessary(action, sq)
        if reason:
            rejected.append(f"{action.heading}: {reason}")
            continue
        if source and action.evidence_text:
            # Evidence must still be present in kept sections.
            from sgte.evidence import is_supported

            if not is_supported(action.steps[0].text if action.steps else action.heading, source, min_coverage=0.45):
                rejected.append(f"{action.heading}: not supported by selected evidence")
                continue
        key = normalize(action.heading)
        if key in seen:
            continue
        seen.add(key)
        kept.append(action)
    kept = _filter_touch_sensitivity_contradictions(kept, sq, rejected)
    return kept, rejected
