"""Intent-aware hybrid mapper: TF-IDF ∪ dense retrieval, then deterministic rerank."""

from __future__ import annotations

import os
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple

from sgte.catalogue_index import CatalogueIndex, metadata_document
from sgte.compatibility import (
    context_compatibility,
    mismatch_penalty,
    operation_compatibility,
    polarity_allows,
    target_compatibility,
)
from sgte.deeplink_repo import DUMMY_URI, DeeplinkHit, DeeplinkRepository
from sgte.embeddings.dense import cosine_dense
from sgte.intent import ActionIntent, candidate_target, extract_intent
from sgte.lexical import tokens, weighted_overlap, weighted_overlap_tokens
from sgte.loaders import DeeplinkRecord
from sgte.paraphrase_policy import (
    apply_conservative_paraphrase_selection,
    is_paraphrase_query,
)
from sgte.polarity import polarity

# Preferred catalogue IDs (verbatim URIs from official deeplinks.json — never synthesized).
_NAV_BAR_ID = "DL-0169"
_WIFI_ID = "DL-0313"
_AUTO_FACTORY_RESET_ID = "DL-0022"

_ENABLE_RE = re.compile(
    r"\b(enable|enabled|turn\s+on|turns\s+on|turned\s+on|switch\s+on|activate|activated)\b",
    re.I,
)
_DISABLE_RE = re.compile(
    r"\b(disable|disabled|turn\s+off|turns\s+off|turned\s+off|switch\s+off|deactivate|deactivated)\b",
    re.I,
)
_NAV_BAR_RE = re.compile(r"\bnavigation\s+bar\b", re.I)
_FULL_SCREEN_GESTURE_RE = re.compile(r"\bfull[\s-]*screen\s+gesture", re.I)
_GESTURE_FUNCTION_RE = re.compile(r"\bgesture\s+function\b", re.I)
_BUTTONS_RE = re.compile(r"\bbuttons?\b", re.I)
_INTERNET_WIFI_RE = re.compile(
    r"\b("
    r"internet\s+connection|verify\s+.{0,40}internet|check\s+.{0,40}internet|"
    r"phone'?s\s+internet|wi-?fi\s+connection|check\s+.{0,40}wi-?fi|"
    r"verify\s+.{0,40}wi-?fi"
    r")\b",
    re.I,
)
_FACTORY_DATA_RESET_RE = re.compile(r"\bfactory\s+data\s+reset\b|\bfactory\s+reset\b", re.I)
_SAFE_MODE_RE = re.compile(r"\bsafe\s*mode\b", re.I)
_PHYSICAL_CHARGER_CHECK_RE = re.compile(
    r"\b("
    r"check\s+charger|"
    r"check\s+(?:the\s+)?device,?\s+(?:the\s+)?charger|"
    r"device,?\s+charger,?\s+and\s+(?:the\s+)?usb|"
    r"charger,?\s+and\s+(?:the\s+)?usb\s+cable|"
    r"charger\s+issues?|"
    r"different[, ].{0,24}charger|"
    r"undamaged\s+charger|"
    r"try\s+using\s+a\s+different.{0,40}charger|"
    r"try\s+a\s+different.{0,40}charger|"
    r"charger.{0,40}usb\s+cable.{0,40}damage|"
    r"inspect.{0,60}charger"
    r")\b",
    re.I,
)

# View WiFi Settings rows that are not the primary Wi-Fi page.
_WIFI_OFFTOPIC_KEYS = frozenset(
    {
        "intelligent wi-fi",
        "wi-fi scanning",
        "hotspot 2.0",
        "turn wi-fi on automatically",
        "switch to mobile data",
    }
)

