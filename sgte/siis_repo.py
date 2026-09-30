"""SIIS knowledge access with a deterministic lexical baseline. No LLM/embeddings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Union

from sgte.lexical import idf_weights, weighted_overlap
from sgte.loaders import SiisRecord, load_siis_responses


@dataclass(frozen=True)
class SiisHit:
    id: str
    original_query: str
    title: str
    content: str
    siis_response: dict
    score: float
    record: SiisRecord
    score_breakdown: Dict[str, float]


class SiisRepository:
    """Weighted lexical retrieval over official SIIS rows.

    Score = 0.50 * overlap(query, original_query)
          + 0.30 * overlap(query, title)
          + 0.20 * overlap(query, content)

    Tokens are lowercased, punctuation-stripped, stopword-filtered.
    IDF is computed from the official 20-row corpus so common words weigh less.
    """

    def __init__(self, records: Sequence[SiisRecord], min_score: float = 0.18):
        self._records: List[SiisRecord] = list(records)
        self.min_score = min_score
        corpus = [self._document(row) for row in self._records]
        self._idf = idf_weights(corpus)

    @classmethod
    def from_file(cls, path: Union[Path, None] = None) -> "SiisRepository":
        return cls(load_siis_responses(path))

    def __len__(self) -> int:
        return len(self._records)

    def all(self) -> List[SiisRecord]:
        return list(self._records)

    def _document(self, row: SiisRecord) -> str:
        return " ".join((row.original_query, row.title, row.content))

    def search(self, query: str, top_k: int = 3, limit: Union[int, None] = None) -> List[SiisHit]:
        k = limit if limit is not None else top_k
        scored: List[SiisHit] = []
        for row in self._records:
            q_score = weighted_overlap(query, row.original_query, self._idf)
            t_score = weighted_overlap(query, row.title, self._idf)
            c_score = weighted_overlap(query, row.content, self._idf)
            score = 0.50 * q_score + 0.30 * t_score + 0.20 * c_score
            if score < self.min_score:
                continue
            scored.append(
                SiisHit(
                    id=row.id,
                    original_query=row.original_query,
                    title=row.title,
                    content=row.content,
                    siis_response=dict(row.siis_response),
                    score=score,
                    record=row,
                    score_breakdown={
                        "original_query": q_score,
                        "title": t_score,
                        "content": c_score,
                    },
                )
            )
        scored.sort(key=lambda hit: (-hit.score, hit.id))
        return scored[:k]


def hit_from_supplied_siis(query: str, siis_response: str) -> SiisHit:
    """Wrap client-supplied SIIS text. Does not retrieve or invent articles."""
    content = siis_response or ""
    first = next((line.strip() for line in content.splitlines() if line.strip()), "Client-supplied SIIS")
    title = first[:120]
    record = SiisRecord(
        id="supplied",
        original_query=query or "",
        title=title,
        content=content,
        siis_response={"title": title, "content": content},
        raw={"source": "client"},
    )
    return SiisHit(
        id="supplied",
        original_query=record.original_query,
        title=title,
        content=content,
        siis_response=dict(record.siis_response),
        score=1.0,
        record=record,
        score_breakdown={"original_query": 1.0, "title": 1.0, "content": 1.0},
    )
