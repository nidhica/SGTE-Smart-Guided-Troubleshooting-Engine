"""Semantic fast-path cache: validated responses only, local embeddings, polarity safety."""

from sgte.cache.semantic import CacheLookup, SemanticCache
from sgte.cache.prewarm import prewarm_cache

__all__ = ["CacheLookup", "SemanticCache", "prewarm_cache"]
