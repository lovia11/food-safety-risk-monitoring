# Implementation Roadmap V2

> Status: CANONICAL
> Applies to: V2
> V2-1 implementation baseline: `a5be2ed9ff07ddc9b347812f281d9d9e638fc6c6`
> Last verified phase: V2-8B
> Owner: Project

Each phase is an independent gate. Completing one phase does not authorize the next. “Schema impact” describes expected design work, not a migration approved by this document.

## V2-0 — Canonical baseline

- **Goal:** Establish one repository-contained product, architecture, domain, UX, knowledge, testing, and decision baseline.
- **Why:** Remove dependence on chat history and contradictory V1 handoffs.
- **Dependencies:** Stabilized schema 8 and V1 UX implementation.
- **In Scope:** Canonical docs, ADRs, README/status rewrite, legacy-doc archival, cold-start and consistency checks.
- **Out of Scope:** Runtime, schema, API, knowledge, and UI behavior changes.
- **Domain impact:** Freezes names, scopes, invariants, and current/future boundaries.
- **Schema impact:** None.
- **Data requirements:** Inspect current governed config and validation metadata without modifying artifacts.
- **UX impact:** Documentation only.
- **Testing:** Link/terminology checks plus existing Python/frontend regression suites.
- **Real-world validation:** None; reuse recorded validation results only.
- **Exit criteria:** A fresh agent answers the canonical cold-start questions correctly; current and future claims are unambiguous.

## V2-1 — Core UX

- **Status:** COMPLETE — implemented and validated against the five-product Historical Validation Set without live collection.

- **Goal:** Improve the product-reading workspace without changing business semantics.
- **Why:** Analysts need faster source-oriented scanning and fewer repetitive evidence cards.
- **Dependencies:** V2-0 and current workspace DTO contracts.
- **In Scope:** 48–56px thumbnail, row click, Product Detail summary, Evidence Source Group presentation, lightbox, compressed one-Snapshot timeline, and explicit knowledge states.
- **Out of Scope:** ProductFact extraction, health-food verification, new mappings, analytics, and Knowledge Base navigation.
- **Domain impact:** No new business entities; presentation grouping must retain individual Evidence records.
- **Schema impact:** None expected; stop for design if current contracts cannot supply source grouping safely.
- **Data requirements:** Existing real/historical Snapshot assets, including missing-image and multi-hit cases.
- **UX impact:** Product Overview and Product Detail only; retain current IA.
- **Testing:** Workflow, typecheck, build, keyboard/lightbox behavior, 1440/1080, long title, missing image, zero/unmapped Evidence, recommendation error, historical Snapshot.
- **Real-world validation:** Inspect approved historical real products; live collection only under separate approval.
- **Exit criteria:** All required states are distinguishable and traceable with no fabricated data or duplicated Evidence-source cards.
- **Implemented result:** Local derived thumbnails, whole-row keyboard navigation, Snapshot summary, compact single-Snapshot presentation, source-oriented Evidence grouping, in-app image/OCR viewers, explicit analysis/knowledge states, and independent region/origin presentation are present. Evidence identities, Review/Sampling semantics, schema, pipeline, and governed knowledge are unchanged.

## V2-2 — ProductFact and declared origin

- **Status:** COMPLETE — implemented with schema 8→9 additive migration and validated against deterministic and five-product offline artifacts.

