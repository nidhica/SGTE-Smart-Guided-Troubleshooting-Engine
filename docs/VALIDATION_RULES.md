# Theme 2 Validation Rules (Programmatic)

**Source of truth:** Samsung PRISM Generative AI Hackathon 2026 Theme 2 PDF (Sections 3–8, Appendix A–C).

Every rule below is intended to be checked **in code**, not by asking an LLM to “please follow the format” (Section 7.5).

Rules apply to a **candidate output** (HTTP `POST /v1/troubleshoot` body and/or a `Goal` / `ContextDeepLinkResponse`). Dataset-level rules apply to `queries.json`, `siis_responses.json`, `deeplinks.json`, and `samples/` once those official files are on disk.

**Not invented:** tokenizer, extra HTTP error codes, and JSON keys that the PDF does not name. Where the spec is silent, the rule is listed under **Gaps**.

---

## How to apply

1. Parse JSON (reject markdown-wrapped payloads first).
2. Validate Pydantic `schema.py` types.
3. Run field syntax / word-count / prefix rules.
4. Run category, ordering, and one-screen rules.
5. Run leak detection on all generated natural-language strings.
6. Run deeplink catalogue membership (exact URI) and reserved-URI rules.
7. Run query-variation count and distinctness.
8. Run no-match / empty-context control-flow rules.
9. Run API envelope and health/meta rules.

Suggested word counter until the spec defines one: split on Unicode whitespace, drop empty tokens. Record that choice; the PDF does not define “word”.

---

## V-JSON — payload hygiene

