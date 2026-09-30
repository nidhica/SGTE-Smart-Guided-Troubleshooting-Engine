"""Prewarm the semantic cache by running the real pipeline. No fabricated responses."""

from __future__ import annotations

from typing import Iterable, List, Optional

from sgte.query.enrich import enrich_query


def prewarm_cache(
    pipeline,
    queries: Iterable[str],
    *,
    include_variations: bool = True,
) -> dict:
    attempted = 0
    cached = 0
    failures: List[str] = []
    seen = set()
    for query in queries:
        variants = [query]
        if include_variations:
            variants.extend(enrich_query(query)["query_variations"])  # type: ignore[arg-type]
        for text in variants:
            key = (text or "").strip()
            if not key or key in seen:
                continue
            seen.add(key)
            attempted += 1
            before = pipeline.cache.stats()["size"]
            try:
                result = pipeline.troubleshoot(key)
                if result.validation is None or not result.validation.ok:
                    failures.append(f"invalid:{key[:80]}")
                    continue
            except Exception as exc:  # noqa: BLE001 — prewarm must continue
                failures.append(f"{type(exc).__name__}:{key[:80]}")
                continue
            after = pipeline.cache.stats()["size"]
            if after > before or result.cache_hit:
                cached += 1
            else:
                failures.append(f"not_cached:{key[:80]}")
    return {
        "entries_attempted": attempted,
        "entries_successfully_cached": cached,
        "failures": failures,
        "failure_count": len(failures),
        "cache_size": pipeline.cache.stats()["size"],
    }