- **Goal:** Introduce provenance-bearing structured facts, starting with explicit product-declared origin.
- **Why:** Current search region cannot answer origin questions and free-form extraction must be auditable.
- **Dependencies:** V2-1 evidence browsing and approved ProductFact contract.
- **In Scope:** ProductFact extraction/storage/API; `declared_origin`; source/conflict/missing/review states; DOM/OCR source support.
- **Out of Scope:** Inferring origin from search region or addresses; broad fact ontology; health-food identity decision.
- **Domain impact:** Adds ProductFact as a Snapshot-scoped derived entity.
- **Schema impact:** Additive schema 8→9 generic `product_facts` table/indexes; schema 8 data, Review/Sampling and re-import behavior are preserved.
- **Data requirements:** Real positive, missing, conflicting DOM/OCR origin fixtures with exact source paths.
- **UX impact:** Independent 搜索页地区 and 商品标称产地 key/value display; missing is `—`.
- **Testing:** Provenance, normalization, conflicts, DOM/OCR sources, missing origin, and explicit non-inference tests.
- **Real-world validation:** Small reviewed product set containing clear, absent, and conflicting origin statements.
- **Exit criteria:** Every stored origin is Snapshot-scoped and source-reconstructable; no false “待采集” value or geographic inference.
- **Implemented result:** Artifact-only extraction writes deterministic, provenance-bearing `product_facts.json`; import builds an idempotent SQLite projection; Workspace DTO/UI exposes none/single/conflict states and DOM/OCR source trace. Extraction failure is degradable and does not alter Analysis/Review eligibility.

## V2-3 — Health-food identity

- **Status:** COMPLETE — implemented with schema 9→10 additive migration, a governed official-source adapter contract, offline official positive fixture and Snapshot workspace UI.

- **Goal:** Resolve health-food identity against authoritative registration/filing records.
- **Why:** Page logos and numbers are clues, not verified identity.
- **Dependencies:** V2-2 provenance model and an approved official-registry acquisition contract.
- **In Scope:** Candidate extraction, official lookup, multi-state resolution, conflict/not-found/unavailable handling, provenance UI.
- **Out of Scope:** Automatic legality judgments, claim consistency, and logo-only confirmation.
- **Domain impact:** Adds HealthFoodIdentity, HealthFoodRegistryRecord, and identity evidence relationships.
- **Schema impact:** Additive identity/registry/read-model changes after review.
- **Data requirements:** Versioned official records plus positive, logo-only, mismatch, not-found, and ambiguous-name fixtures.
- **UX impact:** Identity badge with source and verification state; no boolean shortcut.
- **Testing:** Required identity fixtures, source availability, temporal/version behavior, and path security.
- **Real-world validation:** Manually compare a bounded set against official records.
- **Exit criteria:** Verified identities reproduce the official match; all other cases remain explicit candidate/conflict/not-found/insufficient states.
- **Implemented result:** Seller-managed DOM/OCR candidate extraction, strict current/legacy identifier handling, no OCR character guessing, cached/degradable official provider plus imported-snapshot provider, verbatim official function retention, conservative exact product-name matching, artifact-backed import/rebuild, ten-state API/UI presentation and separate page/official source traces. Claim consistency remains out of scope.

## V2-4 — Monitor coverage

**Status:** COMPLETE — full Reference visibility, governed Query lifecycle, bounded human-reviewed validation, and promote/hold/reject/refine paths are implemented and accepted.

