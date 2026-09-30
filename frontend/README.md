# SGTE Frontend

Premium demonstration UI for the Smart Guided Troubleshooting Engine (Samsung PRISM Theme 2).

This app talks only to the existing FastAPI backend. It does **not** reimplement retrieval, caching, or deeplink logic.

## Prerequisites

- Node.js 20+
- SGTE backend running (see repository root / `docs/API.md`)

## Setup

```bash
cd frontend
npm install
```

## Run (development)

Terminal 1 — backend:

```bash
uvicorn sgte.api:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2 — frontend:

```bash
cd frontend
npm run dev
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173).

Vite proxies `/health` and `/v1` to `http://127.0.0.1:8000`. CORS for localhost is already enabled on the API.

Optional: set `VITE_API_BASE=http://127.0.0.1:8000` to call the API directly without the proxy.

## Build

```bash
cd frontend
npm run build
npm run preview
```

## Example flow

1. Enter: `My screen keeps flickering`
2. Click **Diagnose issue**
3. Review the action plan, category badges, and Settings buttons when the API attaches a deeplink
4. Open **SGTE Insights** for cache / variations metadata returned by the API

## Notes

- No domain field is sent — the API does not accept one.
- Deeplink URIs are used exactly as returned and shown in the action card when present (label + URI).
- Fallback states map to `meta.fallback`: `no_match` / `no_siis_context`.
- Offline demo: open `http://127.0.0.1:5173/?demo=1` with `SGTE_LLM_PROVIDER=mock` (see `docs/demo_guide.md`).
