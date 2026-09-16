# Project Status

## Baseline

- Branch: `ux-redesign-v1`
- V2-4 Wave 1 starting commit: `698b8ad482367ffbd20ba696799c47ebd372d2c3`
- SQLite schema: 13
- Active UI: React/Vite in `frontend/`
- Backend: Python 3.10.x local API and pipeline

## Current Capabilities

- Search/Discovery → Detail → OCR → Phase3 → degradable Inspection Recommendation
- Product Overview and Snapshot workspace with Evidence, context and Review
- Local Snapshot thumbnails, whole-row keyboard navigation, compact Snapshot summary/timeline, and source-grouped Evidence review
- In-app image Lightbox/OCR viewer and explicit analysis/knowledge/recommendation presentation states
- Snapshot-scoped Review with server-enforced analysis readiness
- Product-scoped current Sampling Membership and frozen historical list export
- Web manual-action coordination without HTTP-thread browser control
- Deterministic Historical Validation support
- Snapshot-scoped ProductFact extraction for explicit `declared_origin`, with DOM/OCR provenance, conflict presentation and source trace
- Snapshot-scoped HealthFoodIdentity with seller-managed clue/identifier provenance, degradable official lookup, conservative page-to-registry matching, verbatim official functions and separate page/official source trace
- Full 106-object Monitor Reference picker with operational/query-pending/paused presentation, server-side execution guard, governed Query lifecycle, validation ledger and search-only batch tooling
- V2 Claim domain, runtime, and primary 页面宣传线索 UX with deterministic seller-managed ClaimMentions/ClaimSignals, `claim_analysis.json` authority, schema 11 Claim projection retained by current schema 13, same-Snapshot list summaries/filter, and Evidence trace
- V2-6 ClaimConsistency runtime and primary detail/workspace UX with exact governed Registry normalization, non-adjudicative topic comparison, `claim_consistency.json` authority, schema 12 projection retained by current schema 13, explicit gaps, and separate page/official trace
- V2-7A deterministic Inspection Knowledge inventory and denominator-defined coverage contract
- V2-7B1/B2 schema 13 Inspection Reference boundary with independent depth/lifecycle, seven normalized RegulatoryDocuments, zero-row governed group membership, two promoted non-runtime trace records, and a Recommendation-ready resolver gate
- V2-7C official-full-text deep verification of BJS 202405 plus a deterministic six-case Product Context corpus and completed V2-7 Exit Gate
- V2-8 read-only Knowledge Base with seven read endpoints, denominator-defined summary, six API-backed tabs and traceable detail Drawer
- V2-9A governed 32-metric Analytics Dictionary, deterministic GET-only read model and TypeScript DTO/client contract

## Current Coverage

- Official directory 106 / 106; 18 targets have governed Query records; 16 / 106 are operational
- 19 enabled and validated Reference queries; 1 disabled rejected query; 0 disabled candidate queries; 2 paused targets
- Separate development seed: 1 target / 2 queries
- Legacy/current Phase3 clues: 5 categories / 26 keywords
- V2 Claim design baseline: 5 marketing-topic Claim types / 26 provenance-bearing exact expressions
- V2-6A HealthFunction design baseline: 2 frameworks / 24 of 24 non-nutrient functions / 40 official transition aliases
- Claim→HealthFunction design mappings: 4 `topic_related` / 1 explicit no-mapping Claim gap
- 3 Evidence-to-risk Bridge mappings; 5 Risk-to-substance and 3 Risk-to-group mappings
- 7 indexed / 6 Recommendation-ready Inspection methods, 0 pending / 2 promoted non-runtime candidate traces, 7 RegulatoryDocuments, 201 substances, 227 method-substance links, 44 applicability records
- Static Recommendation reachability: 5/5 explicit mappings structurally ready; 3/5 end-to-end through the current bridge; 0/3 group mappings resolved
- Deterministic Product Context corpus: 6/6 expected outcomes match; 3/6 cases reach `suggested_methods` under the fixture-scoped denominator

## Current Validation

