"""Phase 23 — Conservative paraphrase matching (Policy C).

Deterministic post-selection helpers used by HybridDeeplinkMapper.
Does not invent catalogue URIs. Exact-message queries are handled separately
by Phase 19 preference and must not enter this path.
"""
from __future__ import annotations

import re
from typing import List, Optional, Sequence

_AMBIG = "ambiguous: too close to an alternative"
_PREFIX = re.compile(
    r"^(Enable|Disable|View|Open|Switch|Adjust|Increase|Decrease)\s+(.+)$",
    re.I,
)
_ADJUSTISH = re.compile(r"^(Adjust|Increase|Decrease)\s+", re.I)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def query_polarity(query: str) -> Optional[str]:
    q = norm(query)
    if q.startswith("turn on ") or q.startswith("how do i enable ") or q.startswith("enable "):
        return "enable"
    if q.startswith("turn off ") or q.startswith("how do i disable ") or q.startswith("disable "):
        return "disable"
    if q.startswith("open ") or q.startswith("how do i open ") or q.startswith("view "):
        return "view"
    if q.startswith("change ") or q.startswith("configure ") or q.startswith("how do i switch "):
        return "change"
    return None


def message_polarity(message: str) -> Optional[str]:
    m = norm(message)
    if m.startswith("enable "):
        return "enable"
    if m.startswith("disable "):
        return "disable"
    if m.startswith("view ") or m.startswith("open "):
        return "view"
    if _ADJUSTISH.match(message or ""):
        return "adjust"
    return None


def recover_stem_from_query(query: str) -> Optional[str]:
    q = (query or "").strip()
    patterns = [
        r"(?i)^turn on\s+(.+)$",
        r"(?i)^turn off\s+(.+)$",
        r"(?i)^how do i enable\s+(.+)\?$",
        r"(?i)^how do i disable\s+(.+)\?$",
        r"(?i)^how do i open\s+(.+)\?$",
        r"(?i)^how do i switch\s+(.+)\?$",
        r"(?i)^open\s+(.+)$",
        r"(?i)^change\s+(.+?)\s+settings$",
        r"(?i)^change\s+(.+)$",
        r"(?i)^configure\s+(.+)$",
        r"(?i)^view\s+(.+)$",
        r"(?i)^enable\s+(.+)$",
        r"(?i)^disable\s+(.+)$",
    ]
    for pat in patterns:
        m = re.match(pat, q)
        if m:
            return m.group(1).strip()
    return None


def message_stem(message: str) -> str:
    m = _PREFIX.match((message or "").strip())
    if m:
        return m.group(2).strip()
    return (message or "").strip()


def is_paraphrase_query(action_text: str) -> bool:
    """True when action text looks like a generated paraphrase (not bare catalogue message)."""
    return recover_stem_from_query(action_text) is not None and query_polarity(action_text) is not None


def named_collision_reason(
    *,
    query: str,
    messages: Sequence[str],
    validation_keys: Sequence[str],
) -> Optional[str]:
    stem = recover_stem_from_query(query)
    stem_n = norm(stem) if stem else None
    msgs = [norm(m) for m in messages]

    if stem_n and "security settings" in stem_n and "more" not in stem_n:
        if any("more security" in m for m in msgs) and any(
            (m == "view security settings" or (m.endswith("security settings") and "more " not in m))
            for m in msgs
        ):
            return "paraphrase abstain: security vs more security collision"

    if stem_n and "relumino outline" in stem_n and "shortcut" not in stem_n:
        if any("relumino outline shortcut" in m for m in msgs):
            return "paraphrase abstain: relumino outline vs shortcut collision"

    if stem_n and "double tap to turn on screen" in stem_n:
        if any("double tap to turn off screen" in m for m in msgs):
            return "paraphrase abstain: double-tap on/off collision"

    if stem_n == "adaptive display" or norm(query).endswith("adaptive display"):
        keys = {k.strip().lower() for k in validation_keys if (k or "").strip()}
        if len(keys) > 1:
            return "paraphrase abstain: adaptive display duplicate validation keys"

    return None


def candidate_passes_paraphrase_filters(
    *,
    query: str,
    message: str,
) -> bool:
    """Polarity, view-vs-adjust, and exact stem compatibility."""
    q_pol = query_polarity(query)
    stem = recover_stem_from_query(query)
    stem_n = norm(stem) if stem else None
    mp = message_polarity(message)

    if q_pol in {"enable", "disable"} and mp is not None and mp != q_pol:
        return False
    if q_pol == "view":
        # View/Open paraphrases must not map to Adjust/Increase/Decrease or enable/disable.
        if mp in {"enable", "disable", "adjust"}:
            return False
        if mp not in {None, "view"}:
            return False
    if stem_n and norm(message_stem(message)) != stem_n:
        return False
    return True


def apply_conservative_paraphrase_selection(
    scored: list,
    action_text: str,
    *,
    uniqueness_abs: float,
    uniqueness_ratio: float,
    same_screen,
) -> None:
    """Mutate CandidateScore list in place (Policy C).

    Expects Phase 19 exact-message preference already applied. Clears only
    ambiguity rejections for paraphrase resolution; other rejections stay.

    Order: clear ambiguity → polarity/stem/view-adjust filters → named
    collisions among survivors → multi-message abstention → uniqueness.
    Filtering before collision lets stem-distinct twins (e.g. double-tap on vs
    off) resolve instead of blanket-abstaining whenever both were retrieved.
    """
    if not is_paraphrase_query(action_text):
        return

    pool = [
        c
        for c in scored
        if c.rejection_reason is None or c.rejection_reason == _AMBIG
    ]
    if not pool:
        return

    for c in pool:
        if c.rejection_reason == _AMBIG:
            c.rejection_reason = None

    # Polarity / stem / view-vs-adjust first.
    for c in pool:
        if c.rejection_reason is not None:
            continue
        if not candidate_passes_paraphrase_filters(query=action_text, message=c.message or ""):
            c.rejection_reason = "paraphrase reject: polarity/stem/view-adjust mismatch"

    survivors = [c for c in pool if c.rejection_reason is None]
    if not survivors:
        return

    msgs = [c.message or "" for c in survivors]
    keys = []
    for c in survivors:
        raw = c.record.validation or {}
        keys.append(str(raw.get("key") or ""))

    collision = named_collision_reason(
        query=action_text, messages=msgs, validation_keys=keys
    )
    if collision:
        for c in survivors:
            c.rejection_reason = collision
        return

    distinct_msgs = {norm(c.message or "") for c in survivors}
    if len(distinct_msgs) > 1:
        for c in survivors:
            c.rejection_reason = "paraphrase abstain: multiple plausible messages"
        return

    if len(survivors) == 1:
        return

    survivors.sort(key=lambda c: (-c.final_score, c.catalogue_id or ""))
    all_same = all(same_screen(survivors[0], other) for other in survivors[1:])
    if all_same:
        return

    best, second = survivors[0], survivors[1]
    unique = same_screen(best, second) or (
        best.final_score >= second.final_score + uniqueness_abs
        or best.final_score >= second.final_score * uniqueness_ratio
    )
    if not unique:
        for c in survivors:
            c.rejection_reason = "paraphrase abstain: ambiguous after filters"
        return

    for c in survivors[1:]:
        if not same_screen(best, c):
            c.rejection_reason = "paraphrase reject: not unique after filters"
