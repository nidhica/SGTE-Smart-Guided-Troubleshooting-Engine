"""Embedding provider interface. Catalogue URIs must never be embedded."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Sequence


class EmbeddingProvider(ABC):
    provider_name: str = "base"

    @abstractmethod
    def embed_texts(self, texts: Sequence[str]) -> List[List[float]]:
        """Dense or sparse-as-dense vectors. Input must be metadata text only."""