V2-4 is complete. Wave 1 promoted five standard-name Queries and held 乌梅; Wave 2A promoted 山药、赤小豆、枸杞子、莲子. Wave 2B promoted 菊花 and rejected the standard-name 百合 Query at 50% observed relevance. The separately governed `食用百合` strategy retained `manually_curated` provenance and passed independent Batch 02C review at 90%; 百合 is now operational only through that refined Query, while the naked standard name remains rejected and disabled. The governed evidence therefore includes real Promote, Hold, Reject, and Refinement paths. V2-4 exit validation passed 74/74 targeted Monitor/query/task tests, 6/6 Historical Validation builder tests, 462 Python tests discovered / 461 passed / 1 skipped, frontend workflow 26/26, typecheck, and production build. The Historical Validation Set remains unmodified.

V2-5A Claim Taxonomy & Domain Contract is complete. All 5 legacy Effect labels and 26 exact keywords were inventoried from the repository and migrated exactly once into five marketing-topic Claim types with no gap. ClaimSignal remains separate from HealthFunction, RiskSignal and InspectionRecommendation; formal Claim sources are seller-managed only. Claim taxonomy tests passed 14/14, Monitor regression passed 74/74, Python full regression discovered 476 / passed 475 / skipped 1, and frontend workflow 26/26, typecheck and build passed offline.

V2-5B1 Claim runtime core validation passed offline: Python full regression discovered 496 / passed 495 / skipped 1; frontend workflow passed 26/26; typecheck and production build passed. Claim derivation, artifact/rebuild, schema 10→11 preservation, additive Snapshot API, legacy bridge/Recommendation, Review/Sampling and Monitor compatibility are covered without Detail, OCR or external network execution.

V2-5B2 Claim presentation migration and the V2-5 Exit Gate passed offline: Python full regression discovered 500 / passed 499 / skipped 1; frontend workflow passed 30/30; typecheck and production build passed. Product Overview, Product Detail, Review Queue, Inspection Workspace, and current Sampling now use same-Snapshot V2 Claim projections with four explicit states and Evidence trace. Legacy Effect/Risk/Recommendation APIs remain compatible, while frozen Sampling output is unchanged.

V2-6A HealthFunction Framework & Claim Consistency Contract is complete as a design/governance baseline. Official first-party sources support the two independent 2023 frameworks, complete 24-function non-nutrient catalog, and 40 exact transition aliases. Four project-governed `topic_related` mappings and the `male_function_related` gap are explicit. Registry aliases are asymmetric and cannot approve page Claim wording. Governance tests passed 17/17; Python full regression discovered 517 / passed 516 / skipped 1; frontend workflow passed 30/30; typecheck and production build passed. Runtime, schema 11, API, frontend, Claim taxonomy, Risk/Recommendation, Review/Sampling, and frozen history are unchanged.

V2-6B1 Claim Consistency Runtime Core is complete. The pipeline consumes only persisted identity/Registry and formal Claim artifacts plus the two governed config authorities; it performs no live consistency lookup. Exact resolver, framework isolation, A–L states, conservative partial-unresolved semantics, degradable sidecar failure, schema 11→12 preservation/rebuild, additive Snapshot DTOs, and unchanged Risk/Recommendation/Review/Sampling behavior are covered offline. Targeted cross-domain regression passed 187/187; Python full regression discovered 532 / passed 531 / skipped 1; frontend workflow passed 30/30; typecheck and production build passed. The frontend contains additive types only and has no visible consistency UI.

V2-6B2 Claim Consistency presentation and the V2-6 Exit Gate are complete. Product Detail and Inspection Workspace reuse one Snapshot-scoped component for all operational/domain states and per-Claim relations. Official transition/raw/unresolved text and separate page/Registry source trace are auditable; partial unresolved output never creates a false negative; no overall verdict or score is generated. Targeted cross-domain regression passed 124/124; Python full regression discovered 532 / passed 531 / skipped 1; frontend workflow passed 38/38; typecheck and production build passed. Offline 1440px/1080px acceptance found no page-level horizontal overflow. Runtime, schema 12, governed mappings, Risk/Recommendation, Review/Sampling, and frozen history are unchanged.

