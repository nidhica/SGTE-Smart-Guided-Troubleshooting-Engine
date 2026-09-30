"""In-memory semantic cache. Hits use cosine similarity, never exact-string matching."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sgte.embeddings.dense import HashingEmbeddingProvider, cosine_dense
from sgte.query.canonical import CanonicalQuery, canonicalize
from sgte.query.intent_boundary import boundaries_compatible
from sgte.validator import ResponseValidator, ValidationResult

SCHEMA_VERSION = "theme2.ContextDeeplinkResponse.v1"
# Bump when retrieval/necessity/relevance rules change so stale entries cannot
# bypass updated safety or grounding behavior (Phase 44/45).
LOGIC_VERSION = "sgte.relevance.v3"

_OPPOSITE = {("enable", "disable"), ("disable", "enable"), ("increase", "decrease"), ("decrease", "increase")}


def _jaccard(a: Sequence[str], b: Sequence[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


@dataclass
class CacheEntry:
    id: str
    semantic_key: str
    canonical_query: str
    normalized: str
    operation: str
    domain: str
    intent: str
    response: Dict[str, Any]
    provider: str
    model: str
    schema_version: str
    created_ts: float
    vector: List[float] = field(repr=False)
    boundaries: Tuple[str, ...] = ()
    logic_version: str = LOGIC_VERSION


@dataclass(frozen=True)
class CacheLookup:
    hit: bool
    similarity: float
    threshold: float
    matched_canonical_query: Optional[str]
    cache_entry_id: Optional[str]
    reason: str
    entry: Optional[CacheEntry] = None


class SemanticCache:
    def __init__(
        self,
        *,
        threshold: float = 0.58,
        embedder: Optional[HashingEmbeddingProvider] = None,
        min_token_jaccard: float = 0.30,
        near_dup_cosine: float = 0.92,
        logic_version: str = LOGIC_VERSION,
    ):
        self.threshold = float(threshold)
        self.min_token_jaccard = min_token_jaccard
        self.near_dup_cosine = near_dup_cosine
        self.logic_version = logic_version
        self.embedder = embedder or HashingEmbeddingProvider()
        self._entries: List[CacheEntry] = []
        self._hits = 0
        self._misses = 0
        self._invalidations = 0

    def clear(self) -> None:
        self._entries.clear()
        self._hits = 0
        self._misses = 0
        self._invalidations = 0

    def stats(self) -> Dict[str, Any]:
        return {
            "size": len(self._entries),
            "hits": self._hits,
            "misses": self._misses,
            "invalidations": self._invalidations,
            "threshold": self.threshold,
            "logic_version": self.logic_version,
            "hit_rate": (self._hits / (self._hits + self._misses)) if (self._hits + self._misses) else 0.0,
        }

    def _embed(self, canon: CanonicalQuery) -> List[float]:
        return self.embedder.embed_text(canon.semantic_key)

    def _compatible(self, canon: CanonicalQuery, entry: CacheEntry) -> bool:
        if (canon.operation, entry.operation) in _OPPOSITE:
            return False
        polar = {"enable", "disable", "increase", "decrease"}
        if canon.operation != entry.operation and (
            canon.operation in polar or entry.operation in polar
        ):
            return False
        # Hard structured-intent boundaries (physical damage vs blank, etc.).
        if not boundaries_compatible(canon.boundaries, entry.boundaries):
            return False
        generic = {"user_query", "unknown"}
        if (
            canon.intent not in generic
            and entry.intent not in generic
            and canon.intent != entry.intent
        ):
            return False
        return True

    def _score(self, canon: CanonicalQuery, qv: Sequence[float], entry: CacheEntry) -> Tuple[float, float, float]:
        cosine = cosine_dense(qv, entry.vector)
        jac = _jaccard(canon.tokens, entry.normalized.split())
        combined = 0.50 * max(0.0, cosine) + 0.50 * jac
        return combined, cosine, jac

    def get(
        self,
        query: str,
        validator: Optional[ResponseValidator] = None,
    ) -> CacheLookup:
        canon = canonicalize(query)
        qv = self._embed(canon)
        best: Optional[Tuple[float, float, float, CacheEntry]] = None
        stale_ids: List[str] = []
        for entry in self._entries:
            if getattr(entry, "logic_version", None) != self.logic_version:
                stale_ids.append(entry.id)
                continue
            if not self._compatible(canon, entry):
                continue
            if entry.schema_version != SCHEMA_VERSION:
                continue
            combined, cosine, jac = self._score(canon, qv, entry)
            token_ok = jac >= self.min_token_jaccard or cosine >= self.near_dup_cosine
            if not token_ok:
                continue
            if combined < self.threshold:
                continue
            if best is None or combined > best[0]:
                best = (combined, cosine, jac, entry)
        if stale_ids:
            before = len(self._entries)
            stale_set = set(stale_ids)
            self._entries = [e for e in self._entries if e.id not in stale_set]
            self._invalidations += before - len(self._entries)
        if best is None:
            self._misses += 1
            return CacheLookup(
                hit=False,
                similarity=0.0,
                threshold=self.threshold,
                matched_canonical_query=None,
                cache_entry_id=None,
                reason="stale_logic_version" if stale_ids else "below_threshold_or_empty",
            )
        combined, cosine, jac, entry = best
        if validator is not None:
            checked: ValidationResult = validator.validate(entry.response)
            if not checked.ok:
                self._entries = [e for e in self._entries if e.id != entry.id]
                self._invalidations += 1
                self._misses += 1
                return CacheLookup(
                    hit=False,
                    similarity=combined,
                    threshold=self.threshold,
                    matched_canonical_query=entry.canonical_query,
                    cache_entry_id=entry.id,
                    reason="invalid_cached_response",
                )
        self._hits += 1
        return CacheLookup(
            hit=True,
            similarity=combined,
            threshold=self.threshold,
            matched_canonical_query=entry.canonical_query,
            cache_entry_id=entry.id,
            reason="hit",
            entry=entry,
        )

    def put(
        self,
        query: str,
        validated_response: Dict[str, Any],
        *,
        validator: ResponseValidator,
        provider: str,
        model: str,
    ) -> Optional[CacheEntry]:
        checked = validator.validate(validated_response)
        if not checked.ok or checked.response is None:
            return None
        payload = checked.response.model_dump()
        canon = canonicalize(query)
        entry = CacheEntry(
            id=str(uuid.uuid4()),
            semantic_key=canon.semantic_key,
            canonical_query=canon.normalized or query,
            normalized=canon.normalized,
            operation=canon.operation,
            domain=canon.domain,
            intent=canon.intent,
            response=payload,
            provider=provider,
            model=model,
            schema_version=SCHEMA_VERSION,
            created_ts=time.time(),
            vector=self._embed(canon),
            boundaries=tuple(canon.boundaries),
            logic_version=self.logic_version,
        )
        self._entries.append(entry)
        return entry
