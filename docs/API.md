# REST API (Phase 5)

The HTTP layer is a thin FastAPI wrapper around the existing Phase 4 `TroubleshootingPipeline.troubleshoot()` entry point. It does not reimplement cache, SIIS retrieval, LLM structuring, deeplink mapping, or schema validation.

Official Theme 2 kit files are not modified. This API is not an official Samsung evaluation harness.

## Architecture

```
POST /v1/troubleshoot
  → TroubleshootRequest validation
  → pipeline.troubleshoot(query, siis_response=…)
  → official schema re-check
  → { query, query_variations, response.contexts, meta }
```

Optional `siis_response` is passed into the pipeline as the SIIS article. The engine does **not** retrieve a replacement article and does **not** invent troubleshooting knowledge. Cache lookup/write is skipped when client SIIS is supplied so request-specific text cannot poison the query cache.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness + non-sensitive load flags |
| POST | `/v1/troubleshoot` | Run the engine |

### GET /health

```json
{ "status": "ok", "cache": "ready", "catalogue": "loaded", "siis": "loaded" }
```

Never includes API keys or filesystem paths.

### POST /v1/troubleshoot

Request:

```json
{
  "query": "my phone screen is black",
  "siis_response": "optional raw SIIS response text"
}
```

- `query` required, non-empty after stripping whitespace (original string is preserved in the response)
- `siis_response` optional
- malformed JSON / missing field → HTTP 422

Response:

```json
{
  "query": "my phone screen is black",
  "query_variations": ["…"],
  "response": { "contexts": [] },
  "meta": {
    "latency_ms": 12.3,
    "cache_hit": false,
    "model": "mock-structured",
    "cost_usd": 0.0
  }
}
```

`response` is a `ContextDeeplinkResponse` from official `schema.py`. `meta.latency_ms` is measured wall time for the API handler (not a constant). Cache hits keep `cache_hit=true`, `cost_usd=0.0`, `model` prefixed with `cache:`.

Empty plans include Theme 2 fallback metadata under **`meta.fallback`** only (not inside `schema.py`):

| Value | When |
| --- | --- |
| `"no_match"` | Query has no viable SIIS-backed solution (`contexts: []`) |
| `"no_siis_context"` | Request includes `siis_response` but the text is blank/unusable |

Successful responses omit `meta.fallback`.

## Errors

| Status | When |
| --- | --- |
| 422 | Missing/empty query or invalid JSON |
| 500 | Unexpected failure or failed schema validation |

500 bodies are `{ "error": { "code": "internal_error", "message": "Request failed" } }`. No stack traces, keys, or paths.

CORS: localhost / 127.0.0.1 with any port. No authentication.

## Start the server

```bash
pip install -r requirements.txt
uvicorn sgte.api:app --reload --host 127.0.0.1 --port 8000
```

If `SGTE_LLM_PROVIDER` is unset or `mock`, the existing grounded mock LLM is used (same as Phase 3 tests). Set `SGTE_LLM_PROVIDER=openai` and `SGTE_LLM_API_KEY` for a live model. The API still never fabricates catalogue URIs.

### curl

```bash
curl -s http://127.0.0.1:8000/health

curl -s http://127.0.0.1:8000/v1/troubleshoot ^
  -H "Content-Type: application/json" ^
  -d "{\"query\": \"my phone screen is black\"}"
```

## Tests

```bash
python -m pytest -q
python -m pytest -q tests/test_phase5_api.py
```
