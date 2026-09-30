"""Build official Action/Goal objects from SIIS evidence and catalogue copies only."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from sgte.deeplink_repo import DeeplinkHit, DeeplinkRepository
from sgte.extractor import CandidateAction
from sgte.official_schema import (
    Action,
    Condition,
    Deeplink,
    Goal,
    ResultTypes,
    StepGroup,
    ValidationDeepLink,
    actionCategory,
)
from sgte.query.understand import StructuredQuery, understand_query
from sgte.siis_repo import SiisHit
from sgte.url_leak import url_leak_reasons

_CRITICAL = re.compile(
    r"\b(factory data reset|factory reset|safe mode|firmware|"
    r"software update|force a restart)\b",
    re.IGNORECASE,
)
_CRITICAL_HEADING = re.compile(
    r"^(restart your device|restarting your device)\b",
    re.IGNORECASE,
)
_MANUAL = re.compile(
    r"\b(service center|repair|contact samsung|walk-in|mail-in|premium care|"
    r"physical damage|cracked|liquid exposure|schedule a repair|authorized service)\b",
    re.IGNORECASE,
)
_STEP_PREFIX = re.compile(r"^(?:step\s+\d+\s*[:.-]\s*|\d+\.\s*)", re.IGNORECASE)
_WORD = re.compile(r"[A-Za-z0-9']+")

_RANK = {
    actionCategory.auto: 0,
    actionCategory.critical: 1,
    actionCategory.manual: 2,
}

# Generic function words only — not Samsung procedure knowledge.
_TITLE_STOP = frozenset(
    """
    a an the and or but if then to of in on at by for from with as is are was were
    be been being it its this that these those you your we our they them their my me i
    not no so such can will just also into over after before when while about more most
    other some any only same own too very please samsung phone tablet galaxy device
    does did do don't wont won't some things check first use how
    """.split()
)

_DESC_STOP = frozenset(
    """
    a an the and or but if then to of in on at by for from with as is are was were
    be been being it its this that these those you your we our they them their my me i
    please please samsung galaxy phone tablet device
    """.split()
)

_PROPER = frozenset({"gmail", "bixby", "qr", "usb", "hdmi", "wifi", "wi-fi", "apps", "edge"})
_CONFIG_OPS = frozenset({"enable", "disable", "increase", "decrease"})
_ACTION_VERBS = frozenset(
    {
        "check",
        "force",
        "charge",
        "attempt",
        "enable",
        "disable",
        "remove",
        "customize",
        "use",
        "open",
        "turn",
        "adjust",
        "select",
        "set",
        "restart",
        "clear",
        "inspect",
        "schedule",
        "contact",
        "press",
        "tap",
        "swipe",
        "hold",
        "wipe",
        "uninstall",
        "connect",
        "follow",
        "try",
        "ensure",
        "locate",
        "switch",
        "access",
        "back",
        "navigate",
        "go",
        "insert",
        "readd",
        "re-add",
    }
)


@dataclass
class ActionTrace:
    source_row_id: str
    source_section: str
    evidence_text: str
    catalogue_id: Optional[str]
    deeplink_uri: Optional[str]
    deeplink_score: Optional[float]
    deeplink_evidence: dict
    category: str
    source_index: int


@dataclass
class BuiltPlan:
    goal: Optional[Goal]
    traces: List[ActionTrace] = field(default_factory=list)


def _clean_name(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _sentence_case(words: Sequence[str]) -> str:
    """First word capitalized; later words lowercased unless proper nouns."""
    out: List[str] = []
    for i, raw in enumerate(words):
        token = (raw or "").strip()
        if not token:
            continue
        low = token.lower()
        if low in {"smart"} and i + 1 < len(words) and words[i + 1].lower() == "switch":
            out.append("Smart")
        elif low == "switch" and out and out[-1] == "Smart":
            out.append("Switch")
        elif low in _PROPER or low == "gmail":
            out.append(token[:1].upper() + token[1:].lower() if token.isalpha() else token)
        elif i == 0:
            out.append(token[:1].upper() + token[1:].lower())
        else:
            out.append(token.lower())
    return " ".join(out)


def _title_case_topic(title: str) -> str:
    parts = []
    for word in title.split():
        low = word.lower()
        if low in {"smart"} and parts and False:
            parts.append("Smart")
        elif "-" in word:
            parts.append("-".join(p[:1].upper() + p[1:].lower() if p else p for p in word.split("-")))
        else:
            parts.append(word[:1].upper() + word[1:].lower())
    # Keep Smart Switch as a unit.
    joined = " ".join(parts)
    joined = re.sub(r"\bSmart switch\b", "Smart Switch", joined, flags=re.I)
    joined = re.sub(r"\bGmail\b", "Gmail", joined)
    return joined


def format_goal_title(
    *,
    query: str = "",
    structured: Optional[StructuredQuery] = None,
    hit: Optional[SiisHit] = None,
) -> str:
    """Deterministic 2–3 word sentence-case topic from query/evidence wording."""
    sq = structured or (understand_query(query) if query else None)
    q_low = (query or (sq.original if sq else "") or "").lower()
    hit_title = (hit.title if hit else "") or ""
    hit_low = hit_title.lower()

    if sq:
        symptoms = set(sq.symptoms)
        context = set(sq.context)
        damage = sq.device_state.get("physical_damage")

        if sq.target == "email" or "gmail" in context or "email" in context:
            return "Gmail display" if ("black" in symptoms or "blank" in symptoms or "screen" in q_low) else "Email connection"
        if sq.target == "time_format":
            return "Time format"
        if sq.target == "fast_charging":
            return "Fast charging"
        if sq.target == "touch_sensitivity":
            return "Touch sensitivity"
        if sq.target == "app_fullscreen":
            return "App full screen"
        if sq.target == "camera":
            return "Video flicker"
        if sq.target == "floating_shortcut":
            return "Floating shortcut"
        # Prefer SIIS-aligned titles when the paired article is clearly multi-window / edge.
        if "multi window" in hit_low or "app pairs" in hit_low or "edge panel" in hit_low:
            if "icon" in q_low or "multi" in q_low or "edge panel" in q_low:
                return "Multi window"
            if "edge" in hit_low and "icon" in q_low:
                return "Multi window"
        if sq.target == "smart_switch" or "smart_switch" in context:
            if "black" in symptoms or "blank" in symptoms or "dark" in symptoms:
                return "Black screen"
            return "Smart Switch"
        if damage is True or "cracked" in symptoms or "crack" in symptoms or "cracks" in symptoms:
            return "Cracked screen"
        if sq.target == "touchscreen" or "laggy" in symptoms or "delayed" in symptoms:
            return "Touchscreen lag"
        # Preserve multi-symptom: flicker + black stays a combined display issue label.
        if (
            ("flicker" in symptoms or "flickers" in symptoms or "flickering" in symptoms)
            and ("black" in symptoms or "blank" in symptoms or "dark" in symptoms)
        ):
            return "Screen flicker"
        if "flicker" in symptoms or "flickers" in symptoms or "flickering" in symptoms:
            return "Screen flicker"
        if "distorted" in symptoms:
            return "Screen distortion"
        if "black" in symptoms or "dark" in symptoms:
            return "Black screen"
        if "blank" in symptoms or "white" in symptoms:
            return "Blank screen"
        if sq.target == "battery" or "drain" in symptoms or "drains" in symptoms or "dies" in symptoms:
            return "Battery drain"
        if "charger" in context or re.search(r"\bcharg", q_low):
            return "Battery charging"
        if sq.target == "floating_shortcut":
            return "Floating shortcut"
        if sq.target == "mouse_keys":
            return "Mouse keys"
        if sq.target == "backup":
            return "Data backup"
        if "rotate" in q_low or "rotation" in hit_low:
            return "Screen rotation"
        if "mirror" in q_low or "mirroring" in hit_low:
            return "Screen mirroring"
        if sq.target == "display":
            if "black" in q_low:
                return "Black screen"
            if "blank" in q_low:
                return "Blank screen"
            return "Display issue"

    # Evidence-title fallback using words already present in the SIIS title.
    if "email" in hit_low:
        return "Email connection"
    if "smart switch" in hit_low:
        return "Smart Switch"
    if "cracked" in hit_low or "bleeding" in hit_low:
        return "Cracked screen"
    if "touchscreen" in hit_low:
        return "Touchscreen lag"
    if "flicker" in hit_low:
        return "Screen flicker"
    if "blank" in hit_low or "black" in hit_low:
        return "Black screen"
    if "rotat" in hit_low:
        return "Screen rotation"
    if "mirror" in hit_low:
        return "Screen mirroring"
    if "multi window" in hit_low:
        return "Multi window"
    if "access" in hit_low and "data" in hit_low:
        return "Data access"

    raw_words = _WORD.findall(hit_title) if hit_title else []
    clean = [w for w in raw_words if w.lower() not in _TITLE_STOP]
    if len(clean) >= 2:
        words = clean[:2]
    elif len(clean) == 1:
        words = [clean[0], "issue"]
    else:
        words = ["Device", "issue"]
    return _sentence_case(words)


def format_goal_statement(title: str, structured: Optional[StructuredQuery] = None) -> str:
    kind = "Troubleshooting"
    if structured is not None:
        ops = set(structured.operations)
        if ops & _CONFIG_OPS or any(
            structured.intent.startswith(prefix) for prefix in ("enable_", "disable_", "increase_", "decrease_")
        ):
            kind = "Configuration"
    topic = _title_case_topic(title)
    return f"Follow these steps to perform this {topic} {kind}"


def _format_desc_token(token: str, index: int) -> str:
    low = token.lower()
    if low in {"smart"}:
        return "Smart"
    if low == "switch":
        return "Switch"
    if low in _PROPER or low == "gmail":
        return token[:1].upper() + token[1:].lower()
    if index == 0:
        return low
    return low


_TRAILING_BAD = frozenset({"and", "or", "for", "to", "of", "the", "a", "an", "with", "from", "by", "on", "in", "at"})


def _fit_description_body(words: Sequence[str]) -> List[str]:
    """Keep 3–5 content words so 'It will' + body is 5–7 tokens."""
    cleaned = [w for w in words if w]
    if len(cleaned) > 5:
        cleaned = list(cleaned[:5])
    while len(cleaned) > 3 and cleaned[-1].lower() in _TRAILING_BAD:
        cleaned.pop()
    return cleaned


def format_action_description(action: CandidateAction) -> str:
    """Grounded 5–7 word description starting with 'It will'."""
    heading = _STEP_PREFIX.sub("", _clean_name(action.heading or "")).strip()
    source = heading
    if not source and action.steps:
        source = _clean_name(action.steps[0].text)
    source = source.rstrip(".")
    tokens = _WORD.findall(source)
    if not tokens and action.evidence_text:
        tokens = _WORD.findall(action.evidence_text)[:8]
    if not tokens:
        return "It will guide this troubleshooting step"

    low0 = tokens[0].lower()
    body: List[str]
    if low0 in _ACTION_VERBS or low0.replace("-", "") in _ACTION_VERBS:
        body = [t for t in tokens if t.lower() not in {"please"}]
        # Drop redundant leading articles after the verb when needed for length.
        body = _fit_description_body(body)
        if len(body) < 3:
            extras = [
                w
                for w in _WORD.findall(action.evidence_text or "")
                if w.lower() not in _DESC_STOP and w.lower() not in {b.lower() for b in body}
            ]
            for extra in extras:
                body.append(extra)
                if len(body) >= 3:
                    break
        if len(body) < 3:
            body = list(body) + ["this", "step"][: 3 - len(body)]
        body = _fit_description_body(body)
    else:
        content = [t for t in tokens if t.lower() not in _DESC_STOP]
        if not content:
            content = tokens[:3]
        # Prefer concrete verbs grounded in the heading meaning.
        if any(w.lower() in {"damage", "cracked", "crack", "liquid"} for w in content):
            body = ["check"] + content[:3]
        elif any(w.lower() in {"restart", "reboot"} for w in content):
            body = ["force", "a", "restart"]
        else:
            body = ["address"] + content[:3]
        body = _fit_description_body(body)
        if len(body) < 3:
            body = list(body) + ["this", "issue"][: 3 - len(body)]

    body = _fit_description_body(body)
    while len(body) < 3:
        body.append("step")
    formatted = [_format_desc_token(w, i) for i, w in enumerate(body)]
    # Fix Smart Switch adjacency after lowercasing pass.
    text = "It will " + " ".join(formatted)
    text = re.sub(r"\bsmart switch\b", "Smart Switch", text, flags=re.I)
    words = text.split()
    if len(words) < 5:
        words.extend(["this", "step"][: 5 - len(words)])
    if len(words) > 7:
        words = words[:7]
    return " ".join(words)


def _classify(action: CandidateAction, hit: Optional[DeeplinkHit]) -> actionCategory:
    heading = (action.heading or "").strip()
    if _CRITICAL_HEADING.match(heading) or _CRITICAL.search(heading):
        return actionCategory.critical
    if _MANUAL.search(heading) or _MANUAL.search(action.evidence_text or ""):
        return actionCategory.manual
    if hit is not None:
        return actionCategory.auto
    return actionCategory.manual


def validation_from_catalogue(hit: DeeplinkHit) -> Optional[ValidationDeepLink]:
    raw = hit.validation
    if not raw or not raw.get("deeplink") or not raw.get("key"):
        return None
    kwargs = {"deeplink": raw["deeplink"], "key": raw["key"]}
    if raw.get("resultType"):
        try:
            kwargs["resultType"] = ResultTypes(raw["resultType"])
        except ValueError:
            pass
    if raw.get("condition"):
        try:
            kwargs["condition"] = Condition(raw["condition"])
        except ValueError:
            pass
    if raw.get("value") is not None:
        kwargs["value"] = str(raw["value"])
    return ValidationDeepLink(**kwargs)


def actionable_from_catalogue(hit: DeeplinkHit) -> Deeplink:
    row = hit.record
    return Deeplink(
        deeplink=row.deeplink,
        description=row.description,
        message=row.message or "",
        originalType=row.originalType,
    )


def _order_actions(built: List[tuple[Action, ActionTrace]]) -> List[tuple[Action, ActionTrace]]:
    return sorted(built, key=lambda item: (_RANK[item[0].category], item[1].source_index))


def build_plan(
    hit: SiisHit,
    candidates: Sequence[CandidateAction],
    deeplinks: DeeplinkRepository,
    *,
    structured: Optional[StructuredQuery] = None,
    query: str = "",
) -> BuiltPlan:
    sq = structured or (understand_query(query) if query else None)
    built: List[tuple[Action, ActionTrace]] = []
    for index, candidate in enumerate(candidates):
        step_texts = [step.text for step in candidate.steps if not url_leak_reasons(step.text)]
        if not step_texts:
            continue
        match = deeplinks.find_best_deeplink(
            candidate.heading,
            step_texts,
            candidate.evidence_text,
        )
        category = _classify(candidate, match)
        actionable = None
        validation = None
        catalogue_id = None
        uri = None
        score = None
        evidence: dict = {}
        if category != actionCategory.manual and match is not None:
            actionable = actionable_from_catalogue(match)
            validation = validation_from_catalogue(match)
            catalogue_id = match.id
            uri = match.deeplink
            score = match.score
            evidence = dict(match.evidence)
            if actionable.deeplink != match.record.deeplink:
                actionable = None
                validation = None
                catalogue_id = None
                uri = None
                score = None
                evidence = {}
                category = actionCategory.manual

        action_name = _clean_name(candidate.heading)
        if not action_name:
            continue
        action = Action(
            actionName=action_name,
            description=format_action_description(candidate),
            stepGroups=[
                StepGroup(
                    steps=list(step_texts),
                    actionableDeeplink=actionable,
                    validationDeeplink=validation,
                )
            ],
            category=category,
        )
        trace = ActionTrace(
            source_row_id=candidate.source_row_id,
            source_section=candidate.source_section,
            evidence_text=candidate.evidence_text,
            catalogue_id=catalogue_id,
            deeplink_uri=uri,
            deeplink_score=score,
            deeplink_evidence=evidence,
            category=category.value,
            source_index=index,
        )
        built.append((action, trace))

    if not built:
        return BuiltPlan(goal=None, traces=[])

    ordered = _order_actions(built)
    actions = [item[0] for item in ordered]
    traces = [item[1] for item in ordered]
    title = format_goal_title(query=query, structured=sq, hit=hit)
    goal = Goal(
        goal=format_goal_statement(title, sq),
        title=title,
        actions=actions,
        score=float(min(max(hit.score, 0.0), 1.0)),
    )
    return BuiltPlan(goal=goal, traces=traces)
