"""Environment-driven configuration. No API keys are hard-coded."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from sgte.paths import REPO_ROOT


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@dataclass(frozen=True)
class Settings:
    """
    SGTE_LLM_PROVIDER     mock | openai | gemini | groq | none
    SGTE_LLM_MODEL        provider model id (e.g. gpt-4o-mini, gemini-2.0-flash, llama-3.3-70b-versatile)
    SGTE_LLM_API_KEY      or OPENAI_API_KEY (openai); for gemini prefer GEMINI_API_KEY; for groq prefer GROQ_API_KEY
    GEMINI_API_KEY        required when SGTE_LLM_PROVIDER=gemini
    GROQ_API_KEY          required when SGTE_LLM_PROVIDER=groq
    SGTE_LLM_BASE_URL     optional provider base URL
    SGTE_LLM_MODE         test | production
    SGTE_EMBEDDING_PROVIDER  hashing | minilm | tfidf (local; tfidf still used as fallback)
    SGTE_INDEX_DIR        local embedding index directory
    SGTE_DEBUG            1 to print debug traces to stderr
    SGTE_CACHE            1/0 enable semantic fast-path cache (default 1)
    SGTE_CACHE_THRESHOLD  cosine/jaccard combined hit threshold (default 0.58)
    SGTE_PREWARM_ON_STARTUP  1/0 run prewarm_cache() once at API startup (default 1)
    SGTE_LLM_USD_PER_CALL optional configured cost; never invented
    """

    llm_provider: str
    llm_model: str
    llm_api_key: str
    llm_base_url: str
    llm_mode: str
    embedding_provider: str
    index_dir: Path
    debug: bool
    cache_enabled: bool
    cache_threshold: float
    prewarm_on_startup: bool

    @classmethod
    def from_env(cls) -> "Settings":
        provider = (_env("SGTE_LLM_PROVIDER") or "none").lower()
        mode = (_env("SGTE_LLM_MODE") or ("test" if provider == "mock" else "production")).lower()
        index = _env("SGTE_INDEX_DIR") or str(REPO_ROOT / ".sgte_index")
        cache_raw = _env("SGTE_CACHE", "1").lower()
        thr = _env("SGTE_CACHE_THRESHOLD") or "0.58"
        prewarm_raw = _env("SGTE_PREWARM_ON_STARTUP", "1").lower()

        if provider == "gemini":
            default_model = "gemini-2.0-flash"
            default_base = "https://generativelanguage.googleapis.com/v1beta"
            api_key = _env("GEMINI_API_KEY") or _env("SGTE_LLM_API_KEY")
        elif provider == "groq":
            default_model = "llama-3.3-70b-versatile"
            default_base = "https://api.groq.com/openai/v1"
            api_key = _env("GROQ_API_KEY") or _env("SGTE_LLM_API_KEY")
        else:
            default_model = "gpt-4o-mini"
            default_base = "https://api.openai.com/v1"
            api_key = _env("SGTE_LLM_API_KEY") or _env("OPENAI_API_KEY")

        return cls(
            llm_provider=provider,
            llm_model=_env("SGTE_LLM_MODEL", default_model),
            llm_api_key=api_key,
            llm_base_url=_env("SGTE_LLM_BASE_URL", default_base),
            llm_mode=mode,
            embedding_provider=(_env("SGTE_EMBEDDING_PROVIDER") or "hashing").lower(),
            index_dir=Path(index),
            debug=_env("SGTE_DEBUG") in {"1", "true", "yes"},
            cache_enabled=cache_raw not in {"0", "false", "no", "off"},
            cache_threshold=float(thr),
            prewarm_on_startup=prewarm_raw not in {"0", "false", "no", "off"},
        )