| ID | Rule | Check | Fail if |
| --- | --- | --- | --- |
| V-JSON-01 | Pure JSON delivery | Response body is a JSON object/array; no leading/trailing conversational text | Markdown fences (e.g. `` ```json ``), preamble, or mixed text+JSON (Section 4.2.4) |
| V-JSON-02 | Parseable UTF-8 JSON | `json.loads` succeeds | Parse error |
| V-JSON-03 | No markdown links in body strings | See V-LEAK | Any generated string contains markdown link syntax |

---

## V-SCHEMA — Pydantic / `schema.py`

Validate **`response`** (or `ContextDeepLinkResponse`) and nested models from Appendix A.

| ID | Rule | Check | Fail if |
| --- | --- | --- | --- |
| V-SCHEMA-01 | Root contexts type | `contexts` is a list of `Goal` | Missing/wrong type |
| V-SCHEMA-02 | `Goal` required | `goal: str`, `title: str`, `actions: List[Action]`, `score: float` all present | Any missing |
| V-SCHEMA-03 | `Action` required | `actionName`, `description`, `stepGroups` present | Any missing |
| V-SCHEMA-04 | `StepGroup` required | `steps: List[str]` present | Missing or not list of strings |
| V-SCHEMA-05 | `DeepLink` required | If `actionableDeepLink` is not null: `deeplink` and `description` present | Either missing |
| V-SCHEMA-06 | `ValidationDeepLink` required | If `validationDeepLink` is not null: `deeplink` and `key` present | Either missing |
| V-SCHEMA-07 | `actionCategory` enum | `category` is omitted **or** one of `auto`, `manual`, `critical` | Any other string |
| V-SCHEMA-08 | Default category | If `category` omitted, treat as `manual` (`actionCategory.manual`) | Validator assumes a different default |
| V-SCHEMA-09 | `Condition` enum | If present: `greater` \| `equal` \| `less` | Other value |
| V-SCHEMA-10 | `ResultTypes` enum | If present: `boolean` \| `integer` \| `str` \| `float` (JSON **values**, not Python names `intNum`/`string`/`floatNum`) | Other value |
| V-SCHEMA-11 | Optional DeepLink fields | `message` may be omitted (default `""`); `classes` dict[str,str] or null; `originalType` str or null | Wrong types |
| V-SCHEMA-12 | Optional validation fields | `resultType`, `condition`, `value` may be null | Wrong types |
| V-SCHEMA-13 | Empty contexts allowed | `contexts: []` is schema-valid | Rejecting empty list |
| V-SCHEMA-14 | Strict types | 100% adherence to Pydantic definitions (Section 6.1) | Coercion that violates printed types (e.g. score as string) |
| V-SCHEMA-15 | Schema-valid output lines | Appendix C target ≥ 99% of evaluated lines | — (evaluation metric; still validate 100% of **your** outputs) |

---

## V-GOAL — `goal` string

| ID | Rule | Check | Fail if |
| --- | --- | --- | --- |
| V-GOAL-01 | Required prefix | `goal` starts with `Follow these steps to perform this ` | Any other prefix |
| V-GOAL-02 | Required suffix pattern | After the prefix, remaining text matches `<Topic> Troubleshooting` **or** `<Topic> Configuration` (Section 4.1 exact syntax) | Other endings (e.g. “Fix”, “Guide”) |
| V-GOAL-03 | Non-empty topic | `<Topic>` is non-empty | Prefix+suffix only |

Official examples: `Follow these steps to perform this Swipe Navigation Troubleshooting`.

---

## V-TITLE — `title` string

| ID | Rule | Check | Fail if |
| --- | --- | --- | --- |
| V-TITLE-01 | Word count | Token count ∈ {2, 3} | 1 word or ≥ 4 words |
| V-TITLE-02 | Sentence case | Identifies core issue in sentence case (examples: `Swipe navigation settings`, `Battery fast drain`) | Title Case / ALL CAPS as the whole string (e.g. `Swipe Navigation Settings`) |
| V-TITLE-03 | Non-empty | After strip, length > 0 | Empty |

Sentence-case operationalization not fully specified; a deterministic stand-in: first character of the first word may be uppercase; subsequent words should not be uniformly capitalized unless they are required proper nouns. Flag ALL-CAPS and full Title Case as failures against the printed examples.

---

## V-DESC — `Action.description`

| ID | Rule | Check | Fail if |
| --- | --- | --- | --- |
| V-DESC-01 | Word count | Token count ∈ {5, 6, 7} **exactly** | Outside 5–7 |
| V-DESC-02 | Required prefix | Starts with `It will` (Section 4.1) | Missing or different casing/spelling (`it'll`, `It Will`, `This will`) |
| V-DESC-03 | Plain language benefit | Remainder explains concrete benefit; no URLs (also covered by leak rules) | Contains URLs/links |

Official example: `It will let you choose navigation type` (7 tokens).

---

## V-ANAME — `Action.actionName`

| ID | Rule | Check | Fail if |
| --- | --- | --- | --- |
| V-ANAME-01 | Title Case | `actionName` is Title Case (example: `Configure Navigation Bar Settings`) | sentence case / all lowercase / ALL CAPS |
| V-ANAME-02 | One screen | Name denotes exactly one physical screen or feature | Name concatenates two screens (heuristic: ` and ` joining two settings areas, etc.) — pair with V-SCREEN |

Title Case is not fully defined (hyphenation, small words). Use a documented deterministic check (e.g. every whitespace-separated token matches `[A-Z][^\s]*`) and list known exceptions only after `samples/` are inspected.

---

## V-STEPS — `stepGroups[].steps`

| ID | Rule | Check | Fail if |
| --- | --- | --- | --- |
| V-STEPS-01 | Non-empty list | `steps` has length ≥ 1 when a plan is returned | Empty `steps` on a non-empty action |
| V-STEPS-02 | Strings only | Each step is `str` | Non-string |
| V-STEPS-03 | Imperative UI | Spec requires clear imperative UI steps | (Qualitative; optional heuristic: starts with a verb. Do **not** fail solely on style unless samples define a closed verb list.) |
| V-STEPS-04 | One physical interaction per step | Each step is a single interaction | Multiple commands in one string joined by ` and then ` / `;` **and** two distinct widgets — only fail when clearly two taps; prefer samples as oracle |
| V-STEPS-05 | No URLs in steps | Step text has no web URLs, `www.`, markdown links, or external links (Section 4.1) | Any match of V-LEAK patterns |
| V-STEPS-06 | No fabricated web CTAs | Regex for `Visit <domain>` style injections (Section 7.3 example: `Visit samsung.com/support`) | Match |

---

## V-SCREEN — one-action-one-screen

| ID | Rule | Check | Fail if |
| --- | --- | --- | --- |
| V-SCREEN-01 | One action = one screen | Each `Action` maps to one physical screen/feature (Section 4.1, 7.2) | Two different `actionableDeepLink.deeplink` values under one action (distinct non-null URIs) |
| V-SCREEN-02 | Same-screen grouping | Multiple steps on one screen share one action | Same catalogue URI attached to two sibling actions in one `Goal` (split screen) |
| V-SCREEN-03 | Deeplink unity | Auto action’s stepGroups that carry `actionableDeepLink` share one URI (or all dummy_positive) | Mixed distinct catalogue URIs in one action |

V-SCREEN-01/02/03 are the programmable core of “One Action = One Screen”. Semantic “two screens named in one actionName” is a secondary heuristic.

---

## V-CAT — action category

| ID | Rule | Check | Fail if |
| --- | --- | --- | --- |
| V-CAT-01 | Closed set | See V-SCHEMA-07 | — |
| V-CAT-02 | Manual cannot carry actionable deeplink | If `category == "manual"` (including defaulted omit): every `stepGroups[].actionableDeepLink` is `null` / omitted | Any non-null `actionableDeepLink` |
| V-CAT-03 | Auto is deeplink-reachable | If `category == "auto"`: at least one `actionableDeepLink` with a `deeplink` string | Auto action with no actionable deeplink |
| V-CAT-04 | Auto URI validity | Auto `deeplink` is either an exact catalogue member **or** `bixby://dummy_positive` | Other URI |
| V-CAT-05 | Critical last | In `actions` order, no `critical` action appears **before** a non-`critical` action | `critical` then later `auto`/`manual` |
| V-CAT-06 | Critical examples are critical | If actionName/steps mention factory reset, restart, firmware update, or safe mode (Section 4.1 examples), `category` must be `critical` | Those operations labeled `auto`/`manual` |
| V-CAT-07 | Manual examples are manual | Cleaning ports, replacing hardware, visiting service centers (Section 4.1) must be `manual` and fail V-CAT-02 if a deeplink is attached | Labeled `auto` or carrying a deeplink |

---

## V-ORDER — plan hierarchy

Official phrasings to encode as a **partial order** (fail only on clear inversions):

1. Non-invasive settings **before** critical/destructive (Phase 2)
2. Safe toggles **before** system resets (component 2)
3. Settings toggles → system optimizations → device reboots (Section 6.2)

| ID | Rule | Check | Fail if |
| --- | --- | --- | --- |
| V-ORDER-01 | Critical suffix | Same as V-CAT-05 | Critical not last |
| V-ORDER-02 | Reboot/reset last among remaining | Device reboot / factory reset / firmware / safe mode appear after toggle/configuration actions | Reboot before a settings-toggle action |
| V-ORDER-03 | Destructive last | Spec: least disruptive first; destructive last | Destructive action index < non-destructive index |

Do not invent a full numeric rank for every Settings page. Use category + the named destructive operations.

---

## V-SCORE — confidence

| ID | Rule | Check | Fail if |
| --- | --- | --- | --- |
| V-SCORE-01 | Type | JSON number / Python float | Non-numeric |
| V-SCORE-02 | Range | `0.0 <= score <= 1.0` | Outside inclusive range |
| V-SCORE-03 | Present on every Goal | Required field | Missing |

---

## V-LEAK — URL / web leak detection

Apply to **all generated natural-language fields**: `goal`, `title`, `actionName`, `description`, every `steps[]` item, and `query_variations[]`. Do **not** treat a well-formed `bixby://` value **inside** `*.deeplink` as a leak.

| ID | Rule | Check | Fail if |
| --- | --- | --- | --- |
| V-LEAK-01 | No `http` | Case-insensitive substring `http` in NL fields | Match (`http` also covers `https`) |
| V-LEAK-02 | No `https` | Explicit `https` | Match |
| V-LEAK-03 | No `www.` | Substring `www.` | Match |
| V-LEAK-04 | No markdown links | Pattern `\[[^\]]*\]\([^)]+\)` | Match |
| V-LEAK-05 | No `samsung.com/support`-style CTAs | Regex for `visit\s+\S+\.\S+` and known support hosts (Section 7.3) | Match |
| V-LEAK-06 | No fabricated web URLs in deeplink fields | `actionableDeepLink.deeplink` / `ValidationDeepLink.deeplink` must **not** be `http(s):` | Web URL used as deeplink |
| V-LEAK-07 | Dataset SIIS | `siis_responses.json` text contains no web URLs or images (Section 3) | URL or image reference in SIIS corpus |
| V-LEAK-08 | Absolute zero leaks | Appendix C: Absolute URL leaks measured value **0** | Any V-LEAK-* failure in an evaluated output |

Implementation note from spec: **programmatic regex scrub**, including a correction loop that strips leaks **after** generation (Section 4.2.1, 7.5).

---

## V-DL — deeplink catalogue membership and reserved URI

Requires loaded official `deeplinks.json`. Build `CATALOGUE_URIS` = set of every `deeplink` / URI field **as stored in that file** (inspect file; do not assume the key name beyond the URI pattern `bixby://masked/act/...`).

| ID | Rule | Check | Fail if |
| --- | --- | --- | --- |
| V-DL-01 | Scheme on catalogue copies | Non-dummy actionable URI matches `bixby://masked/act/` prefix (Section 3) | Other scheme/path pattern |
| V-DL-02 | Exact URI membership | Every non-dummy `actionableDeepLink.deeplink` ∈ `CATALOGUE_URIS` (byte-for-byte) | Any alteration, truncation, or invented token |
| V-DL-03 | No URI mutation | Compare to catalogue string equality | Case/path/query changes |
| V-DL-04 | Reserved placeholder | `bixby://dummy_positive` allowed **only** when the target Settings screen is not in the catalogue (Section 3) | Dummy used **and** a catalogue URI exists that the sample/gold mapping already binds — gold from `samples/` when present |
| V-DL-05 | Dummy not a substitute for manual | `manual` still cannot carry dummy (V-CAT-02) | Dummy on manual |
| V-DL-06 | Validation URI | If `validationDeepLink` present, its `deeplink` is catalogue-valid (same membership rule) unless samples show otherwise | Unknown URI |
| V-DL-07 | Auto coverage metric | Appendix C: auto actions carrying valid actionable deeplink ≥ 99% | Track as metric |
| V-DL-08 | Catalog validity metric | Appendix C: exact URI match **100%** | Any miss |
| V-DL-09 | Retrieval must not use URI string as the match key | Matcher/index inputs are `description`, `message`, `qna_description` (Section 7.4) | Implementation searches by masked URI token as the semantic query |
| V-DL-10 | Verbatim copy | Output URI equals catalogue URI character-for-character | LLM-generated lookalike |
| V-DL-11 | Screen vs parent menu | Prefer exact target screen URI, not a parent Settings menu (Section 6.2) | Gold `samples/` URI is a child screen but output is parent (when samples exist) |

---

## V-QVAR — query variations

| ID | Rule | Check | Fail if |
| --- | --- | --- | --- |
| V-QVAR-01 | Present on success body | `query_variations` is a list of strings (Appendix B) | Missing on `POST /v1/troubleshoot` 200 |
| V-QVAR-02 | Count inclusive 8–10 | `8 <= len(query_variations) <= 10` | < 8 or > 10 |
| V-QVAR-03 | Distinct | All entries unique under a documented normalization (minimum: exact string uniqueness) | Duplicate exact strings |
| V-QVAR-04 | Stronger duplicate detection | Recommended additional: casefold + collapse whitespace; fail if two variations normalize equal | Near-duplicate exact paraphrases |
| V-QVAR-05 | Type | Every element `str` and non-empty after strip | Empty/non-string |
| V-QVAR-06 | Register coverage (weak) | Spec names registers: formal, casual, keyword-only, frustrated, typo-inclusive | **Not fully programmable** without labeled gold; do not fail production on a homemade classifier. Optionally **warn** if all strings have identical length/punctuation profile |
| V-QVAR-07 | Leak-free | Each variation passes V-LEAK | Leak in a paraphrase |
| V-QVAR-08 | Count is code-enforced | If an LLM emits 7 or 11, trim/regenerate in the application layer (Section 7.5) | Shipping raw LLM count |

Whether the canonical `query` may appear inside `query_variations` is **not specified**. Do not fail on inclusion/exclusion until `samples/` decide it. Still count the array length as 8–10.

---

## V-MATCH — no-hallucination / no-match

| ID | Rule | Check | Fail if |
| --- | --- | --- | --- |
| V-MATCH-01 | Empty contexts on no solution | If reference text has no viable solution: `contexts == []` | Invented actions |
| V-MATCH-02 | Fallback key | Empty plan includes fallback metadata `"fallback": "no_match"` (Section 4.2.3) | Empty contexts without that metadata |
| V-MATCH-03 | No hallucinated steps | Every action/step must be grounded in provided SIIS/reference text when `siis_response` was supplied | Steps whose content cannot be aligned to the provided text (programmatic: optional overlap/entailment **only if** samples define a method; otherwise use gold `samples/` exactness) |
| V-MATCH-04 | No hallucinated URIs | V-DL-02 | Invented `bixby://` tokens |
| V-MATCH-05 | `no_siis_context` boundary | Phase 4 requires a graceful fallback named `"no_siis_context"` | Unspecified payload; implement a distinct fallback **string** but do not invent extra fields beyond `fallback` until confirmed |
| V-MATCH-06 | Omitted SIIS | If request has no `siis_response`, do not fabricate article text; use cache lookup (Section 5) | Generating a plan from model memory with cache_hit false and no SIIS **and** non-empty contexts when cache miss has no source — treat as hallucination unless a cached plan is returned |

Grounding (V-MATCH-03) is only strictly programmable against `samples/` gold outputs or a defined overlap metric. The **control-flow** rules V-MATCH-01/02/04 are fully programmable.

---

## V-API — HTTP envelope

| ID | Rule | Check | Fail if |
| --- | --- | --- | --- |
| V-API-01 | Troubleshoot path | `POST /v1/troubleshoot` | Wrong path |
| V-API-02 | Request `query` | Body contains string `query` | Missing |
| V-API-03 | Request `siis_response` optional | Omission is valid | 4xx solely because SIIS omitted |
| V-API-04 | Request SIIS type | If present, string (raw text), not a nested SIIS JSON object (Section 5) | Object/array type |
| V-API-05 | Response wrapper keys | Success body has `query`, `query_variations`, `response`, `meta` (Appendix B) | Missing any |
| V-API-06 | `response.contexts` | `response` matches `ContextDeepLinkResponse` | Goal fields at the wrong nesting |
| V-API-07 | `meta.latency_ms` | Number (example: 212) | Missing/non-numeric |
| V-API-08 | `meta.cache_hit` | Boolean | Missing/non-boolean |
| V-API-09 | `meta.model` | String (example: `gpt-4o-mini`); on cache hit may still be present | Missing in success example shape |
| V-API-10 | `meta.cost_usd` | Number; **0.0 on cache hit** (Appendix B + Appendix C cache-hit cost $0.00) | Cache hit with non-zero cost |
| V-API-11 | Health path | `GET /health` | — |
| V-API-12 | Health body | HTTP 200 and `{"status": "ok"}` | Other shape |
| V-API-13 | Health meaning | 200 only when cache, model connections, **and** vector indexes are initialized | Returning ok while indexes are cold |
| V-API-14 | Completeness | Output includes all actions, steps, associated deeplinks (overview PDF) | Dropping deeplink objects for auto actions |

---

## V-CACHE — cache path (behavioral tests)

| ID | Rule | Check | Fail if |
| --- | --- | --- | --- |
| V-CACHE-01 | Hit skips LLM | `cache_hit: true` ⇒ no model invocation; `cost_usd == 0` | LLM called on hit |
| V-CACHE-02 | Hit latency | P95 ≤ 300 ms for exact match **and** unseen paraphrase hits (Section 6, Appendix C) | P95 > 300 ms |
| V-CACHE-03 | Miss writes after validation | On miss: run pipeline [0]–[2], **schema-validate**, then write cache (Section 2) | Writing unvalidated JSON |
| V-CACHE-04 | Semantic key | Cache key is semantic, not raw query string (Section 7.1) | Only exact-string map (must still **also** hit paraphrases ≥ 80%) |
| V-CACHE-05 | Paraphrase hit rate | ≥ 80% hits on unseen paraphrases (Section 6.2 / Appendix C) | Metric below target |
| V-CACHE-06 | Determinism | Identical or semantically identical inputs → consistent action plans (Section 6.1) | Divergent action lists on repeat of the same cache key |
| V-CACHE-07 | Pre-warm | Omitted SIIS uses pre-warmed cache (Section 5) | Cold LLM path required for every canonical query that should already be cached |

---

## V-LAT — latency / cost accounting

| ID | Rule | Check | Fail if |
| --- | --- | --- | --- |
| V-LAT-01 | `latency_ms` reflects real elapsed time | Compare to measured server time | Hard-coded constant |
| V-LAT-02 | Cold P95 | ≤ 8000 ms (Appendix C) / ≤ 8 s (Section 6) | P95 above |
| V-LAT-03 | Cost formula | `(prompt tokens + completion tokens) × rate` (Appendix C) | Unrelated number |
| V-LAT-04 | Cache hit cost | $0.00 | Non-zero |

---

## V-DATA — starter dataset integrity (once files exist)

| ID | Rule | Check | Fail if |
| --- | --- | --- | --- |
| V-DATA-01 | `queries.json` domains | Queries span only the four named domains: Battery, Display, Camera, Performance | Extra domain labels **if** the file contains a domain field; if it does not, do not invent a domain field |
| V-DATA-02 | `siis_responses.json` cleanliness | No web URLs; no images (Section 3) | V-LEAK or image URLs/data URIs |
| V-DATA-03 | `deeplinks.json` size | Catalogue of **~575** masked Settings deeplinks | Order-of-magnitude mismatch after counting URI records |
| V-DATA-04 | Catalogue URI pattern | Entries use `bixby://masked/act/...` | Other pattern (except documenting dummy if it appears) |
| V-DATA-05 | Catalogue metadata | Records include descriptive strings named `description`, `message`, `qna_description` (Section 3) | Those names absent **after the file is inspected** |
| V-DATA-06 | `samples/` count | **Five** complete input-output pairs | Not five |
| V-DATA-07 | Samples validate | Each sample **output** passes this entire rule set | Official sample would fail our validator — stop and reconcile; do not “fix” gold |
| V-DATA-08 | `schema.py` identity | On-disk `schema.py` matches Appendix A | Drift |

Do not add uniqueness/join rules between queries and SIIS until the files show the keys.

---

## V-RETR — retrieval implementation checks

| ID | Rule | Check | Fail if |
| --- | --- | --- | --- |
| V-RETR-01 | Dual index | Deeplink index uses BM25 **and** dense embeddings (Section 8 Phase 2) | Single-method only when claiming spec compliance |
| V-RETR-02 | Metadata fields | Index documents `description`, `message`, `qna_description` | Indexing only the URI |
| V-RETR-03 | Masked URI not used as lexical query target | Section 7.4 | Matching `bixby://masked/act/` tokens as text queries |

---

## Ordering of validators (recommended)

```
V-JSON → V-API (envelope) → V-SCHEMA → V-GOAL → V-TITLE → V-DESC → V-ANAME
  → V-STEPS → V-SCREEN → V-CAT → V-ORDER → V-SCORE
  → V-LEAK → V-DL → V-QVAR → V-MATCH → V-CACHE/V-LAT (runtime)
```

On no-match outputs, skip field syntax on actions (there are none); still run V-JSON, V-SCHEMA (empty list), V-MATCH-01/02, V-API, V-LEAK on remaining strings (`query`, `query_variations`, `meta`).

---

## Gaps (not programmable until the official spec/files resolve them)

These are **not** rules to implement as if they were decided:

- Exact JSON schemas of `queries.json` / `siis_responses.json` / `deeplinks.json`
- Word-tokenization definition
- Where `fallback` sits (`meta.fallback` vs top-level)
- JSON value for `"no_siis_context"`
- Whether `query` is a required request field in a schema (only shown in the example)
- Full ranking function among multiple `auto` actions
- Gold alignment algorithm for “derived purely from reference text”
- Whether dummy_positive appears inside `deeplinks.json` or only as a reserved constant
- Hyphen/`and` policy for Title Case and sentence case

When `samples/` and the three JSON files are added, extend this list with **file-derived** checks only.