@dataclass(frozen=True)
class RankWeights:
    """Configurable rerank weights. Ranking is never delegated to the LLM.

    final_score =
        w_semantic * semantic_similarity
        + w_lexical * lexical_similarity
        + w_target * target_compatibility
        + w_operation * operation_compatibility
        + w_context * context_compatibility
        - w_mismatch * mismatch_penalties
    """

    semantic: float = 0.26
    lexical: float = 0.16
    target: float = 0.30
    operation: float = 0.16
    context: float = 0.12
    mismatch: float = 1.0
    min_final: float = 0.40
    min_target: float = 0.18
    min_semantic: float = 0.06
    uniqueness_abs: float = 0.03
    uniqueness_ratio: float = 1.08
    tfidf_k: int = 20
    dense_k: int = 20

    @classmethod
    def from_env(cls) -> "RankWeights":
        def f(name: str, default: float) -> float:
            raw = os.environ.get(name, "").strip()
            return float(raw) if raw else default

        def i(name: str, default: int) -> int:
            raw = os.environ.get(name, "").strip()
            return int(raw) if raw else default

        return cls(
            semantic=f("SGTE_W_SEMANTIC", 0.26),
            lexical=f("SGTE_W_LEXICAL", 0.16),
            target=f("SGTE_W_TARGET", 0.30),
            operation=f("SGTE_W_OPERATION", 0.16),
            context=f("SGTE_W_CONTEXT", 0.12),
            mismatch=f("SGTE_W_MISMATCH", 1.0),
            min_final=f("SGTE_MIN_FINAL", 0.40),
            min_target=f("SGTE_MIN_TARGET", 0.18),
            min_semantic=f("SGTE_MIN_SEMANTIC", 0.06),
            uniqueness_abs=f("SGTE_UNIQUENESS_ABS", 0.03),
            uniqueness_ratio=f("SGTE_UNIQUENESS_RATIO", 1.08),
            tfidf_k=i("SGTE_TFIDF_K", 20),
            dense_k=i("SGTE_DENSE_K", 20),
        )


@dataclass
class CandidateScore:
    catalogue_id: str
    message: str
    description: str
    qna_description: str
    semantic_score: float
    lexical_score: float
    operation_compatibility: float
    target_compatibility: float
    context_compatibility: float
    mismatch_penalty: float
    final_score: float
    rejection_reason: Optional[str]
    record: DeeplinkRecord
    hit: DeeplinkHit
    combined_score: float = 0.0


@dataclass
class MappingTimings:
    query_embed_ms: float = 0.0
    retrieval_ms: float = 0.0
    rerank_ms: float = 0.0
    total_ms: float = 0.0


def _same_catalogue_screen(a: CandidateScore, b: CandidateScore) -> bool:
    """True when two candidates are duplicate rows for the same Settings screen.

    Official catalogue contains repeated messages (e.g. multiple 'Enable WiFi' rows).
    Those must not trigger ambiguity abstention — any matching URI is copied verbatim.
    """
    msg_a = (a.message or "").strip().lower()
    msg_b = (b.message or "").strip().lower()
    if not msg_a or msg_a != msg_b:
        return False
    type_a = (a.record.originalType or "").strip().lower()
    type_b = (b.record.originalType or "").strip().lower()
    return type_a == type_b


def _validation_key(row: DeeplinkRecord) -> str:
    raw = row.validation or {}
    return str(raw.get("key") or "").strip().lower()


def _message_enable_disable(message: str) -> Optional[str]:
    msg = (message or "").strip().lower()
    if msg.startswith("enable "):
        return "enable"
    if msg.startswith("disable "):
        return "disable"
    return polarity(message or "")


def _blob_enable_disable(blob: str) -> Optional[str]:
    """Return enable/disable only when polarity is clear and non-conflicting.

    State descriptions like "is enabled" / "are disabled" are ignored so they do
    not cancel an imperative enable/disable instruction in the same evidence.
    """
    text = blob or ""
    cleaned = re.sub(
        r"\b(?:is|are|was|were|be|been|being)\s+(?:enabled|disabled)\b",
        " ",
        text,
        flags=re.I,
    )
    has_en = bool(_ENABLE_RE.search(cleaned))
    has_dis = bool(_DISABLE_RE.search(cleaned))
    if has_en and has_dis:
        return None
    if has_en:
        return "enable"
    if has_dis:
        return "disable"
    return None


