"""Deeplink catalogue lookup by metadata only. Never generate or rewrite URIs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Sequence, Union

from sgte.lexical import idf_weights, tokens, weighted_overlap, weighted_overlap_tokens
from sgte.loaders import DeeplinkRecord, load_deeplinks

METADATA_FIELDS = (
    "description",
    "message",
    "qna_description",
    "originalType",
    "control_type",
    "id",
)

DUMMY_URI = "bixby://dummy_positive"


@dataclass(frozen=True)
class DeeplinkHit:
    id: str
    deeplink: str
    metadata: Dict[str, Any]
    validation: Optional[Dict[str, Any]]
    score: float
    record: DeeplinkRecord
    evidence: Dict[str, float]


class DeeplinkRepository:
    def __init__(self, records: Sequence[DeeplinkRecord], min_score: float = 0.32):
        self._records: List[DeeplinkRecord] = list(records)
        self.min_score = min_score
        self._by_action_uri = {row.deeplink: row for row in self._records}
        self._validation_uris = {
            row.validation["deeplink"]
            for row in self._records
            if row.validation and isinstance(row.validation.get("deeplink"), str)
        }
        self._idf = idf_weights([self._metadata_blob(row) for row in self._records])
        # Pre-tokenize catalogue field text once. Search reuses these sets so repeated
        # normalize/token work is not redoed for every query×row×field (scores unchanged).
        self._field_tokens: List[Dict[str, FrozenSet[str]]] = [
            self._row_field_tokens(row) for row in self._records
        ]
        self._field_tokens_by_id: Dict[str, Dict[str, FrozenSet[str]]] = {
            row.id: toks for row, toks in zip(self._records, self._field_tokens)
        }

    @classmethod
    def from_file(cls, path: Union[Path, None] = None) -> "DeeplinkRepository":
        return cls(load_deeplinks(path))

    def __len__(self) -> int:
        return len(self._records)

    def all(self) -> List[DeeplinkRecord]:
        return list(self._records)

    def contains_actionable_uri(self, uri: str) -> bool:
        return uri in self._by_action_uri

    def contains_validation_uri(self, uri: str) -> bool:
        return uri in self._validation_uris

    def get_by_actionable_uri(self, uri: str) -> Optional[DeeplinkRecord]:
        """Membership/exact copy helper. Not used as a search ranking key."""
        return self._by_action_uri.get(uri)

    def _metadata_blob(self, row: DeeplinkRecord) -> str:
        parts: List[str] = []
        for field in METADATA_FIELDS:
            value = getattr(row, field, None)
            if value is None or value == "":
                continue
            parts.append(str(value))
        return " ".join(parts)

    def _row_field_tokens(self, row: DeeplinkRecord) -> Dict[str, FrozenSet[str]]:
        out: Dict[str, FrozenSet[str]] = {}
        for field in METADATA_FIELDS:
            value = getattr(row, field, None)
            if value is None or value == "":
                continue
            out[field] = tokens(str(value))
        return out

    def _field_scores_pre(
        self, query_tokens: FrozenSet[str], field_toks: Dict[str, FrozenSet[str]]
    ) -> Dict[str, float]:
        # Include every non-empty field (even score 0) so combined_score weights
        # match the pre-optimization _field_scores path exactly.
        scores: Dict[str, float] = {}
        for field, doc_toks in field_toks.items():
            scores[field] = weighted_overlap_tokens(query_tokens, doc_toks, self._idf)
        return scores

    def _field_scores(self, query: str, row: DeeplinkRecord) -> Dict[str, float]:
        scores: Dict[str, float] = {}
        for field in METADATA_FIELDS:
            value = getattr(row, field, None)
            if value is None or value == "":
                continue
            scores[field] = weighted_overlap(query, str(value), self._idf)
        return scores

    def _combined_score(self, field_scores: Dict[str, float]) -> float:
        weights = {
            "message": 2.5,
            "description": 1.6,
            "qna_description": 1.6,
            "originalType": 0.15,
            "control_type": 0.05,
            "id": 0.2,
        }
        num = 0.0
        den = 0.0
        for field, score in field_scores.items():
            w = weights.get(field, 1.0)
            num += w * score
            den += w
        return num / den if den else 0.0

    def search(self, query: str, limit: int = 5) -> List[DeeplinkHit]:
        """Rank catalogue rows by lexical overlap on metadata. URI is never queried."""
        query_tokens = tokens(query)
        if not query_tokens:
            return []
        scored: List[DeeplinkHit] = []
        for row, field_toks in zip(self._records, self._field_tokens):
            if row.deeplink == DUMMY_URI:
                continue
            field_scores = self._field_scores_pre(query_tokens, field_toks)
            score = self._combined_score(field_scores)
            if score <= 0:
                continue
            scored.append(self._hit(row, score, field_scores))
        scored.sort(key=lambda hit: (-hit.score, hit.id))
        return scored[:limit]

    def find_best_deeplink(
        self,
        action_text: str,
        steps: Optional[Sequence[str]] = None,
        context: Optional[str] = None,
    ) -> Optional[DeeplinkHit]:
        """Return the best metadata match, or None if below confidence threshold.

        Masked URIs are never used as matching features and are never synthesized.
        """
        blob = " ".join(
            part for part in (action_text, " ".join(steps or ()), context or "") if part
        )
        ranked = self.search(blob, limit=2)
        if not ranked:
            return None
        best = ranked[0]
        if best.score < self.min_score:
            return None
        if len(ranked) > 1:
            second = ranked[1]
            same_screen = (best.metadata.get("message") or "").strip().lower() == (
                second.metadata.get("message") or ""
            ).strip().lower() and (best.metadata.get("originalType") or "") == (
                second.metadata.get("originalType") or ""
            )
            unique = same_screen or (
                best.score >= second.score + 0.015 or best.score >= second.score * 1.05
            )
            if not unique:
                return None
        catalogue = self._by_action_uri.get(best.deeplink)
        if catalogue is None or best.deeplink != catalogue.deeplink:
            return None
        return best

    def _hit(self, row: DeeplinkRecord, score: float, evidence: Dict[str, float]) -> DeeplinkHit:
        return DeeplinkHit(
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
            score=score,
            record=row,
            evidence=evidence,
        )
