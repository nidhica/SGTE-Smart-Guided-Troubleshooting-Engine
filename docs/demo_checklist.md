# SGTE Demo Checklist (Judge Package)

Use this before and during the judge demo. Startup commands match `docs/demo_guide.md` and `frontend/README.md`.

**Mode reminder:** MOCK only. Confirm the **MOCK MODE** banner before presenting.  
**Production gate:** UNSATISFIED — do not claim production readiness.

---

## Pre-flight

- [ ] Python 3.12+ available; `pip install -r requirements.txt` already done
- [ ] Node.js 18+ (frontend README recommends 20+)
- [ ] Working directory is the repo root: `Smart_Guided_TroubleShoot`
- [ ] No live API keys required for this demo
- [ ] Judge docs open: `docs/judge_demo_script.md`, `docs/demo_results_summary.md`

---

## 1. Start backend (PowerShell)

```powershell
cd "c:\Users\NIDHI C A\OneDrive\Desktop\Smart_Guided_TroubleShoot"
$env:SGTE_LLM_PROVIDER = "mock"
$env:SGTE_DEMO_OFFLINE = "1"
$env:SGTE_PREWARM_ON_STARTUP = "0"
uvicorn sgte.api:app --host 127.0.0.1 --port 8000
```

Leave this terminal running. Expected: uvicorn listening on `127.0.0.1:8000`.

---

## 2. Start frontend (PowerShell)

```powershell
cd "c:\Users\NIDHI C A\OneDrive\Desktop\Smart_Guided_TroubleShoot\frontend"
npm install
npm run dev
```

- Dev URL: **http://127.0.0.1:5173**
- **Demo entry (required):** **http://127.0.0.1:5173/?demo=1**
- Vite proxies `/health` and `/v1` to `http://127.0.0.1:8000`
- Optional direct API base: `VITE_API_BASE=http://127.0.0.1:8000`

---

## 3. Verify the API is reachable

**Browser or PowerShell:**

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Confirm at least:

| Field | Expected |
|-------|----------|
| `status` | `ok` |
| `execution_mode` | `MOCK` |
| `llm_provider` | `mock` |
| `catalogue` | `loaded` |
| `siis` | `loaded` |
| `production_authorized` | `false` |
| `implementation_gate_satisfied` | `false` |

Also open the UI with `?demo=1` and confirm the **MOCK MODE** banner is visible.

---

## 4. Clear the cache before the demo

Cold-cache demo (matches Phase 47 procedure):

```powershell
Invoke-RestMethod -Method POST http://127.0.0.1:8000/v1/cache/clear
```

Expect `status: ok` and `cache_size: 0` (or reduced size after clear).

Re-check health if desired: `cache_logic_version` should remain `sgte.relevance.v3`.

---

## 5. Supported demo sequence (≈3 minutes)

Paste exact strings. Outcomes are Phase 47–verified.

| Step | Query | Expect |
|------|-------|--------|
| 1 | `My phone screen is not responding properly to touch.` | **plan** — ordered touch steps; no Full Screen Gesture Function |
| 2 | `How do I turn off fast charging?` | **plan** — Disable Fast charging + URI (DL-0403) |
| 3 | `A floating circle is appearing on my screen. How do I remove it?` | **`no_match`** |
| 4 | `How do I make sourdough bread?` | **`no_match`** |

**Optional extras**

| Query | Expect |
|-------|--------|
| `I want to use two apps at the same time on my phone.` | **plan** + DL-0270 |
| `How do I increase touch sensitivity?` | **plan** + DL-0126 |
| `Gmail is showing a blank screen when I open it.` | **`no_match`** |

Full 13-query table: `docs/judge_demo_script.md` §5 / `docs/demo_results_summary.md` §1.

---

## 6. Fallback plan if something fails

### Backend will not start

1. Confirm port 8000 is free; stop any other uvicorn process.
2. Re-set env vars in the **same** PowerShell session (`SGTE_LLM_PROVIDER=mock`, `SGTE_DEMO_OFFLINE=1`).
3. From repo root: `python -c "from sgte.api import app; print('ok')"`.
4. If UI is up but API is down, do **not** improvise live-provider mode — stay MOCK or fall back to recorded Phase 47 JSON.

### Frontend will not start

1. `cd frontend` → `npm install` → `npm run dev`.
2. Confirm Node version; try opening `http://127.0.0.1:5173/?demo=1` again.
3. **API-only fallback:** demonstrate with PowerShell against the mock API:

```powershell
Invoke-RestMethod -Method POST http://127.0.0.1:8000/v1/troubleshoot `
  -ContentType "application/json" `
  -Body '{"query":"How do I turn off fast charging?"}'
```

4. Or walk judges through `evaluation/phase47_final_demo/final_demo_results.json` and `docs/demo_results_summary.md` (pre-recorded verified outputs).

### Wrong / unexpected answers mid-demo

1. Confirm health still shows `execution_mode: MOCK`.
2. Clear cache again (`POST /v1/cache/clear`).
3. Re-run the exact Phase 47 query string (no paraphrasing).
4. If still wrong, stop changing config — show Phase 47 artifacts as the verified record. Do **not** modify backend logic during the demo.

### Stop services

- Frontend terminal: Ctrl+C  
- Backend terminal: Ctrl+C  

---

## 7. Final reminders (say / show)

- [ ] **MOCK MODE** banner visible (`?demo=1`)
- [ ] Health shows `production_authorized: false`
- [ ] Do not claim live-provider accuracy
- [ ] Do not invent deeplink URIs if none appear
- [ ] `no_match` is a feature (abstention), not a failure of the demo
- [ ] Phase 43–47 evaluation folders remain unmodified evidence
