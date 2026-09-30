# SGTE Demo Guide (Phase 42)

Samsung PRISM GenAI Hackathon 2026 — Theme: Smart Guided Troubleshooting Engine.

**Offline release candidate:** `SGTE-OFFLINE-RC-20260927-a51bd646a78f`  
**Final offline handoff:** `SGTE-OFFLINE-HANDOFF-20260927-e8db7385746b`  
**Production gate:** UNSATISFIED — this is a demo, not production readiness.

## 1. Project overview

SGTE accepts a natural-language device complaint, retrieves Samsung SIIS
troubleshooting evidence, and returns a grounded action plan. When the official
deeplink catalogue supports it, exact Settings URIs are attached. Out-of-scope
queries abstain with `no_match`.

## 2. Prerequisites

- Python 3.12+ with `pip install -r requirements.txt`
- Node.js 18+ (frontend README suggests 20+)
- No live LLM API keys required for MOCK mode

## 3. Start backend and frontend

From the repository root (`Smart_Guided_TroubleShoot`):

**Terminal 1 — backend (MOCK):**

```powershell
cd "c:\Users\NIDHI C A\OneDrive\Desktop\Smart_Guided_TroubleShoot"
$env:SGTE_LLM_PROVIDER = "mock"
$env:SGTE_DEMO_OFFLINE = "1"
$env:SGTE_PREWARM_ON_STARTUP = "0"
uvicorn sgte.api:app --host 127.0.0.1 --port 8000
```

**Terminal 2 — frontend:**

```powershell
cd "c:\Users\NIDHI C A\OneDrive\Desktop\Smart_Guided_TroubleShoot\frontend"
npm install
npm run dev
```

Open: **http://127.0.0.1:5173/?demo=1**

Health check: **http://127.0.0.1:8000/health**

## 4. Enable mock mode

Required for the offline showcase:

```powershell
$env:SGTE_LLM_PROVIDER = "mock"
$env:SGTE_DEMO_OFFLINE = "1"
```

The UI shows a **MOCK MODE** banner when health reports `execution_mode=MOCK`
or when `?demo=1` is used. Do **not** put API keys in the repository.

## 5–6. Demo scenarios and expected behavior

Use the **Demo scenarios** chips on the landing page (`?demo=1`), or paste the
full complaint text.

| Chip | Maps to | Complaint theme | Expected (documentary) |
|------|---------|-----------------|------------------------|
| A · Supported | DEMO-A | Black/blank screen (official Q2) | Grounded multi-step plan; deeplinks may be absent |
| B · Catalogue link | DEMO-B | Touch lag (official Q19) | Plan with at least one **exact catalogue URI** when mock attaches it |
| C · Multi-symptom | DEMO-C | Flash/blank + Gmail (official Q1) | Multi-step / multi-symptom structure |
| D · Abstain | DEMO-D | Baking (out of scope) | **`no_match` abstention** |
| E · Unresolved | DEMO-E | Blank during Smart Switch QR (official Q5) | Corpus-limited / unresolved-evidence showcase — do not invent success |

**Connectivity-related complaint:** There is **no dedicated Phase 15
connectivity demo chip**. Do not invent one. Closest verified pack is
display/touch official queries (A–C, E). Settings example “Change time format”
is available in non-demo example chips only.

UI should show:

1. Complaint input  
2. Submitted query echoed on results / fallback  
3. Ordered actions and steps  
4. Deeplink **label + exact URI** when present; explicit “no verified catalogue deeplink” when absent  
5. Clear `no_match` / unsupported state  
6. Loading (“analyzing”) and error states  

## 7. Known limitations

- MockLLM ≠ live-provider accuracy  
- Implementation / production gate **UNSATISFIED**  
- Many supported actions have no catalogue deeplink by design  
- Adaptive Display and other product/catalogue/SIIS blockers remain open  
- No dedicated connectivity demo scenario in the verified Phase 15 pack  
- Deeplink “Open Settings” is non-destructive deep-link navigation only  

## 8. Stop the application

- Frontend: Ctrl+C in the `npm run dev` terminal  
- Backend: Ctrl+C in the `uvicorn` terminal  

Optional CLI scenario pack (offline mock):

```powershell
python evaluation/phase15_demo_runner.py
```
