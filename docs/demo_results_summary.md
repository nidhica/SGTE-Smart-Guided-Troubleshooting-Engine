# SGTE Demo Results Summary

**Source of truth:** `evaluation/phase47_final_demo/` (live mock API, 2026-09-27)  
**Mode:** MOCK · `llm_provider: mock` · `demo_offline: true` · `cache_logic_version: sgte.relevance.v3`  
**Do not treat these results as live-provider accuracy.**

Related packages (preserved, not overwritten):

- `evaluation/phase47_final_demo/` — final demo validation
- `evaluation/phase41_final_offline_handoff/` — offline handoff READY_WITH_LIMITATIONS
- `evaluation/phase38_offline_release_candidate/` — offline RC `SGTE-OFFLINE-RC-20260927-a51bd646a78f`

---

## 1. Phase 47 plan / no_match results

| ID | Exact query | Status | Key output |
|----|-------------|--------|------------|
| Q1 | Gmail is showing a blank screen when I open it. | **no_match** | Empty plan |
| Q2 | My phone is charging slowly. What should I do? | **no_match** | Empty plan |
| Q3 | I want to use two apps at the same time on my phone. | **plan** | 8 multi-window actions; DL-0270 on first |
| Q4 | How do I make an app use the full screen? | **no_match** | Empty plan |
| Q5 | The QR code is not appearing in Smart Switch. | **no_match** | Empty plan |
| Q6 | A floating circle is appearing on my screen. How do I remove it? | **no_match** | Empty plan |
| Q7 | My phone screen is not responding properly to touch. | **plan** | Restart; Safe Mode; Touchscreen factors; Touch Sensitivity Setting |
| Q8 | How do I increase touch sensitivity? | **plan** | Enable Touch sensitivity · DL-0126 |
| Q9 | How do I turn off double tap to wake? | **no_match** | Empty plan (recorded) |
| Q10 | How do I turn off fast charging? | **plan** | Disable Fast charging · DL-0403 |
| Q11 | How do I change the navigation bar settings? | **no_match** | Empty plan (recorded) |
| Q12 | How do I factory reset my phone? | **no_match** | Empty plan (recorded) |
| Q13 | How do I make sourdough bread? | **no_match** | Empty plan |

**Counts:** 4 plan · 9 no_match · cache cleared before run · all 13 `cache_hit: false`

Machine-readable: `evaluation/phase47_final_demo/final_demo_results.json`

---

## 2. Exact URI verification (deeplink integrity)

| Metric | Value |
|--------|------:|
| Total actions returned | 14 |
| Actions with a URI | 3 |
| Verified catalogue deeplinks (exact URI match) | **3** |
| Manual-only actions | **11** |
| Invalid or mismatched deeplinks | **0** |

| Query | Action | Catalogue ID | Exact URI |
|-------|--------|--------------|-----------|
| Q3 | Swipe gestures for Multi window | DL-0270 | `bixby://masked/act/6c0fd865eb` |
| Q8 | Enable Touch sensitivity | DL-0126 | `bixby://masked/act/14eb42b895` |
| Q10 | Disable Fast charging | DL-0403 | `bixby://masked/act/a70d908ca1` |

Source: `evaluation/phase47_final_demo/deeplink_integrity_report.json`

---

## 3. Test results (executed in Phase 47)

| Suite | Result |
|-------|--------|
| Critical demo regressions (13 checks) | **all_critical_ok: true** |
| Focused pytest (Phases 43–46) | **32 passed** (15.41s) |
| Full suite `pytest tests -q` | **762 passed** (190.42s) |

Source: `evaluation/phase47_final_demo/regression_test_report.json`

---

## 4. Mock-mode limitations

- Results use a **grounded mock LLM**, not a live provider.
- Mock behavior demonstrates pipeline policy and catalogue integrity — **not** live LLM accuracy.
- No API keys are required or claimed for this demo package.
- Offline RC / handoff packages (Phases 38, 41) explicitly mark evaluation as mock/offline only.

---

## 5. Production gate status

| Gate field | Value |
|------------|-------|
| `production_authorized` | **false** |
| `implementation_gate_satisfied` | **false** |
| Overall | **UNSATISFIED** |
| Phase 41 handoff | READY_WITH_LIMITATIONS (not production) |
| Phase 38 RC | Offline release candidate only |

**Safe claim:** mock-mode demo validated.  
**Unsafe claim (do not make):** production ready / live-provider validated.

---

## 6. Known unsupported scenarios and evidence gaps

From Phase 47 actual abstentions and Phases 38/41 documented limitations:

**In the 13-query demo set (verified `no_match`):**

- App-attributed Gmail blank without inventing connectivity/email-server plans (Q1)
- Slow charging without inventing battery-drain / fast-charging plans (Q2)
- Full-screen complaint without inventing Smart View / mirroring plans (Q4)
- Smart Switch missing QR without inventing a missing-QR plan (Q5)
- Ambiguous floating circle (Q6)
- Double tap to wake / navigation bar / factory reset when evidence is insufficient (Q9, Q11, Q12)
- Out-of-scope non-device query (Q13)

**Broader documented gaps (Phases 38–41 — still open; not “fixed” by Phase 47):**

- Production authorization not granted; live provider unavailable
- Adaptive Display clarification prepared-not-sent
- Product decisions pending; SIIS / catalogue / schema dependencies open
- Many SIIS-backed actions have no catalogue deeplink (manual-only by design)
- Offline handoff ≠ production safety

---

## 7. Pointers for judges

| Document | Use |
|----------|-----|
| `docs/judge_demo_script.md` | Spoken walkthrough |
| `docs/demo_checklist.md` | Startup / fallback ops |
| `docs/final_demo_script.md` | Longer Phase 47 presentation script |
| `docs/demo_guide.md` | Environment startup reference |
| `evaluation/phase47_final_demo/final_demo_report.md` | Full validation narrative |
