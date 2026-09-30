"""Test-only LLM stub. Production must not use this unless SGTE_LLM_PROVIDER=mock."""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, Optional

from sgte.llm.base import LLMProvider


class MockLLMProvider(LLMProvider):
    provider_name = "mock"
    model_name = "mock-structured"

    def __init__(self, canned: Optional[Dict[str, Any]] = None, factory: Optional[Callable[[str], Dict[str, Any]]] = None):
        self.canned = canned
        self.factory = factory

    def generate_structured_response(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
    ) -> Dict[str, Any]:
        if self.factory is not None:
            return self.factory(prompt)
        if self.canned is not None:
            return json.loads(json.dumps(self.canned))
        raise RuntimeError("MockLLMProvider has no canned response or factory")