V2-7A Inspection Knowledge Inventory & Coverage Contract is complete. An offline deterministic audit computes the actual method, analyte, applicability, Risk mapping, bridge and Recommendation reachability matrices from the three governed configs. Lifecycle and knowledge depth are independent; the current five methods form a small deep-parsed corpus, not national coverage. Reference-only candidates cannot enter runtime until a depth-aware gate exists. Audit/governance tests passed 9/9; targeted domain packs passed 210/210 Inspection, 49/49 Claim/Consistency, 30/30 Review/Sampling, and 39/39 Monitor/Discovery/Task; Python full regression discovered 541 / passed 540 / skipped 1; frontend workflow passed 38/38; typecheck and production build passed. No schema, API, frontend, knowledge record or Recommendation behavior changed.

V2-7B1 Inspection Reference Index Infrastructure & Recommendation Boundary is complete. The additive schema 12→13 migration, config schema 2 depth/document/group contracts, five explicit Recommendation-ready existing methods, two isolated candidate records, and the operational depth filter are implemented. No candidate was promoted and existing Recommendation semantics remain unchanged.

V2-7B1 validation passed fully offline: focused Inspection/Reference/Risk/Recommendation regression 193/193; Python full regression discovered 552 / passed 551 / skipped 1; frontend workflow 38/38; typecheck and production build passed.

V2-7B2 Bounded Official Method Verification & Promotion is complete. First-party records promote exactly BJS 202405 (current) and GB/T 5009.170-2003 (revoked predecessor) as `reference_only`, close the predecessor lifecycle edge, and explicitly correct the former BJS `weight_loss`/sibutramine planning association. Coverage is now 7/7 reference-complete and 5/7 deep. No analyte/applicability/Risk/group/bridge facts or Recommendation path changed. Targeted offline regression passed 223/223; no full suite, frontend suite or live collection was required by this bounded Gate.

V2-7C Deep Verified Subset & Exit Gate is complete. Only BJS 202405 was deepened from the official SAMR full text, adding 95 explicit analyte relations and seven method-level source scopes while reusing 11 existing CAS identities and adding 84. The six-case context corpus passes every expectation; 3/6 cases enter `suggested_methods` under its fixed denominator. The existing Recommendation algorithm naturally consumes the new governed facts, while Risk/Claim/group mappings, schema/API/frontend, Phase3, D2–D6, Review/Sampling and frozen history remain unchanged. Focused regression passed 195/195; Python full regression discovered 555 / passed 554 / skipped 1; frontend workflow passed 38/38; typecheck and production build passed offline.

V2-8A Knowledge Read API & UX Contract is complete. Seven GET-only endpoints expose the same governed Monitor, HealthFunction, Substance, RiskMapping, InspectionMethod and RegulatoryDocument authorities used by runtime, with separate summary denominators, deterministic server-side filtering/pagination, source/version trace and explicit gaps. Frontend DTO/client/mapper contracts are ready, while Sidebar/routing/page/tabs remain untouched. Knowledge read API/domain tests passed 9/9; the broader targeted pack passed 168/168; frontend typecheck passed. Schema 13, knowledge facts and every existing business workflow remain unchanged.

V2-8B Knowledge Base UI and the V2-8 Exit Gate are complete. The first-level `#/knowledge` route implements exactly six canonical tabs using only the V2-8A API clients, with server search/filter/pagination, hash URL state, factual summary cards, accessible detail Drawer, governed source links and explicit Knowledge Gaps. Method lifecycle remains independent from knowledge depth; Monitor Reference remains independent from operational readiness; HealthFunction remains independent from Claim; group mappings remain unexpanded. Targeted Knowledge regression passed 168/168; Python full regression discovered 564 / passed 563 / skipped 1; frontend workflow passed 43/43; typecheck/build and 1440px/1080px local acceptance passed. No schema, config or business runtime changed.

