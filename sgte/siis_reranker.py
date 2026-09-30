"""Deterministic SIIS candidate reranking. No embeddings, LLM, or row-id lists."""

from __future__ import annotations

from typing import Dict, Iterable, List, Sequence

from sgte.lexical import weighted_overlap
from sgte.query.understand import StructuredQuery, understand_query
from sgte.siis_repo import SiisHit

CANDIDATE_POOL = 8
PER_ISSUE_POOL = 4


def _clip(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _unique_text(parts: Iterable[str]) -> str:
    seen = []
    for part in parts:
        text = (part or "").replace("_", " ").strip()
        if text and text not in seen and text != "general":
            seen.append(text)
    return " ".join(seen)


def _focus_match(query_text: str, hit: SiisHit) -> float:
    if not (query_text or "").strip():
        return 0.0
    title = weighted_overlap(query_text, hit.title or "")
    original = weighted_overlap(query_text, hit.original_query or "")
    return _clip(max(title, original))


def _target_score(sq: StructuredQuery, hit: SiisHit) -> float:
    phrases = [sq.target] + [issue.target for issue in sq.issues]
    # Map structured targets to SIIS title wording.
    expand = {
        "touchscreen": "touchscreen touch respond",
        "display": "display screen blank black",
        "camera": "camera video recording",
        "smart_switch": "smart switch transfer",
        "time_format": "time format clock hour",
        "fast_charging": "fast charging charge battery",
        "touch_sensitivity": "touch sensitivity",
        "app_fullscreen": "full screen fullscreen display",
    }
    for key, extra in expand.items():
        if sq.target == key or any(i.target == key for i in sq.issues):
            phrases.append(extra)
    scores = [_focus_match(phrase, hit) for phrase in phrases if phrase]
    return max(scores) if scores else 0.0


def _symptom_score(sq: StructuredQuery, hit: SiisHit) -> float:
    symptoms = list(sq.symptoms)
    for issue in sq.issues:
        symptoms.extend(issue.symptoms)
    phrase = _unique_text(symptoms)
    return _focus_match(phrase, hit)


def _context_score(sq: StructuredQuery, hit: SiisHit) -> float:
    ctx = list(sq.context)
    for issue in sq.issues:
        ctx.extend(issue.context)
    phrase = _unique_text(ctx)
    if not phrase:
        return 0.0
    focused = _focus_match(phrase, hit)
    body = weighted_overlap(phrase, hit.content or "")
    return _clip(max(focused, 0.5 * body))


def _contradiction_penalty(sq: StructuredQuery, hit: SiisHit) -> float:
    blob = f"{hit.title} {hit.original_query} {(hit.content or '')[:400]}".lower()
    penalty = 0.0
    if sq.device_state.get("phone_powers_on") and (
        "won't turn on" in blob
        or "will not turn on" in blob
        or "does not power" in blob
        or "device not turning on" in blob
        or "not turning on" in blob
    ):
        penalty = max(penalty, 0.40)
    if sq.device_state.get("physical_damage") is True:
        software = any(w in blob for w in ("rotate", "rotation", "brightness", "mirroring"))
        cracked = "crack" in blob or "broken" in blob or "bleeding" in blob
        if software and not cracked:
            penalty = max(penalty, 0.35)
    symptoms = set(sq.symptoms)
    for issue in sq.issues:
        symptoms.update(issue.symptoms)
    flick = bool(symptoms & {"flicker", "flickers", "flickering"})
    camera_ctx = sq.target == "camera" or bool(set(sq.context) & {"camera", "video", "recording"})
    camera_siis = any(w in blob for w in ("camera", "video flickering", "shutter", "super steady"))
    # Display/screen flicker must not prefer camera/video SIIS.
    if flick and not camera_ctx and camera_siis:
        penalty = max(penalty, 0.55)
    # Camera/video flicker must not prefer blank-display articles.
    if camera_ctx and flick and ("blank or black" in blob or "blank display" in blob):
        penalty = max(penalty, 0.45)
    # Touch failure (visible/unspecified) must not prefer blank/invisible-screen articles.
    if sq.target == "touchscreen" and sq.device_state.get("display_visible") is not False:
        head = f"{hit.title or ''} {hit.original_query or ''}".lower()
        if "blank or black" in head or "nothing is visible" in blob:
            penalty = max(penalty, 0.55)
        # Prefer dedicated touchscreen articles over data-access-when-unresponsive.
        if "touchscreen" not in head and "touch issues" not in head:
            if ("access" in head and "data" in head) or (
                "does not respond" in head and "touch" not in head
            ):
                penalty = max(penalty, 0.55)
    # Time-format settings must not attach to unrelated SIIS (multi-window, etc.).
    if sq.target == "time_format":
        if not any(w in blob for w in ("time", "clock", "24-hour", "24 hour", "hour format")):
            penalty = max(penalty, 0.70)
    if sq.target == "fast_charging":
        if "fast charg" not in blob and "fast-charg" not in blob:
            penalty = max(penalty, 0.70)
    if sq.target == "touch_sensitivity":
        if "touch sensitivity" not in blob and "touch-sensitivity" not in blob:
            penalty = max(penalty, 0.70)
    if sq.target == "app_fullscreen":
        if any(w in blob for w in ("mirror", "smart view", "smartview", "cast")):
            penalty = max(penalty, 0.70)
    # Gmail/email + blank: penalize email-server connectivity articles.
    # TITLE-only: corpus pairs email-server rows with blank/flash original_queries.
    email_ctx = sq.target == "email" or bool(set(sq.context) & {"gmail", "email"})
    blankish = bool(symptoms & {"blank", "black", "dark"}) or (
        sq.device_state.get("display_visible") is False
    )
    if email_ctx and blankish:
        title = (hit.title or "").lower()
        if any(
            w in title
            for w in ("email server", "not responding", "internet", "wi-fi", "wifi")
        ) and not any(w in title for w in ("blank", "black")):
            penalty = max(penalty, 0.65)
    # Smart Switch + blank: prefer blank/black or check-first over Secure Folder / transfer titles.
    # Use TITLE (not OQ): corpus pairs transfer articles with blank+QR original_queries, which
    # would otherwise falsely clear this penalty via OQ "blank" wording.
    if "smart_switch" in sq.context or sq.target == "smart_switch":
        blank = bool(symptoms & {"blank", "black", "dark"}) or sq.device_state.get("display_visible") is False
        title = (hit.title or "").lower()
        transfer_title = ("secure folder" in title and "smart switch" in title) or (
            "transfer" in title and "smart switch" in title
        )
        if blank and transfer_title and "blank" not in title and "black" not in title:
            penalty = max(penalty, 0.45)
    # Multi-symptom flicker + black: prefer blank/black over camera-only SIIS.
    blank = bool(symptoms & {"blank", "black", "dark"})
    if flick and blank and camera_siis and not camera_ctx:
        penalty = max(penalty, 0.60)
    return penalty


def score_hit(hit: SiisHit, sq: StructuredQuery) -> Dict[str, float]:
    original_query_score = float(hit.score_breakdown.get("original_query", 0.0))
    title_score = float(hit.score_breakdown.get("title", 0.0))
    content_score = float(hit.score_breakdown.get("content", 0.0))
    target_score = _target_score(sq, hit)
    symptom_score = _symptom_score(sq, hit)
    context_score = _context_score(sq, hit)
    contradiction = _contradiction_penalty(sq, hit)
    rerank_score = (
        0.35 * original_query_score
        + 0.25 * title_score
        + 0.10 * content_score
        + 0.15 * target_score
        + 0.10 * symptom_score
        + 0.05 * context_score
        - contradiction
    )
    return {
        "rerank_original_query": original_query_score,
        "rerank_title": title_score,
        "rerank_content": content_score,
        "rerank_target": target_score,
        "rerank_symptom": symptom_score,
        "rerank_context": context_score,
        "rerank_contradiction": contradiction,
        "rerank_score": rerank_score,
        "lexical_score": float(hit.score),
    }


def rerank_siis_hits(hits: Sequence[SiisHit], sq: StructuredQuery) -> List[SiisHit]:
    ranked: List[SiisHit] = []
    for hit in hits:
        extra = score_hit(hit, sq)
        breakdown = dict(hit.score_breakdown)
        breakdown.update(extra)
        ranked.append(
            SiisHit(
                id=hit.id,
                original_query=hit.original_query,
                title=hit.title,
                content=hit.content,
                siis_response=hit.siis_response,
                score=hit.score,
                record=hit.record,
                score_breakdown=breakdown,
            )
        )
    ranked.sort(
        key=lambda item: (
            -float(item.score_breakdown.get("rerank_score", 0.0)),
            -float(item.score),
            item.id,
        )
    )
    return ranked


def collect_siis_candidates(siis, query: str, sq: StructuredQuery, top_k: int = 3) -> List[SiisHit]:
    """Broader lexical pool. Does not change SiisRepository scoring."""
    pool = max(int(top_k), CANDIDATE_POOL)
    collected: List[SiisHit] = []
    seen = set()

    def _add(batch: Sequence[SiisHit]) -> None:
        for hit in batch:
            if hit.id in seen:
                continue
            seen.add(hit.id)
            collected.append(hit)

    if len(sq.issues) > 1:
        per_issue = max(PER_ISSUE_POOL, pool // 2)
        for issue in sq.issues:
            qtext = f"{issue.target} {' '.join(issue.symptoms)} {query}"
            _add(siis.search(qtext, top_k=per_issue))
        _add(siis.search(query, top_k=pool))
        if not collected:
            _add(siis.search(query, top_k=pool))
        return collected
    return list(siis.search(query, top_k=pool))


def _is_smart_switch_transfer_title(hit: SiisHit) -> bool:
    title = (hit.title or "").lower()
    if "blank" in title or "black" in title:
        return False
    return ("secure folder" in title and "smart switch" in title) or (
        "transfer" in title and "smart switch" in title
    )


def _is_blank_primary_evidence(hit: SiisHit) -> bool:
    """Primary blank/unusable-display evidence (not Smart Switch transfer instructions)."""
    title = (hit.title or "").lower()
    content_head = ((hit.content or "")[:480]).lower()
    if "blank or black" in title:
        return True
    if "check first" in title and any(
        w in content_head for w in ("mouse", "keyboard", "usb", "blank", "black", "visible", "touchscreen")
    ):
        return True
    if "access" in title and "data" in title:
        return True
    return False


def _is_camera_flicker_evidence(hit: SiisHit) -> bool:
    """Camera/video shutter flicker article — off-domain for display blank/flicker."""
    title = (hit.title or "").lower()
    content_head = ((hit.content or "")[:480]).lower()
    blob = f"{title} {content_head}"
    return any(w in blob for w in ("camera", "video flickering", "shutter", "super steady"))


def _is_email_only_evidence(hit: SiisHit) -> bool:
    """Email-server article — must not replace blank-primary via generalized fallback."""
    title = (hit.title or "").lower()
    return "email" in title and "blank" not in title and "black" not in title


def _blank_symptoms(sq: StructuredQuery) -> bool:
    symptoms = set(sq.symptoms)
    for issue in sq.issues:
        symptoms.update(issue.symptoms)
    return bool(symptoms & {"blank", "black", "dark"}) or sq.device_state.get("display_visible") is False


def _eligible_blank_primary(
    hit: SiisHit,
    query: str,
    sq: StructuredQuery,
    confident_fn,
) -> bool:
    """Confident blank/check-first evidence only — never camera, email, or SS transfer."""
    if not confident_fn(hit, query=query, structured=sq):
        return False
    if not _is_blank_primary_evidence(hit):
        return False
    if _is_camera_flicker_evidence(hit):
        return False
    if _is_email_only_evidence(hit):
        return False
    if _is_smart_switch_transfer_title(hit):
        return False
    # Fold/open flicker: USB check-first is not a flicker remedy (Phase 78 S09).
    symptoms = set(sq.symptoms)
    for issue in sq.issues:
        symptoms.update(issue.symptoms)
    flick = bool(symptoms & {"flicker", "flickers", "flickering", "flashes", "flash"})
    open_ctx = bool(set(sq.context) & {"opening_device", "opening_app"})
    camera_ctx = sq.target == "camera" or bool(set(sq.context) & {"camera", "video", "recording"})
    if flick and open_ctx and not camera_ctx:
        title = (hit.title or "").lower()
        content_head = ((hit.content or "")[:480]).lower()
        if "check first" in title and any(
            w in content_head for w in ("mouse", "keyboard", "usb")
        ):
            return False
    return True


def select_primary_siis(
    hits: Sequence[SiisHit],
    query: str,
    sq: StructuredQuery,
    *,
    confident_fn=None,
) -> SiisHit | None:
    """Choose grounding SIIS: specific context evidence, else primary-problem evidence.

    For blank/black display, off-domain context articles (Smart Switch transfer, camera
    flicker, email-server connectivity) or an unconfident top hit yield the next
    confident blank/check-first row.
    """
    if not hits:
        return None
    top = hits[0]
    if confident_fn is None:
        return top
    blank = _blank_symptoms(sq)
    if not blank:
        return top

    top_conf = bool(confident_fn(top, query=query, structured=sq))
    # Trigger: unconfident top, or blank-irrelevant context article at top.
    # Email-server connectivity titles also trigger blank-primary fallback when the
    # complaint is a blank/black display (Phase 43 — do not keep Wi-Fi/Safe Mode plans).
    needs_fallback = (
        (not top_conf)
        or _is_smart_switch_transfer_title(top)
        or _is_camera_flicker_evidence(top)
        or _is_email_only_evidence(top)
    )
    if not needs_fallback:
        return top

    for hit in hits:
        if hit.id == top.id and (
            _is_smart_switch_transfer_title(top)
            or _is_camera_flicker_evidence(top)
            or _is_email_only_evidence(top)
        ):
            continue
        if _eligible_blank_primary(hit, query, sq, confident_fn):
            return hit
    return top


def retrieve_siis(siis, query: str, sq: StructuredQuery | None = None, top_k: int = 3) -> List[SiisHit]:
    structured = sq or understand_query(query)
    candidates = collect_siis_candidates(siis, query, structured, top_k=top_k)
    ranked = rerank_siis_hits(candidates, structured)
    keep = max(int(top_k), len(structured.issues) if len(structured.issues) > 1 else int(top_k))
    # Blank/black queries: keep enough ranked hits so blank-primary fallback can see
    # check-first rows that sit just outside default top_k=3 (e.g. official Q9 → row_17).
    if _blank_symptoms(structured):
        keep = max(keep, min(5, len(ranked)))
    return ranked[:keep]


def format_ranked_hits(hits: Sequence[SiisHit], limit: int = 8) -> str:
    lines: List[str] = []
    for i, hit in enumerate(hits[:limit], start=1):
        bd = hit.score_breakdown
        rerank = bd.get("rerank_score")
        rerank_s = f"{rerank:.3f}" if isinstance(rerank, (int, float)) else "n/a"
        lines.append(
            f"{i}. {hit.id} lexical={hit.score:.3f} rerank={rerank_s} "
            f"oq={bd.get('original_query', 0.0):.3f} title={bd.get('title', 0.0):.3f} "
            f"content={bd.get('content', 0.0):.3f} target={bd.get('rerank_target', 0.0):.3f} "
            f"symptom={bd.get('rerank_symptom', 0.0):.3f} context={bd.get('rerank_context', 0.0):.3f} "
            f"contra={bd.get('rerank_contradiction', 0.0):.3f} | {hit.title}"
        )
    return "\n".join(lines) or "(none)"
