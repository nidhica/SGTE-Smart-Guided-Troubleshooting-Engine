"""Deterministic structured query from user wording. Not a Samsung knowledge base."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from sgte.intent import extract_intent
from sgte.lexical import normalize, token_list
from sgte.polarity import polarity

# More specific targets first. Patterns fire only when those words appear.
_TARGET_PATTERNS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("floating_shortcut", ("floating", "circle", "overlay", "shortcut")),
    ("time_format", ("time format", "24 hour", "24-hour", "12 hour", "12-hour", "clock format")),
    ("fast_charging", ("fast charging", "fast charge")),
    ("slow_charging", ("charging slowly", "slow charging", "charges slowly", "charge slowly")),
    ("touch_sensitivity", ("touch sensitivity",)),
    ("camera", ("camera", "recorded video", "video recording", "super steady", "shutter speed")),
    ("touchscreen", ("touch", "touchscreen", "laggy", "lag", "delayed")),
    ("smart_switch", ("smart switch", "smartswitch", "data transfer")),
    ("mouse_keys", ("mouse keys", "mouse")),
    ("battery", ("battery", "drain", "drains", "dies", "charging", "charger", "charge")),
    ("email", ("gmail", "email", "inbox")),
    ("backup", ("backup", "samsung cloud")),
    ("display", ("screen", "display", "blank", "black", "flicker", "flickers", "brightness")),
)

_SYMPTOM_WORDS = (
    "blank",
    "black",
    "white",
    "flicker",
    "flickers",
    "flickering",
    "flashes",
    "flash",
    "laggy",
    "lag",
    "delayed",
    "delay",
    "cracked",
    "cracks",
    "crack",
    "broken",
    "drain",
    "drains",
    "dies",
    "unusable",
    "unresponsive",
    "frozen",
    "dark",
    "distorted",
)

_VISIBILITY_SYMPTOMS = ("blank", "black", "dark")
_FLICKER_SYMPTOMS = ("flicker", "flickers", "flickering", "flashes", "flash")
_CRACK_SYMPTOMS = ("crack", "cracks", "cracked")

_EMPTY_DISPLAY_RE = re.compile(
    r"(?:"
    r"(?:screen|display)\s+(?:is\s+)?(?:showing|sees)\s+nothing"
    r"|(?:showing|sees)\s+nothing(?:\s+\w+){0,6}\s+(?:on\s+(?:the\s+)?)?(?:screen|display)"
    r"|nothing\s+on\s+the\s+(?:screen|display)"
    r"|\b(?:no\s+image|no\s+picture|shows?\s+no\s+image)\b"
    r"|(?:screen|display)\s+(?:turns?|turned|goes|went)\s+off"
    r")",
    re.I,
)

_NO_IMAGE_RE = re.compile(r"\b(?:no\s+image|no\s+picture|shows?\s+no\s+image|does\s+not\s+show|doesn't\s+show)\b", re.I)

_TIME_FORMAT_RE = re.compile(
    r"\b(?:time\s+format|24[\s-]?hour|12[\s-]?hour|clock\s+format)\b",
    re.I,
)

_FAST_CHARGING_RE = re.compile(r"\bfast\s+charg(?:e|ing)\b", re.I)
_SLOW_CHARGING_RE = re.compile(
    r"\b(?:charg(?:e|es|ing)\s+slowly|slow(?:ly)?\s+charg(?:e|ing)?)\b",
    re.I,
)
_TOUCH_SENSITIVITY_RE = re.compile(r"\btouch\s+sensitivity\b", re.I)
_APP_FULLSCREEN_RE = re.compile(r"\b(?:full[\s-]?screen|fullscreen)\b", re.I)
_MIRROR_CAST_RE = re.compile(
    r"\b(?:smart\s*view|mirror(?:ing)?|cast(?:ing)?|samsung\s+tv)\b",
    re.I,
)
_SPLIT_MULTI_RE = re.compile(r"\b(?:split\s+screen|multi[\s-]?window|app\s+pairs)\b", re.I)
# Edge/Apps-edge identity cues beyond bare "floating circle".
_FLOATING_FEATURE_RE = re.compile(
    r"\b(?:edge\s*panels?|apps?\s*edge|shortcuts?|recent\s+apps|multi\s*window|"
    r"overlay\s+shortcut|quick\s+shortcuts?)\b",
    re.I,
)
# Missing/not-appearing QR in Smart Switch (distinct from blank display while scanning).
_MISSING_QR_RE = re.compile(
    r"\b(?:qr\s*codes?|qr)\b.{0,48}\b(?:not\s+(?:appearing|appear|showing|displayed)|"
    r"isn'?t\s+(?:appearing|appear|showing)|doesn'?t\s+(?:appear|show)|missing)\b"
    r"|\b(?:not\s+(?:appearing|appear|showing)|missing).{0,48}\b(?:qr\s*codes?|qr)\b",
    re.I,
)

_CAMERA_FLICKER_RE = re.compile(
    r"\b(?:camera|recorded\s+video|video\s+recording|recording|shutter|super\s+steady)\b",
    re.I,
)

_TOUCH_FAIL_RE = re.compile(
    r"\b(?:don'?t\s+respond|does\s+not\s+respond|doesn'?t\s+respond|unresponsive|"
    r"not\s+respond(?:ing)?|won'?t\s+respond|areas?\s+.+?\s+touch|touch\s+.+?\s+respond)\b",
    re.I,
)

_DEVICE_RE = re.compile(
    r"\b(s\d{2}\s*ultra|s\d{2}|z\s*flip\s*\d+|flip|a\d{2,4}g?|galaxy|tablet|phone|device)\b",
    re.I,
)


@dataclass(frozen=True)
class QueryIssue:
    target: str
    symptoms: Tuple[str, ...]
    context: Tuple[str, ...]
    operations: Tuple[str, ...]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "symptoms": list(self.symptoms),
            "context": list(self.context),
            "operations": list(self.operations),
        }


@dataclass(frozen=True)
class StructuredQuery:
    original: str
    device: str
    target: str
    symptoms: Tuple[str, ...]
    states: Tuple[str, ...]
    context: Tuple[str, ...]
    constraints: Tuple[str, ...]
    operations: Tuple[str, ...]
    device_state: Dict[str, Any]
    intent: str
    issues: Tuple[QueryIssue, ...]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "device": self.device,
            "target": self.target,
            "symptoms": list(self.symptoms),
            "states": list(self.states),
            "context": list(self.context),
            "constraints": list(self.constraints),
            "operations": list(self.operations),
            "device_state": dict(self.device_state),
            "intent": self.intent,
            "issues": [i.as_dict() for i in self.issues],
        }

    def issue_key(self) -> str:
        parts = [self.intent, self.target] + [i.target for i in self.issues] + list(self.operations)
        return " ".join(parts)


def _targets(text: str) -> List[str]:
    bag = set(token_list(text, min_len=3, drop_stopwords=True))
    lowered = normalize(text)
    found: List[str] = []
    for name, words in _TARGET_PATTERNS:
        if any(w in bag or w in lowered for w in words):
            found.append(name)
    if _TIME_FORMAT_RE.search(text or ""):
        if "time_format" not in found:
            found.insert(0, "time_format")
    if _FAST_CHARGING_RE.search(text or ""):
        if "fast_charging" not in found:
            found.insert(0, "fast_charging")
    if _SLOW_CHARGING_RE.search(text or ""):
        if "slow_charging" not in found:
            found.insert(0, "slow_charging")
    if _TOUCH_SENSITIVITY_RE.search(text or ""):
        if "touch_sensitivity" not in found:
            found.insert(0, "touch_sensitivity")
    # App immersive fullscreen — distinct from Smart View mirroring / Split screen.
    if (
        _APP_FULLSCREEN_RE.search(text or "")
        and not _MIRROR_CAST_RE.search(text or "")
        and not _SPLIT_MULTI_RE.search(text or "")
    ):
        if "app_fullscreen" not in found:
            found.insert(0, "app_fullscreen")
    # Camera/video flicker domain (avoid bare "video" alone matching display apps).
    if re.search(r"\b(camera|recorded\s+video|video\s+recording)\b", text or "", re.I) or (
        re.search(r"\bvideo\b", text or "", re.I)
        and re.search(r"\bflicker", text or "", re.I)
    ):
        if "camera" not in found:
            found.insert(0, "camera")
    return found or ["general"]


def floating_feature_identified(text: str) -> bool:
    """True when floating-circle complaint names Edge/shortcuts (not bare circle)."""
    return bool(_FLOATING_FEATURE_RE.search(text or ""))


def missing_smart_switch_qr_complaint(text: str, *, context: Tuple[str, ...] = ()) -> bool:
    """True for Smart Switch QR not appearing — not blank-screen-while-scanning.

    Wireless-transfer howto text says a QR 'will be displayed'; that is not evidence
    for diagnosing a missing QR code.
    """
    raw = text or ""
    ctx = set(context)
    if (
        "smart_switch" not in ctx
        and not re.search(r"\bsmart\s*switch\b", raw, re.I)
        and not re.search(r"\bdata\s+transfer\b", raw, re.I)
    ):
        return False
    if "qr" not in ctx and not re.search(r"\bqr\b", raw, re.I):
        return False
    if not _MISSING_QR_RE.search(raw):
        return False
    # Blank/black display while scanning QR is a different complaint (official Q5 / DEMO-E).
    symptoms = _symptoms(raw)
    if any(s in symptoms for s in _VISIBILITY_SYMPTOMS):
        return False
    if _empty_display_phrase(raw) or _NO_IMAGE_RE.search(raw):
        return False
    return True


def _expand_symptom_families(hit: List[str]) -> List[str]:
    """Deterministic synonym/morphology expansion for known display symptom families."""
    out = list(hit)

    def _ensure(family: Tuple[str, ...]) -> None:
        if any(member in out for member in family):
            for member in family:
                if member not in out:
                    out.append(member)

    _ensure(_VISIBILITY_SYMPTOMS)
    _ensure(_FLICKER_SYMPTOMS)
    _ensure(_CRACK_SYMPTOMS)
    return out


def _empty_display_phrase(text: str) -> bool:
    return bool(_EMPTY_DISPLAY_RE.search(text or ""))


def _symptoms(text: str) -> Tuple[str, ...]:
    lowered = normalize(text)
    hit = [w for w in _SYMPTOM_WORDS if re.search(rf"\b{re.escape(w)}\b", lowered)]
    if _empty_display_phrase(text) or _NO_IMAGE_RE.search(text or ""):
        for member in _VISIBILITY_SYMPTOMS:
            if member not in hit:
                hit.append(member)
    hit = _expand_symptom_families(hit)
    return tuple(dict.fromkeys(hit))


def _device_state(text: str) -> Dict[str, Any]:
    low = text.lower()
    state: Dict[str, Any] = {}
    if re.search(r"\b(powers? on|powered on|rings?|otherwise works|phone works)\b", low):
        state["phone_powers_on"] = True
    if re.search(r"\brings?\b", low):
        state["phone_can_ring"] = True

    touch_fail = bool(_TOUCH_FAIL_RE.search(text or ""))
    if touch_fail:
        state["touch_responsive"] = False
    # Explicit visibility wording (distinct from blank/black).
    if re.search(r"\b(visible|can see|still see)\b", low):
        state["display_visible"] = True

    blankish = bool(
        re.search(r"\b(black|blank|dark|no (image|text|display))\b", low)
        or _empty_display_phrase(text)
        or _NO_IMAGE_RE.search(text or "")
    )
    flashish = bool(re.search(r"\b(flashes?|flickers?|flickering)\b", low))
    # Interactive use while reporting blank/flash ⇒ device is powered on
    # (in-app / intermittent display ≠ device-not-turning-on).
    if (blankish or flashish) and re.search(
        r"\b("
        r"when(?:ever)?\s+i\s+(?:tap|open|use|search|launch)|"
        r"while\s+(?:i\s+)?(?:am\s+)?using|"
        r"open(?:ing)?\s+(?:an?\s+)?(?:email|gmail|app)|"
        r"in\s+(?:gmail|the\s+app)|"
        r"after\s+it\s+works|"
        r"goes?\s+blank\s+again|"
        r"use\s+the\s+\w+\s+app|"
        r"happens?\s+with\s+other\s+apps"
        r")\b",
        low,
    ):
        state["phone_powers_on"] = True
    # Touch-unresponsive alone is not "display invisible".
    if blankish and state.get("display_visible") is not True:
        state["display_visible"] = False

    if re.search(r"\b(cracked|cracks|crack|broken glass|physically damaged)\b", low):
        state["physical_damage"] = True
    if re.search(r"\bno physical damage\b", low):
        state["physical_damage"] = False
    return state


def _context_tokens(text: str) -> Tuple[str, ...]:
    low = normalize(text)
    raw = text or ""
    ctx: List[str] = []
    for word in ("gmail", "email", "smart switch", "smart tutor", "qr", "charger"):
        if word in low:
            ctx.append(word.replace(" ", "_"))
    if _CAMERA_FLICKER_RE.search(raw):
        for tag in ("camera", "video"):
            if tag not in ctx:
                ctx.append(tag)
    if re.search(r"\b(open(?:ing)?\s+an?\s+app|whenever\s+i\s+open)\b", raw, re.I):
        if "opening_app" not in ctx:
            ctx.append("opening_app")
    if re.search(r"\b(open(?:ing)?\s+it|when\s+i\s+open|fold)\b", raw, re.I):
        if "opening_device" not in ctx:
            ctx.append("opening_device")
    return tuple(ctx)


def _operations(text: str) -> Tuple[str, ...]:
    op = extract_intent(text).operation
    polar = polarity(text)
    found: List[str] = []
    if polar:
        found.append(polar)
    elif op not in {"unknown", "open"}:
        found.append(op)
    if (
        _TIME_FORMAT_RE.search(text or "")
        and "update" not in found
        and re.search(r"\b(change|switch|set|make|want)\b", text or "", re.I)
    ):
        found.append("update")
    # Touch-sensitivity catalogue pairs are Enable/Disable; map increase/decrease.
    if _TOUCH_SENSITIVITY_RE.search(text or ""):
        mapped: List[str] = []
        for item in found:
            if item == "increase":
                mapped.append("enable")
            elif item == "decrease":
                mapped.append("disable")
            else:
                mapped.append(item)
        found = mapped
        if not found:
            if re.search(r"\b(increase|raise|boost|higher)\b", text or "", re.I):
                found.append("enable")
            elif re.search(r"\b(decrease|reduce|lower)\b", text or "", re.I):
                found.append("disable")
    return tuple(dict.fromkeys(found))


def _split_multi_issues(text: str) -> List[str]:
    parts = re.split(r"\band\b", text, flags=re.I)
    parts = [c.strip(" ,.") for c in parts if c.strip(" ,.")]
    if len(parts) < 2:
        return [text]
    labeled = [
        (
            c,
            [
                t
                for t in _targets(c)
                if t in {"display", "touchscreen", "battery", "floating_shortcut", "camera"}
            ],
        )
        for c in parts
    ]
    named = [t[0] for t in labeled if t[1]]
    primaries = {t[1][0] for t in labeled if t[1]}
    if len(primaries) >= 2 and len(named) >= 2:
        return named
    return [text]


def _select_primary(targets: List[str], symptoms: Tuple[str, ...], text: str, context: Tuple[str, ...]) -> str:
    """Choose primary target without letting product terms erase display symptoms."""
    if not targets:
        return "general"
    if "time_format" in targets or _TIME_FORMAT_RE.search(text or ""):
        return "time_format"
    if "fast_charging" in targets or _FAST_CHARGING_RE.search(text or ""):
        return "fast_charging"
    if "slow_charging" in targets or _SLOW_CHARGING_RE.search(text or ""):
        return "slow_charging"
    if "touch_sensitivity" in targets or _TOUCH_SENSITIVITY_RE.search(text or ""):
        return "touch_sensitivity"
    if "app_fullscreen" in targets:
        return "app_fullscreen"
    flick = any(s in symptoms for s in _FLICKER_SYMPTOMS)
    blank = any(s in symptoms for s in _VISIBILITY_SYMPTOMS) or bool(_NO_IMAGE_RE.search(text or ""))
    crack = any(s in symptoms for s in _CRACK_SYMPTOMS)
    if "camera" in targets and flick and _CAMERA_FLICKER_RE.search(text or ""):
        return "camera"
    # Charger-triggered screen flash/flicker is a display issue, not battery drain.
    if (
        "display" in targets
        and (flick or re.search(r"\bflash", text or "", re.I))
        and ("charger" in context or re.search(r"\bcharg", text or "", re.I))
    ):
        return "display"
    if "touchscreen" in targets and (
        _TOUCH_FAIL_RE.search(text or "")
        or any(s in symptoms for s in ("laggy", "lag", "delayed", "unresponsive"))
    ):
        # Dead inner display (no image) + touch failure → display primary; allow data-access SIIS.
        if blank or _NO_IMAGE_RE.search(text or ""):
            if "display" in targets:
                return "display"
        if not blank and not crack:
            return "touchscreen"
    if blank or crack or (flick and "display" in targets):
        if "display" in targets:
            return "display"
    if "smart_switch" in targets and blank:
        return "display" if "display" in targets else "smart_switch"
    return targets[0]


def understand_query(query: str) -> StructuredQuery:
    original = query or ""
    device_m = _DEVICE_RE.search(original)
    device = device_m.group(1).lower() if device_m else ""
    symptoms = _symptoms(original)
    context = _context_tokens(original)
    operations = _operations(original)
    dstate = _device_state(original)
    # Touch-only: do not invent display_invisible; keep explicit visible=True / no-image blank.
    if (
        dstate.get("touch_responsive") is False
        and dstate.get("display_visible") is not True
        and not any(s in symptoms for s in _VISIBILITY_SYMPTOMS)
        and not _NO_IMAGE_RE.search(original)
    ):
        dstate.pop("display_visible", None)

    chunks = _split_multi_issues(original)
    issues: List[QueryIssue] = []
    for chunk in chunks:
        tgts = _targets(chunk)
        chunk_symptoms = _symptoms(chunk) or symptoms
        chunk_ctx = _context_tokens(chunk) or context
        primary_chunk = _select_primary(tgts, chunk_symptoms, chunk, chunk_ctx)
        issues.append(
            QueryIssue(
                target=primary_chunk,
                symptoms=chunk_symptoms,
                context=chunk_ctx,
                operations=_operations(chunk) or operations,
            )
        )
    targets = _targets(original)
    primary = _select_primary(targets, symptoms, original, context)
    # Ensure smart_switch context survives when display is primary.
    if "smart_switch" in targets and "smart_switch" not in context:
        context = tuple([*context, "smart_switch"])
    if primary == "camera" and "camera" not in context:
        context = tuple([*context, "camera", "video"])

    intent = "troubleshoot"
    if primary == "time_format":
        intent = "time_format"
    elif primary in {"fast_charging", "slow_charging", "touch_sensitivity", "app_fullscreen"}:
        intent = primary
    elif operations and primary != "general":
        intent = f"{operations[0]}_{primary}"
    elif primary != "general":
        intent = f"{primary}_troubleshooting"
    constraints: List[str] = []
    if dstate.get("phone_powers_on"):
        constraints.append("device_powers_on")
    if dstate.get("physical_damage") is True:
        constraints.append("physical_damage")
    if dstate.get("physical_damage") is False:
        constraints.append("no_physical_damage")
    if dstate.get("touch_responsive") is False:
        constraints.append("touch_unresponsive")
    if dstate.get("display_visible") is False:
        constraints.append("display_invisible")
    if dstate.get("display_visible") is True:
        constraints.append("display_visible")
    states = tuple(sorted(dstate.keys()))
    return StructuredQuery(
        original=original,
        device=device,
        target=primary,
        symptoms=symptoms,
        states=states,
        context=context,
        constraints=tuple(constraints),
        operations=operations,
        device_state=dstate,
        intent=intent,
        issues=tuple(issues),
    )
