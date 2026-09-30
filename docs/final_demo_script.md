# SGTE Final Demo Script — Samsung PRISM GenAI Hackathon 2026

**Project:** Smart Guided Troubleshooting Engine (SGTE)  
**Mode:** MOCK (offline demo) — not live-provider validation  
**Production gate:** UNSATISFIED  
**Evidence base for this script:** `evaluation/phase47_final_demo/` (13-query live mock API run)

---

## A. Opening (60–90 seconds)

**Introduce SGTE**

SGTE is an evidence-grounded troubleshooting engine for Galaxy device complaints. A user describes a problem in natural language; SGTE retrieves Samsung SIIS troubleshooting evidence, builds an ordered action plan when evidence supports it, and attaches exact official-catalogue Settings deeplinks when available.

**Problem it addresses**

Generic assistants often invent steps, mix unrelated settings, or suggest unsupported plans. SGTE prefers abstention (`no_match`) when evidence is insufficient, rather than forcing a recommendation.

**Evidence-grounded approach**

- Retrieve SIIS guidance matched to the complaint.
- Recommend only actions supported by that evidence (and catalogue URIs only when they match exactly).
- Abstain on ambiguous, unsupported, or out-of-scope queries.

**Say clearly before demos:**

> “This demonstration runs in **MOCK** mode with a grounded mock LLM. Results show pipeline behavior and catalogue integrity. They do **not** prove live-provider accuracy. The production authorization gate remains **unsatisfied**.”

**UI cues to point at:** MOCK MODE banner (`?demo=1`), health `execution_mode: MOCK`, `production_authorized: false`.

---

## B. Live demonstration sequence

Startup (from `docs/demo_guide.md`):

```powershell
# Terminal 1 — backend
$env:SGTE_LLM_PROVIDER = "mock"
$env:SGTE_DEMO_OFFLINE = "1"
$env:SGTE_PREWARM_ON_STARTUP = "0"
uvicorn sgte.api:app --host 127.0.0.1 --port 8000

# Terminal 2 — frontend
cd frontend
npm run dev
```

Open: **http://127.0.0.1:5173/?demo=1**  
Confirm health: **http://127.0.0.1:8000/health** → `execution_mode: MOCK`, `production_authorized: false`.

Use these four verified queries from the Phase 47 run (actual API outputs).

### Demo 1 — Supported troubleshooting plan (touch responsiveness)

| Field | Value |
|-------|--------|
| **User query** | `My phone screen is not responding properly to touch.` |
| **Expected interaction** | Submit → analyze → ordered plan |
| **Actual verified behavior** | Status: **plan**. Actions: Restarting Your Device → Safe Mode → Factors Affecting Touchscreen Performance → Touch Sensitivity Setting. **No** Full Screen Gesture Function. |
| **Point out** | Ordered critical/manual steps; no unrelated gesture-navigation plan; actions are manual-only (no catalogue URI on this plan). |

### Demo 2 — Verified catalogue deeplink (fast charging OFF)

| Field | Value |
|-------|--------|
| **User query** | `How do I turn off fast charging?` |
| **Expected interaction** | Submit → single settings action with deeplink |
| **Actual verified behavior** | Status: **plan**. Action: **Disable Fast charging**. Catalogue ID **DL-0403**. URI `bixby://masked/act/a70d908ca1` (exact catalogue match). |
| **Point out** | Exact catalogue URI + label; evidence-aligned settings action (not inventing battery tips). |

*Optional alternate deeplink beat (same session):*  
`How do I increase touch sensitivity?` → **Enable Touch sensitivity**, **DL-0126**, `bixby://masked/act/14eb42b895`.

### Demo 3 — Ambiguous complaint that abstains (floating circle)

| Field | Value |
|-------|--------|
| **User query** | `A floating circle is appearing on my screen. How do I remove it?` |
| **Expected interaction** | Submit → clear abstention |
| **Actual verified behavior** | Status: **`no_match`**. No Edge panel / Assistive touch / floating-feature plan forced. |
| **Point out** | Ambiguity → abstain rather than guess which floating UI feature. |

### Demo 4 — Unsupported / out-of-scope (`no_match`)

| Field | Value |
|-------|--------|
| **User query** | `How do I make sourdough bread?` |
| **Expected interaction** | Submit → unsupported state |
| **Actual verified behavior** | Status: **`no_match`**. Empty action list. |
| **Point out** | Out-of-scope query does not fabricate device steps. |

### Optional short beats (if time allows)

| Query | Actual result (Phase 47) | Talking point |
|-------|--------------------------|---------------|
| Multi-window: `I want to use two apps at the same time on my phone.` | **plan** with Multi window actions; verified **DL-0270** on swipe-gestures action | Supported multi-window path + one catalogue URI |
| Gmail blank: `Gmail is showing a blank screen when I open it.` | **`no_match`** | Does **not** invent Wi-Fi / email-server troubleshooting |
| Smart Switch QR: `The QR code is not appearing in Smart Switch.` | **`no_match`** | Does **not** invent a missing-QR plan |
| Slow charging: `My phone is charging slowly. What should I do?` | **`no_match`** | Does **not** push unrelated battery-drain / fast-charging plans |

---

## C. Capabilities demonstrated (checklist)

- [x] Supported troubleshooting plan (Q7 touch)
- [x] Verified catalogue deeplink (Q10 / optional Q8)
- [x] Ambiguous abstention (Q6 floating circle)
- [x] Unsupported `no_match` (Q13 sourdough)

---

## D. Closing (45–60 seconds)

**Capabilities shown**

- Grounded SIIS-backed plans when evidence supports the complaint.
- Exact official-catalogue deeplinks when mappings exist.
- Deliberate abstention for ambiguous, unsupported, and out-of-scope cases.

**Current limitations (state honestly)**

- MOCK mode ≠ live LLM accuracy; no claim of production readiness.
- Many valid actions are manual-only (no catalogue URI by design).
- Some device settings (e.g. double tap to wake, navigation bar, factory reset in this run) correctly return `no_match` when evidence/catalogue support is insufficient.
- Production authorization / implementation gate: **UNSATISFIED**.

**Closing line**

> “SGTE’s demo priority is trustworthy guidance: recommend when evidence supports it, attach only verified catalogue deeplinks, and abstain when it does not. Mock results illustrate that policy — they are not a substitute for live-provider evaluation.”
