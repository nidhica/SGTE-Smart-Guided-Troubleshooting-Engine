# SGTE Offline Demo (Phase 15)

Reproducible offline demonstration of the Smart Guided Troubleshooting Engine
using the existing MockLLM path. This demo does **not** claim production readiness
and does **not** bypass the implementation gate.

For the concise Phase 42 hackathon demo guide (start/stop, scenarios, limitations),
see **[demo_guide.md](demo_guide.md)**.

## Requirements

- Python 3.12+ with `pip install -r requirements.txt`
- Node.js 18+ for the React frontend (`frontend/`)
- No live LLM API keys required for MOCK mode

## Startup (offline / MOCK)

PowerShell:

```powershell
cd "c:\Users\NIDHI C A\OneDrive\Desktop\Smart_Guided_TroubleShoot"
$env:SGTE_LLM_PROVIDER = "mock"
$env:SGTE_DEMO_OFFLINE = "1"
$env:SGTE_PREWARM_ON_STARTUP = "0"
uvicorn sgte.api:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open: http://127.0.0.1:5173/?demo=1

The UI shows a **MOCK** banner. Health reports `execution_mode=MOCK` and
`production_authorized=false` / `implementation_gate_satisfied=false`.

## Scenario pack (CLI)

```powershell
python evaluation/phase15_demo_runner.py
```

Writes:

- `evaluation/results/phase15_demo_scenarios.json`
- `evaluation/results/phase15_demo_execution_report.json`
- `evaluation/results/phase15_demo_validation_report.json`
- `evaluation/results/phase15_demo_readiness_report.json`
- `evaluation/results/phase15_final_report.json`

## Demo scenarios

| ID | Intent |
|----|--------|
| DEMO-A-SUPPORTED | Official Q2 — supported black-screen plan |
| DEMO-B-CATALOGUE-DEEPLINK | Official Q19 — exact catalogue URI when present |
| DEMO-C-MULTI-SYMPTOM | Official Q1 — multi-symptom / partial support |
| DEMO-D-ABSTENTION | Out-of-scope baking query — `no_match` abstention |
| DEMO-E-UNRESOLVED-EVIDENCE | Official Q5 — unresolved / corpus-limited evidence |

## Tests

```powershell
python -m pytest tests/test_phase15_offline_demo.py -q
```

## Expected behavior

- Complaint → intent / retrieval → evidence-grounded actions
- Exact catalogue deeplinks labeled **verified**; missing links labeled **not auto-executable**
- Abstention for out-of-scope queries
- Schema validation enforced
- MOCK vs LIVE clearly labeled

## Known limitations

- MockLLM is not a live-provider accuracy demonstration
- Implementation gate remains **UNSATISFIED**
- Many supported actions have no catalogue deeplink by design
- Unresolved product decisions / SIIS / catalogue gaps remain open (Phase 13–14)
- Deeplink “Open Settings” is non-destructive deep-link navigation only

## Catalogues & fingerprints

Recorded in Phase 15 readiness / execution reports when available
(`.sgte_index/deeplink_index_meta.json` fingerprint, `deeplinks.json` sha256).

## Live provider (optional, not the offline demo)

See **[live_provider_setup.md](live_provider_setup.md)** for authorized provider configuration,
readiness checks (Phase 17), and bounded live re-entry. Summary:

```powershell
$env:SGTE_LLM_PROVIDER = "openai"   # or groq / gemini
$env:OPENAI_API_KEY = "..."
# Do not set SGTE_DEMO_OFFLINE=1
uvicorn sgte.api:app --host 127.0.0.1 --port 8000
```

Live mode requires credentials in the **process environment** and is **out of scope** for the offline showcase.
