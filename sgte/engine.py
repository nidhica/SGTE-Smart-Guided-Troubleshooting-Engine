"""Deterministic SIIS retrieval + deeplink mapping pipeline. No LLM."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional

from sgte.builder import ActionTrace, build_plan
from sgte.deeplink_repo import DeeplinkRepository
from sgte.extractor import extract_candidate_actions
from sgte.official_schema import ContextDeeplinkResponse
from sgte.siis_repo import SiisHit, SiisRepository
from sgte.validator import ResponseValidator, ValidationResult


def no_match_response() -> ContextDeeplinkResponse:
    return ContextDeeplinkResponse(contexts=[])


def no_match_dict() -> dict:
    return no_match_response().model_dump()


@dataclass
class PipelineResult:
    response: ContextDeeplinkResponse
    siis_hits: List[SiisHit]
    matched: bool
    traces: List[ActionTrace] = field(default_factory=list)
    retrieval_ms: float = 0.0
    mapping_ms: float = 0.0
    validation: Optional[ValidationResult] = None
    extraction_empty: bool = False
    # HTTP-envelope metadata only (not part of official schema.py). Values: no_match | no_siis_context.
    fallback: Optional[str] = None


# Back-compat alias used by Phase 1 tests.
Phase1Result = PipelineResult


class TroubleshootingEngine:
    def __init__(
        self,
        siis: Optional[SiisRepository] = None,
        deeplinks: Optional[DeeplinkRepository] = None,
        retrieval_min_score: Optional[float] = None,
    ):
        self.siis = siis or SiisRepository.from_file()
        if retrieval_min_score is not None:
            self.siis.min_score = retrieval_min_score
        self.deeplinks = deeplinks or DeeplinkRepository.from_file()
        self.validator = ResponseValidator(self.deeplinks)

    def retrieve_siis(self, query: str, top_k: int = 3) -> List[SiisHit]:
        return self.siis.search(query, top_k=top_k)

    def respond(self, query: str, top_k: int = 3) -> PipelineResult:
        t0 = time.perf_counter()
        hits = self.retrieve_siis(query, top_k=top_k)
        retrieval_ms = (time.perf_counter() - t0) * 1000.0
        if not hits:
            empty = no_match_response()
            return PipelineResult(
                response=empty,
                siis_hits=[],
                matched=False,
                retrieval_ms=retrieval_ms,
                mapping_ms=0.0,
                validation=self.validator.validate(empty.model_dump()),
                fallback="no_match",
            )

        t1 = time.perf_counter()
        top = hits[0]
        candidates = extract_candidate_actions(top.record)
        plan = build_plan(top, candidates, self.deeplinks, query=query)
        mapping_ms = (time.perf_counter() - t1) * 1000.0

        if plan.goal is None:
            empty = no_match_response()
            return PipelineResult(
                response=empty,
                siis_hits=hits,
                matched=True,
                traces=[],
                retrieval_ms=retrieval_ms,
                mapping_ms=mapping_ms,
                validation=self.validator.validate(empty.model_dump()),
                extraction_empty=True,
                fallback="no_match",
            )

        response = ContextDeeplinkResponse(contexts=[plan.goal])
        dumped = response.model_dump()
        validation = self.validator.validate(dumped)
        return PipelineResult(
            response=response,
            siis_hits=hits,
            matched=True,
            traces=plan.traces,
            retrieval_ms=retrieval_ms,
            mapping_ms=mapping_ms,
            validation=validation,
        )
