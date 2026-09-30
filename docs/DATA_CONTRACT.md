# Theme 2 Data Contract

**Source of truth:** Samsung PRISM Generative AI Hackathon 2026, Theme 2 specification:

- `Theme 2_Troubleshooting_Smart Guided Troubleshooting Engine.pdf` (author: Binny Lakra / PRISM / SRI-Bangalore)
- Cross-checked against the 3rd Edition overview PDF Theme 2 summary where it repeats the same constraints

This document records **only** what those official materials state. It does **not** invent JSON keys, join IDs, or catalogue record shapes that are not visible in the specification or in Appendix A (`schema.py`).

**Workspace note:** At documentation time, `queries.json`, `siis_responses.json`, `deeplinks.json`, `samples/`, and a standalone `schema.py` file were **not present** in `Smart_Guided_TroubleShoot`. Their **purpose** is specified in Section 3 of the Theme 2 PDF. Their **exact on-disk JSON tree** must be copied from those official starter files when they are added. Until then, do not assume extra fields.

---

## Provenance map

| Official artifact | Where the contract is defined |
| --- | --- |
| `queries.json` | Section 3 (purpose + domain scope only) |
| `siis_responses.json` | Section 3 (purpose + content constraints only) |
| `deeplinks.json` | Section 3 (catalogue size, URI pattern, metadata names) + Appendix A models used at output time |
| `samples/` | Section 3 (five complete input-output pairs) |
| `schema.py` | Appendix A (full Pydantic listing) + Section 4.1 (field-level phrasing rules) |
| API request/response | Section 5 + Appendix B |
| Operational constraints | Sections 4.2, 6, 7, 8 |

---

## 1. Exact structure of `queries.json`

**Official text (Section 3):**

> `queries.json`: Canonical user queries spanning four primary device domains: **Battery, Display, Camera, and Performance**.

That is the entire file-level contract in the specification.

**What is therefore known**

- The file contains **canonical user queries**.
- Coverage is **four domains only**: Battery, Display, Camera, Performance.

**What is not specified in the PDF (do not invent)**

- Top-level JSON type (array vs object vs object-of-arrays)
- Record keys (`id`, `query`, `domain`, etc.)
- Whether a query is a string or a nested object
- How a query record joins to `siis_responses.json` or `samples/`
- Count of queries

When the official file is available, transcribe its actual keys here. Until then, treat `queries.json` as the **canonical-query corpus** for those four domains, not as a schema you may extend.

---

## 2. Exact structure of `siis_responses.json`

**Official text (Section 3):**

> `siis_responses.json`: Pre-cleaned customer-care reference text containing troubleshooting instructions without web URLs or images.

SIIS is named in Section 1 as the internal knowledge repository used by customer-support agents.

**What is therefore known**

- Content is **pre-cleaned customer-care reference text**.
- Content contains **troubleshooting instructions**.
- Content must **not** include **web URLs** or **images**.

**What is not specified in the PDF (do not invent)**

- Top-level JSON type
- Record keys
- Whether each entry is raw text, an article object, or a list of paragraphs
- Join key to `queries.json`
- How `siis_response` on the API maps onto a row in this file (the API field is a **raw text string**, not a JSON object)

The API (Section 5) treats SIIS knowledge as **optional raw text**:

```json
"siis_response": "<optional raw text context>"
```

So the **runtime input** is a string. The **file** is a dataset of such reference text. The file’s wrapper schema is not printed in the PDF.

---

## 3. Exact structure of `deeplinks.json`

**Official text (Section 3):**

> `deeplinks.json`: A catalog of **~575** masked in-app Settings deeplinks (`bixby://masked/act/...`). Metadata includes descriptive intent strings (`description`, `message`, `qna_description`), control types, and toggle validation rules.

> `bixby://dummy_positive`: A reserved generic placeholder used exclusively when a step opens a valid Settings screen not currently indexed in the catalog.

**What is therefore known**

