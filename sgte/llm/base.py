"""LLM provider interface. The model may only structure SIIS evidence."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class LLMError(RuntimeError):
    """Base LLM failure. Subclasses may carry structured classification."""

    kind: str = "llm_error"
    http_status: Optional[int] = None
    api_code: Optional[str] = None
    api_type: Optional[str] = None
    safe_message: str = ""

    def __init__(
        self,
        message: str,
        *,
        kind: Optional[str] = None,
        http_status: Optional[int] = None,
        api_code: Optional[str] = None,
        api_type: Optional[str] = None,
        safe_message: Optional[str] = None,
    ):
        super().__init__(message)
        if kind is not None:
            self.kind = kind
        self.http_status = http_status
        self.api_code = api_code
        self.api_type = api_type
        self.safe_message = safe_message if safe_message is not None else message


class LLMProvider(ABC):
    provider_name: str = "base"
    model_name: str = ""
    last_cost_usd: float = 0.0

    @abstractmethod
    def generate_structured_response(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return a JSON object. Must not invent catalogue URIs."""


class MissingCredentialsError(LLMError):
    kind = "authentication"


class LLMHTTPError(LLMError):
    """HTTP-layer provider failure with optional OpenAI error body fields."""

    kind = "http_error"
