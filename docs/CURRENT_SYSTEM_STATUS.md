# Current System Status

> Status: CANONICAL
> Applies to: V2
> V2-3 starting baseline: `0c597dd51ac577dd5d1b35fe90c0bc5a9a2495ca`
> V2-5A design starting baseline: `90dbb484e2aa01b8dab7b3872723cd1f251eb5cf`
> V2-6A design starting baseline: `696bf4178cbc018fca6d257ba156ec6f3a33fc1e`
> V2-7A audit starting baseline: `5a8368fcb8b46fed9f5cb2714a32df52c0f377d0`
> Owner: Project

> **ACTIVE DEVELOPMENT OVERLAY — 2026-09-20**  
> The detailed sections below preserve accepted V2-3～V2-9 historical baselines and therefore contain older schema/count snapshots. For current B3/B4/B5 development, [AI_HANDOFF_V2.md](AI_HANDOFF_V2.md) and current code/config supersede those old counts.

Current active facts:

```text
branch                    = ux-redesign-v1
accepted runtime baseline = a1fcbc9f1f8e44a8954e29cafe06a06e15d93835
SQLite schema             = 14
Claim taxonomy            = 7 types / 42 exact expressions
Claim Inspection Bridge   = claim-inspection-bridge-v2.6 / 25 mappings
Risk Reference            = 2026.09-c7 / 83 mappings
                            13 current + 70 historical
Inspection Reference      = 2026.09-b11 / 11 methods
                            10 current recommendation_ready
                            1 revoked reference_only
                            219 Substance / 263 MethodSubstance
                            61 MethodApplicability / 9 RegulatoryDocument
Method candidate manifest = 2026.09-b17 / 12 records
                            6 promoted traces + 6 verification
active program            = B5
```

Current B5 state:

- KJ201901 / KJ201902, BJS201808 and BJS201901 are already promoted; do not repeat them.
- BJS201901 official legacy DOC is reproducibly parsed with `antiword`; B5-8B is accepted at `inspection-reference@2026.09-b11`.
- BJS201901 added 14 Method-only canonical Substance identities, reused 13 existing identities, added 27 MethodSubstance and 8 conservative MethodApplicability; it added **zero** Risk mappings.
- Source `格列本脲 / 10238-21-8` is normalized to canonical `格列苯脲 / 10238-21-8`; `吡格列酮 / 111025-46-8` is a direct existing canonical match.
- BJS202504 / BJS202501 / BJS202601 / BJS202602 remain deferred at `verification/reference_only`.
- BJS202409 B5-9A/B is **DEFERRED / RUNTIME UNCHANGED**: official identity/current page is verified, but stable official Method body/attachment provenance remains unavailable; third-party PDFs remain cross-check only.
- Immediate next subtask is **B5-10A BJS202502 deep verification**, preserving Method→Risk separation.


This document preserves the accepted historical V2 baseline. The active B3/B4/B5 development overlay above and `AI_HANDOFF_V2.md` supersede older counts and phase-next markers elsewhere in this file.

## Baseline

- Branch: `ux-redesign-v1`
- V2-3 starting HEAD: `0c597dd51ac577dd5d1b35fe90c0bc5a9a2495ca`
- SQLite schema: 14
- Backend entry: `python -m src.local_api`
- Production static UI: `frontend/dist`, built from `frontend/`
- Current primary navigation: 商品总览、排查档案、抽检清单、知识库
- Retired V1 `web/` frontend: absent from the active workspace

## Current runtime

The React/Vite frontend calls a local `ThreadingHTTPServer`. `TaskManager` starts `StandalonePipeline`, which performs Search/Discovery, Detail collection, OCR, Phase3 analysis, and Inspection Recommendation. Run artifacts are written under `output/<run_id>/`; `DataStore` imports queryable run facts into SQLite and supports Review and Sampling workflows.