| Fact | Official value |
| --- | --- |
| Role | In-app Settings deeplink catalogue |
| Approximate size | ~575 entries |
| URI pattern | `bixby://masked/act/...` |
| Named metadata fields | `description`, `message`, `qna_description` |
| Additional metadata (named, not typed) | control types; toggle validation rules |
| Reserved non-indexed URI | `bixby://dummy_positive` |

**Matching rule (Section 7.4), which constrains how catalogue fields are used**

Deeplink identifiers (`bixby://masked/act/...`) are **obfuscated tokens**. Matching **must** be performed on descriptive metadata fields:

- `description`
- `message`
- `qna_description`

Matching **must not** be performed on the URI string itself.

**Relationship to Appendix A**

Appendix A defines the **output** objects `DeepLink` and `ValidationDeepLink`. It does **not** reprint the on-disk `deeplinks.json` record. Overlap that **is** named in both places:

| Catalogue (Section 3 / 7.4) | Appendix A model |
| --- | --- |
| masked URI | `BaseDeepLink.deeplink: str` |
| `description` | `DeepLink.description: str` |
| `message` | `DeepLink.message: Optional[str] = ""` |
| toggle validation rules | `ValidationDeepLink` (`key`, `resultType`, `condition`, `value`) |
| control types | not a dedicated Appendix A field; closest optional fields are `DeepLink.classes` and `DeepLink.originalType` — **do not equate them until the file is inspected** |
| `qna_description` | **not** a field on Appendix A `DeepLink` (catalogue-only / retrieval-only field) |

**Exact JSON tree of `deeplinks.json` is not printed.** Do not assume array-of-`DeepLink` vs a dict keyed by URI vs a split of actionable vs validation records until the official file is present.

---

## 4. Exact Pydantic / `schema.py` models

Appendix A is the official data-contract reference. Transcribed from that appendix (Python as printed):

```python
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel

class BaseDeepLink(BaseModel):
    deeplink: str

class DeepLink(BaseDeepLink):
    description: str
    message: Optional[str] = ""
    classes: Optional[Dict[str, str]] = None
    originalType: Optional[str] = None

class Condition(str, Enum):
    greater = "greater"
    equal = "equal"
    less = "less"

class ResultTypes(str, Enum):
    boolean = "boolean"
    intNum = "integer"
    string = "str"
    floatNum = "float"

class actionCategory(str, Enum):
    auto = "auto"
    manual = "manual"
    critical = "critical"

class ValidationDeepLink(BaseDeepLink):
    key: str
    resultType: Optional[ResultTypes] = None
    condition: Optional[Condition] = None
    value: Optional[str] = None

class StepGroup(BaseModel):
    steps: List[str]
    validationDeepLink: Optional[ValidationDeepLink] = None
    actionableDeepLink: Optional[DeepLink] = None

class Action(BaseModel):
    actionName: str
    description: str
    stepGroups: List[StepGroup]
    category: Optional[actionCategory] = actionCategory.manual

class Goal(BaseModel):
    goal: str
    title: str
    actions: List[Action]
    score: float

class ContextDeepLinkResponse(BaseModel):
    """RAG response containing a list of Goal objects."""
    contexts: List[Goal] = []
```

### 4.1 Model graph

```
ContextDeepLinkResponse
  contexts: List[Goal]
    Goal
      goal, title, score
      actions: List[Action]
        Action
          actionName, description, category
          stepGroups: List[StepGroup]
            StepGroup
              steps: List[str]
              validationDeepLink?: ValidationDeepLink  →  deeplink, key, resultType?, condition?, value?
              actionableDeepLink?: DeepLink            →  deeplink, description, message?, classes?, originalType?
```

### 4.2 Enumerations (closed sets)

**`actionCategory`**

| Member | Wire value |
| --- | --- |
| `auto` | `"auto"` |
| `manual` | `"manual"` |
| `critical` | `"critical"` |

Default on `Action.category` if omitted: **`actionCategory.manual`**.

**`Condition`**

| Member | Wire value |
| --- | --- |
| `greater` | `"greater"` |
| `equal` | `"equal"` |
| `less` | `"less"` |

**`ResultTypes`**