def _wants_navigation_bar(blob: str) -> bool:
    text = blob or ""
    if _NAV_BAR_RE.search(text):
        return True
    if _FULL_SCREEN_GESTURE_RE.search(text):
        return True
    if _GESTURE_FUNCTION_RE.search(text) and _BUTTONS_RE.search(text):
        return True
    return False


def _wants_primary_wifi(blob: str) -> bool:
    return bool(_INTERNET_WIFI_RE.search(blob or ""))


def _is_user_factory_reset(blob: str) -> bool:
    return bool(_FACTORY_DATA_RESET_RE.search(blob or ""))


def _wants_safe_mode(blob: str) -> bool:
    return bool(_SAFE_MODE_RE.search(blob or ""))


def _wants_physical_charger_check(blob: str) -> bool:
    return bool(_PHYSICAL_CHARGER_CHECK_RE.search(blob or ""))


def _catalogue_mentions_safe_mode(cand: CandidateScore) -> bool:
    blob = f"{cand.message} {cand.description} {cand.qna_description}".lower()
    return "safe mode" in blob or "safemode" in blob


def _catalogue_is_physical_charger(cand: CandidateScore) -> bool:
    """True only when catalogue text is about a physical charger swap/check.

    Check Battery Performance rows (cable/wireless charging settings) never qualify.
    """
    blob = f"{cand.message} {cand.description} {cand.qna_description}".lower()
    if "battery performance" in blob:
        return False
    if "wireless charging" in blob or "cable charging" in blob:
        return False
    if (cand.catalogue_id or "").startswith("DL-051") and "battery" in blob:
        return False
    return bool(
        re.search(r"\b(different|undamaged|try).{0,40}charger\b", blob)
        or re.search(r"\bcheck\s+charger\b", blob)
    )


