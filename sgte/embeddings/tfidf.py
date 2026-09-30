"""Local TF-IDF embeddings over catalogue metadata. No network, no URI features."""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from sgte.embeddings.base import EmbeddingProvider
from sgte.lexical import token_list


def _l2_normalize(vec: Dict[int, float]) -> Dict[int, float]:
    norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
    return {i: v / norm for i, v in vec.items()}


def cosine_sparse(a: Dict[int, float], b: Dict[int, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return float(sum(v * b.get(i, 0.0) for i, v in a.items()))


class TfidfEmbeddingProvider(EmbeddingProvider):
    """Fits a vocabulary on provided documents and encodes queries with the same IDF."""

    provider_name = "tfidf"

    def __init__(self) -> None:
        self.vocab: Dict[str, int] = {}
        self.idf: List[float] = []
        self._fitted = False

    def fit(self, documents: Sequence[str]) -> None:
        df: Counter[str] = Counter()
        tokenized = [token_list(doc) for doc in documents]
        for tokens in tokenized:
            df.update(set(tokens))
        terms = sorted(df)
        self.vocab = {term: i for i, term in enumerate(terms)}
        n = max(len(documents), 1)
        self.idf = [0.0] * len(terms)
        for term, idx in self.vocab.items():
            self.idf[idx] = math.log((n + 1) / (df[term] + 1)) + 1.0
        self._fitted = True

    def embed_texts(self, texts: Sequence[str]) -> List[List[float]]:
        if not self._fitted:
            raise RuntimeError("TfidfEmbeddingProvider.fit() must run before encode")
        dense: List[List[float]] = []
        dim = len(self.vocab)
        for text in texts:
            sparse = self._encode_sparse(text)
            row = [0.0] * dim
            for i, v in sparse.items():
                row[i] = v
            dense.append(row)
        return dense

    def encode_sparse(self, text: str) -> Dict[int, float]:
        return self._encode_sparse(text)

    def _encode_sparse(self, text: str) -> Dict[int, float]:
        counts = Counter(token_list(text))
        raw: Dict[int, float] = {}
        for term, tf in counts.items():
            idx = self.vocab.get(term)
            if idx is None:
                continue
            raw[idx] = (1.0 + math.log(tf)) * self.idf[idx]
        return _l2_normalize(raw)

    def dump(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"vocab": self.vocab, "idf": self.idf}),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> "TfidfEmbeddingProvider":
        payload = json.loads(path.read_text(encoding="utf-8"))
        inst = cls()
        inst.vocab = {k: int(v) for k, v in payload["vocab"].items()}
        inst.idf = [float(x) for x in payload["idf"]]
        inst._fitted = True
        return inst