- **Goal:** Expand operational SearchQuery coverage safely while exposing all 106 Reference targets.
- **Why:** Reference breadth and reliable discovery are different quality dimensions.
- **Dependencies:** V2-0 governance and stable discovery evaluation tooling.
- **In Scope:** Knowledge visibility for all targets; query provenance/status; staged Pilot → Validated Batch → Expanded Operational Set.
- **Out of Scope:** Enabling all 106 at once, unreviewed synonym expansion, or rewriting Discovery algorithms without evidence.
- **Domain impact:** Strengthens MonitorTarget/SearchQuery lifecycle and validation records.
- **Schema impact:** Only if validation metadata cannot be represented; requires separate contract approval.
- **Data requirements:** Per-query source, observed sample relevance, result volume/duplicate/scope notes, failure modes, validation date and dataset version. Do not claim recall without a complete labeled population.
- **UX impact:** Distinguish Reference from operational availability in task creation and Knowledge views.
- **Testing:** Dataset integrity, stable IDs, enabled-query validation, multi-query global analysis cap, and regressions.
- **Real-world validation:** Run bounded batches; promote only queries meeting documented acceptance.
- **Exit criteria:** Every enabled query is traceable and validated; coverage is reported separately from the 106-reference denominator.
- **V2-4A result:** 106 formal targets are searchable in task creation; 5 are operational, 12 first-batch candidates remain disabled/unvalidated, and 当归 remains paused. The batch plan is [MONITOR_QUERY_VALIDATION_PLAN_V2_4.md](MONITOR_QUERY_VALIDATION_PLAN_V2_4.md).
- **V2-4 Wave 1 result:** 5 standard-name Queries/Targets (山楂、沙棘、罗汉果、黑芝麻、蜂蜜) were promoted; 乌梅 was held as disabled `paused_scope_issue`. See [MONITOR_QUERY_VALIDATION_RESULTS_V2_4_BATCH_01A.md](MONITOR_QUERY_VALIDATION_RESULTS_V2_4_BATCH_01A.md).
- **V2-4 Wave 2A result:** 4 standard-name Queries/Targets (山药、赤小豆、枸杞子、莲子) were promoted. Operational Reference coverage is now 14/106; 百合 and 菊花 remain disabled Wave 2B candidates. See [MONITOR_QUERY_VALIDATION_RESULTS_V2_4_BATCH_02A.md](MONITOR_QUERY_VALIDATION_RESULTS_V2_4_BATCH_02A.md).
- **V2-4 Wave 2B result:** 菊花 was promoted; the standard-name 百合 Query was rejected at 50% observed relevance while its MonitorTarget remains in the Reference. Operational Reference coverage is 15/106. See [MONITOR_QUERY_VALIDATION_RESULTS_V2_4_BATCH_02B.md](MONITOR_QUERY_VALIDATION_RESULTS_V2_4_BATCH_02B.md).
- **V2-4 Lily refinement result:** `食用百合` retained its `manually_curated` provenance, passed the unchanged Gate at 90% observed relevance, and became the only active Query for the 百合 Target. The standard-name `百合` Query remains rejected and disabled. See [MONITOR_QUERY_VALIDATION_RESULTS_V2_4_BATCH_02C.md](MONITOR_QUERY_VALIDATION_RESULTS_V2_4_BATCH_02C.md).
- **V2-4 exit result:** all enabled Queries are traceable `search_validated` records; all 106 Reference Targets remain visible; operational coverage is reported separately as 16/106; Promote, Hold, Reject, and Refinement each have preserved real governance evidence.

## V2-5 — Claim taxonomy

**Status:** COMPLETE — governed Claim domain, runtime, primary presentation, and legacy separation accepted; legacy Effect/Risk/Recommendation remains a compatibility layer.

### V2-5A — Claim Taxonomy & Domain Contract

**Status:** COMPLETE — design baseline and deterministic governance tests accepted; production Claim extraction is unchanged.

- **Goal:** Replace the overloaded Effect concept at the design level with separate ClaimMention observations and ClaimSignal marketing topics.
- **Why:** Page wording, official functions, risk interpretation, and inspection knowledge have different identities and authorities.
- **Dependencies:** V2-2 provenance model, V2 knowledge governance, and completed V2-4 coverage.
- **In Scope:** Complete 5-Effect/26-expression legacy inventory and migration; `claim-taxonomy-v2.0`; ClaimMention/ClaimSignal contracts; seller-managed source boundary; future schema/API/storage draft; ADR and deterministic governance tests.
- **Out of Scope:** Runtime extraction, schema/API migration, HealthFunction consistency, RiskSignal generation, inspection bridge changes, semantic/fuzzy matching, or vocabulary expansion.
- **Domain impact:** Freezes Snapshot-scoped ClaimMention and ClaimSignal contracts and keeps HealthFunction/RiskSignal/Recommendation separate.
- **Schema impact:** Design only. Schema 10 remains current.
- **Data requirements:** Existing `config/effect_keywords.json` and current bridge/code/tests as the audited legacy authority; no fabricated expressions.
- **UX impact:** Freezes future 页面宣传线索 wording and Evidence drill-down; current frontend unchanged.
- **Testing:** Machine-readable schema, unique/referential IDs, 100% legacy coverage, source policy, provenance, and absence of forbidden cross-domain mappings.
- **Real-world validation:** None; offline design/governance phase.
- **Exit result:** All 26 legacy expressions map exactly once into five marketing topics with no taxonomy gap; the three legacy Effect/Risk bridges remain separately documented compatibility paths.

