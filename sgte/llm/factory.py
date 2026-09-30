"""Construct an LLM provider from environment settings."""

from __future__ import annotations

from sgte.llm.base import LLMProvider, MissingCredentialsError
from sgte.llm.gemini_provider import GeminiProvider
from sgte.llm.groq_provider import GroqProvider
from sgte.llm.mock import MockLLMProvider
from sgte.llm.openai_provider import OpenAICompatibleProvider
from sgte.settings import Settings


def build_llm_provider(settings: Settings, *, mock: MockLLMProvider | None = None) -> LLMProvider:
    name = settings.llm_provider
    if name in {"", "none"}:
        if settings.llm_mode == "production":
            raise MissingCredentialsError(
                "SGTE_LLM_PROVIDER is unset. Set it to openai (with SGTE_LLM_API_KEY), "
                "gemini (with GEMINI_API_KEY), groq (with GROQ_API_KEY), or mock for tests. "
                "Production will not silently fabricate LLM output."
            )
        if mock is None:
            raise MissingCredentialsError("No LLM provider configured")
        return mock
    if name == "mock":
        if mock is None:
            raise MissingCredentialsError("SGTE_LLM_PROVIDER=mock requires an injected MockLLMProvider")
        return mock
    if name == "openai":
        return OpenAICompatibleProvider(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            base_url=settings.llm_base_url,
        )
    if name == "gemini":
        return GeminiProvider(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            base_url=settings.llm_base_url,
        )
    if name == "groq":
        return GroqProvider(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            base_url=settings.llm_base_url,
        )
    raise MissingCredentialsError(f"Unknown SGTE_LLM_PROVIDER={name!r}")
