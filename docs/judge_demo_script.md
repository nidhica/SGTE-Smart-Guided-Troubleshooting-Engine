# SGTE Judge Demo Script

**Project:** Smart Guided Troubleshooting Engine (SGTE)  
**Hackathon:** Samsung PRISM GenAI Hackathon 2026  
**Demo mode:** MOCK (grounded mock LLM) — **not** live-provider validation  
**Production gate:** UNSATISFIED  
**Evidence:** Phase 47 live mock API run (`evaluation/phase47_final_demo/`)  
**Companion docs:** `docs/demo_results_summary.md`, `docs/demo_checklist.md`, `docs/final_demo_script.md`

---

## 1. Thirty-second introduction

SGTE turns a natural-language Galaxy device complaint into an **evidence-grounded** action plan. It retrieves Samsung SIIS troubleshooting guidance, returns ordered steps when evidence supports the complaint, and attaches **exact** official-catalogue Settings deeplinks when they match. When evidence is insufficient, ambiguous, or out of scope, it abstains with **`no_match`** instead of inventing advice.

> Say once, clearly: “This demo runs in **MOCK** mode. It shows pipeline behavior and catalogue integrity. It does **not** prove live LLM accuracy. The production authorization gate remains **unsatisfied**.”

---

## 2. Problem SGTE solves

Generic assistants often:

- Invent steps that are not supported by official troubleshooting evidence
- Mix unrelated settings (for example Wi-Fi tips for an app blank screen)
- Force a recommendation when the complaint is ambiguous

SGTE’s design priority is **trustworthy guidance**: recommend when SIIS evidence supports it; attach only verified catalogue URIs; abstain otherwise.

---

## 3. Architecture and workflow (simple)

```
User complaint
    → Query understanding (intent / target / symptoms)
    → Semantic cache (logic version sgte.relevance.v3)
    → SIIS retrieve + rerank + section filter
    → Plan build (ordered actions / steps)
    → Official deeplink catalogue attach (exact URI only when mapped)
    → Response: plan  |  no_match abstention
```

- **Backend:** FastAPI (`uvicorn sgte.api:app` on `127.0.0.1:8000`)
- **Frontend:** React UI (`npm run dev` → `http://127.0.0.1:5173/?demo=1`); Vite proxies `/health` and `/v1` to the API
- **Evidence sources:** Samsung SIIS corpus + official deeplink catalogue (loaded at boot)
- **MOCK path:** `SGTE_LLM_PROVIDER=mock` + `SGTE_DEMO_OFFLINE=1` — grounded mock factory, no live API keys

UI cues: **MOCK MODE** banner, health `execution_mode: MOCK`, `production_authorized: false`.

---

## 4. Three-minute live demo walkthrough

Open `http://127.0.0.1:5173/?demo=1`. Confirm MOCK banner. Clear cache (see checklist). Run these four Phase 47–verified queries.

| # | Time | Query | What to show | Verified outcome (Phase 47) |
|---|------|-------|--------------|-----------------------------|
| 1 | ~45s | `My phone screen is not responding properly to touch.` | Ordered plan; no Full Screen Gesture Function | **plan** — Restart → Safe Mode → Touchscreen factors → Touch Sensitivity Setting (manual-only) |
| 2 | ~45s | `How do I turn off fast charging?` | Settings action + exact URI | **plan** — Disable Fast charging, **DL-0403**, `bixby://masked/act/a70d908ca1` |
| 3 | ~40s | `A floating circle is appearing on my screen. How do I remove it?` | Clear abstention | **`no_match`** — does not guess Edge / Assistive touch |
| 4 | ~30s | `How do I make sourdough bread?` | Out-of-scope abstention | **`no_match`** — empty action list |

**Optional 20-second beats (if judges ask):**

- Multi-window: `I want to use two apps at the same time on my phone.` → **plan** + **DL-0270**
- Touch sensitivity: `How do I increase touch sensitivity?` → **Enable Touch sensitivity**, **DL-0126**
- Gmail blank / Smart Switch QR / slow charging → **`no_match`** (no invented Wi-Fi, missing-QR, or battery-drain plans)

---

## 5. Thirteen critical regression queries (Phase 47 actual outcomes)

Use these exact strings. Outcomes below are from the Phase 47 live mock API run — not aspirational targets.