### V2-5B1 — ClaimMention / ClaimSignal runtime core

**Status:** COMPLETE — runtime, artifact, schema 11 projection, and additive Snapshot API contract implemented offline.

- **Goal:** Produce provenance-bearing ClaimMention and ClaimSignal artifacts and expose them through compatible read models/API/UI.
- **Dependencies:** Accepted V2-5A contract and taxonomy.
- **In Scope:** Seller-managed exact-expression extraction, signal aggregation, artifact authority, additive storage/API implementation, and compatibility migration.
- **Out of Scope:** Claim-to-HealthFunction consistency, automated RiskSignal, legality/compliance judgment, or new inspection mapping.
- **Domain impact:** Implements the accepted ClaimMention/ClaimSignal entities without changing their meaning.
- **Schema impact:** Additive schema 10→11; all prior entities and human Review/Sampling state are preserved.
- **Data requirements:** Positive, zero-hit, multiple-mention, OCR trace, UGC-only, and excluded-other-product fixtures.
- **UX impact:** Adds typed Claim DTOs only; visible 页面宣传线索 migration remains V2-5B2.
- **Testing:** Exact extraction, provenance, aggregation, taxonomy version, source boundary, compatibility, migration/rebuild, and non-adjudication language.
- **Real-world validation:** None in B1; offline deterministic fixtures only, with no Detail/OCR/network execution or vocabulary expansion.
- **Exit criteria:** Runtime Claim records reproduce source Evidence, only eligible sources create formal signals, and legacy behavior is migrated without silent loss.

### V2-5B2 — Claim UX and legacy presentation migration

**Status:** COMPLETE — primary Claim presentation, exact Claim filter, legacy separation, and V2-5 exit regression accepted offline.

- **Goal:** Present the implemented ClaimSignal/ClaimMention contract as 页面宣传线索 and downgrade legacy Effect wording without deleting compatibility data.
- **Dependencies:** Accepted V2-5B1 runtime core and additive Snapshot API.
- **In Scope:** Claim workspace presentation, Mention source trace, explicit not-generated/error/zero states, and any approved Claim filters.
- **Out of Scope:** Claim-to-HealthFunction consistency, automated RiskSignal, legality/compliance judgment, new inspection mapping, or legacy artifact deletion.
- **Schema impact:** None. Schema 11 remains current.
- **API impact:** Product/Snapshot list rows add batched same-Snapshot `claimSignalSummaries`; filter options add governed `claimTypes`; `/api/products?claim_type=` is additive. Legacy `effect=` and `effects[]` remain compatibility contracts.
- **UX impact:** Product Overview, Product Detail, Review Queue, Inspection Workspace, and current Sampling use V2 Claim. Four Claim states remain distinct; Mention expansion traces to existing Evidence. Historical frozen Sampling displays its unchanged legacy field as 旧版冻结分析结果.
- **Testing:** Claim/UI state matrix, UGC and legacy separation, same-Snapshot list/filter semantics, trace fallback, current/frozen Sampling separation, legacy Risk/Recommendation compatibility, and full offline regression.
- **Exit result:** V2-5 Claim domain, runtime, and primary presentation are complete. This does not remove the legacy Effect/Risk/Recommendation compatibility pipeline.

## V2-6 — Health-food claim consistency

**Status:** COMPLETE — governed frameworks/mappings, exact normalization, Snapshot runtime/projection, primary detail/workspace presentation, and the V2-6 Exit Gate are accepted.

### V2-6A — HealthFunction Framework & Claim Consistency Contract

**Status:** DESIGN BASELINE / COMPLETE — official framework, transition normalization, topic mapping, assessment contract, ADR, and deterministic governance tests accepted.

