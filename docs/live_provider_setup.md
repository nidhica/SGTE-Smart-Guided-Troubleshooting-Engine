# Live provider setup (SGTE)

This document explains how to configure an **authorized** live LLM provider using
the existing SGTE settings. It does **not** create API keys and does **not**
authorize production use.

Related evaluation phases:

- Phase 15 — offline MockLLM demo
- Phase 16 — mock baseline + live evaluation (blocked when unconfigured)
- Phase 17 — readiness check + bounded live re-entry

## How SGTE loads configuration

SGTE reads **process environment variables** via `Settings.from_env()` in
`sgte/settings.py`.

Important:

- A local `.env` file may exist for operator convenience and is **gitignored**.
- SGTE does **not** auto-load `.env`. Export variables into your shell (or your
  process manager) before running readiness checks or live evaluation.
- Never commit API keys. Never paste keys into evaluation reports.

Copy `.env.example` as a reminder of variable names only:

```powershell
Copy-Item .env.example .env
# Then edit .env locally and export into the process, or set $env: vars below.
```

## Supported providers

| `SGTE_LLM_PROVIDER` | Required credentials (any one) | Default model |
|---------------------|--------------------------------|---------------|
| `mock` | none (tests / offline demo) | mock |
| `none` | none (explicitly unconfigured) | — |
| `openai` | `SGTE_LLM_API_KEY` or `OPENAI_API_KEY` | `gpt-4o-mini` |
| `gemini` | `GEMINI_API_KEY` or `SGTE_LLM_API_KEY` | `gemini-2.0-flash` |
| `groq` | `GROQ_API_KEY` or `SGTE_LLM_API_KEY` | `llama-3.3-70b-versatile` |

Optional:

- `SGTE_LLM_MODEL` — override the default model id
- `SGTE_LLM_BASE_URL` — override the provider base URL
- `SGTE_LLM_MODE` — `test` or `production`

Provider HTTP calls use a **60 second** timeout and **no automatic retries**
(single request). Failures are classified (auth, timeout, rate limit, etc.).

## PowerShell examples

### Offline / mock (default demo path)

```powershell
$env:SGTE_LLM_PROVIDER = "mock"
python evaluation/phase15_demo_runner.py
```

### Readiness check only (no live scenario traffic)

```powershell
$env:SGTE_LLM_PROVIDER = "openai"   # or gemini / groq
$env:OPENAI_API_KEY = "<authorized-key>"
# Do not print the key. Do not commit it.
python evaluation/phase17_provider_readiness.py
```

Phase 17 readiness constructs the provider object locally and **does not** send
an HTTP request merely to verify that a key string is present.

A status of `LIVE_PROVIDER_CONFIGURED` means configuration and local
initialization succeeded. It does **not** prove the vendor endpoint is reachable
or that live evaluation will succeed.

### Bounded live re-entry

When readiness is `LIVE_PROVIDER_CONFIGURED`, the same Phase 17 command resumes
the Phase 16 live procedure for the five Phase 15 scenarios (max five requests).

Results are written under `evaluation/results/phase17_*.json`. Phase 16 reports
are **not** overwritten.

## Safety rules

1. Keep `production_authorization` false until the implementation gate is met.
2. Do not invent deeplink URIs or fabricate live responses.
3. Keep mock (`MOCK`) and live (`LIVE`) execution clearly separated.
4. If configuration is missing, expect `LIVE_PROVIDER_UNAVAILABLE` and
   `live_evaluation_status=BLOCKED`.

## Implementation gate

Live-provider readiness alone does **not** satisfy the production implementation
gate. External product decisions, SIIS evidence, and catalogue coverage remain
required.
