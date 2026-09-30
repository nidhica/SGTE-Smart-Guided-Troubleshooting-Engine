"""Reject LLM output that is not supported by retrieved SIIS text."""

from __future__ import annotations

import re
from typing import Iterable, List, Sequence, Tuple

from sgte.lexical import token_list
from sgte.url_leak import url_leak_reasons

_PATH_HINT = re.compile(
    r"settings\s*[>→/]+\s*\w|\bgo to settings\s*>",
    re.IGNORECASE,
)


def coverage(text: str, source: str) -> float:
    needles = token_list(text, min_len=4)
    if not needles:
        needles = token_list(text, min_len=3)
    if not needles:
        return 1.0
    hay = set(token_list(source, min_len=3, drop_stopwords=False))
    return sum(1 for t in needles if t in hay) / len(needles)


def is_supported(text: str, source: str, min_coverage: float = 0.7) -> bool:
    if url_leak_reasons(text):
        return False
    return coverage(text, source) >= min_coverage


def looks_like_invented_path(text: str, source: str) -> bool:
    if not _PATH_HINT.search(text):
        return False
    return coverage(text, source) < 0.85


def multi_screen_name(action_name: str) -> bool:
    lowered = action_name.lower()
    if " and " not in lowered:
        return False
    features = ("display", "battery", "wifi", "wi-fi", "apps", "camera", "sound", "lock")
    hits = [f for f in features if f in lowered]
    return len(set(hits)) >= 2


def grounded_steps(steps: Sequence[str], source: str) -> Tuple[List[str], List[str]]:
    kept: List[str] = []
    rejected: List[str] = []
    for step in steps:
        if looks_like_invented_path(step, source) or not is_supported(step, source):
            rejected.append(step)
            continue
        kept.append(step)
    return kept, rejected