- **Goal:** Govern official HealthFunction identity and freeze a reproducible, non-adjudicative Claim consistency contract.
- **Dependencies:** V2-3 verified identity, V2-5 Claim runtime/presentation, and official 2023 SAMR/NHC/NATCM catalogs and transition table.
- **In Scope:** Complete 24/24 non-nutrient functions; separate nutrient-supplement framework; stable IDs; exact current/official-transition normalization; four `topic_related` mappings; explicit male-function gap; future assessment/attention contracts.
- **Out of Scope:** Production normalization/assessment, schema/API/UI, fuzzy mapping, Claim→Risk, Recommendation changes, legality/compliance or probability output.
- **Domain impact:** Establishes design baselines for HealthFunction, HealthFunctionAlias, ClaimHealthFunctionMapping, ClaimConsistencyAssessment, and ClaimExpressionAttention.
- **Schema/API impact:** None. Schema 11 and production API remain unchanged.
- **Data requirements:** First-party official sources, full transition table, exact raw-string preservation, and offline A–L contract fixtures.
- **UX impact:** Future wording only; no frontend behavior changed.
- **Testing:** Dataset provenance/completeness, referential integrity, exact normalization, fuzzy rejection, mapping separation, asymmetric alias behavior, non-adjudicative state/relation matrix, and full offline regression.
- **Exit result:** At the V2-6A exit, `health-functions-v2.0` and `claim-health-function-mapping-v2.0` became governed design authorities while production runtime remained absent; V2-6B1 subsequently implemented that accepted contract.

### V2-6B1 — Claim Consistency Runtime Core

**Status:** COMPLETE — runtime, sidecar authority, schema 12 projection, additive Snapshot API and TypeScript contracts implemented offline.

- **Goal:** Implement Snapshot-scoped normalization and ClaimConsistencyAssessment using the V2-6A contract.
- **Why:** Analysts need transparent official-function comparison clues without automatic legal verdicts.
- **Dependencies:** Accepted V2-6A datasets/contracts and an explicit artifact/schema/API implementation review.
- **In Scope:** `claim_consistency.json`, strict governed config loaders, exact Registry resolver, versioned comparison runtime, additive rebuildable projection/API, and TypeScript DTOs.
- **Out of Scope:** `pass/fail`, `合法/违法`, efficacy truth, RiskSignal, Claim→Risk, inspection triggers, or enforcement conclusions.
- **Domain impact:** Implements the accepted derived assessment without changing Claim, HealthFoodIdentity, Review, Sampling, or Recommendation meaning.
- **Schema impact:** Additive schema 11→12; all prior entities and human Review/Sampling state are preserved.
- **Data requirements:** Verified official records and page fixtures spanning every accepted state/relation and unresolved gap.
- **Testing:** State matrix, versions, raw/resolved preservation, unavailable/unresolved sources, Snapshot isolation, and non-adjudication language.
- **Real-world validation:** Not part of B1; runtime validation uses governed recorded fixtures with zero network access.
- **Exit result:** Assessments are reproducible, explanatory, non-binary, reconstructable from artifacts, and never exceed source evidence. Visible consistency UI remains absent.

### V2-6B2 — Consistency UX and V2-6 Exit Gate

**Status:** COMPLETE — shared non-adjudicative Product Detail/Inspection Workspace presentation and V2-6 exit regression accepted offline.

- **Goal:** Present the implemented Snapshot assessment without turning topic relations into verdicts, then evaluate the complete V2-6 exit criteria.
- **Dependencies:** Accepted V2-6B1 runtime/API contracts and explicit UX review.
- **In Scope:** Product Detail/Inspection Workspace consistency presentation, official/page trace reuse, state wording, accessibility, and V2-6 exit validation.
- **Out of Scope:** ClaimExpressionAttention automatic classification, Claim→Risk, Recommendation changes, legality/compliance, Review automation, Sampling changes, or V2-7.
- **Schema/API impact:** None expected; consume the additive B1 contract.
- **Exit criteria:** Every operational/domain state and Knowledge Gap remains explicit, page and official evidence remain separate, and full offline regression passes.
- **Exit result:** One shared component presents all accepted states and relations without browser-side recomputation or total verdicts. Existing page/official trace surfaces are reused; ClaimExpressionAttention remains an explicit future governance gap; Risk/Recommendation/Review/Sampling and frozen history are unchanged.

