"""Call counters wrapping SIIS / LLM / mapper. Used to prove cache hits skip the cold path."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional


class CountingLLM:
    def __init__(self, inner: Any):
        self.inner = inner
        self.calls = 0
        self.provider_name = inner.provider_name
        self.model_name = inner.model_name
        self.last_cost_usd = 0.0

    def generate_structured_response(self, prompt: str, *, system: Optional[str] = None) -> Dict[str, Any]:
        self.calls += 1
        out = self.inner.generate_structured_response(prompt, system=system)
        self.last_cost_usd = float(getattr(self.inner, "last_cost_usd", 0.0) or 0.0)
        return out


class CountingSiis:
    def __init__(self, inner: Any):
        self.inner = inner
        self.calls = 0

    def search(self, *args: Any, **kwargs: Any):
        self.calls += 1
        return self.inner.search(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)


class CountingMapper:
    def __init__(self, inner: Any):
        self.inner = inner
        self.calls = 0

    def find_best_deeplink(self, *args: Any, **kwargs: Any):
        self.calls += 1
        return self.inner.find_best_deeplink(*args, **kwargs)

    def debug_rank(self, *args: Any, **kwargs: Any):
        self.calls += 1
        return self.inner.debug_rank(*args, **kwargs)

    def candidates(self, *args: Any, **kwargs: Any):
        self.calls += 1
        return self.inner.candidates(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)