| Member | Wire value |
| --- | --- |
| `boolean` | `"boolean"` |
| `intNum` | `"integer"` |
| `string` | `"str"` |
| `floatNum` | `"float"` |

Python member names and JSON values are **not** identical for `intNum` / `string` / `floatNum`. Validators must compare against the **enum values**, not the Python identifiers.

### 4.3 What Appendix A does **not** define

The following appear in Section 5 / Appendix B but are **not** fields of `Goal` or `ContextDeepLinkResponse`:

- `query`
- `query_variations`
- `response` (wrapper around `contexts`)
- `meta` (`latency_ms`, `cache_hit`, `model`, `cost_usd`)
- `fallback` / `"no_match"` / `"no_siis_context"`

Those belong to the **HTTP envelope**, not to `schema.py`. See Section 15.

---

## 5. Relationship between queries and SIIS responses

**Specified**

1. **Pipeline input** (Section 2) is `Raw Complaint (+ Optional SIIS Raw Knowledge Text)`.
2. **Structure extraction** (pipeline component 1) “parses unstructured customer-care reference text into a structured `Goal` object”.
3. **No-hallucination** (Section 4.2.3): troubleshooting plans **must derive purely from provided reference text**.
4. **API** (Section 5): `query` is the complaint; `siis_response` is optional raw text. If `siis_response` is omitted, the engine performs **semantic lookup against pre-warmed cache entries**.
5. **Roadmap Phase 4** names an error boundary `"no_siis_context"` in addition to `"no_match"`.
6. Datasets: `queries.json` holds canonical complaints; `siis_responses.json` holds the pre-cleaned articles those complaints would be resolved against.

**Not specified (join mechanics)**

- Whether each canonical query has exactly one SIIS article
- Shared identifier, filename pairing, or order-based alignment
- Whether `samples/` is the only official pairing

**Implementable interpretation that stays inside the spec**

- When `siis_response` **is present**: extract the plan **only** from that text (plus deeplink catalogue for URI attachment). Do not add steps from model memory.
- When `siis_response` **is absent**: do **not** invent SIIS text; look up a **pre-validated cached plan** by semantic similarity to the query / paraphrases. If nothing is usable, empty `contexts` + `fallback` (Section 4.2.3 / Phase 4).

---

## 6. Relationship between actions and deeplink catalogue entries

**Specified**

1. Each **action** represents **exactly one physical screen or feature**. Multiple UI steps on the same screen are grouped under that single action (Section 4.1, One-Action-One-Screen).
2. Phase 2 **matches target screens to deeplink catalog entries**.
3. `actionableDeepLink` must be a **verbatim masked URI copied from the catalog** matching the target screen (Section 4.1).
4. Retrieval/matching uses **semantic descriptions**, never hallucinated or altered URLs (Section 4.2.2, Section 7.4).
5. Evaluation requires **exact URI match** against the catalogue for deeplink catalog validity (Appendix C: 100%).
6. **`auto`** actions are standard configuration screens **reachable via deeplink**.
7. **`manual`** actions **cannot carry an actionable deeplink**.
8. If the correct Settings screen is valid but **not indexed**, use reserved URI `bixby://dummy_positive` (Section 3). Appendix B’s worked example uses `"deeplink": "bixby://dummy_positive"` on an `auto` action together with catalogue-style `description` and `message`.

**Attachment point in the schema**

- Catalogue URI + display metadata → `StepGroup.actionableDeepLink` (`DeepLink`)
- Toggle validation rules → `StepGroup.validationDeepLink` (`ValidationDeepLink`)
- An `Action` may have multiple `stepGroups`; each group may independently carry actionable and/or validation deeplinks.

**`DeepLink` vs catalogue**

At output time, copy:

- `deeplink` **verbatim** from the matched catalogue row (or `bixby://dummy_positive` when the screen is not indexed)
- `description` / `message` from that row’s metadata (Appendix B example)

Do not synthesize a `bixby://masked/act/...` string.

---

## 7. All required fields

### 7.1 `schema.py` required fields (no default in Appendix A)