## V2-7 — Inspection knowledge coverage

**Status:** COMPLETE — V2-7A, V2-7B1, V2-7B2 and V2-7C accepted.

- **Goal:** Expand governed inspection knowledge using **wide Reference Index + deep Verified Subset**.
- **Why:** Broad discoverability is useful, but only deeply parsed, provenance-complete mappings can drive recommendations.
- **Dependencies:** V2-5 claim/risk separation and current D2–D6 contracts.
- **In Scope:** Broad official-method metadata; deep parsing for project-relevant risks, analytes, contexts and applicability; source/version lifecycle.
- **Out of Scope:** Treating every indexed method as recommendation-ready or inferring Risk links from analytes.
- **Domain impact:** Strengthens RegulatoryDocument, KnowledgeDataset, SubstanceGroup, method and applicability relationships.
- **Schema impact:** Additive normalization only if approved; existing recommendation compatibility must be retained.
- **Data requirements:** Official documents, method scopes, analytes, replacement/effective metadata and product-context basis.
- **UX impact:** Clear reference-only vs verified/applicable states and gaps.
- **Testing:** Provenance, referential integrity, lifecycle, supersession, negative applicability and no reverse inference.
- **Real-world validation:** Independently verify a focused set of high-priority methods/mappings.
- **Exit criteria:** Deep mappings are source-complete; broad index entries cannot drive unsupported recommendations.

### V2-7A — Inspection Knowledge Inventory & Coverage Contract

**Status:** COMPLETE — deterministic audit and canonical design baseline accepted offline.

- **Goal:** Inventory the actual governed chain, separate lifecycle from knowledge depth, define denominator-scoped metrics, and select source-grounded next work.
- **In Scope:** Offline audit tool, current method/risk/reachability matrices, Wide Reference Index vs Deep Verified Subset, `RegulatoryDocument` design, promotion and Recommendation gates, deterministic governance tests.
- **Out of Scope:** Knowledge-record expansion, schema/API/frontend changes, Recommendation changes, Claim→Risk, group inference, Knowledge Base UI, or Analytics.
- **Result:** The current five methods are a small deep-parsed corpus. Five of eight Risk target mappings are explicit Substances; three are unresolved Groups. Three of five explicit mappings are end-to-end reachable through the current legacy bridge, covering two of three governed Risk categories. Candidates remain outside runtime import.
- **Exit criteria:** Inventory is reproducible from governed configs; every metric has a denominator/version; group and reverse-inference boundaries are tested; existing Recommendation output is unchanged.

### V2-7B — Wide Official Method Reference Expansion

**Status:** COMPLETE — B1 infrastructure and B2 bounded official verification/promotion are complete.

- **Goal:** Expand first-party official method identity/lifecycle coverage without making shallow records Recommendation-capable.
- **Dependencies:** V2-7A coverage contract and the completed V2-7B1 depth/candidate boundary.
- **Initial candidates:** BJS 202405 exact identity/full text from its current SAMR discovery source; GB/T 5009.170-2003 predecessor identity/lifecycle from first-party standards evidence.
- **Required boundary:** Reference-only records cannot enter D5 resolution. Exact titles, lifecycle and documents must be verified before promotion; candidate status is not `verified_reference`.
- **Out of Scope:** Bulk third-party imports, Risk inference from analytes, Claim→Risk, and deep promotion without source scope.

#### V2-7B1 — Inspection Reference Index Infrastructure & Recommendation Boundary

**Status:** COMPLETE — additive storage, validation and runtime isolation accepted offline.

- **Result:** Schema 13 persists independent lifecycle/depth, normalized RegulatoryDocument links and explicit group membership. A validated non-runtime manifest records exactly two candidates. The five existing methods remain the complete runtime index and all explicitly pass `recommendation_ready`; operational resolution filters by both readiness and lifecycle.
- **Non-result:** No candidate, method, analyte, applicability, Risk/group mapping or group member was added; no API/frontend or Recommendation output changed.