Playwright uses a visible Chrome/CDP session. `ManualActionGate` lets a web task wait for login or verification while the worker retains browser ownership; the HTTP thread only acknowledges user action. CLI execution without a web adapter retains the terminal fallback.

## Pipeline readiness

The shared backend predicate currently projects:

```text
DetailCollected
→ OcrInputReady
→ OcrReady
→ AnalysisReady
→ RecommendationAvailable (degradable)
→ ReviewEligible
```

`ReviewEligible` is driven by successful Phase3 analysis. Recommendation generation is degradable: a Recommendation error does not invalidate Evidence or prevent Review. Search-only, Detail-failed, and OCR-failed snapshots are retained as facts but are not business-pending Reviews.

Task flow states are `future`, `active`, `done`, `partial`, and `failed`, derived from stage facts and counts rather than from terminal task stage alone.

## Current data and workflow

- One stable Product may have multiple ProductSnapshots.
- Evidence remains snapshot-scoped and preserves seller-managed, UGC, and excluded-other-product origins.
- ProductFact is Snapshot-scoped. Its authority is `product_facts.json`; SQLite is a rebuildable query projection. V2-2 implements only `declared_origin`.
- HealthFoodIdentity is a separate Snapshot-scoped enrichment. Its authority is `health_food_identity.json`; SQLite indexes the identity assessment and reusable normalized official record. Page clue, identifier candidate, official record and verified current-product match are never collapsed into one boolean.
- Review is Snapshot-scoped with `pending`, `recommend_follow_up`, and `no_further_action`.
- Current Sampling Membership is Product-scoped and records its source Snapshot.
- Review and Sampling repositories do not mutate each other. Application-level decision transactions coordinate compound business actions.
- A pending Snapshot may coexist with a Product membership based on another Snapshot.
- Frozen Sampling Lists and their item indexes preserve historical export facts.
- V2-5 implements Snapshot-scoped ClaimMention and ClaimSignal records from seller-managed Evidence only. `claim_analysis.json` is the derived authority; the Claim tables introduced in schema 11 remain rebuildable projections in current schema 13. Snapshot Detail exposes full Mentions/Signals; Product/Queue list DTOs expose batched same-Snapshot summaries and an exact governed Claim filter.
- `claim-taxonomy-v2.0` remains the sole governed runtime taxonomy with 5 Claim types and 26 exact expressions. ClaimSignal is not an Official Health Function, RiskSignal, legality conclusion, substance, method, or Recommendation trigger. UGC and `excluded_other_product` Evidence cannot create formal Claims; SearchQuery/task keywords are not Claim input.
- V2-6B1 implements the Snapshot-scoped, degradable `claim_consistency.json` authority. It compares only a verified HealthFoodIdentity's persisted Registry functions with formal V2 ClaimSignals through exact governed HealthFunction resolution and the four `topic_related` mappings. The assessment/function/per-Claim projections introduced in schema 12 remain rebuildable in current schema 13; Snapshot Detail/workspace expose additive status and assessment DTOs. The runtime does not perform a live Registry lookup and does not change Risk, Recommendation, Review eligibility/status, or Sampling.
- V2-7 separates the seven-method Wide Reference Index from its six-method Recommendation-ready subset. `knowledge_depth` is persisted independently of lifecycle, every indexed method links to a normalized RegulatoryDocument, explicit group membership has a governed zero-row contract, and operational resolution is restricted to current `recommendation_ready` methods. The non-runtime candidate manifest records two completed b7 promotion traces; current facts enter SQLite only through `inspection-reference@2026.09-b8` and are counted once. BJS 202405 is now deep-verified for 95 explicit analytes and seven official source scopes; revoked GB/T 5009.170-2003 remains `reference_only`.

## Current product-reading UX