| Model | Required fields |
| --- | --- |
| `BaseDeepLink` | `deeplink` |
| `DeepLink` | `deeplink`, `description` |
| `ValidationDeepLink` | `deeplink`, `key` |
| `StepGroup` | `steps` |
| `Action` | `actionName`, `description`, `stepGroups` |
| `Goal` | `goal`, `title`, `actions`, `score` |

`ContextDeepLinkResponse.contexts` has default `[]`, so it may be omitted in construction but the object still serializes with `contexts`.

### 7.2 Section 4.1 required **content** on those fields (in addition to type)

These are required when a successful (non-empty) plan is returned:

| Field | Required form |
| --- | --- |
| `Goal.goal` | Exact syntax: `Follow these steps to perform this <Topic> Troubleshooting` **or** `Follow these steps to perform this <Topic> Configuration` |
| `Goal.title` | 2 to 3 words, sentence case, identifying the core issue |
| `Goal.score` | Float in `[0.0, 1.0]` |
| `Action.actionName` | Title Case; one physical screen/feature |
| `Action.description` | Exactly 5 to 7 words, starting with `"It will"` |
| `StepGroup.steps` | Clear imperative UI steps; one physical interaction per step; no URLs or external links |
| `query_variations` (API envelope) | 8 to 10 distinct paraphrases |

### 7.3 API request

| Field | Required? | Official basis |
| --- | --- | --- |
| `query` | Present in the only request example; the endpoint “processes a customer complaint” | Section 5 |
| `siis_response` | Optional | Section 5 explicitly |

The PDF does not print a Pydantic request model.

### 7.4 API success envelope (Appendix B)

Present in the official 200 example:

- `query`
- `query_variations`
- `response.contexts` (list of `Goal`)
- `meta.latency_ms`
- `meta.cache_hit`
- `meta.model`
- `meta.cost_usd`

### 7.5 Health

`GET /health` → HTTP 200 and `{"status": "ok"}` when caching layer, model connections, and vector indexes are fully initialized.

---

## 8. All optional fields

### 8.1 Appendix A optional fields (default shown)

| Model | Field | Default |
| --- | --- | --- |
| `DeepLink` | `message` | `""` |
| `DeepLink` | `classes` | `None` |
| `DeepLink` | `originalType` | `None` |
| `ValidationDeepLink` | `resultType` | `None` |
| `ValidationDeepLink` | `condition` | `None` |
| `ValidationDeepLink` | `value` | `None` |
| `StepGroup` | `validationDeepLink` | `None` |
| `StepGroup` | `actionableDeepLink` | `None` |
| `Action` | `category` | `actionCategory.manual` |
| `ContextDeepLinkResponse` | `contexts` | `[]` |

Appendix B serializes a missing validation link as JSON `null` (`"validationDeepLink": null`).

### 8.2 Optional API / operational fields

| Field | Official basis |
| --- | --- |
| Request `siis_response` | Section 5 |
| `meta.fallback` = `"no_match"` | Section 4.2.3 (shown as fallback metadata, not as a `schema.py` field) |
| `"no_siis_context"` | Section 8 Phase 4 error boundary (payload location not printed) |

### 8.3 Catalogue-only field not on output `DeepLink`

| Field | Where named |
| --- | --- |
| `qna_description` | Section 3 and Section 7.4 (retrieval metadata) |

---

## 9. Action categories and their constraints

Closed enum: `auto` | `manual` | `critical`.

| Category | Official definition | Constraints |
| --- | --- | --- |
| `auto` | Standard configuration screens reachable via deeplink | Expected to resolve to a catalogue URI (or `bixby://dummy_positive` if the screen is not indexed). Appendix C target: auto actions carrying a valid actionable deeplink ≥ 99%. |
| `manual` | Physical interventions (examples: cleaning ports, replacing hardware, visiting service centers) | **Cannot carry an actionable deeplink** |
| `critical` | Disruptive or irreversible operations (examples: factory reset, restart, firmware update, safe mode) | **Must be ordered last** |

Schema default is `manual`. Emitting `auto` or `critical` therefore requires an explicit category.