#### V2-7B2 — Bounded Official Method Verification & Promotion

**Status:** COMPLETE — accepted first-party verification and bounded `reference_only` promotion.

- **Goal:** Resolve the approved candidate identities/documents and promote only the records whose verified depth is supported by evidence.
- **Boundary:** Candidate count is not index coverage. Lower-depth records remain excluded from Recommendation by construction.
- **Result:** BJS 202405 is indexed as current with its exact official title; GB/T 5009.170-2003 is indexed as a revoked predecessor with its distinct exact title and bidirectional lifecycle link to GB/T 45443-2025. Both remain `reference_only`. The old BJS `weight_loss`/sibutramine planning association is explicitly corrected; no analyte, applicability, Risk/group mapping or runtime Recommendation path was added.

### V2-7C — Deep Verified Subset & V2-7 Exit Gate

**Status:** COMPLETE — priority deep verification and the V2-7 Exit Gate passed offline.

- **Goal:** Deep-verify priority analyte/scope/applicability paths and close V2-7 with context-corpus reachability evidence.
- **Dependencies:** Versioned V2-7B index, depth-aware resolver, RegulatoryDocument/lifecycle handling, and accepted priority set.
- **In Scope:** Full-text analyte parsing, positive/conditional/negative applicability, explicit unknowns, method/document supersession, context-defined Recommendation reachability and complete regression.
- **Out of Scope:** Risk probability, laboratory claims, automatic group expansion, new Claim/Risk causality, UI navigation, or Analytics.
- **Result:** BJS 202405 alone is deepened from official full text to 95 explicit analyte relations and seven method-level product scopes. The six-case deterministic Product Context corpus passes all expected applicable, not-applicable, insufficient-context, regression and unresolved-group outcomes; context-corpus Recommendation reachability is 3/6 under its fixed denominator. The index is 7/7 reference-complete and 6/7 deep. Revoked GB/T 5009.170-2003 remains `reference_only`; no Risk/Claim/group relation or Recommendation algorithm changes.
- **Validation:** Focused Inspection/Reference/Recommendation regression 195/195; Python full suite discovered 555 / passed 554 / skipped 1; frontend workflow 38/38; typecheck and production build passed offline.

## V2-8 — Knowledge Base UI

**Status:** COMPLETE — V2-8A read contract and V2-8B visible UI accepted offline.

- **Goal:** Make governed runtime knowledge inspectable without creating a second static knowledge copy.
- **Why:** Analysts need to understand sources, coverage, versions, and gaps behind results.
- **Dependencies:** V2-3 through V2-7 governed data and Knowledge API contract.
- **In Scope:** A 知识库 navigation item with tabs: 食药物质目录、保健功能、风险物质、风险映射、检验方法、官方文件.
- **Out of Scope:** UI-only mock knowledge, editing regulated datasets in the browser, or hiding provenance.
- **Domain impact:** No new semantic entity; provides read models over governed runtime datasets.
- **Schema impact:** Read-index/API additions only after design; no duplicate source-of-truth store.
- **Data requirements:** Version/lifecycle/source/coverage fields from the same datasets used by analysis.
- **UX impact:** Search, filter, detail, source links, lifecycle badges and Knowledge Gap/coverage presentation.
- **Testing:** API/UI consistency, empty/version/superseded states, links, pagination and accessibility.
- **Real-world validation:** Analysts trace sample recommendations back through displayed knowledge.
- **Exit criteria:** Every displayed record maps to governed runtime data; no mock or divergent copies exist.

### V2-8A — Knowledge Read API & UX Contract

**Status:** COMPLETE — read model, API/DTO contract and canonical UX baseline accepted offline.

