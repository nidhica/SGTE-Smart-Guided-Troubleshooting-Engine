"""Google Gemini generateContent JSON. Requires GEMINI_API_KEY from the environment.

Uses the public Generative Language REST API via urllib (no extra dependency).
Does not invent catalogue URIs. Does not silently fall back to mock.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict, Optional
from urllib.parse import quote

from sgte.llm.base import LLMError, LLMHTTPError, LLMProvider, MissingCredentialsError
from sgte.llm.openai_provider import redact_secrets

_DEFAULT_BASE = "https://generativelanguage.googleapis.com/v1beta"
_SECRET_RE_EXTRA = re.compile(r"(?i)(AIza[0-9A-Za-z\-_]{10,}|x-goog-api-key\s*[:=]\s*\S+)")


def _redact(text: str) -> str:
    """Redact OpenAI-style secrets and Gemini API key patterns."""
    return _SECRET_RE_EXTRA.sub("[REDACTED]", redact_secrets(text or ""))


def _safe_read_http_body(exc: urllib.error.HTTPError, *, limit: int = 4096) -> str:
    try:
        raw = exc.read(limit) or b""
    except Exception:  # noqa: BLE001
        return ""
    try:
        return raw.decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return ""


def parse_gemini_error_body(body_text: str) -> Dict[str, Optional[str]]:
    out: Dict[str, Optional[str]] = {
        "api_message": None,
        "api_code": None,
        "api_type": None,
        "api_status": None,
    }
    text = _redact((body_text or "").strip())
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
    status = err.get("status")
    out["api_message"] = _redact(str(msg))[:300] if msg is not None else None
    out["api_code"] = str(code) if code is not None else None
    out["api_status"] = str(status) if status is not None else None
    out["api_type"] = out["api_status"]
    return out


def classify_gemini_http_error(
    status: Optional[int],
    body_text: str = "",
    *,
    reason: str = "",
) -> Dict[str, Any]:
    parsed = parse_gemini_error_body(body_text)
    api_status = (parsed.get("api_status") or "").upper()
    api_message = (parsed.get("api_message") or "").lower()
    reason_l = (reason or "").lower()
    combined = f"{api_status} {api_message} {reason_l}"

    kind = "http_error"
    confidence = "low"
    note = ""

    if status in {401, 403} or api_status in {"UNAUTHENTICATED", "PERMISSION_DENIED"}:
        kind = "authentication"
        confidence = "high"
        note = "HTTP/status indicates authentication or permission failure."
    elif (status is not None and 500 <= status <= 599) or api_status in {"INTERNAL", "UNAVAILABLE"}:
        kind = "server_error"
        confidence = "high"
        note = "HTTP 5xx or Gemini INTERNAL/UNAVAILABLE."
    elif status == 429 or api_status == "RESOURCE_EXHAUSTED":
        if "quota" in combined or "billing" in combined:
            kind = "insufficient_quota"
            confidence = "medium"
            note = "HTTP 429/RESOURCE_EXHAUSTED with quota/billing language."
        elif api_status == "RESOURCE_EXHAUSTED":
            kind = "rate_limit_or_quota_unspecified"
            confidence = "low"
            note = "RESOURCE_EXHAUSTED without clear quota vs rate-limit distinction."
        else:
            kind = "rate_limit_or_quota_unspecified"
            confidence = "low"
            note = "HTTP 429 without enough body detail to distinguish quota vs rate limit."
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
        "api_status": parsed.get("api_status"),
        "confidence": confidence,
        "note": note,
    }


def _format_http_error_message(status: Optional[int], reason: str, classified: Dict[str, Any]) -> str:
    parts = [f"LLM HTTP error: HTTP Error {status}: {reason or 'Error'}"]
    parts.append(f"kind={classified['kind']}")
    if classified.get("api_code"):
        parts.append(f"api_code={classified['api_code']}")
    if classified.get("api_status") or classified.get("api_type"):
        parts.append(f"api_status={classified.get('api_status') or classified.get('api_type')}")
    if classified.get("api_message"):
        parts.append(f"api_message={classified['api_message']}")
    err_obj: Dict[str, Any] = {}
    if classified.get("api_code"):
        err_obj["code"] = classified["api_code"]
    if classified.get("api_status"):
        err_obj["status"] = classified["api_status"]
    if classified.get("api_message"):
        err_obj["message"] = classified["api_message"]
    if err_obj:
        parts.append("body=" + json.dumps({"error": err_obj}, ensure_ascii=True))
    return " | ".join(parts)


def extract_gemini_text(payload: Dict[str, Any]) -> str:
    """Pull the first candidate text part from a generateContent response."""
    try:
        candidates = payload["candidates"]
        content = candidates[0]["content"]
        parts = content["parts"]
        texts = [p.get("text") for p in parts if isinstance(p, dict) and p.get("text")]
        if not texts:
            raise KeyError("parts.text")
        return "".join(str(t) for t in texts)
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(
            "Unexpected LLM payload",
            kind="malformed_response",
            safe_message="Unexpected LLM payload",
        ) from exc


def parse_structured_json(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if not text:
        raise LLMError(
            "LLM did not return JSON",
            kind="malformed_response",
            safe_message="LLM did not return JSON",
        )
    # Strip optional markdown fences without inventing content.
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
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
    return parsed


class GeminiProvider(LLMProvider):
    """Gemini generateContent provider. Selected via SGTE_LLM_PROVIDER=gemini."""

    provider_name = "gemini"

    def __init__(self, api_key: str, model: str, base_url: str = _DEFAULT_BASE):
        if not api_key:
            raise MissingCredentialsError(
                "GEMINI_API_KEY is required for provider=gemini"
            )
        self.api_key = api_key
        self.model_name = model or "gemini-2.0-flash"
        self.base_url = (base_url or _DEFAULT_BASE).rstrip("/")
        self.last_usage = None
        self.last_cost_usd = 0.0

    def _endpoint(self) -> str:
        # Key is sent via header only — never append to URL (avoids accidental logging).
        model = quote(self.model_name, safe="-_.")
        return f"{self.base_url}/models/{model}:generateContent"

    def generate_structured_response(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
            },
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        else:
            body["systemInstruction"] = {"parts": [{"text": "Return JSON only."}]}

        request = urllib.request.Request(
            self._endpoint(),
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body_text = _safe_read_http_body(exc)
            classified = classify_gemini_http_error(
                exc.code, body_text, reason=str(exc.reason or "")
            )
            message = _format_http_error_message(exc.code, str(exc.reason or ""), classified)
            raise LLMHTTPError(
                message,
                kind=classified["kind"],
                http_status=exc.code,
                api_code=classified.get("api_code"),
                api_type=classified.get("api_type"),
                safe_message=_redact(message),
            ) from exc
        except urllib.error.URLError as exc:
            raise LLMError(
                f"LLM HTTP error: {exc}",
                kind="timeout" if "timed out" in str(exc).lower() else "network_error",
                safe_message=_redact(f"LLM HTTP error: {exc}"),
            ) from exc

        if not isinstance(payload, dict):
            raise LLMError(
                "Unexpected LLM payload",
                kind="malformed_response",
                safe_message="Unexpected LLM payload",
            )

        text = extract_gemini_text(payload)
        parsed = parse_structured_json(text)

        usage = payload.get("usageMetadata") if isinstance(payload, dict) else None
        raw = os.environ.get("SGTE_LLM_USD_PER_CALL", "").strip()
        self.last_cost_usd = float(raw) if raw else 0.0
        self.last_usage = usage
        return parsed