**Ordering constraints that mention category / disruption**

- Pipeline Phase 2: sequence **non-invasive settings first → critical/destructive last**
- Component 2 challenge: **safe toggles before system resets**
- Evaluation “Plan Hierarchy”: **Settings toggles → system optimizations → device reboots**

These three phrasings are official. They are consistent (least disruption first, reboots/resets last) but are **not** a fully specified comparator for every mixed pair (e.g. two `auto` toggles). See ambiguities.

---

## 10. One-action-one-screen rule

**Section 4.1 (`actionName`):**

> Title Case. Represents **exactly one physical screen or feature**. Multiple steps occurring on the same screen **must be grouped under a single action**.

**Section 7.2 (pitfall):**

> Over-Granular vs. Under-Granular Actions: Creating a separate action for every single tap fragments the UI, while bundling multiple screens into one action breaks deeplinking. The rule is strictly: **One Action = One Screen**.

**Section 4.1 (`stepGroups[].steps`):**

> Clear, imperative UI steps. **One physical interaction per step**. No URLs or external links.

**Implications that stay inside the spec**

- One `Action` ↔ one target screen/feature ↔ at most one logical deeplink target for that action’s auto path
- Multiple `steps` inside `stepGroups` are taps **on that same screen** (plus navigation phrasing as in Appendix B: “Navigate to and open Settings.”, “Tap on Display.”, …)
- Splitting one screen into many actions is a spec violation; merging two screens into one action is a spec violation because it breaks deeplink resolution

---

## 11. Deeplink validation requirements

| Requirement | Source |
| --- | --- |
| URIs are masked `bixby://masked/act/...` tokens | Section 3, 7.4 |
| Copy URI **verbatim** from `deeplinks.json` | Section 4.1, 4.2.2 |
| Do **not** hallucinate or alter URLs | Section 4.2.2 |
| Match on `description`, `message`, `qna_description`; **never** on the URI string | Section 7.4 |
| Index `deeplinks.json` with **dual retrieval: BM25 keyword + dense embeddings** | Section 8 Phase 2 |
| Prefer **exact target screens**, not high-level parent menus | Section 6.2 Screen Resolution Accuracy |
| `manual` actions must not carry `actionableDeepLink` | Section 4.1 |
| Unindexed but valid Settings screen → `bixby://dummy_positive` only | Section 3 |
| Output deeplink catalog validity measured by **exact URI match** at **100%** | Appendix C |
| Auto actions with valid actionable deeplink **≥ 99%** | Appendix C |
| `ValidationDeepLink` carries `key` plus optional `resultType`, `condition`, `value` for toggle checks | Appendix A + Section 3 “toggle validation rules” |
| Appendix B shows `validationDeepLink: null` when unused | Appendix B |

`ValidationDeepLink.deeplink` is still required by the model when the object is present.

---

## 12. URL leakage requirements

**Section 4.2.1 — Zero URL Leaks (absolute):**

> Absolute prohibition of web URLs (`http`, `https`, `www.`, markdown links). Models often inject generic help URLs from pretraining memory; these must be **programmatically scrubbed**.

**Section 6.1:**

> Zero Leakage: Strict elimination of extraneous web links or fabricated URLs.

**Section 7.3:**

> LLMs tend to generate strings like `Visit samsung.com/support`. Enforce **programmatic regex filters** on generated steps.

**Also:**

- `siis_responses.json` itself is pre-cleaned **without web URLs or images** (Section 3)
- `stepGroups[].steps` must contain **no URLs or external links** (Section 4.1)
- API body must be **pure JSON** with no markdown wrapping (Section 4.2.4)

In-app `bixby://...` URIs are the **allowed** deeplink scheme. The leak ban is about **web** URLs and markdown links, not about well-formed catalogue `bixby://` URIs sitting in `actionableDeepLink.deeplink`.

---

## 13. No-hallucination / no-match behavior

**Section 4.2.3:**

> Troubleshooting plans must derive **purely from provided reference text**. If the reference data contains **no viable solution**, the engine must return an empty list (`contexts: []`) with fallback metadata (`"fallback": "no_match"`).