- **Goal:** Expose the six governed domains through one consistent read-only contract before implementing visible navigation or pages.
- **Result:** Seven GET-only endpoints provide separate denominator-defined summary counts and paginated/filterable MonitorTarget, HealthFunction, Substance, RiskMapping, InspectionMethod and RegulatoryDocument records. Source/version trace, lifecycle, depth and Knowledge Gaps remain explicit. Schema-13 projections are reused for Monitor/Inspection/Risk; the existing strict governed loader is reused for HealthFunction.
- **Frontend result:** TypeScript DTOs, GET clients and stable depth/gap/source presentation mappings exist. No Sidebar, route, page, tab or CSS was added.
- **Boundary:** No POST/PUT/DELETE knowledge operation, mock catalog, browser inference, schema change or business-state mutation exists.
- **Validation:** targeted backend/domain/API regression 168/168 and frontend typecheck pass offline.

### V2-8B — Knowledge Base UI Implementation

**Status:** COMPLETE — first-level navigation, six governed tabs and V2-8 Exit Gate accepted offline.

- **Goal:** Implement the 知识库 navigation, six tabs, list/detail/filter/empty/gap/source states using only the V2-8A DTOs.
- **Boundary:** No browser editing, duplicated static knowledge, inferred relations, Analytics or V2-9 work.
- **Result:** `#/knowledge` provides API-backed summary facts, common search/filter/offset-pagination interaction, accessible row actions and a focus-managed read-only detail Drawer. Availability, lifecycle, knowledge depth, Knowledge Gap and source/version provenance remain separate.
- **Validation:** targeted Knowledge regression 168/168; Python full regression discovered 564 / passed 563 / skipped 1; frontend workflow 43/43; typecheck and production build pass. Local 1440px/1080px checks show no page-level horizontal overflow.

## V2-9 — Analytics

**Status:** NEXT — requires a separate phase Gate; not implemented in V2-8.

- **Goal:** Provide denominator-defined operational, clue, geography, and knowledge-quality metrics.
- **Why:** Counts without population, stage, source, and coverage definitions are misleading.
- **Dependencies:** Stable domain facts from earlier phases and an approved metric dictionary.
- **In Scope:** Pipeline metrics (search, Detail, OCR, analysis, Review, Sampling); claim category/seller/UGC/unmapped metrics; independent search-region and declared-origin geography; knowledge quality metrics.
- **Out of Scope:** A “全国风险地图,” population risk inference, or metrics from mixed undefined denominators.
- **Domain impact:** Adds Analytics Read Model and metric definitions, not new source facts.
- **Schema impact:** Read-model/materialization changes only after definition review.
- **Data requirements:** Metric name, numerator, denominator, time basis, dataset version, filters, missing-data rule and provenance.
- **UX impact:** 统计分析 page with titles such as 已采集商品地区分布、页面线索商品地区分布、商品标称产地分布.
- **Testing:** Metric fixtures, zero denominators, missing facts, deduplication, snapshot/product scope and geographic non-conflation.
- **Real-world validation:** Reconcile dashboard samples against raw artifacts and database queries.
- **Exit criteria:** Every metric is reproducible from its dictionary and cannot be misread as representative national risk.

## V2-10 — Evaluation and thesis

- **Goal:** Evaluate the complete V2 system and produce thesis-ready evidence without overstating conclusions.
- **Why:** The project needs a reproducible account of design, implementation, limitations and measured performance.
- **Dependencies:** Accepted prior phases and frozen evaluation protocols.
- **In Scope:** Test corpus, metric evaluation, error analysis, usability evidence, architecture/ADR synthesis, reproducibility package and thesis material.
- **Out of Scope:** Last-minute feature expansion, retroactive fixture editing, unsupported population or legal claims.
- **Domain impact:** None unless evaluation exposes a separately approved correction.
- **Schema impact:** None expected.
- **Data requirements:** Governed, de-identified where necessary, versioned evaluation sets and exact environment metadata.
- **UX impact:** Final acceptance and documented limitations, not redesign by anecdote.
- **Testing:** Full regression, phase gates, offline fixtures, approved real-world E2E and reproducibility rerun.
- **Real-world validation:** Bounded end-to-end cases reviewed against source artifacts and expert expectations.
- **Exit criteria:** Results are reproducible; limitations and coverage are explicit; thesis claims match measured evidence and non-adjudication boundaries.
