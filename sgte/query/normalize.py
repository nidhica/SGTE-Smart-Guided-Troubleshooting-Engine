"""Deterministic query normalization for the semantic cache.

Polarity and control words are preserved. This is not SIIS knowledge.
"""

from __future__ import annotations

import re
import unicodedata

_WS = re.compile(r"\s+")
_URL = re.compile(r"https?://\S+|bixby://\S+", re.IGNORECASE)
_PUNCT = re.compile(r"[^a-z0-9]+")

# Safe fillers only. Never drop polarity / control words.
PROTECTED = frozenset(
    {
        "enable",
        "disable",
        "enabled",
        "disabled",
        "on",
        "off",
        "increase",
        "decrease",
        "open",
        "close",
        "turn",
        "activate",
        "deactivate",
        "switch",
    }
)

FILLERS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "if",
        "then",
        "my",
        "me",
        "i",
        "we",
        "you",
        "your",
        "our",
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
        "really",
        "very",
        "quite",
        "please",
        "just",
        "currently",
        "actually",
        "basically",
        "extremely",
        "totally",
        "completely",
        "so",
        "too",
        "also",
        "even",
        "still",
        "kind",
        "kinda",
        "sort",
        "bit",
        "hello",
        "hi",
        "hey",
        "thanks",
        "thank",
        "help",
        "issue",
        "problem",
        "question",
        "report",
        "user",
        "reports",
    }
)


def strip_urls(text: str) -> str:
    return _URL.sub(" ", text or "")


def normalize_query(text: str) -> str:
    """Lowercase, strip URLs/punctuation, collapse space, drop safe fillers."""
    raw = strip_urls(text or "")
    folded = unicodedata.normalize("NFKC", raw).lower().replace("'", " ")
    folded = _PUNCT.sub(" ", folded)
    tokens = []
    for tok in _WS.split(folded.strip()):
        if not tok:
            continue
        if tok in PROTECTED:
            tokens.append(tok)
            continue
        if tok in FILLERS:
            continue
        tokens.append(tok)
    return " ".join(tokens)