**Pipeline component 1 challenge:**

> Eliminating LLM hallucination; strictly adhering to source text; enforcing exact field constraints.

**Section 4.2.2:**

> Hallucinating or altering URLs is strictly forbidden.

**Section 8 Phase 4:**

> Implement error boundaries and graceful fallbacks (`"no_match"`, `"no_siis_context"`).

**Empty-plan shape that is specified**

- `ContextDeepLinkResponse.contexts` = `[]` (this is also the schema default)
- Fallback metadata: `"fallback": "no_match"`

The PDF does **not** print whether `fallback` lives under `meta` or at the top level. Appendix B’s success example has `meta` but no `fallback` key. See ambiguities.

Do **not** invent steps, screens, or URIs when SIIS/reference text has no solution.

---

## 14. Query variation requirements

**Section 2 pipeline [0] Query Enrichment:**

- Normalize colloquial text into a canonical technical query
- Generate **semantic cache key** and **8–10 distinct paraphrases**

**Section 4.1 `query_variations`:**

> **8 to 10** distinct paraphrases across varied registers (**formal, casual, keyword-only, frustrated, typo-inclusive**). Inclusive range.

**Section 6.2:**

> Semantic Paraphrase Hit Rate: Achieving **≥ 80%** cache hit rates on diverse, unseen query paraphrases.

**Appendix B** shows `query_variations` as an array of strings on the HTTP 200 body, alongside the canonical `query`. Several example strings are **visually truncated** in the PDF rendering; do not reconstruct the cut-off suffixes.

**Registers that must be represented (named):** formal, casual, keyword-only, frustrated, typo-inclusive.

**Not specified:** uniqueness algorithm (case folding, punctuation), whether the original `query` is counted inside the 8–10, or per-register quotas.

---

## 15. API input/output contract

### 15.1 `POST /v1/troubleshoot`

Processes a customer complaint and returns an actionable plan.

**Request body (Section 5):**

```json
{
  "query": "phone swipe gestures wrong direction after app install",
  "siis_response": "<optional raw text context>"
}
```

- If `siis_response` is omitted: semantic lookup against **pre-warmed cache** entries.

**Success body (Appendix B), official keys:**

```json
{
  "query": "<string>",
  "query_variations": ["<string>", "... 8 to 10 total ..."],
  "response": {
    "contexts": [ { "goal": "...", "title": "...", "score": 0.93, "actions": [ ... ] } ]
  },
  "meta": {
    "latency_ms": 212,
    "cache_hit": true,
    "model": "gpt-4o-mini",
    "cost_usd": 0.0
  }
}
```

`response` is a `ContextDeepLinkResponse` (`contexts: List[Goal]`).

Appendix B title: example is a complete compliant response serialized **per line** in `results.jsonl`.

**No-match body (keys that are specified):**

- `response.contexts` = `[]` **or** equivalently the `ContextDeepLinkResponse` empty list
- `"fallback": "no_match"` as fallback metadata

**Delivery (Section 4.2.4):**

> API responses must never include markdown wrapping (e.g. `json` fences) or conversational preamble. **Pure JSON.**

Overview PDF addendum: the output JSON should include **all actions, steps, and associated deeplinks**. Mapping must stay reusable (production target **10k+ scenarios**). Deeplinks must **logically resolve** to the action steps.

### 15.2 `GET /health`

HTTP **200** and `{"status": "ok"}` when:

- caching layer
- model connections
- vector indexes

are **fully initialized**.

### 15.3 Latency / cost metadata (must be real, not decorative)

| Path | Official target |
| --- | --- |
| Cache hit (exact query match) | P95 ≤ **300 ms** |
| Cache hit (unseen semantic paraphrase) | P95 ≤ **300 ms** |
| Cold query (full pipeline) | P95 ≤ **8000 ms** (Appendix C); Section 6 also states P95 ≤ **8 s** |
| Cache-hit inference cost | **$0.00** |
| Cold-query cost | Tracked; method = `(prompt tokens + completion tokens) × rate` |
| Semantic cache hit rate on unseen paraphrases | ≥ **80%** |

