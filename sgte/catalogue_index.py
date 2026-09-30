"""Precomputed catalogue index: TF-IDF + dense local embeddings. Never embeds URIs."""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from sgte.deeplink_repo import DUMMY_URI, DeeplinkRepository
from sgte.embeddings.base import EmbeddingProvider
from sgte.embeddings.dense import build_dense_provider, cosine_dense
from sgte.embeddings.tfidf import TfidfEmbeddingProvider, cosine_sparse
from sgte.loaders import DeeplinkRecord
from sgte.intent import extract_intent, candidate_target
from sgte.lexical import token_list
from sgte.polarity import original_type_polarity, polarity

_URI = re.compile(r"bixby://\S+", re.IGNORECASE)

METADATA_EMBED_FIELDS = (
    "message",
    "description",
    "qna_description",
    "originalType",
    "control_type",
)


def metadata_document(row: DeeplinkRecord) -> str:
    parts = []
    for field in METADATA_EMBED_FIELDS:
        value = getattr(row, field, None)
        if value is None or value == "":
            continue
        parts.append(str(value))
    text = " ".join(parts)
    cleaned = _URI.sub(" ", text)
    if "bixby://" in cleaned.lower():
        raise ValueError("masked URI leaked into embedding document")
    return cleaned


def normalized_catalogue_entry(row: DeeplinkRecord) -> dict:
    """Index-only view of catalogue text. Never includes the URI."""
    msg = row.message or ""
    intent = extract_intent(msg)
    op = polarity(msg) or original_type_polarity(row.originalType) or intent.operation
    doc = metadata_document(row)
    return {
        "catalogue_id": row.id,
        "description": row.description,
        "message": msg,
        "originalType": row.originalType,
        "normalized_target": candidate_target(msg, row.description or "", row.qna_description or ""),
        "normalized_operation": op,
        "normalized_context": row.qna_description or "",
        "keywords": token_list(doc, min_len=3),
    }


def _fingerprint(docs: Sequence[str], provider: str) -> str:
    h = hashlib.sha256()
    h.update(provider.encode("utf-8"))
    for doc in docs:
        h.update(doc.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


class CatalogueIndex:
    def __init__(
        self,
        repo: DeeplinkRepository,
        tfidf: TfidfEmbeddingProvider,
        sparse: List[Dict[int, float]],
        dense_provider: EmbeddingProvider,
        dense: List[List[float]],
        stats: dict,
    ):
        self.repo = repo
        self.embedder = tfidf
        self.sparse = sparse
        self.dense_provider = dense_provider
        self.dense = dense
        self.stats = stats
        self.rows = [row for row in repo.all() if row.deeplink != DUMMY_URI]

    @classmethod
    def build(
        cls,
        repo: DeeplinkRepository,
        index_dir: Path,
        dense_name: str = "hashing",
    ) -> "CatalogueIndex":
        t0 = time.perf_counter()
        rows = [row for row in repo.all() if row.deeplink != DUMMY_URI]
        docs = [metadata_document(row) for row in rows]
        dense_provider = build_dense_provider(dense_name)
        fp = _fingerprint(docs, dense_provider.provider_name)
        tfidf_path = index_dir / "deeplink_tfidf.json"
        sparse_path = index_dir / "deeplink_sparse.json"
        dense_path = index_dir / "deeplink_dense.json"
        meta_path = index_dir / "deeplink_index_meta.json"
        if (
            tfidf_path.is_file()
            and sparse_path.is_file()
            and dense_path.is_file()
            and meta_path.is_file()
            and json.loads(meta_path.read_text(encoding="utf-8")).get("fingerprint") == fp
        ):
            tfidf = TfidfEmbeddingProvider.load(tfidf_path)
            raw = json.loads(sparse_path.read_text(encoding="utf-8"))
            sparse = [{int(k): float(v) for k, v in row.items()} for row in raw]
            dense = json.loads(dense_path.read_text(encoding="utf-8"))
            stats = json.loads(meta_path.read_text(encoding="utf-8"))
            stats["index_load_ms"] = (time.perf_counter() - t0) * 1000.0
            stats["index_build_ms"] = stats.get("index_build_ms", 0.0)
        else:
            tfidf = TfidfEmbeddingProvider()
            tfidf.fit(docs)
            sparse = [tfidf.encode_sparse(doc) for doc in docs]
            dense = dense_provider.embed_texts(docs)
            index_dir.mkdir(parents=True, exist_ok=True)
            tfidf.dump(tfidf_path)
            sparse_path.write_text(
                json.dumps([{str(k): v for k, v in row.items()} for row in sparse]),
                encoding="utf-8",
            )
            dense_path.write_text(json.dumps(dense), encoding="utf-8")
            build_ms = (time.perf_counter() - t0) * 1000.0
            stats = {
                "fingerprint": fp,
                "n": len(rows),
                "uri_in_corpus": False,
                "dense_provider": dense_provider.provider_name,
                "dense_model": getattr(dense_provider, "model_name", dense_provider.provider_name),
                "dense_local": getattr(dense_provider, "local", True),
                "index_build_ms": build_ms,
                "index_load_ms": build_ms,
            }
            meta_path.write_text(json.dumps(stats), encoding="utf-8")
        return cls(repo, tfidf, sparse, dense_provider, dense, stats)

    def documents_contain_uri_scheme(self) -> bool:
        return any("bixby://" in metadata_document(row).lower() for row in self.rows)

    def documents_contain_deeplink_uri(self) -> bool:
        return any((row.deeplink or "") in metadata_document(row) for row in self.rows)

    def tfidf_search(self, text: str, limit: int = 20) -> List[Tuple[DeeplinkRecord, float]]:
        query = _URI.sub(" ", text or "")
        qv = self.embedder.encode_sparse(query)
        scored = []
        for row, vec in zip(self.rows, self.sparse):
            score = cosine_sparse(qv, vec)
            if score > 0:
                scored.append((row, score))
        scored.sort(key=lambda item: (-item[1], item[0].id))
        return scored[:limit]

    def dense_search(
        self,
        text: str,
        limit: int = 20,
        query_vector: Optional[List[float]] = None,
    ) -> List[Tuple[DeeplinkRecord, float]]:
        query = _URI.sub(" ", text or "")
        if query_vector is None:
            qv = self.dense_provider.embed_texts([query])[0]
        else:
            qv = query_vector
        scored = []
        for row, vec in zip(self.rows, self.dense):
            score = cosine_dense(qv, vec)
            if score > 0:
                scored.append((row, score))
        scored.sort(key=lambda item: (-item[1], item[0].id))
        return scored[:limit]

    def semantic_search(self, text: str, limit: int = 20) -> List[Tuple[DeeplinkRecord, float]]:
        """Union ranking used by older tests: prefer dense, fill with TF-IDF."""
        merged: Dict[str, Tuple[DeeplinkRecord, float]] = {}
        for row, score in self.tfidf_search(text, limit=limit):
            merged[row.deeplink] = (row, score)
        for row, score in self.dense_search(text, limit=limit):
            prev = merged.get(row.deeplink)
            if prev is None or score > prev[1]:
                merged[row.deeplink] = (row, score)
        ranked = sorted(merged.values(), key=lambda item: (-item[1], item[0].id))
        return ranked[:limit]
