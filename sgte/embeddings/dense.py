"""Local dense embeddings via signed feature hashing. No API, no URI features.

Optional MiniLM wrapper is selected by SGTE_EMBEDDING_PROVIDER=minilm when
sentence-transformers is installed. Default is this hashing encoder so the
pipeline stays fully local.
"""

from __future__ import annotations

import hashlib
import math
from typing import List, Sequence

from sgte.embeddings.base import EmbeddingProvider
from sgte.lexical import token_list


def _trigrams(token: str) -> List[str]:
    padded = f"#{token}#"
    return [padded[i : i + 3] for i in range(len(padded) - 2)]


def hash_feature(feature: str, dim: int) -> tuple[int, float]:
    digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
    unsigned = int.from_bytes(digest, "little")
    idx = unsigned % dim
    sign = 1.0 if digest[0] % 2 == 0 else -1.0
    return idx, sign


def l2_normalize(vec: List[float]) -> List[float]:
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine_dense(a: Sequence[float], b: Sequence[float]) -> float:
    return float(sum(x * y for x, y in zip(a, b)))


class HashingEmbeddingProvider(EmbeddingProvider):
    """384-d signed n-gram hashing. Deterministic, local, no network."""

    provider_name = "hashing-ngram"
    model_name = "blake2b-char3-token-384"
    local = True

    def __init__(self, dim: int = 384):
        self.dim = dim

    def embed_texts(self, texts: Sequence[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]

    def embed_text(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        tokens = token_list(text, min_len=2, drop_stopwords=True)
        for tok in tokens:
            i, s = hash_feature(f"t:{tok}", self.dim)
            vec[i] += s
            for tri in _trigrams(tok):
                j, s2 = hash_feature(f"g:{tri}", self.dim)
                vec[j] += 0.5 * s2
        return l2_normalize(vec)


class MiniLMEmbeddingProvider(EmbeddingProvider):
    """Optional local SentenceTransformer. Falls back by raising ImportError."""

    provider_name = "minilm"
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    local = True

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer  # type: ignore

        self.model_name = model_name
        self._model = SentenceTransformer(model_name)

    def embed_texts(self, texts: Sequence[str]) -> List[List[float]]:
        vectors = self._model.encode(list(texts), normalize_embeddings=True, show_progress_bar=False)
        return [list(map(float, row)) for row in vectors]


def build_dense_provider(name: str) -> EmbeddingProvider:
    name = (name or "hashing").lower()
    if name in {"tfidf", "hashing", "hashing-ngram", "local"}:
        return HashingEmbeddingProvider()
    if name in {"minilm", "sentence", "sbert"}:
        try:
            return MiniLMEmbeddingProvider()
        except Exception:
            return HashingEmbeddingProvider()
    return HashingEmbeddingProvider()
