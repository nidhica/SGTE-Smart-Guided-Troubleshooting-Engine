"""Deterministic text normalization and explainable lexical scoring. No embeddings."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from typing import Dict, FrozenSet, List, Sequence, Set

# Generic English function words only — not Samsung-specific knowledge.
STOPWORDS = frozenset(
    """
    a an the and or but if then than to of in on at by for from with as is are was were
    be been being it its this that these those you your we our they them their my me i
    not no so such can will just also into over after before when while about more most
    other some any only same own than too very please do does did
    """.split()
)

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_WS = re.compile(r"\s+")

# Expand before apostrophe stripping so "won't" does not become the content token "won".
_CONTRACTION_RULES: List[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bwon't\b", re.IGNORECASE), "will not"),
    (re.compile(r"\bcan't\b", re.IGNORECASE), "cannot"),
    (re.compile(r"\bdon't\b", re.IGNORECASE), "do not"),
    (re.compile(r"\bdoesn't\b", re.IGNORECASE), "does not"),
    (re.compile(r"\bdidn't\b", re.IGNORECASE), "did not"),
    (re.compile(r"\bisn't\b", re.IGNORECASE), "is not"),
    (re.compile(r"\baren't\b", re.IGNORECASE), "are not"),
    (re.compile(r"\bcouldn't\b", re.IGNORECASE), "could not"),
    (re.compile(r"\bwouldn't\b", re.IGNORECASE), "would not"),
    (re.compile(r"\bshouldn't\b", re.IGNORECASE), "should not"),
]

# Join short hyphenated compounds (e.g. Wi-Fi → wifi) before length filtering.
_HYPHEN_COMPOUND = re.compile(r"\b([A-Za-z]{1,4})-([A-Za-z]{1,4})\b")
# Standalone 2-letter uppercase acronyms in the original input (e.g. TV).
_UPPER_ACRONYM = re.compile(r"\b[A-Z]{2}\b")

# Samsung-kit anonymized product names → corpus SIIS wording (narrow aliases).
_CORPUS_PRODUCT_ALIASES: List[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\btechcorp\b", re.IGNORECASE), "samsung"),
    (re.compile(r"\bnexa\b", re.IGNORECASE), "galaxy"),
    (re.compile(r"\bquick\s+assist\b", re.IGNORECASE), "smart tutor"),
    (re.compile(r"\bdata\s+transfer\b", re.IGNORECASE), "smart switch"),
]


def expand_corpus_product_aliases(text: str) -> str:
    """Map kit anonymized product names onto SIIS corpus vocabulary."""
    out = text or ""
    for pattern, repl in _CORPUS_PRODUCT_ALIASES:
        out = pattern.sub(repl, out)
    return out


# Narrow morphology only — not a general stemmer. Aligns flicker/crack surface forms
# for lexical overlap, symptom focus, and head-evidence token compare.
_TOKEN_MORPH_CANON: Dict[str, str] = {
    "flickers": "flicker",
    "flickering": "flicker",
    "flashes": "flicker",
    "flash": "flicker",
    "cracks": "crack",
    "cracked": "crack",
}


# Empty-display paraphrases (screen/display-scoped) → blank for lexical/symptom alignment.
_EMPTY_DISPLAY_PHRASE_RULES: List[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"\b((?:screen|display)\s+(?:is\s+)?)(?:showing|sees)\s+nothing\b",
            re.IGNORECASE,
        ),
        r"\1blank",
    ),
    (
        re.compile(
            r"\b(?:showing|sees)\s+nothing((?:\s+\w+){0,6}\s+(?:on\s+(?:the\s+)?)?(?:screen|display))\b",
            re.IGNORECASE,
        ),
        r"blank\1",
    ),
    (
        re.compile(r"\bnothing\s+on\s+the\s+(screen|display)\b", re.IGNORECASE),
        r"blank on the \1",
    ),
]


def expand_contractions(text: str) -> str:
    """Deterministic English contraction expansion (negation-preserving)."""
    out = text or ""
    for pattern, repl in _CONTRACTION_RULES:
        out = pattern.sub(repl, out)
    return out


def expand_empty_display_phrases(text: str) -> str:
    """Map screen/display empty paraphrases to blank (not bare 'nothing')."""
    out = text or ""
    for pattern, repl in _EMPTY_DISPLAY_PHRASE_RULES:
        out = pattern.sub(repl, out)
    return out


def _short_acronyms(original: str) -> Set[str]:
    """Lowercased 2-letter acronyms that appear uppercase in the original text."""
    folded = unicodedata.normalize("NFKC", original or "")
    return {m.group(0).lower() for m in _UPPER_ACRONYM.finditer(folded)}


def normalize(text: str) -> str:
    if not text:
        return ""
    folded = unicodedata.normalize("NFKC", text)
    folded = expand_contractions(folded)
    folded = expand_empty_display_phrases(folded)
    folded = expand_corpus_product_aliases(folded)
    folded = _HYPHEN_COMPOUND.sub(lambda m: f"{m.group(1)}{m.group(2)}", folded)
    folded = folded.lower()
    # Straight and common curly apostrophes → space (after contraction expansion).
    for mark in ("'", "\u2019", "\u2018", "`"):
        folded = folded.replace(mark, " ")
    folded = _NON_ALNUM.sub(" ", folded)
    return _WS.sub(" ", folded).strip()


def token_list(text: str, min_len: int = 3, drop_stopwords: bool = True) -> List[str]:
    allow_short = _short_acronyms(text)
    out: List[str] = []
    for raw in normalize(text).split(" "):
        if not raw:
            continue
        if drop_stopwords and raw in STOPWORDS:
            continue
        # Keep intentional short acronyms (TV); never promote stopwords (to/on/in/of).
        if len(raw) < min_len and raw not in allow_short:
            continue
        if raw in STOPWORDS:
            continue
        out.append(_TOKEN_MORPH_CANON.get(raw, raw))
    return out


def tokens(text: str, min_len: int = 3, drop_stopwords: bool = True) -> FrozenSet[str]:
    return frozenset(token_list(text, min_len=min_len, drop_stopwords=drop_stopwords))


def overlap_score(query: str, document: str) -> float:
    query_tokens = tokens(query)
    if not query_tokens:
        return 0.0
    shared = query_tokens & tokens(document)
    return len(shared) / len(query_tokens)


def idf_weights(documents: Sequence[str]) -> Dict[str, float]:
    n = max(len(documents), 1)
    df: Counter[str] = Counter()
    for doc in documents:
        df.update(tokens(doc))
    return {term: math.log((n + 1) / (count + 1)) + 1.0 for term, count in df.items()}


def weighted_overlap(query: str, document: str, idf: Dict[str, float] | None = None) -> float:
    return weighted_overlap_tokens(tokens(query), tokens(document), idf)


def weighted_overlap_tokens(
    query_tokens: FrozenSet[str],
    document_tokens: FrozenSet[str],
    idf: Dict[str, float] | None = None,
) -> float:
    """Same scoring as weighted_overlap, using pre-tokenized sets (behavior-identical)."""
    if not query_tokens:
        return 0.0
    shared = query_tokens & document_tokens
    if not shared:
        return 0.0
    weights = idf or {}

    def w(term: str) -> float:
        return weights.get(term, 1.0)

    return sum(w(t) for t in shared) / sum(w(t) for t in query_tokens)