- Product Overview derives a local saved-asset thumbnail URL for each representative Snapshot. Missing or unreadable assets fall back to one consistent placeholder; no remote marketplace image is required.
- Every Product row is a pointer-accessible and keyboard-accessible detail target while preserving independent-control boundaries.
- Product Detail and Inspection Workspace share a Snapshot summary for page clues, seller/UGC Evidence counts, knowledge-bridge state, and Review state.
- A single Snapshot uses a compact timestamp/source row; two or more Snapshots use the selectable timeline.
- Evidence records remain unchanged as facts. The React presentation groups them by `content_origin`, `source_type`, and source asset/context, collapses repeated snippets for reading, and retains all Evidence IDs in the group model.
- Seller-managed Evidence is primary, UGC is explicitly auxiliary, and excluded-other-product content is outside the primary counts.
- Saved images and OCR text open in an in-application modal. Image preview supports close/escape/backdrop, previous/next, zoom, viewport containment, and the Evidence associated with the active image.
- Analysis presentation distinguishes not analyzed, analyzed with zero Evidence, Evidence without a verified mapping, mapped Risk without a verified Method, available Recommendation, unavailable Recommendation, and Recommendation error.
- 页面宣传线索 is the primary Claim presentation in Product Overview, Product Detail, Review Queue, Inspection Workspace, and current Sampling. Complete-with-Claims, complete-zero, not-generated, and error remain distinct; ClaimMention expansion shows original text, the exact expression, friendly source type, and existing Evidence trace.
- Legacy Effect badges/keywords are hidden from the active primary Claim UX. Frozen Sampling history is unchanged and, when shown, is explicitly labeled 旧版冻结分析结果 rather than V2 Claim.
- Search-page region and product-declared origin are independent keys. Explicit seller-managed DOM parameters and conservatively labeled detail-image OCR may supply `declared_origin`; search region, title wording, UGC, shipping, seller/manufacturer/warehouse addresses and raw-material origin never do.
- Product Detail and Inspection Workspace expose a separate 保健食品身份 section. Only a valid unambiguous identifier, a found official record, and formatting-normalized exact equality with an explicit page product name can display `保健食品 · 已核验`. Page and official sources remain separate; candidates, unavailable lookup, not-found, mismatch and conflict remain explicit.
- Product Detail and Inspection Workspace share the same 保健功能一致性 section after 页面宣传线索 and before legacy Risk/Recommendation. Operational and domain states remain separate; raw and normalized official functions are both auditable; per-Claim topic relations use informational, attention, or neutral presentation without a total verdict. Page trace returns to the existing Claim/Evidence section, while official trace reuses the existing Registry source modal.
- A missing declared origin is `—`. Equal DOM/OCR values retain both sources under one presentation value; different explicit values are displayed as a conflict without automatic arbitration.
- Origin source trace opens the exact DOM/OCR text and reuses the existing image Lightbox for OCR image provenance.

## Current OCR environment

The reproducible supported baseline is:

- Python 3.10.0 (Python 3.10.x runtime family)
- PaddlePaddle 3.2.0
- PaddleOCR 3.7.0
- PaddleX 3.7.2
- PP-OCRv6, BOS model source, CPU

OCR writes versioned run diagnostics. No input image and zero successful images are stage failures; partial image success may continue with failed items preserved in the manifest.

## Current governed coverage

Counts below are computed from the governed configuration at the verified commit:

| Area | Current coverage |
|---|---:|
| Official Reference MonitorTargets | 106 / 106 |
| Reference targets with any governed Query | 18 |
| Operational Reference targets | 16 / 106 |
| Enabled / validated Reference queries | 19 / 19 |
| Candidate, disabled Reference queries | 0 |
| Rejected, disabled Reference queries | 1 |
| Paused Reference targets | 2 |
| Separate development-seed targets/queries | 1 / 2 |
| Legacy/current Phase3 clue categories/keywords | 5 / 26 |
| V2 Claim runtime types/expressions | 5 / 26 |
| Official HealthFunction frameworks | 2 |
| 2023 non-nutrient HealthFunctions | 24 / 24 |
| Official transition aliases | 40 |
| Claim→HealthFunction topic mappings / explicit Claim gaps | 4 / 1 |
| Evidence-to-risk Bridge mappings | 3 |
| Risk-to-substance / Risk-to-group mappings | 5 / 3 |
| Inspection methods | 7 |
| Pending / promoted inspection-method candidate traces | 0 / 2 |
| Recommendation-ready inspection methods | 5 / 7 indexed methods |
| Regulatory documents / linked methods | 7 / 7 |
| Inspection substances | 117 |
| Method-substance links | 132 |
| Method applicability records | 37 |
| Substance regulatory contexts | 1 |
| Recommendation structural reachability | 5 / 5 explicit Risk→Substance mappings |
| Recommendation end-to-end reachability | 3 / 5 explicit mappings; 2 / 3 Risk categories |
| Governed group resolution | 0 / 3 group mappings |
| Governed group-membership records | 0 |

The 106-object Reference is not 106-object operational search coverage. Only a target enabled with at least one enabled `search_validated` Query is operational. V2-4 Wave 1 promoted the standard-name Queries for 山楂、沙棘、罗汉果、黑芝麻、蜂蜜. Wave 2A promoted 山药、赤小豆、枸杞子、莲子. Wave 2B promoted 菊花 and rejected the standard-name 百合 Query after its observed relevance was 50%. The independently reviewed `食用百合` refinement retained `manually_curated` provenance, achieved 90% observed relevance, and is now the only executable strategy for the operational 百合 MonitorTarget; the rejected naked `百合` Query remains disabled. 乌梅 remains disabled `paused_scope_issue` because human review confirmed stable medicinal-material/medicinal-use scope mixing; 当归 remains paused for its earlier recorded scope issue. The separate development seed is not merged into the verified Reference count.

## Current validation support