`meta.cache_hit` is boolean in Appendix B. `meta.cost_usd` is `0.0` on a cache hit in that example.

---

## 16. Constraints that must be implemented deterministically (not via LLM)

The specification repeatedly forbids relying on the model to obey natural-language constraints. Implement these in application code (validators, regex, ordering, cache, retrieval).

| Constraint | Why the spec says it is deterministic |
| --- | --- |
| Pydantic schema + strict field types | Section 6.1 Schema Conformance 100%; Phase 1 “schema validation harness using `schema.py`” |
| `goal` prefix / exact syntax | Section 4.1; Appendix C “Rule compliance (Goal / Title / Description syntax)” |
| `title` 2–3 words, sentence case | Section 4.1; Section 7.5: prompting an LLM for word counts is **unreliable** |
| `description` exactly 5–7 words, starts with `"It will"` | Section 4.1, 7.5 |
| `actionName` Title Case | Section 4.1 |
| One action = one screen | Section 4.1, 7.2 |
| One physical interaction per step | Section 4.1 |
| Zero URL leaks (`http`, `https`, `www.`, markdown links) | Section 4.2.1 **programmatic scrub**; Section 7.3 **programmatic regex** |
| No URLs/external links inside `steps` | Section 4.1 |
| `actionableDeepLink.deeplink` verbatim catalogue membership (or reserved `bixby://dummy_positive`) | Section 4.2.2; never generate URI from the LLM |
| Deeplink **retrieval** on metadata, not on the masked URI | Section 7.4 |
| `manual` ⇒ no actionable deeplink | Section 4.1 |
| `critical` last; non-invasive first | Section 4.1, Phase 2 “implement action ordering logic” |
| `query_variations` count 8–10 and distinctness | Section 4.1 (count is a hard range; generation may use an LLM, **count/dedup must be checked in code**) |
| Cache keying is **semantic**, not raw-string | Section 7.1; cache hit must skip LLM (Section 2 [3]) |
| Cache miss: run pipeline [0]–[2], **validate schema**, **then** write cache | Section 2 [3] |
| Empty plan + `fallback: no_match` when reference has no solution | Section 4.2.3 (control flow, not a creative LLM choice) |
| Pure JSON response (no markdown fences / preamble) | Section 4.2.4 |
| Health reflects real init of cache, models, indexes | Section 5 |
| Deterministic execution for identical or semantically identical inputs | Section 6.1 |

**Allowed LLM uses (named by the spec)**

- Query enrichment / normalisation (component 0)
- Structure extraction from SIIS text (Phase 1)
- Semantic paraphrase generation (component 0)
- Assisting screen matching **via embeddings**, with BM25 (Phase 2) — the **URI itself** is still copied from the catalogue

---

## Appendix B field checklist (worked example, non-truncated parts)

Use this only as the official **shape** example, not as extra schema.

**Goal**

- `goal`: `Follow these steps to perform this Swipe Navigation Troubleshooting`
- `title`: `Swipe navigation settings` (3 words, sentence case)
- `score`: `0.93`
- `actions[0].actionName`: `Configure Navigation Bar Settings`
- `actions[0].description`: `It will let you choose navigation type` (7 words, `"It will"` prefix)
- `actions[0].category`: `auto`
- `steps`: imperative sentences ending with a period; no URLs
- `actionableDeepLink.deeplink`: `bixby://dummy_positive`
- `actionableDeepLink.description` / `message`: present
- `validationDeepLink`: `null`

**`meta` example values:** `latency_ms` 212, `cache_hit` true, `model` `gpt-4o-mini`, `cost_usd` 0.0

---

## Starter assets still required on disk

Copy these official files into the repo before implementing parsers:

1. `queries.json`
2. `siis_responses.json`
3. `deeplinks.json`
4. `samples/` (five input-output pairs)
5. `schema.py` (should match Appendix A)

Until those files are present, parsers and indexes must not be coded against guessed keys.
