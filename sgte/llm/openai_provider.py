"""OpenAI-compatible chat completions JSON. Requires an API key from the environment."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple

from sgte.llm.base import LLMError, LLMHTTPError, LLMProvider, MissingCredentialsError

# Never echo secrets from error bodies into exception strings or logs.
_SECRET_RE = re.compile(
    r"(?i)(authorization\s*[:=]\s*bearer\s+\S+|sk-[a-z0-9\-_]{8,}|"
    r"api[_-]?key\s*[:=]\s*\S+|\"key\"\s*:\s*\"[^\"]+\")"
)


def redact_secrets(text: str) -> str:
    if not text:
        return ""
    return _SECRET_RE.sub("[REDACTED]", text)


def _safe_read_http_body(exc: urllib.error.HTTPError, *, limit: int = 4096) -> str:
    try:
        raw = exc.read(limit) or b""
    except Exception:  # noqa: BLE001
        return ""
    try:
        return raw.decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return ""


def parse_openai_error_body(body_text: str) -> Dict[str, Optional[str]]:
    """Extract safe OpenAI error fields from a response body. Never returns secrets."""
    out: Dict[str, Optional[str]] = {
        "api_message": None,
        "api_code": None,
        "api_type": None,
        "api_param": None,
    }
    text = redact_secrets((body_text or "").strip())
    if not text:
        return out
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        out["api_message"] = text[:300]
        return out
    err = payload.get("error") if isinstance(payload, dict) else None
    if not isinstance(err, dict):
        out["api_message"] = text[:300]
        return out
    msg = err.get("message")
    code = err.get("code")
    typ = err.get("type")
    param = err.get("param")
    out["api_message"] = redact_secrets(str(msg))[:300] if msg is not None else None
    out["api_code"] = str(code) if code is not None else None
    out["api_type"] = str(typ) if typ is not None else None
    out["api_param"] = str(param) if param is not None else None
    return out


def classify_openai_http_error(
    status: Optional[int],
    body_text: str = "",
    *,
    reason: str = "",
) -> Dict[str, Any]:
    """Classify an OpenAI-compatible HTTP failure without guessing beyond evidence.

    Returns keys: kind, http_status, api_code, api_type, api_message, confidence, note
    """
    parsed = parse_openai_error_body(body_text)
    api_code = (parsed.get("api_code") or "").lower()
    api_type = (parsed.get("api_type") or "").lower()
    api_message = parsed.get("api_message") or ""
    msg_l = api_message.lower()
    reason_l = (reason or "").lower()
    combined = f"{api_code} {api_type} {msg_l} {reason_l}"

    kind = "http_error"
    confidence = "low"
    note = ""

    if status in {401, 403}:
        kind = "authentication"
        confidence = "high"
        note = "HTTP status indicates authentication/authorization failure."
    elif status is not None and 500 <= status <= 599:
        kind = "server_error"
        confidence = "high"
        note = "HTTP 5xx server error."
    elif status == 429:
        # Distinguish quota/billing only when the body/code says so.
        quota_markers = (
            "insufficient_quota",
            "billing_not_active",
            "billing",
            "quota",
            "exceeded your current quota",
            "credit",
        )
        rate_markers = ("rate_limit", "rate limit", "too many requests", "tokens per min", "requests per min")
        has_quota = any(m in combined for m in quota_markers) or api_code == "insufficient_quota"
        has_rate = any(m in combined for m in rate_markers) or api_code in {
            "rate_limit_exceeded",
            "rate_limit_error",
        }
        if has_quota and not has_rate:
            kind = "insufficient_quota"
            confidence = "high" if api_code == "insufficient_quota" or "insufficient_quota" in combined else "medium"
            note = "HTTP 429 with quota/billing evidence in API body."
        elif has_quota and has_rate:
            # Body mentions both or ambiguous markers — do not over-claim.
            if api_code == "insufficient_quota":
                kind = "insufficient_quota"
                confidence = "high"
                note = "HTTP 429 with api_code=insufficient_quota."
            elif api_code in {"rate_limit_exceeded", "rate_limit_error"}:
                kind = "rate_limit"
                confidence = "high"
                note = "HTTP 429 with rate-limit api_code."
            else:
                kind = "rate_limit_or_quota_unspecified"
                confidence = "low"
                note = "HTTP 429 with mixed/ambiguous body markers; quota vs rate limit not distinguished."
        elif has_rate and api_code in {"rate_limit_exceeded", "rate_limit_error"}:
            kind = "rate_limit"
            confidence = "high"
            note = "HTTP 429 with rate-limit api_code."
        elif has_rate and body_text.strip():
            kind = "rate_limit"
            confidence = "medium"
            note = "HTTP 429 with rate-limit language in body; no explicit insufficient_quota code."
        elif body_text.strip():
            kind = "rate_limit_or_quota_unspecified"
            confidence = "low"
            note = "HTTP 429 with body present but no clear quota vs rate-limit code."
        else:
            kind = "rate_limit_or_quota_unspecified"
            confidence = "low"
            note = (
                "HTTP 429 Too Many Requests without a usable API error body; "
                "cannot distinguish rate limit from insufficient quota."
            )
    elif status is not None:
        kind = "http_error"
        confidence = "medium"
        note = f"HTTP {status} without a more specific mapping."

    return {
        "kind": kind,
        "http_status": status,
        "api_code": parsed.get("api_code"),
        "api_type": parsed.get("api_type"),
        "api_message": parsed.get("api_message"),
        "confidence": confidence,
        "note": note,
    }


def classify_error_text(detail: str) -> Dict[str, Any]:
    """Best-effort classification from a previously recorded error_detail string."""
    text = redact_secrets(detail or "")
    lower = text.lower()
    status = None
    m = re.search(r"http error\s+(\d{3})", lower)
    if m:
        status = int(m.group(1))
    # Recover embedded body if provider included it after "body="
    body = ""
    if "body=" in lower:
        body = text.split("body=", 1)[1].strip()[:4096]
    reason = ""
    if "too many requests" in lower:
        reason = "Too Many Requests"
    elif "unauthorized" in lower:
        reason = "Unauthorized"
    elif "internal server error" in lower:
        reason = "Internal Server Error"
    if status is not None:
        return classify_openai_http_error(status, body, reason=reason)
    if "did not return json" in lower or "jsondecode" in lower:
        return {
            "kind": "malformed_response",
            "http_status": None,
            "api_code": None,
            "api_type": None,
            "api_message": text[:300],
            "confidence": "high",
            "note": "Provider reported non-JSON model content.",
        }
    if "unexpected llm payload" in lower or "empty" in lower:
        return {
            "kind": "malformed_response",
            "http_status": None,
            "api_code": None,
            "api_type": None,
            "api_message": text[:300],
            "confidence": "medium",
            "note": "Provider reported empty/unexpected payload.",
        }
    if "timed out" in lower or "timeout" in lower:
        return {
            "kind": "timeout",
            "http_status": None,
            "api_code": None,
            "api_type": None,
            "api_message": text[:300],
            "confidence": "high",
            "note": "Provider timed out.",
        }
    if "budget exceeded" in lower:
        return {
            "kind": "request_budget_exceeded",
            "http_status": None,
            "api_code": None,
            "api_type": None,
            "api_message": text[:300],
            "confidence": "high",
            "note": "Evaluation harness request budget exceeded.",
        }
    return {
        "kind": "llm_error",
        "http_status": status,
        "api_code": None,
        "api_type": None,
        "api_message": text[:300],
        "confidence": "low",
        "note": "Insufficient detail to classify further.",
    }


def _format_http_error_message(status: Optional[int], reason: str, classified: Dict[str, Any]) -> str:
    parts = [f"LLM HTTP error: HTTP Error {status}: {reason or 'Error'}"]
    parts.append(f"kind={classified['kind']}")
    if classified.get("api_code"):
        parts.append(f"api_code={classified['api_code']}")
    if classified.get("api_type"):
        parts.append(f"api_type={classified['api_type']}")
    if classified.get("api_message"):
        parts.append(f"api_message={classified['api_message']}")
    # Embed a redacted body snippet so offline reclassification can use api_code/message.
    err_obj: Dict[str, Any] = {}
    if classified.get("api_code"):
        err_obj["code"] = classified["api_code"]
    if classified.get("api_type"):
        err_obj["type"] = classified["api_type"]
    if classified.get("api_message"):
        err_obj["message"] = classified["api_message"]
    if err_obj:
        parts.append("body=" + json.dumps({"error": err_obj}, ensure_ascii=True))
    return " | ".join(parts)


class OpenAICompatibleProvider(LLMProvider):
    provider_name = "openai"

    def __init__(self, api_key: str, model: str, base_url: str):
        if not api_key:
            raise MissingCredentialsError(
                "SGTE_LLM_API_KEY or OPENAI_API_KEY is required for provider=openai"
            )
        self.api_key = api_key
        self.model_name = model
        self.base_url = base_url.rstrip("/")
        self.last_usage = None
        self.last_cost_usd = 0.0

    def generate_structured_response(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
    ) -> Dict[str, Any]:
        body = {
            "model": self.model_name,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system or "Return JSON only."},
                {"role": "user", "content": prompt},
            ],
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body_text = _safe_read_http_body(exc)
            classified = classify_openai_http_error(exc.code, body_text, reason=str(exc.reason or ""))
            message = _format_http_error_message(exc.code, str(exc.reason or ""), classified)
            raise LLMHTTPError(
                message,
                kind=classified["kind"],
                http_status=exc.code,
                api_code=classified.get("api_code"),
                api_type=classified.get("api_type"),
                safe_message=redact_secrets(message),
            ) from exc
        except urllib.error.URLError as exc:
            raise LLMError(
                f"LLM HTTP error: {exc}",
                kind="timeout" if "timed out" in str(exc).lower() else "network_error",
                safe_message=redact_secrets(f"LLM HTTP error: {exc}"),
            ) from exc
        try:
            text = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(
                f"Unexpected LLM payload: {type(payload).__name__}",
                kind="malformed_response",
                safe_message="Unexpected LLM payload",
            ) from exc
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMError(
                "LLM did not return JSON",
                kind="malformed_response",
                safe_message="LLM did not return JSON",
            ) from exc
        if not isinstance(parsed, dict):
            raise LLMError(
                "LLM JSON root must be an object",
                kind="malformed_response",
                safe_message="LLM JSON root must be an object",
            )
        usage = payload.get("usage") if isinstance(payload, dict) else None
        import os

        raw = os.environ.get("SGTE_LLM_USD_PER_CALL", "").strip()
        self.last_cost_usd = float(raw) if raw else 0.0
        self.last_usage = usage
        return parsed