class HybridDeeplinkMapper:
    def __init__(
        self,
        repo: DeeplinkRepository,
        index: Optional[CatalogueIndex] = None,
        min_score: Optional[float] = None,
        lexical_limit: int = 20,
        semantic_limit: int = 20,
        weights: Optional[RankWeights] = None,
    ):
        self.repo = repo
        self.index = index
        self.weights = weights or RankWeights.from_env()
        self.min_score = self.weights.min_final if min_score is None else min_score
        self.lexical_limit = lexical_limit or self.weights.tfidf_k
        self.semantic_limit = semantic_limit or self.weights.dense_k
        self.last_debug: List[CandidateScore] = []
        self.last_intent: Optional[ActionIntent] = None
        self.last_timings = MappingTimings()
        self.last_action_text = ""
        self._by_id: Dict[str, DeeplinkRecord] = {row.id: row for row in self.repo.all()}
        # Exact catalogue message → rows (for grounded exact-match preference).
        by_message: Dict[str, List[DeeplinkRecord]] = defaultdict(list)
        for row in self.repo.all():
            if not row.deeplink or row.deeplink == DUMMY_URI:
                continue
            msg = (row.message or "").strip().lower()
            if msg:
                by_message[msg].append(row)
        self._by_message: Dict[str, List[DeeplinkRecord]] = dict(by_message)
        # Request-scoped reuse for identical (action, steps, context) only.
        self._rank_cache: Dict[tuple, List[CandidateScore]] = {}
        self._rank_meta: Dict[tuple, tuple] = {}
        self._best_cache: Dict[tuple, Optional[DeeplinkHit]] = {}
        # Request-scoped retrieval reuse keyed by exact evidence blob string.
        self._retrieve_cache: Dict[str, tuple] = {}
        # Request-scoped dense embedding reuse for identical text only.
        self._text_embed_cache: Dict[str, List[float]] = {}
        self.request_cache_hits = 0
        self.request_cache_misses = 0
        self.request_retrieve_hits = 0
        self.request_retrieve_misses = 0
        self.request_embed_calls = 0
        self.request_embed_cache_hits = 0

    def clear_request_cache(self) -> None:
        """Drop per-request mapping reuse. Call at the start of each troubleshoot."""
        self._rank_cache.clear()
        self._rank_meta.clear()
        self._best_cache.clear()
        self._retrieve_cache.clear()
        self._text_embed_cache.clear()
        self.request_cache_hits = 0
        self.request_cache_misses = 0
        self.request_retrieve_hits = 0
        self.request_retrieve_misses = 0
        self.request_embed_calls = 0
        self.request_embed_cache_hits = 0

    @staticmethod
    def _request_key(
        action_text: str,
        steps: Optional[Sequence[str]],
        context: Optional[str],
    ) -> tuple:
        return (action_text or "", tuple(steps or ()), context or "")

    def _blob(self, action_text: str, steps: Optional[Sequence[str]], context: Optional[str]) -> str:
        return " ".join(part for part in (action_text, " ".join(steps or ()), context or "") if part)

    def _embed_text_cached(self, text: str) -> List[float]:
        """Dense-embed text once per identical string within the current request."""
        if self.index is None:
            raise RuntimeError("dense embed requires catalogue index")
        key = text or ""
        cached = self._text_embed_cache.get(key)
        if cached is not None:
            self.request_embed_cache_hits += 1
            return cached
        vec = self.index.dense_provider.embed_texts([key])[0]
        self._text_embed_cache[key] = vec
        self.request_embed_calls += 1
        return vec

    def _ensure_catalogue_candidate(
        self,
        scored: List[CandidateScore],
        catalogue_id: str,
        blob: str,
        intent: ActionIntent,
        lexical_hits: Dict[str, DeeplinkHit],
        semantic_map: Dict[str, float],
    ) -> None:
        if any(c.catalogue_id == catalogue_id for c in scored):
            return
        row = self._by_id.get(catalogue_id)
        if row is None or row.deeplink == DUMMY_URI:
            return
        lex_hit = lexical_hits.get(row.deeplink)
        lex = lex_hit.score if lex_hit else 0.0
        sem = semantic_map.get(row.deeplink, 0.0)
        scored.append(self._score_row(blob, intent, row, lex, sem))

    def _exact_message_rows(self, action_text: str) -> List[DeeplinkRecord]:
        key = (action_text or "").strip().lower()
        if not key:
            return []
        return list(self._by_message.get(key) or [])

    def _apply_exact_message_preference(
        self, scored: List[CandidateScore], action_text: str
    ) -> None:
        """When action text equals a catalogue message, prefer those rows only.

        Rejects near-matches (e.g. Fast wireless vs Fast charging, turn off vs on)
        without inventing URIs or weakening polarity/uniqueness for non-exact queries.
        """
        key = (action_text or "").strip().lower()
        if not key or key not in self._by_message:
            return
        exact_viable = [
            c
            for c in scored
            if c.rejection_reason is None and (c.message or "").strip().lower() == key
        ]
        if not exact_viable:
            return
        for cand in scored:
            if cand.rejection_reason is not None:
                continue
            if (cand.message or "").strip().lower() == key:
                continue
            cand.rejection_reason = "exact catalogue message preferred over near-match"

    def _apply_factory_reset_hard_negative(self, scored: List[CandidateScore], blob: str) -> None:
        if not _is_user_factory_reset(blob):
            return
        for cand in scored:
            key = _validation_key(cand.record)
            if cand.catalogue_id == _AUTO_FACTORY_RESET_ID or key == "auto factory reset":
                cand.rejection_reason = (
                    "factory data reset must not map to auto factory reset"
                )

    def _apply_safe_mode_hard_negative(self, scored: List[CandidateScore], blob: str) -> None:
        """Safe mode has no catalogue entry; reject touch-and-hold false friends."""
        if not _wants_safe_mode(blob):
            return
        for cand in scored:
            if cand.rejection_reason is not None:
                continue
            if _catalogue_mentions_safe_mode(cand):
                continue
            cand.rejection_reason = (
                "safe mode has no matching catalogue entry "
                "(must not map to touch-and-hold settings)"
            )

    def _apply_physical_charger_hard_negative(
        self, scored: List[CandidateScore], blob: str
    ) -> None:
        """Physical charger check ≠ Check Battery Performance / wireless charging."""
        if not _wants_physical_charger_check(blob):
            return
        for cand in scored:
            if cand.rejection_reason is not None:
                continue
            if _catalogue_is_physical_charger(cand):
                continue
            cand.rejection_reason = (
                "physical charger/device/USB inspection has no matching catalogue entry "
                "(must not map to battery performance / charging settings)"
            )

    def _apply_navigation_bar_alias(
        self,
        scored: List[CandidateScore],
        blob: str,
        intent: ActionIntent,
        lexical_hits: Dict[str, DeeplinkHit],
        semantic_map: Dict[str, float],
    ) -> None:
        if not _wants_navigation_bar(blob):
            return
        self._ensure_catalogue_candidate(
            scored, _NAV_BAR_ID, blob, intent, lexical_hits, semantic_map
        )
        for cand in scored:
            if cand.catalogue_id == _NAV_BAR_ID:
                cand.rejection_reason = None
                cand.final_score = max(cand.final_score, self.weights.min_final + 0.20)
                cand.combined_score = cand.final_score
                continue
            msg = (cand.message or "").lower()
            key = _validation_key(cand.record)
            # Unrelated gesture-control twins lose to View Navigation bar.
            if "gesture control" in msg and key != "navigation bar":
                cand.rejection_reason = (
                    cand.rejection_reason
                    or "navigation-bar alias prefers View Navigation bar"
                )
            if key in {"corner actions", "mute with gestures"}:
                cand.rejection_reason = (
                    cand.rejection_reason
                    or "navigation-bar alias prefers View Navigation bar"
                )

    def _apply_wifi_preference(
        self,
        scored: List[CandidateScore],
        blob: str,
        intent: ActionIntent,
        lexical_hits: Dict[str, DeeplinkHit],
        semantic_map: Dict[str, float],
    ) -> None:
        if not _wants_primary_wifi(blob):
            return
        self._ensure_catalogue_candidate(
            scored, _WIFI_ID, blob, intent, lexical_hits, semantic_map
        )
        for cand in scored:
            key = _validation_key(cand.record)
            if cand.catalogue_id == _WIFI_ID:
                cand.rejection_reason = None
                cand.final_score = max(cand.final_score, self.weights.min_final + 0.20)
                cand.combined_score = cand.final_score
                continue
            if key in _WIFI_OFFTOPIC_KEYS:
                cand.rejection_reason = (
                    cand.rejection_reason
                    or "internet/Wi-Fi check prefers primary Wi-Fi settings"
                )
                continue
            if (cand.message or "").lower().startswith("view wifi") and key != "wi-fi":
                cand.rejection_reason = (
                    cand.rejection_reason
                    or "internet/Wi-Fi check prefers primary Wi-Fi settings"
                )

    def _apply_enable_disable_polarity(self, scored: List[CandidateScore], blob: str) -> None:
        """Resolve Enable/Disable twins that share validation.key when polarity is clear.

        Ambiguous evidence leaves both candidates; uniqueness abstention still applies.
        Does not globally prefer Enable for 'settings' wording alone.
        """
        pol = _blob_enable_disable(blob)
        by_key: Dict[str, List[Tuple[CandidateScore, str]]] = defaultdict(list)
        for cand in scored:
            if cand.rejection_reason is not None:
                continue
            key = _validation_key(cand.record)
            msg_pol = _message_enable_disable(cand.message)
            if not key or msg_pol not in {"enable", "disable"}:
                continue
            by_key[key].append((cand, msg_pol))

        for key, items in by_key.items():
            sides = {mp for _, mp in items}
            if sides != {"enable", "disable"}:
                continue
            if pol is None:
                # Explicit abstention path: keep both; uniqueness will reject.
                continue
            for cand, msg_pol in items:
                if msg_pol != pol:
                    cand.rejection_reason = (
                        f"enable/disable polarity mismatch: evidence requires {pol}"
                    )

    def _semantic_target(
        self,
        intent: ActionIntent,
        row: DeeplinkRecord,
        *,
        target_vec: Optional[List[float]] = None,
    ) -> float:
        lexical_t = target_compatibility(
            intent.target,
            candidate_target(row.message or "", row.description or "", row.qna_description or ""),
        )
        if self.index is None:
            return lexical_t
        qv = target_vec if target_vec is not None else self._embed_text_cached(intent.target or "")
        # Match prior batch embed_texts([target, message, description, qna]) including empty strings.
        field_vecs = [
            self._embed_text_cached(row.message or ""),
            self._embed_text_cached(row.description or ""),
            self._embed_text_cached(row.qna_description or ""),
        ]
        dense_t = max(cosine_dense(qv, vec) for vec in field_vecs)
        return 0.62 * lexical_t + 0.38 * max(0.0, dense_t)

    def _score_row(
        self,
        blob: str,
        intent: ActionIntent,
        row: DeeplinkRecord,
        lex: float,
        sem: float,
        *,
        target_vec: Optional[List[float]] = None,
        blob_tokens: Optional[FrozenSet[str]] = None,
    ) -> CandidateScore:
        w = self.weights
        tgt = self._semantic_target(intent, row, target_vec=target_vec)
        op = operation_compatibility(intent.operation, row)
        ctx = context_compatibility(blob, row)
        pen = mismatch_penalty(blob, row, intent)
        field_toks = self.repo._field_tokens_by_id.get(row.id) or {}
        if blob_tokens is not None:
            message = weighted_overlap_tokens(
                blob_tokens, field_toks.get("message", frozenset()), self.repo._idf
            )
            description = weighted_overlap_tokens(
                blob_tokens, field_toks.get("description", frozenset()), self.repo._idf
            )
            qna = weighted_overlap_tokens(
                blob_tokens, field_toks.get("qna_description", frozenset()), self.repo._idf
            )
        else:
            message = weighted_overlap(blob, row.message or "", self.repo._idf)
            description = weighted_overlap(blob, row.description or "", self.repo._idf)
            qna = weighted_overlap(blob, row.qna_description or "", self.repo._idf)
        lex_blend = max(lex, 0.5 * message + 0.3 * description + 0.2 * qna)
        final = (
            w.semantic * sem
            + w.lexical * lex_blend
            + w.target * tgt
            + w.operation * op
            + w.context * ctx
            - w.mismatch * pen
        )
        reason = None
        if not polarity_allows(intent, row):
            reason = f"operation conflict: action {intent.operation} vs catalogue polarity"
        elif tgt < w.min_target:
            reason = f"weak target compatibility ({tgt:.3f} < {w.min_target})"
        elif sem < w.min_semantic and lex_blend < 0.12:
            reason = "weak similarity"
        elif final < w.min_final:
            reason = f"final score below threshold ({final:.3f} < {w.min_final})"
        evidence = {
            "semantic": sem,
            "lexical": lex_blend,
            "target": tgt,
            "operation": op,
            "context": ctx,
            "mismatch": pen,
            "final": final,
        }
        hit = DeeplinkHit(
            id=row.id,
            deeplink=row.deeplink,
            metadata={
                "description": row.description,
                "message": row.message,
                "qna_description": row.qna_description,
                "originalType": row.originalType,
                "control_type": row.control_type,
            },
            validation=row.validation,
            score=final,
            record=row,
            evidence=evidence,
        )
        return CandidateScore(
            catalogue_id=row.id,
            message=row.message or "",
            description=row.description or "",
            qna_description=row.qna_description or "",
            semantic_score=sem,
            lexical_score=lex_blend,
            operation_compatibility=op,
            target_compatibility=tgt,
            context_compatibility=ctx,
            mismatch_penalty=pen,
            final_score=final,
            rejection_reason=reason,
            record=row,
            hit=hit,
            combined_score=final,
        )

    def _retrieve(
        self, blob: str
    ) -> tuple[Dict[str, DeeplinkHit], Dict[str, float], MappingTimings]:
        if blob in self._retrieve_cache:
            self.request_retrieve_hits += 1
            return self._retrieve_cache[blob]

        self.request_retrieve_misses += 1
        timings = MappingTimings()
        t0 = time.perf_counter()
        lexical_hits = {
            hit.deeplink: hit for hit in self.repo.search(blob, limit=self.lexical_limit)
        }
        query_vector = None
        if self.index is not None:
            t_embed = time.perf_counter()
            # Strip URI scheme consistently with CatalogueIndex.dense_search.
            cleaned = re.sub(r"bixby://\S+", " ", blob or "", flags=re.IGNORECASE)
            query_vector = self._embed_text_cached(cleaned)
            timings.query_embed_ms = (time.perf_counter() - t_embed) * 1000.0
        semantic_map: Dict[str, float] = {}
        t_ret = time.perf_counter()
        if self.index is not None:
            for row, score in self.index.tfidf_search(blob, limit=self.weights.tfidf_k):
                semantic_map[row.deeplink] = max(semantic_map.get(row.deeplink, 0.0), score)
            for row, score in self.index.dense_search(
                blob, limit=self.weights.dense_k, query_vector=query_vector
            ):
                semantic_map[row.deeplink] = max(semantic_map.get(row.deeplink, 0.0), score)
        timings.retrieval_ms = (time.perf_counter() - t_ret) * 1000.0
        timings.total_ms = (time.perf_counter() - t0) * 1000.0
        result = (lexical_hits, semantic_map, timings)
        self._retrieve_cache[blob] = result
        return result

    def debug_rank(
        self,
        action_text: str,
        steps: Optional[Sequence[str]] = None,
        context: Optional[str] = None,
        limit: int = 8,
    ) -> List[CandidateScore]:
        key = self._request_key(action_text, steps, context)
        if key in self._rank_cache:
            self.request_cache_hits += 1
            scored = self._rank_cache[key]
            intent, cached_action, timings = self._rank_meta[key]
            self.last_intent = intent
            self.last_action_text = cached_action
            self.last_timings = timings
            self.last_debug = scored[:limit]
            return scored[:limit]

        self.request_cache_misses += 1
        t0 = time.perf_counter()
        blob = self._blob(action_text, steps, context)
        # Prefer polarity cues from the full evidence blob when present.
        intent = extract_intent(blob if _blob_enable_disable(blob) else (action_text or blob))
        self.last_intent = intent
        self.last_action_text = action_text
        lexical_hits, semantic_map, timings = self._retrieve(blob)
        t_rank = time.perf_counter()
        uris = set(lexical_hits) | set(semantic_map)
        # Grounded injection: if action text equals a catalogue message exactly,
        # include those catalogue URIs even if retrieval missed them.
        for row in self._exact_message_rows(action_text):
            uris.add(row.deeplink)
        blob_tokens = tokens(blob)
        target_vec = None
        if self.index is not None:
            target_vec = self._embed_text_cached(intent.target or "")
        scored: List[CandidateScore] = []
        for uri in uris:
            row = self.repo.get_by_actionable_uri(uri)
            if row is None or row.deeplink == DUMMY_URI or row.deeplink != uri:
                continue
            lex_hit = lexical_hits.get(uri)
            lex = lex_hit.score if lex_hit else 0.0
            sem = semantic_map.get(uri, 0.0)
            scored.append(
                self._score_row(
                    blob,
                    intent,
                    row,
                    lex,
                    sem,
                    target_vec=target_vec,
                    blob_tokens=blob_tokens,
                )
            )

        # Narrow deterministic post-filters (catalogue URIs copied verbatim only).
        self._apply_factory_reset_hard_negative(scored, blob)
        self._apply_safe_mode_hard_negative(scored, blob)
        self._apply_physical_charger_hard_negative(scored, blob)
        self._apply_navigation_bar_alias(scored, blob, intent, lexical_hits, semantic_map)
        self._apply_wifi_preference(scored, blob, intent, lexical_hits, semantic_map)
        self._apply_enable_disable_polarity(scored, blob)
        self._apply_exact_message_preference(scored, action_text)

        scored.sort(key=lambda c: (-c.final_score, c.catalogue_id))
        # Phase 19 exact-message queries keep uniqueness gate.
        # Phase 23 Policy C applies only to paraphrase queries (not exact catalogue messages).
        exact_rows = self._exact_message_rows(action_text)
        if exact_rows:
            self._apply_uniqueness_gate(scored)
        elif is_paraphrase_query(action_text):
            self._apply_uniqueness_gate(scored)
            apply_conservative_paraphrase_selection(
                scored,
                action_text,
                uniqueness_abs=self.weights.uniqueness_abs,
                uniqueness_ratio=self.weights.uniqueness_ratio,
                same_screen=_same_catalogue_screen,
            )
        else:
            self._apply_uniqueness_gate(scored)
        timings.rerank_ms = (time.perf_counter() - t_rank) * 1000.0
        timings.total_ms = (time.perf_counter() - t0) * 1000.0
        self.last_timings = timings
        self.last_debug = scored[:limit]
        self._rank_cache[key] = scored
        self._rank_meta[key] = (intent, action_text, timings)
        return scored[:limit]

    def _apply_uniqueness_gate(self, scored: List[CandidateScore]) -> None:
        viable = [c for c in scored if c.rejection_reason is None]
        if len(viable) <= 1:
            return
        best, second = viable[0], viable[1]
        unique = _same_catalogue_screen(best, second) or (
            best.final_score >= second.final_score + self.weights.uniqueness_abs
            or best.final_score >= second.final_score * self.weights.uniqueness_ratio
        )
        if not unique:
            for item in scored:
                if item.rejection_reason is None:
                    item.rejection_reason = "ambiguous: too close to an alternative"

    def candidates(
        self,
        action_text: str,
        steps: Optional[Sequence[str]] = None,
        context: Optional[str] = None,
        limit: int = 8,
    ) -> List[CandidateScore]:
        return self.debug_rank(action_text, steps, context, limit=limit)

    def find_best_deeplink(
        self,
        action_text: str,
        steps: Optional[Sequence[str]] = None,
        context: Optional[str] = None,
    ) -> Optional[DeeplinkHit]:
        key = self._request_key(action_text, steps, context)
        if key in self._best_cache:
            self.request_cache_hits += 1
            # Keep last_debug/intent aligned with find_best callers that inspect them.
            if key in self._rank_cache:
                scored = self._rank_cache[key]
                intent, cached_action, timings = self._rank_meta[key]
                self.last_intent = intent
                self.last_action_text = cached_action
                self.last_timings = timings
                self.last_debug = scored[:8]
            return self._best_cache[key]

        ranked = self.debug_rank(action_text, steps, context, limit=8)
        viable = [c for c in ranked if c.rejection_reason is None]
        if not viable:
            self._best_cache[key] = None
            return None
        best = viable[0]
        catalogue = self.repo.get_by_actionable_uri(best.record.deeplink)
        if catalogue is None or catalogue.deeplink != best.record.deeplink:
            self._best_cache[key] = None
            return None
        self._best_cache[key] = best.hit
        return best.hit

    def format_topk(self, action_text: Optional[str] = None, k: int = 3) -> str:
        action = action_text or self.last_action_text
        lines = [f"Action: {action}"]
        ranked = self.last_debug[:k]
        if not ranked:
            lines.append("  (no candidates)")
            return "\n".join(lines)
        for i, cand in enumerate(ranked, start=1):
            lines.append(f"Candidate {i}")
            lines.append(f"  catalogue ID: {cand.catalogue_id}")
            lines.append(f"  message: {cand.message}")
            lines.append(f"  description: {cand.description}")
            lines.append(f"  semantic score: {cand.semantic_score:.3f}")
            lines.append(f"  lexical score: {cand.lexical_score:.3f}")
            lines.append(f"  operation compatibility: {cand.operation_compatibility:.3f}")
            lines.append(f"  target compatibility: {cand.target_compatibility:.3f}")
            lines.append(f"  final score: {cand.final_score:.3f}")
            lines.append(f"  rejection reason: {cand.rejection_reason or '(accepted)'}")
        return "\n".join(lines)


def assert_no_uri_in_embedding_text(index: CatalogueIndex) -> None:
    if index.documents_contain_uri_scheme() or index.documents_contain_deeplink_uri():
        raise AssertionError("catalogue embedding text contains a deeplink URI")
    for row in index.rows:
        doc = metadata_document(row)
        if "bixby://" in doc.lower() or (row.deeplink and row.deeplink in doc):
            raise AssertionError(f"URI leaked into embedding document for {row.id}")
