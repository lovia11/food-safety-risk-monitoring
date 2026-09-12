# Implementation Roadmap V2

> Status: CANONICAL
> Applies to: V2
> Last verified against commit: `bbe992e54f9fc583b312f919f32f91f43e53fb06`
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

## V2-2 — ProductFact and declared origin

- **Goal:** Introduce provenance-bearing structured facts, starting with explicit product-declared origin.
- **Why:** Current search region cannot answer origin questions and free-form extraction must be auditable.
- **Dependencies:** V2-1 evidence browsing and approved ProductFact contract.
- **In Scope:** ProductFact extraction/storage/API; `declared_origin`; source/conflict/missing/review states; DOM/OCR source support.
- **Out of Scope:** Inferring origin from search region or addresses; broad fact ontology; health-food identity decision.
- **Domain impact:** Adds ProductFact as a Snapshot-scoped derived entity.
- **Schema impact:** Additive migration only after proposal review; preserve schema 8 data and re-import behavior.
- **Data requirements:** Real positive, missing, conflicting DOM/OCR origin fixtures with exact source paths.
- **UX impact:** Independent 搜索页地区 and 商品标称产地 key/value display; missing is `—`.
- **Testing:** Provenance, normalization, conflicts, DOM/OCR sources, missing origin, and explicit non-inference tests.
- **Real-world validation:** Small reviewed product set containing clear, absent, and conflicting origin statements.
- **Exit criteria:** Every stored origin is Snapshot-scoped and source-reconstructable; no false “待采集” value or geographic inference.

## V2-3 — Health-food identity

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

## V2-4 — Monitor coverage

- **Goal:** Expand operational SearchQuery coverage safely while exposing all 106 Reference targets.
- **Why:** Reference breadth and reliable discovery are different quality dimensions.
- **Dependencies:** V2-0 governance and stable discovery evaluation tooling.
- **In Scope:** Knowledge visibility for all targets; query provenance/status; staged Pilot → Validated Batch → Expanded Operational Set.
- **Out of Scope:** Enabling all 106 at once, unreviewed synonym expansion, or rewriting Discovery algorithms without evidence.
- **Domain impact:** Strengthens MonitorTarget/SearchQuery lifecycle and validation records.
- **Schema impact:** Only if validation metadata cannot be represented; requires separate contract approval.
- **Data requirements:** Per-query source, relevance sample, recall/precision notes, failure modes, validation date and dataset version.
- **UX impact:** Distinguish Reference from operational availability in task creation and Knowledge views.
- **Testing:** Dataset integrity, stable IDs, enabled-query validation, multi-query global analysis cap, and regressions.
- **Real-world validation:** Run bounded batches; promote only queries meeting documented acceptance.
- **Exit criteria:** Every enabled query is traceable and validated; coverage is reported separately from the 106-reference denominator.

## V2-5 — Claim taxonomy

- **Goal:** Replace the overloaded Effect concept with governed claim domains.
- **Why:** Page marketing, official functions, risk expressions, and disease/treatment wording have different semantics.
- **Dependencies:** V2-2 ProductFact provenance and V2 knowledge governance.
- **In Scope:** Models/datasets for Official Health Functions, Marketing Expressions, Risk Claims, and Disease/Treatment Expressions; explicit mappings and gaps.
- **Out of Scope:** Generating a complete vocabulary in one pass or using semantic similarity as verified equivalence.
- **Domain impact:** Adds ClaimSignal and ClaimTaxonomyTerm and explicit mapping relations.
- **Schema impact:** Additive claim entities/read models after API/domain review; preserve legacy Phase3 output compatibility.
- **Data requirements:** Authoritative function catalog plus curated page-expression fixtures with provenance and lifecycle.
- **UX impact:** Show actual expression, normalized category, source origin, mapping status and Knowledge Gap.
- **Testing:** Exact official claim, marketing paraphrase, treatment wording, ambiguity, UGC-only, and no-implicit-mapping cases.
- **Real-world validation:** Dual-review a bounded corpus and document disagreements/unmapped top expressions.
- **Exit criteria:** ClaimSignal, HealthFunction, and RiskSignal cannot be confused in data or UI; coverage is measurable by layer.

## V2-6 — Health-food claim consistency

- **Goal:** Compare verified identity/functions with page ClaimSignals using evidence-bearing assessments.
- **Why:** Analysts need transparent mismatch clues without automatic legal verdicts.
- **Dependencies:** V2-3 verified identity and V2-5 claim taxonomy/mappings.
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
