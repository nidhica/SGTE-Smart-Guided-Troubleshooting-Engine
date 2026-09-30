"""Estimated request cost. Cache/mock/local are zero. No invented provider prices."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CostReport:
    cost_usd: float
    source: str


def estimate_cost_usd(
    *,
    cache_hit: bool,
    provider_name: str,
    provider_cost_usd: Optional[float] = None,
) -> CostReport:
    if cache_hit:
        return CostReport(cost_usd=0.0, source="cache")
    name = (provider_name or "").lower()
    if name in {"mock", "none", "local", "hashing", "hashing-ngram", ""}:
        return CostReport(cost_usd=0.0, source="local")
    if provider_cost_usd is not None:
        return CostReport(cost_usd=float(provider_cost_usd), source="provider")
    raw = os.environ.get("SGTE_LLM_USD_PER_CALL", "").strip()
    if raw:
        return CostReport(cost_usd=float(raw), source="configured")
    return CostReport(cost_usd=0.0, source="unknown_unpriced")