- Historical Validation Set: five real sample products under `historical_validation_20260911`, intended for deterministic test/demo support without live collection.
- Its scope is described in `HISTORICAL_VALIDATION_CANDIDATES.md`; it is not representative production coverage.
- V2-0B validation: Python 397 discovered / 396 passed / 1 skipped; Historical Validation builder 6/6; frontend workflow 12/12; frontend typecheck and production build passed.
- V2-1 validation: affected Python suites 40 discovered / 39 passed / 1 skipped; frontend workflow 18/18; frontend typecheck and production build passed. The five-product historical set was inspected at 1440px and 1080px with no page-level horizontal overflow or browser console error.
- V2-2 validation: Python 414 discovered / 413 passed / 1 skipped; frontend workflow 19/19; frontend typecheck and production build passed. Deterministic A–L origin fixtures, schema 8→9 preservation, import/rebuild/API tests, and offline extraction against the same five-product historical set produced six source records, including one explicit conflict. The Product Detail source trace was inspected at 1440px and 1080px with no page-level horizontal overflow or browser console error.
- V2-3 source support is documented in [HEALTH_FOOD_REGISTRY_SOURCE_AUDIT.md](HEALTH_FOOD_REGISTRY_SOURCE_AUDIT.md). Ordinary tests use a governed recorded official response; live official lookup is best-effort and never a CI dependency.
- The five-product Historical Validation Set contains no valid registration/filing identifier and no positive strong identity candidate. Product `674221193698` has an explicit negative `是否保健食品…否` parameter and remains `no_indicator`; the other four also remain `no_indicator`. No historical artifact was edited or re-OCRed.
- V2-3 validation: Python 441 discovered / 440 passed / 1 skipped; Historical Validation builder 6/6; frontend workflow 22/22; frontend typecheck and production build passed. Identifier, provider, matching, degradation, schema 9→10 and artifact rebuild contracts are covered. Product Detail plus page/official evidence dialogs were inspected locally at 1440px and 1080px without page-level horizontal overflow or new browser console errors.
- V2-4A established full Reference visibility, three-state availability, strict Query lifecycle/execution guards, a tracked validation ledger, and a search-only batch artifact contract. V2-4 Wave 1 completed six standard-name Query reviews: five were promoted and 乌梅 was held. Wave 2A promoted 山药、赤小豆、枸杞子、莲子. Wave 2B promoted 菊花 and rejected only the standard-name 百合 search strategy, not its MonitorTarget. The immutable result records are [Batch 01A](MONITOR_QUERY_VALIDATION_RESULTS_V2_4_BATCH_01A.md), [Batch 02A](MONITOR_QUERY_VALIDATION_RESULTS_V2_4_BATCH_02A.md), and [Batch 02B](MONITOR_QUERY_VALIDATION_RESULTS_V2_4_BATCH_02B.md).
- V2-4A validation: Python 452 discovered / 451 passed / 1 skipped; Historical Validation builder 6/6; frontend workflow 24/24; frontend typecheck and production build passed. The new task picker was inspected locally at 1440px and 1080px with all 106 options, no horizontal overflow, correct operational/pending/paused behavior, and no new browser console warnings/errors.
- V2-4B2 validation: Python 459 discovered / 458 passed / 1 skipped; targeted Monitor review/governance tests 45/45; Historical Validation builder 6/6; frontend workflow 24/24; frontend typecheck and production build passed. Offline local UI acceptance confirmed the five promoted Targets are searchable and runnable, while 乌梅 remains visible as `暂缓` with its action disabled and the scope-mixing reason shown.
- V2-4B4 validation: Python 460 discovered / 459 passed / 1 skipped; targeted Monitor review/governance tests 46/46; Historical Validation builder 6/6; frontend workflow 24/24; frontend typecheck and production build passed. Offline local UI acceptance confirmed 山药、赤小豆、枸杞子、莲子 each expose only the promoted standard-name Query and are runnable; 乌梅 remains disabled as `暂缓`, while 百合、菊花 remain disabled in the `待验证` state. No live collection or external network access was used.
- V2-4B6 validation: PART A targeted Monitor governance tests 47/47; final Monitor/Query regression 56/56; Python 461 discovered / 460 passed / 1 skipped; frontend workflow 24/24; frontend typecheck and production build passed. Batch `v2-4b-batch-02c` collected 15 unique `食用百合` Search Result cards with every human-review and decision field still empty. No Detail or downstream processing ran.
- V2-4 exit validation: Batch `v2-4b-batch-02c` human review skipped ambiguous Rank 8 and used Rank 11, producing 10 assessable / 9 relevant / 1 raw-scope / 90% observed relevance and `promote`. The immutable result is [Batch 02C](MONITOR_QUERY_VALIDATION_RESULTS_V2_4_BATCH_02C.md). Targeted Monitor/query/task regression passed 74/74; Historical Validation builder passed 6/6; Python full regression discovered 462 / passed 461 / skipped 1; frontend workflow passed 26/26; typecheck and production build passed. All B7 validation was offline; no Detail or downstream processing ran.
- V2-5A Claim Taxonomy & Domain Contract is **DESIGN BASELINE / COMPLETE**. The machine-readable `claim-taxonomy-v2.0` covers every one of the 26 current legacy expressions exactly once across five marketing topics, with no taxonomy gap and no HealthFunction/Risk/inspection mapping. Claim taxonomy tests passed 14/14; Monitor regression passed 74/74; Python full regression discovered 476 / passed 475 / skipped 1; frontend workflow passed 26/26; typecheck and production build passed. Validation was fully offline and schema remains 10.
- V2-5B1 ClaimMention / ClaimSignal runtime core is **COMPLETE**. Deterministic seller-managed extraction, UGC/excluded-source blocking, zero/not-generated/error artifact semantics, schema 10→11 preservation and rebuild, additive Snapshot API projection, and legacy Effect/Risk/Recommendation/Review/Sampling compatibility are covered. Python full regression discovered 496 / passed 495 / skipped 1; frontend workflow passed 26/26; typecheck and production build passed. Validation was fully offline with no Detail, OCR or external network execution.
- V2-5B2 Claim UX and legacy presentation migration is **COMPLETE**. Primary active-Snapshot surfaces use V2 Claim projections; Product list filtering is exact and same-Snapshot; ClaimMention source drill-down reuses Evidence; current Sampling and frozen legacy history stay distinct. Python full regression discovered 500 / passed 499 / skipped 1; frontend workflow passed 30/30; typecheck and production build passed. No taxonomy, schema, Risk/Recommendation, Review/Sampling business state, frozen export, Detail/OCR, or external network behavior changed.
- V2-6A HealthFunction Framework & Claim Consistency Contract is **DESIGN BASELINE / COMPLETE**. `health-functions-v2.0` records two separate official frameworks, the complete 24/24 non-nutrient catalog, and 40 source-backed transition aliases. `claim-health-function-mapping-v2.0` records four `topic_related` mappings and the explicit `male_function_related` gap. Exact Registry normalization and a non-adjudicative A–L assessment contract are covered by 17/17 deterministic governance tests. Python full regression discovered 517 / passed 516 / skipped 1; frontend workflow passed 30/30; typecheck and production build passed. No production runtime, schema, API, frontend, Claim taxonomy, Risk/Recommendation, Review/Sampling, or frozen-history behavior changed.
- V2-6B1 Claim Consistency Runtime Core is **COMPLETE**. The independent runtime validates both governed datasets, resolves Registry strings only by exact current names or exact official transition aliases, preserves unresolved raw strings, enforces the frozen state precedence and conservative partial-resolution relations, and writes a degradable Snapshot sidecar. Schema 11→12 migration, transactional artifact rebuild, invalid-artifact clearing, additive Snapshot API/TypeScript contracts, A–L cases, API states and cross-domain independence are covered offline. Targeted cross-domain regression passed 187/187; Python full regression discovered 532 / passed 531 / skipped 1; frontend workflow passed 30/30; typecheck and production build passed. No visible consistency UI, Attention classification, Claim→Risk/Recommendation bridge, live provider request, Detail or OCR execution was added.
- V2-6B2 Claim Consistency UX and the V2-6 Exit Gate are **COMPLETE**. Product Detail and Inspection Workspace reuse one Snapshot-scoped presentation component across all operational/domain states and all four per-Claim relations. Page/official source controls reuse existing trace surfaces; unresolved negatives remain protected from false `not recorded` presentation; ClaimExpressionAttention remains an explicit manual-governance gap. Targeted cross-domain regression passed 124/124; Python full regression discovered 532 / passed 531 / skipped 1; frontend workflow passed 38/38; typecheck and production build passed. Offline UI acceptance covered 1440px and 1080px with no page-level horizontal overflow. Schema 12, runtime, governed datasets, Risk/Recommendation, Review/Sampling, and frozen history are unchanged.
- V2-7A Inspection Knowledge Inventory & Coverage Contract is **AUDIT / DESIGN BASELINE / COMPLETE**. The deterministic offline audit separates the five-method Wide Reference Index from the Deep Verified Subset, freezes lifecycle/depth and group boundaries, reports versioned denominator-defined reachability, and records two first-party candidate work items without promoting them. The current five methods pass the static deep gate for their explicit relations; three group mappings remain unresolved. Audit/governance tests passed 9/9; Inspection/Risk/Recommendation targeted regression passed 210/210; Claim/Consistency passed 49/49; Review/Sampling passed 30/30; Monitor/Discovery/Task passed 39/39; Python full regression discovered 541 / passed 540 / skipped 1; frontend workflow passed 38/38; typecheck and production build passed. Schema 12, API, frontend, governed knowledge records, Phase3, D2–D6 and Recommendation output are unchanged.
- V2-7B1 Inspection Reference Index Infrastructure & Recommendation Boundary is **COMPLETE**. Schema 12→13 adds conservative depth storage, normalized RegulatoryDocument rows and explicit group-membership storage; `inspection-reference@2026.09-b6` declares all five existing methods `recommendation_ready`, while two candidate records stay in a validated non-runtime manifest. The production resolver admits only current `recommendation_ready` methods. Existing method/analyte/applicability and Risk/bridge semantics, API/frontend behavior, Phase3, D2–D6 and Recommendation output remain unchanged.
- V2-7B1 validation: focused Inspection/Reference/Risk/Recommendation regression passed 193/193; Python full regression discovered 552 / passed 551 / skipped 1; frontend workflow passed 38/38; typecheck and production build passed. The audit is deterministic and offline; no official-site retrieval, Taobao, Detail, OCR, historical rewrite or candidate promotion occurred.
- V2-7B2 Bounded Official Method Verification & Promotion is **COMPLETE**. First-party records verify BJS 202405 as current `食品中西地那非、他达拉非等化合物的测定` and GB/T 5009.170-2003 as the revoked predecessor `保健食品中褪黑素含量的测定`, fully replaced by GB/T 45443-2025. Both are indexed only at `reference_only`; the former BJS `weight_loss`/sibutramine planning association is explicitly invalidated. The index is 7/7 reference-complete and 5/7 deep; the predecessor lifecycle edge is closed. Analytes, applicability, Risk/group mappings, group membership, bridge, Phase3, D2–D6, Recommendation output, schema/API/frontend and frozen history are unchanged. Targeted Inspection/Reference/Risk/Recommendation regression passed 223/223 offline.
- V2-7C Deep Verified Subset & Exit Gate is **COMPLETE**. `inspection-reference@2026.09-b8` promotes only BJS 202405 to `recommendation_ready` using the official SAMR full text: 95 Appendix A compounds, seven product categories, and retained qualitative/quantitative and sample-preparation context. Eleven Substance identities are reused by CAS and 84 are added. A versioned six-case Product Context corpus passes all expectations and reports context-corpus Recommendation reachability as 3/6; the metric is fixture-scoped, not population coverage. Risk/Claim/group mappings, group membership, existing five deep methods, the Recommendation algorithm, schema/API/frontend, Phase3, D2–D6, Review/Sampling and frozen history are unchanged. Focused regression passed 195/195; Python full regression discovered 555 / passed 554 / skipped 1; frontend workflow passed 38/38; typecheck and production build passed offline.
- V2-7 is **COMPLETE**. The final bounded index is 7/7 reference-complete and 6/7 deep, with 201 Substances, 227 MethodSubstance relations, 44 applicability facts and 0/3 resolved group mappings. Only revoked GB/T 5009.170-2003 remains `reference_only`.
- V2-8A Knowledge Read API & UX Contract is **COMPLETE**. Seven GET-only endpoints expose separate summary, Monitor Reference, HealthFunction, Substance, Risk mapping, InspectionMethod and RegulatoryDocument read models with deterministic query/filter/offset/limit handling, source/version trace and explicit Knowledge Gaps. Monitor/Inspection/Risk records read the same schema-13 projections used by runtime; HealthFunction reads the same strictly validated governed JSON used by Claim Consistency. Frontend DTO/client/domain-mapper contracts exist, but Sidebar, routing, page and tabs do not. Targeted backend/domain/API regression passed 168/168 and frontend typecheck passed. Schema 13, governed knowledge, Discovery, Claim, identity/consistency, Risk, Recommendation, Review, Sampling and frozen history are unchanged.
- V2-8B Knowledge Base UI & V2-8 Exit Gate is **COMPLETE**. `#/knowledge` is a first-level read-only route with the six canonical API-backed tabs, separate summary facts, server search/filter/offset pagination, URL state, explicit loading/empty/error/content states and a focus-managed detail Drawer. Availability, lifecycle, project knowledge depth, Knowledge Gaps and source/version provenance remain separate. Targeted Knowledge regression passed 168/168; Python full regression discovered 564 / passed 563 / skipped 1; frontend workflow passed 43/43; typecheck and production build passed. Offline 1440px/1080px checks found no page-level horizontal overflow. Schema 13, governed knowledge and every existing business workflow remain unchanged.
- V2-8 is **COMPLETE**.
- V2-9A Analytics Metric Dictionary & Read Model is **COMPLETE**. `analytics-metrics-v2.0` governs 32 count/ratio/distribution/coverage metrics across pipeline, formal Claim, geography and knowledge domains plus four explicit unavailable/future metrics. Six GET-only endpoints expose denominator-defined values, zero-denominator nulls, grain/time/dedup/missing rules, applied filters and dataset versions. Runtime metrics use Task-created cohorts; V2 formal Claim never falls back to legacy Effect/UGC; search region and declared origin remain separate; Knowledge metrics reuse V2-7 audit and V2-8 summary calculations. The current local baseline is byte-for-byte deterministic across two reads. Targeted Analytics tests passed 9/9 and frontend typecheck passed. Schema 13, business facts, configs other than the new metric authority, runtime workflows and visible navigation are unchanged.
- V2-9 is **IN PROGRESS**; V2-9B visible Analytics UI and Exit Gate are not implemented.