V2-9A Analytics Metric Dictionary & Read Model is complete. `analytics-metrics-v2.0` defines 32 implemented count/ratio/distribution/coverage metrics and four explicit unavailable/future metrics. Runtime metrics share Task-created cohorts, preserve Product/Snapshot grains and zero denominators; formal Claim excludes legacy Effect/UGC; search region and evidence-backed declared origin remain separate; Knowledge coverage reuses V2-7 audit and V2-8 summary. Six GET-only endpoints and frontend DTO/client contracts are implemented without visible navigation, charts, materialization or schema change. Targeted Analytics tests passed 9/9 and typecheck passed; the current local baseline repeated identically.

## Known Limitations

Additional ProductFact types, human fact editing, ClaimExpressionAttention governance, the visible Analytics UI, and further separately governed Operational Search expansion are Future V2 work. The Analytics dictionary/read API exists, but no Analytics navigation, page or chart is implemented. The Knowledge Base is implemented as a read-only surface and does not provide governance editing. V2 Claim primary UX and the Claim consistency runtime/presentation are implemented, while Phase3 still emits the unchanged legacy Effect compatibility contract; UGC may still influence that legacy path. Official registry lookup remains a low-frequency, cached, best-effort integration because the public site exposes no API stability or availability contract. The system does not make legality, efficacy, laboratory-detection, enforcement, geographic-verification, or risk-probability conclusions.

## Current Development Phase

V2-5 — COMPLETE. Governed taxonomy, ClaimMention/ClaimSignal runtime, artifact authority, rebuildable Claim projection (introduced in schema 11 and retained in schema 12), primary 页面宣传线索 UX, exact same-Snapshot filter, and legacy separation are implemented.

V2-6A — DESIGN BASELINE / COMPLETE. HealthFunction Framework & Claim Consistency Contract is governed; its accepted meaning is unchanged by the B1 implementation.

V2-6B1 — COMPLETE. Claim Consistency runtime/artifact, schema 12 projection, and additive Snapshot API/TypeScript contracts are implemented; visible UI is not.

V2-6B2 — COMPLETE. Shared Product Detail/Inspection Workspace presentation, separate page/official trace, state/relation semantics, and the V2-6 Exit Gate are accepted.

V2-6 — COMPLETE. The HealthFunction framework, exact Registry normalization, governed Claim topic mapping, Snapshot consistency runtime, rebuildable projection, and primary consistency UX are established. ClaimExpressionAttention governance and Claim→Risk remain outside this completion meaning.

V2-7A — AUDIT / DESIGN BASELINE / COMPLETE. Current inventory, depth model, RegulatoryDocument contract, group boundary, coverage denominators, reachability and candidate plan are frozen.

V2-7B1 — COMPLETE. The index/deep-subset boundary is enforced; no knowledge expansion has occurred yet.

V2-7B2 — COMPLETE. Exactly two first-party-verified identities are promoted at `reference_only`; no deep/runtime expansion occurred.

V2-7C — COMPLETE. BJS 202405 is deep-verified, the deterministic context corpus is governed, and the Exit Gate passes.

V2-7 — COMPLETE. The bounded Wide Reference Index/Deep Verified Subset contract is implemented and validated.

V2-8A — COMPLETE. The read-only Knowledge contract, seven endpoints, TypeScript DTO/client layer and canonical six-tab UX baseline are implemented.

V2-8B — COMPLETE. First-level navigation, six governed tabs, server-driven list interaction, read-only Drawer and source/gap presentation are accepted.

V2-8 — COMPLETE. The governed Knowledge read model and inspectable UI are implemented without an editing or inference path.

V2-9A — COMPLETE. The governed metric dictionary, deterministic read-only metric projections, explicit unavailable metrics, six GET endpoints and frontend DTO/client contract are accepted.

V2-9 — IN PROGRESS. The visible Analytics UI and Exit Gate remain outstanding.

## Next Gate

V2-9B Analytics UI & V2-9 Exit Gate is NEXT and requires a separate phase Gate.

See [Current System Status](docs/CURRENT_SYSTEM_STATUS.md) and the [V2 Roadmap](docs/IMPLEMENTATION_ROADMAP_V2.md).
