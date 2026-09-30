"""Groq chat completions via the OpenAI-compatible API.

Docs: https://console.groq.com/docs/openai
Base URL: https://api.groq.com/openai/v1
Requires GROQ_API_KEY. No automatic retries. Does not silently fall back to mock.

Uses the same JSON chat.completions contract as OpenAICompatibleProvider, but sets an
explicit User-Agent so the request is not identified solely as Python-urllib (which has
been observed to receive Cloudflare-style HTTP 403 / error code 1010 against Groq).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from sgte.llm.base import LLMError, LLMHTTPError, MissingCredentialsError
from sgte.llm.openai_provider import (
    OpenAICompatibleProvider,
    _format_http_error_message,
    _safe_read_http_body,
    classify_openai_http_error,
    redact_secrets,
)

_DEFAULT_BASE = "https://api.groq.com/openai/v1"
_DEFAULT_MODEL = "llama-3.3-70b-versatile"
_USER_AGENT = "SGTE-GroqProvider/1.0"


class GroqProvider(OpenAICompatibleProvider):
    """Groq provider selected via SGTE_LLM_PROVIDER=groq.

    Same contract as OpenAICompatibleProvider (temperature=0, response_format=json_object,
    timeout=60, single request) plus an explicit User-Agent header.
    """

    provider_name = "groq"

    def __init__(
        self,
        api_key: str,
        model: str = _DEFAULT_MODEL,
        base_url: str = _DEFAULT_BASE,
    ):
        if not api_key:
            raise MissingCredentialsError(
                "GROQ_API_KEY is required for provider=groq"
            )
        super().__init__(
            api_key=api_key,
            model=model or _DEFAULT_MODEL,
            base_url=(base_url or _DEFAULT_BASE).rstrip("/"),
        )
        self.provider_name = "groq"

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
                "User-Agent": _USER_AGENT,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body_text = _safe_read_http_body(exc)
            classified = classify_openai_http_error(
                exc.code, body_text, reason=str(exc.reason or "")
            )
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
        raw = os.environ.get("SGTE_LLM_USD_PER_CALL", "").strip()
        self.last_cost_usd = float(raw) if raw else 0.0
        self.last_usage = usage
        return parsed