## Known limitations and future changes

The following are **not implemented** at this baseline:

- **NEXT:** V2-9B Analytics UI & V2-9 Exit Gate, subject to its own Gate.
- **FUTURE CHANGE:** the separately governed ClaimExpressionAttention dataset. Claim→Risk mapping remains outside V2-6 and is not implied by the implemented topic comparison.
- **FUTURE CHANGE:** the visible Analytics navigation/page/charts. The governed Metric Dictionary, deterministic read model and GET contract are implemented by V2-9A.
- Current Phase3 and Recommendation compatibility paths still use `config/effect_keywords.json`, legacy `detectedEffects`/`effect` fields, and the separately governed three-record Effect/Risk bridge. UGC may therefore still influence the legacy Effect path and downstream auxiliary legacy interpretation. The V2 Claim runtime does not consume those Effect conclusions, blocks UGC formally, and does not rewrite legacy Evidence or frozen exports.
- The existing recorded HealthFood Registry positive uses a descriptive official-function sentence that is not an exact current name or transition alias; future normalization must preserve it as unresolved unless a separate source-backed mapping is governed.

The five existing Effect categories are an operational Phase3 clue vocabulary, not the final V2 Claim taxonomy.

## Canonical references

- Product boundaries: [PRODUCT_REQUIREMENTS_V2.md](PRODUCT_REQUIREMENTS_V2.md)
- Current/target architecture: [SYSTEM_V2_ARCHITECTURE.md](SYSTEM_V2_ARCHITECTURE.md)
- Domain model: [DOMAIN_MODEL_V2.md](DOMAIN_MODEL_V2.md)
- HealthFunction framework: [HEALTH_FUNCTION_FRAMEWORK_V2.md](HEALTH_FUNCTION_FRAMEWORK_V2.md)
- Claim consistency contract: [CLAIM_CONSISTENCY_V2.md](CLAIM_CONSISTENCY_V2.md)
- Inspection knowledge audit: [INSPECTION_KNOWLEDGE_AUDIT_V2_7.md](INSPECTION_KNOWLEDGE_AUDIT_V2_7.md)
- Inspection coverage contract: [INSPECTION_KNOWLEDGE_COVERAGE_V2.md](INSPECTION_KNOWLEDGE_COVERAGE_V2.md)
- Knowledge Base UI contract: [KNOWLEDGE_BASE_UI_V2.md](KNOWLEDGE_BASE_UI_V2.md)
- Analytics metric/read contract: [ANALYTICS_V2.md](ANALYTICS_V2.md)
- Roadmap: [IMPLEMENTATION_ROADMAP_V2.md](IMPLEMENTATION_ROADMAP_V2.md)
