# Implementation Roadmap V2

> Status: CANONICAL
> Applies to: V2
> V2-1 implementation baseline: `a5be2ed9ff07ddc9b347812f281d9d9e638fc6c6`
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

### V2-5B — ClaimMention / ClaimSignal runtime implementation

**Status:** NEXT — implementation requires a separate human Gate.

- **Goal:** Produce provenance-bearing ClaimMention and ClaimSignal artifacts and expose them through compatible read models/API/UI.
- **Dependencies:** Accepted V2-5A contract and taxonomy.
- **In Scope:** Seller-managed exact-expression extraction, signal aggregation, artifact authority, additive storage/API implementation, compatibility migration and Claim presentation.
- **Out of Scope:** Claim-to-HealthFunction consistency, automated RiskSignal, legality/compliance judgment, or new inspection mapping.
- **Domain impact:** Implements the accepted ClaimMention/ClaimSignal entities without changing their meaning.
- **Schema impact:** Additive only after migration/API review; schema 10 and human state must be preserved.
- **Data requirements:** Positive, zero-hit, multiple-mention, OCR trace, UGC-only, and excluded-other-product fixtures.
- **UX impact:** Introduces 页面宣传线索 with original wording/source trace while preserving explicit compatibility states.
- **Testing:** Exact extraction, provenance, aggregation, taxonomy version, source boundary, compatibility, migration/rebuild, and non-adjudication language.
- **Real-world validation:** Separately approved bounded artifact corpus; no automatic vocabulary expansion.
- **Exit criteria:** Runtime Claim records reproduce source Evidence, only eligible sources create formal signals, and legacy behavior is migrated without silent loss.

## V2-6 — Health-food claim consistency

- **Goal:** Compare verified identity/functions with page ClaimSignals using evidence-bearing assessments.
- **Why:** Analysts need transparent mismatch clues without automatic legal verdicts.
- **Dependencies:** V2-3 verified identity, accepted V2-5 Claim runtime, and an explicit V2-6 function-mapping contract.
- **In Scope:** The comparison of verified official identity + official health functions + page claims; required states and detailed explanation.
- **Out of Scope:** `pass/fail`, `合法/违法`, efficacy truth, or enforcement conclusions.
- **Domain impact:** Adds ClaimConsistencyAssessment with compared claims, official functions, matched mapping, unmatched claims, disease/treatment expressions, Evidence, official source, and gaps.
- **Schema impact:** Additive derived artifact/index after contract review.
- **Data requirements:** Official records and page fixtures spanning consistent, out-of-scope, treatment, unavailable, insufficient and manual-review cases.
- **UX impact:** A traceable assessment section with evidence/source links and explicit gaps.
- **Testing:** State matrix, version changes, mismatch, unavailable source, ambiguous mapping and non-adjudication language.
- **Real-world validation:** Expert review of a bounded identified-health-food set.
- **Exit criteria:** Assessments are reproducible, explanatory, non-binary, and never exceed source evidence.

## V2-7 — Inspection knowledge coverage

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

## V2-8 — Knowledge Base UI

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

## V2-9 — Analytics

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
