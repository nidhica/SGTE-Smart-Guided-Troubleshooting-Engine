"""Deterministic register-aware query paraphrases. No LLM; no invented facts."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence, Set, Tuple

from sgte.query.canonical import canonicalize
from sgte.query.normalize import normalize_query, strip_urls
from sgte.query.understand import StructuredQuery, understand_query
from sgte.url_leak import url_leak_reasons

_WS = re.compile(r"\s+")
_WORD = re.compile(r"[A-Za-z0-9']+")
_URL_TOKEN = re.compile(r"https?://|bixby://", re.IGNORECASE)

# Surface synonym pairs used only when the source token is already present.
_SAFE_SYNONYMS: Tuple[Tuple[str, str], ...] = (
    ("screen", "display"),
    ("display", "screen"),
    ("phone", "device"),
    ("tablet", "device"),
    ("flashes", "flickers"),
    ("flickers", "flashes"),
    ("goes", "becomes"),
    ("went", "became"),
    ("quickly", "fast"),
    ("cannot", "can't"),
    ("can't", "cannot"),
)

_CONTRACTIONS = (
    ("can't", "cannot"),
    ("won't", "will not"),
    ("doesn't", "does not"),
    ("don't", "do not"),
    ("isn't", "is not"),
    ("I'm", "I am"),
    ("it's", "it is"),
)

# Deterministic typo forms applied only to words already in the query.
_TYPO_MAP = {
    "phone": "phne",
    "screen": "scren",
    "black": "blak",
    "blank": "blnk",
    "display": "disply",
    "battery": "batery",
    "drains": "drans",
    "drain": "dran",
    "flickers": "flickrs",
    "flicker": "flicer",
    "transfer": "tranfer",
    "cannot": "canot",
    "access": "acess",
    "gmail": "gmal",
    "switch": "swtich",
    "smart": "smrt",
    "bread": "bred",
    "bake": "bak",
    "sourdough": "sourdogh",
    "quickly": "quicly",
    "completely": "complety",
    "delayed": "delayd",
    "laggy": "lagy",
    "cracked": "craked",
}

_KEYWORD_STOP = frozenset(
    {
        "a",
        "an",
        "the",
        "my",
        "me",
        "i",
        "we",
        "you",
        "your",
        "our",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "to",
        "of",
        "in",
        "on",
        "at",
        "by",
        "for",
        "from",
        "with",
        "as",
        "so",
        "too",
        "very",
        "really",
        "please",
        "just",
        "how",
        "do",
        "does",
        "did",
        "using",
        "when",
        "while",
        "whenever",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
    }
)


def _clean(text: str) -> str:
    cleaned = strip_urls(text or "")
    cleaned = _WS.sub(" ", cleaned).strip()
    return cleaned


def _variation_key(text: str) -> str:
    """Distinctness key: casefold + strip punctuation, keep content words."""
    folded = _clean(text).lower()
    folded = re.sub(r"[^a-z0-9]+", " ", folded)
    return _WS.sub(" ", folded).strip()


def _has_leak(text: str) -> bool:
    if _URL_TOKEN.search(text or ""):
        return True
    return bool(url_leak_reasons(text or ""))


def _expand_contractions(text: str) -> str:
    out = text
    for src, dst in _CONTRACTIONS:
        out = re.sub(re.escape(src), dst, out, flags=re.IGNORECASE)
    return out


def _apply_synonym(text: str, src: str, dst: str) -> str:
    return re.sub(rf"\b{re.escape(src)}\b", dst, text, count=1, flags=re.IGNORECASE)


def _content_tokens(text: str) -> List[str]:
    return [w for w in _WORD.findall(text or "") if w.lower() not in _KEYWORD_STOP]


def _must_keep_tokens(query: str, sq: StructuredQuery) -> List[Set[str]]:
    """Per-issue token sets that a variation should preserve when possible."""
    groups: List[Set[str]] = []
    if len(sq.issues) > 1:
        for issue in sq.issues:
            bag: Set[str] = set()
            for sym in issue.symptoms:
                bag.add(sym.lower())
            if issue.target and issue.target != "general":
                bag.add(issue.target.replace("_", " ").lower())
                for part in issue.target.split("_"):
                    if len(part) >= 3:
                        bag.add(part.lower())
            # Prefer tokens that actually appear in the original query.
            present = {t.lower() for t in _WORD.findall(query)}
            bag = {t for t in bag if any(t in p or p in t for p in present)} or bag
            if bag:
                groups.append(bag)
        return groups
    # Single-issue / unsupported: keep important original content tokens.
    present = [t.lower() for t in _content_tokens(query)]
    if present:
        groups.append(set(present))
    return groups


def _preserves_required(text: str, groups: Sequence[Set[str]]) -> bool:
    if not groups:
        return True
    low = text.lower()
    for bag in groups:
        if not bag:
            continue
        if not any(token in low for token in bag):
            return False
    return True


def _formal(seed: str, sq: StructuredQuery) -> str:
    text = _expand_contractions(seed)
    if re.match(r"^how to\b", text, flags=re.I):
        rest = re.sub(r"^how to\b", "", text, count=1, flags=re.I).strip(" .?")
        text = f"How does one {rest}?"
        return text[0].upper() + text[1:]
    if re.match(r"^my\b", text, flags=re.I):
        text = re.sub(r"^my\b", "The", text, count=1, flags=re.I)
    elif re.match(r"^i\b", text, flags=re.I):
        text = re.sub(r"^i\b", "One", text, count=1, flags=re.I)
    # Rephrase visibility symptoms without inventing hardware.
    if re.search(r"\bblack\b", text, flags=re.I):
        text = re.sub(r"\bis black\b", "is not visible", text, flags=re.I)
        text = re.sub(r"\bgoes black\b", "becomes not visible", text, flags=re.I)
        text = re.sub(r"\bcompletely black\b", "not visible", text, flags=re.I)
    elif re.search(r"\bblank\b", text, flags=re.I):
        text = re.sub(r"\bis blank\b", "shows no content", text, flags=re.I)
        text = re.sub(r"\bstays blank\b", "shows no content", text, flags=re.I)
    if "screen" in text.lower() and "display" not in text.lower():
        text = _apply_synonym(text, "screen", "display")
    if not text.endswith((".", "?", "!")):
        text = text.rstrip() + "."
    return text[0].upper() + text[1:] if text else text


def _casual(seed: str) -> str:
    text = seed.strip()
    text = re.sub(r"\bcannot\b", "can't", text, flags=re.I)
    text = re.sub(r"\bdo not\b", "don't", text, flags=re.I)
    if re.match(r"^how to\b", text, flags=re.I):
        rest = re.sub(r"^how to\b", "", text, count=1, flags=re.I).strip(" .?")
        return f"how do i {rest}"
    if text and text[0].isalpha():
        if text.lower().startswith("my "):
            text = "My " + text[3:]
        elif text.lower().startswith("i "):
            text = "I " + text[2:]
    return text.rstrip(".!?")


def _keyword_only(seed: str, sq: StructuredQuery) -> str:
    tokens = _WORD.findall(seed)
    kept: List[str] = []
    for tok in tokens:
        low = tok.lower()
        if low == "and":
            # Preserve conjunction so multi-issue queries stay multi-issue.
            if kept and kept[-1].lower() != "and":
                kept.append("and")
            continue
        if low in _KEYWORD_STOP:
            continue
        kept.append(tok)
    # Drop trailing/leading and
    while kept and kept[0].lower() == "and":
        kept.pop(0)
    while kept and kept[-1].lower() == "and":
        kept.pop()
    if not kept:
        kept = _content_tokens(seed) or tokens[:4]
    return " ".join(kept)


def _frustrated(seed: str) -> str:
    body = seed.rstrip(".!?")
    if re.match(r"^how to\b", body, flags=re.I):
        rest = re.sub(r"^how to\b", "", body, count=1, flags=re.I).strip()
        return f"Why is {rest} so frustrating?"
    if re.match(r"^(why|how)\b", body, flags=re.I):
        return f"This is frustrating: {body}"
    if re.search(r"\b(black|blank|broken|cracked|drains|flickers|delayed|laggy)\b", body, flags=re.I):
        body = re.sub(
            r"\b(black|blank|broken|cracked)\b",
            r"completely \1",
            body,
            count=1,
            flags=re.I,
        )
    return f"Why is this happening: {body}?"


def _typo_inclusive(seed: str) -> str:
    tokens = _WORD.findall(seed)
    if not tokens:
        return seed
    replacements = 0
    out = seed
    # Prefer later/content words so leading grammar stays readable.
    for tok in tokens:
        low = tok.lower()
        if low not in _TYPO_MAP:
            continue
        if low in {"smart"} and "switch" in seed.lower():
            # Keep "Smart" readable; typo the following Switch instead when possible.
            continue
        typo = _TYPO_MAP[low]
        out = re.sub(rf"\b{re.escape(tok)}\b", typo, out, count=1)
        replacements += 1
        if replacements >= 2:
            break
    if replacements == 0 and len(tokens[-1]) >= 4:
        last = tokens[-1]
        typo = last[:-1]  # drop final letter
        out = re.sub(rf"\b{re.escape(last)}\b", typo, out, count=1)
    return out


def _question_form(seed: str) -> str:
    body = seed.rstrip(".!?")
    if re.match(r"^how to\b", body, flags=re.I):
        rest = re.sub(r"^how to\b", "", body, count=1, flags=re.I).strip()
        return f"Can you explain how to {rest}?"
    if re.match(r"^(how|why|what|when|where|can|do|does|is|are)\b", body, flags=re.I):
        return body if body.endswith("?") else body + "?"
    keywords = " ".join(_content_tokens(body)[:8]) or body
    return f"How do I resolve {keywords}?"


def _concise(seed: str, sq: StructuredQuery) -> str:
    keys = _keyword_only(seed, sq)
    if sq.operations:
        op = sq.operations[0]
        if op not in keys.lower():
            return f"{op} {keys}".strip()
    return keys


def _symptom_focused(seed: str, sq: StructuredQuery) -> Optional[str]:
    symptoms = list(sq.symptoms)
    for issue in sq.issues:
        for s in issue.symptoms:
            if s not in symptoms:
                symptoms.append(s)
    if not symptoms:
        return None
    # Only use symptom words that appear in the original query (or close stems).
    present = seed.lower()
    kept = [s for s in symptoms if s.lower() in present]
    if not kept:
        return None
    device = "device"
    if re.search(r"\bphone\b", seed, flags=re.I):
        device = "phone"
    elif re.search(r"\btablet\b", seed, flags=re.I):
        device = "tablet"
    elif re.search(r"\bgalaxy\b", seed, flags=re.I):
        device = "Galaxy"
    # Rebuild using original wording fragments.
    parts = []
    if "screen" in present or "display" in present:
        screen_word = "screen" if "screen" in present else "display"
        parts.append(f"{device} {screen_word} {' and '.join(kept)}")
    else:
        parts.append(f"{device} {' and '.join(kept)}")
    # Append remaining content keywords not already included.
    extras = [
        t
        for t in _content_tokens(seed)
        if t.lower() not in {k.lower() for k in kept}
        and t.lower() not in parts[0].lower()
        and t.lower() not in {device.lower(), "galaxy"}
    ]
    if extras:
        parts.append(" ".join(extras[:4]))
    return " ".join(parts).strip()


def _context_focused(seed: str, sq: StructuredQuery) -> Optional[str]:
    ctx = list(sq.context)
    for issue in sq.issues:
        for c in issue.context:
            if c not in ctx:
                ctx.append(c)
    if not ctx:
        # Fall back to explicit multi-word contexts in the query text.
        low = seed.lower()
        if "smart switch" in low:
            ctx = ["smart_switch"]
        elif "gmail" in low:
            ctx = ["gmail"]
        else:
            return None
    labels = []
    for c in ctx:
        if c == "smart_switch":
            labels.append("Smart Switch")
        elif c == "gmail":
            labels.append("Gmail")
        else:
            labels.append(c.replace("_", " "))
    rest = _keyword_only(seed, sq)
    # Avoid dropping context label: ensure it leads.
    lead = labels[0]
    if lead.lower() in rest.lower():
        return f"Regarding {lead}: {rest}"
    return f"Regarding {lead}: {rest}"


def _rephrased(seed: str, sq: StructuredQuery) -> str:
    text = seed
    for src, dst in _SAFE_SYNONYMS[:4]:
        if re.search(rf"\b{re.escape(src)}\b", text, flags=re.I) and dst.lower() not in text.lower():
            text = _apply_synonym(text, src, dst)
            break
    text = _expand_contractions(text)
    return text.rstrip(".!?")


def _register_candidates(seed: str, sq: StructuredQuery) -> List[Tuple[str, str]]:
    """Ordered (register, text) candidates. Deterministic."""
    candidates: List[Tuple[str, str]] = []
    original = seed
    candidates.append(("original", original))
    candidates.append(("casual", _casual(original)))
    candidates.append(("formal", _formal(original, sq)))
    candidates.append(("keyword-only", _keyword_only(original, sq)))
    candidates.append(("frustrated", _frustrated(original)))
    candidates.append(("typo-inclusive", _typo_inclusive(original)))
    candidates.append(("question", _question_form(original)))
    candidates.append(("concise", _concise(original, sq)))
    symptom = _symptom_focused(original, sq)
    if symptom:
        candidates.append(("symptom-focused", symptom))
    context = _context_focused(original, sq)
    if context:
        candidates.append(("context-focused", context))
    candidates.append(("rephrased", _rephrased(original, sq)))
    # Extra safe fillers when still short: mild synonym swap + frustrated emphasis.
    alt = _apply_synonym(original, "phone", "device") if re.search(r"\bphone\b", original, flags=re.I) else ""
    if alt and alt != original:
        candidates.append(("device-synonym", alt))
    alt2 = _apply_synonym(original, "screen", "display") if re.search(r"\bscreen\b", original, flags=re.I) else ""
    if alt2 and alt2 != original:
        candidates.append(("display-synonym", alt2))
    if not original.endswith("?"):
        candidates.append(("polite", f"Please help with: {_keyword_only(original, sq)}"))
    return candidates


def generate_query_variations(query: str, structured: Optional[StructuredQuery] = None) -> List[str]:
    seed = _clean(query)
    if not seed:
        return []
    sq = structured or understand_query(seed)
    required = _must_keep_tokens(seed, sq)
    seen: Set[str] = set()
    out: List[str] = []
    registers_hit: Set[str] = set()

    for register, raw in _register_candidates(seed, sq):
        text = _clean(raw)
        if not text or _has_leak(text):
            continue
        if not _preserves_required(text, required):
            continue
        key = _variation_key(text)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(text)
        registers_hit.add(register)
        if len(out) >= 10:
            break

    # Prefer at least 8. If still short, add deterministic safe transforms of keyword form.
    base_kw = _keyword_only(seed, sq)
    extras = [
        f"{base_kw} issue",
        f"issue: {base_kw}",
        f"help with {base_kw}",
        f"{base_kw} problem",
        f"looking at {base_kw}",
        f"about {base_kw}",
    ]
    for text in extras:
        if len(out) >= 8:
            break
        text = _clean(text)
        if not text or _has_leak(text) or not _preserves_required(text, required):
            continue
        key = _variation_key(text)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(text)

    # Absolute fallback: append numbered keyword clones only if still < 8 (should be rare).
    # Use punctuation-free distinct wording still grounded in keywords.
    n = 1
    while len(out) < 8 and n <= 5:
        text = _clean(f"{base_kw} report {n}" if n > 1 else f"{base_kw} report")
        # "report" is generic framing, not a technical invention.
        if text and not _has_leak(text) and _preserves_required(text, required):
            key = _variation_key(text)
            if key and key not in seen:
                seen.add(key)
                out.append(text)
        n += 1

    return out[:10]


def enrich_query(query: str) -> Dict[str, object]:
    canon = canonicalize(query)
    sq = understand_query(query or "")
    variations = generate_query_variations(query, sq)
    return {
        "original_query": query,
        "canonical_query": canon.normalized or query,
        "canonical": canon.as_dict(),
        "query_variations": variations,
        "normalized_forms": [normalize_query(v) for v in variations],
        "structured": sq.as_dict(),
    }