| ID | Exact query | Expected demo outcome | Why it matters |
|----|-------------|----------------------|----------------|
| Q1 | Gmail is showing a blank screen when I open it. | **`no_match`** | No unsupported email-server / Wi-Fi plan |
| Q2 | My phone is charging slowly. What should I do? | **`no_match`** | No unrelated battery-drain / fast-charging plan |
| Q3 | I want to use two apps at the same time on my phone. | **plan** (Multi window actions; DL-0270 on swipe-gestures action) | Supported multi-window path |
| Q4 | How do I make an app use the full screen? | **`no_match`** | No unsupported screen-mirroring plan |
| Q5 | The QR code is not appearing in Smart Switch. | **`no_match`** | No unsupported missing-QR plan |
| Q6 | A floating circle is appearing on my screen. How do I remove it? | **`no_match`** | Ambiguous floating UI → abstain |
| Q7 | My phone screen is not responding properly to touch. | **plan** without Full Screen Gesture Function | Touch plan stays on-topic |
| Q8 | How do I increase touch sensitivity? | **plan** — Enable Touch sensitivity, **DL-0126** | Verified catalogue deeplink |
| Q9 | How do I turn off double tap to wake? | **`no_match`** (recorded) | Insufficient evidence → abstain |
| Q10 | How do I turn off fast charging? | **plan** — Disable Fast charging, **DL-0403** | Verified catalogue deeplink |
| Q11 | How do I change the navigation bar settings? | **`no_match`** (recorded) | Insufficient evidence → abstain |
| Q12 | How do I factory reset my phone? | **`no_match`** (recorded) | Insufficient evidence → abstain |
| Q13 | How do I make sourdough bread? | **`no_match`** | Out-of-scope |

All 13 critical regression checks in Phase 47: **PASSED**.

---

## 6. Why the system sometimes returns `no_match`

`no_match` is a **deliberate trust feature**, not a crash:

1. **Out of scope** — e.g. baking (Q13)
2. **Ambiguous complaint** — e.g. “floating circle” without identifying the feature (Q6)
3. **Evidence gap** — SIIS / catalogue do not support a safe plan for that exact complaint (Q1 Gmail blank, Q5 missing QR, Q2 slow charging, Q4 fullscreen, Q9/Q11/Q12 settings)
4. **Relevance guard** — avoid forcing unrelated plans (Wi-Fi for Gmail blank, mirroring for fullscreen, Fast Charging for “charging slowly”)

Point to judges: abstaining is preferable to hallucinated steps.

---

## 7. Verified deeplinks vs manual-only actions

| Kind | Meaning | Phase 47 count |
|------|---------|----------------:|
| **Verified catalogue deeplink** | Action includes a URI that **exactly** matches an official catalogue entry (ID + URI) | **3** |
| **Manual-only action** | SIIS-backed step with **no** catalogue URI attached | **11** |
| **Invalid / mismatched URI** | URI not in catalogue or does not match | **0** |

Verified in Phase 47:

| Catalogue ID | Action | Exact URI |
|--------------|--------|-----------|
| DL-0270 | Swipe gestures for Multi window | `bixby://masked/act/6c0fd865eb` |
| DL-0126 | Enable Touch sensitivity | `bixby://masked/act/14eb42b895` |
| DL-0403 | Disable Fast charging | `bixby://masked/act/a70d908ca1` |

Many correct plans are manual-only by design — the catalogue does not cover every SIIS action. SGTE does **not** invent URIs.

---

## 8. Closing — limitations and future improvements

**State clearly**

- Demo is **MOCK** — not live-provider accuracy
- Production / implementation gate: **UNSATISFIED** (`production_authorized: false`)
- Offline handoff (Phase 41): **READY_WITH_LIMITATIONS** — not a production release
- Evidence gaps remain (e.g. Adaptive Display clarification prepared-not-sent; product decisions pending — Phases 38–41)
- Many actions remain manual-only until catalogue coverage grows

**Future improvements (honest, non-claims)**

- Live-provider evaluation under an authorized gate (not done in this package)
- Broader SIIS / catalogue coverage for settings gaps (double-tap wake, navigation bar, factory reset, etc.)
- Resolution of documented production blockers from Phases 38–41

**Closing line**

> “SGTE recommends when evidence supports it, attaches only verified catalogue deeplinks, and abstains when it does not. Mock results illustrate that policy — they are not a substitute for live-provider evaluation.”
