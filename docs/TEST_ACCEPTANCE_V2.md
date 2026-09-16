# Test and Acceptance V2

> Status: CANONICAL
> Applies to: V2
> Last verified phase: V2-8B
> Owner: Project

Testing is proportional to changed risk. A phase must pass targeted checks before broad regression. Real-world validation supplements deterministic tests; it never replaces them.

## 1. Universal gate

Every implementation report states the starting commit, changed files, schema/API/domain impact, targeted tests, broad tests required by the phase, real validation performed, known gaps, new commit, and git status. Do not change historical fixture hashes to force a pass.

## 2. Documentation gate

- All canonical files declare `Status: CANONICAL`, `Applies to: V2`, verified commit, and `Owner: Project`.
- Links resolve and canonical documents link to the right authority.
- Terminology matches the registry in Product Requirements.
- Current implementation and Future changes are distinguishable.
- Active docs identify schema 13 as the sole current schema; prior-version details remain only in archived or explicit migration history.
- Retired IA and `web/` do not appear as current.
- Archived material is marked non-normative and is never cited as a higher authority.
- A cold-start reader can answer the 16 canonical baseline questions without chat context.

## 3. Baseline regression commands

Run from repository root with the intended Python interpreter:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

Run frontend checks from `frontend/`:

```powershell
npm run test:workflow
npm run typecheck
npm run build
```

Historical Validation builder changes additionally run their dedicated test module(s). The exact targeted command should be reported from the current test filename, not copied from an obsolete handoff.

## 4. UX gate

Required deterministic coverage:

- product-list/filter/query and Snapshot selection workflows;
- Evidence Source Group presentation while preserving distinct Evidence records;
- sidebar session state and keyboard focus;
- lightbox open/close, `Esc`, zoom, previous/next and active evidence;
- recommendation failure that leaves Evidence/Review usable;
- one-Snapshot compressed and multi-Snapshot timeline behavior;
- loading, API error, true empty, missing image, long title, zero Evidence, unmapped Evidence, and historical Snapshot.

Required visual acceptance at 1440px and 1080px includes list-only and split-detail modes. Typecheck and production build are mandatory. Do not loop indefinitely for minor pixel differences.

## 5. ProductFact gate — Current V2-2

At minimum test:

- every fact has an explicit Snapshot and reconstructable source;
- missing origin remains absent and presents `—`;
- conflicting origins remain separate/conflicted rather than arbitrarily selected;
- OCR-derived and DOM-derived facts retain distinct methods and paths;
- exact source text/image is available;
- normalization does not overwrite raw value;
- search-page region, seller location and manufacturer location are never inferred as declared origin;
- re-import and historical Snapshot behavior preserve scope and provenance.
- strong-label allowlist and explicit exclusions cover title-only, UGC/Q&A, search region, shipping/seller/manufacturer/warehouse locations, raw-material origin and isolated OCR place wording;
- schema 8→9 migration preserves all pre-existing entity rows and human business state;
- extraction failure remains degradable and cannot change Analysis readiness or Review eligibility;
- DTO/presentation retains equal-value multi-source provenance and exposes conflicts without arbitration.

Real validation includes clear-origin, missing-origin and conflicting-origin pages reviewed against the artifact.

## 6. HealthFoodIdentity gate — Current V2-3

At minimum test:

- real positive with authoritative record match;
- logo-only negative/insufficient case;
- registration number mismatch;
- official record not found or source unavailable;
- ambiguous product name;
- conflicting page clues;
- record version/effective-state behavior;
- no boolean collapse and no automatic legal conclusion.
- current/legacy registration and filing formats, whitespace/punctuation/case normalization, invalid length/year and non-supported historical formats;
- ambiguous OCR characters retained without correction or lookup;
- UGC and recommendation-area exclusion, duplicate-source retention and multi-identifier conflict;
- found/not-found/unavailable/malformed provider results, fresh cache reuse, raw artifact/hash and normalized-record parsing;
- official health functions preserved verbatim with absent fields left `null`/`[]`;
- exact/formatting-only product-name match, missing strong name, title-only insufficiency and mismatch;
- schema 9→10 preservation, idempotent re-import, SQLite rebuild from artifact and old-run compatibility;
- identity/provider failure cannot alter Analysis, Review or Sampling;
- all ten states, separate page/official evidence, source link and OCR Lightbox behavior in frontend workflow coverage.

Real validation compares a bounded set with official records and preserves the lookup source/time.

## 7. Claim gate

### 7.1 V2-5A design baseline — Accepted history

Acceptance requires:

- `config/claim_taxonomy_v2.json` is machine-readable and versioned;
- Claim type and expression IDs are unique, and every expression references an existing Claim type;
- the actual legacy keyword set is read from `config/effect_keywords.json` and has exactly 100% one-to-one migration coverage;
- no legacy expression is silently lost, duplicated, or attributed to an unknown Claim type;
- every active expression has provenance, and legacy expressions are not represented as official-source vocabulary;
- seller-managed Evidence is the only formal Claim source; UGC is auxiliary and excluded-other-product content is forbidden;
- ClaimMention preserves raw text/Evidence trace while ClaimSignal preserves every mention/Evidence ID;
- ClaimSignal, HealthFunction, RiskSignal, and InspectionRecommendation have separate contracts;
- no Claim type or expression contains Risk, HealthFunction, legality, substance, method, or inspection mapping;
- deterministic schema/governance tests, full Python regression, Monitor regression, frontend workflow, typecheck, and build pass offline;
- the V2-5A acceptance itself left schema 10 and production Claim extraction unchanged.

### 7.2 V2-5B1 Claim runtime core — Accepted history

Acceptance requires:

- the strict runtime loader consumes only `config/claim_taxonomy_v2.json`, rejects duplicate/unknown IDs, unsupported modes, missing provenance, and forbidden cross-domain mappings;
- literal substring matching retains every configured overlapping expression and every repeated occurrence with deterministic IDs and ordering;
- only seller-managed Evidence creates formal ClaimMentions; UGC and `excluded_other_product` remain retained outside formal Claims, while SearchQuery/task keywords are never Claim input;
- each Mention retains raw/normalized text, expression identity, Evidence ID, asset type and source locator; each Signal retains every Mention/Evidence ID;
- zero Claim is a valid complete artifact, while missing and failed/invalid artifacts remain `not_generated` and `error`;
- schema 10→11 is additive, preserves all entities and human Review/Sampling state, and rebuilds Claim projections transactionally from `claim_analysis.json` without rerunning Detail/OCR/Phase3;
- Snapshot/detail APIs add Claim status/Mentions/Signals while legacy Effect fields remain available;
- Claim success/zero/failure cannot change Analysis readiness, Review eligibility/state, Sampling, Risk bridge, or Recommendation;
- pipeline, API, schema, compatibility, full Python, Monitor, frontend workflow, typecheck, and build regressions pass offline with zero live collection/OCR/network work.

### 7.3 V2-5B2 Claim presentation — Current

Acceptance requires:

- Product Overview, Product Detail, Review Queue, Inspection Workspace, and current Sampling read same-Snapshot V2 Claim projections without converting `detectedEffects`, Evidence keywords, UGC, excluded-other-product content, or SearchQuery into Claims;
- complete-with-Claims, complete-zero, not-generated, and error have distinct wording and visual semantics; red is reserved for actual Claim execution error;
- ClaimSignal uses an informational display label and expression count; ClaimMention expansion shows `rawText` before the matched expression, a friendly source type, and the existing Evidence trace or an explicit unavailable fallback;
- Product-list Claim summaries are batched from SQLite and never require per-row artifact I/O; exact `claim_type` filtering uses the representative Snapshot within the active filter scope and never falls back to legacy Effect;
- Claim presentation does not modify Review status/eligibility, Sampling membership, Risk output, or Recommendation output, and creates no Claim-to-HealthFunction or Claim-to-Risk causal edge;
- legacy `effect=`/`effects[]` contracts remain available, while active primary UI hides old Effect badges/keywords and frozen Sampling JSON/XLSX remains byte-semantics compatible and is not rewritten;
- Claim/API, legacy bridge, Recommendation, Review/Sampling, Monitor, full Python, frontend workflow, typecheck, and build regressions pass offline.

V2-5B2 exit validation discovered 500 Python tests / passed 499 / skipped 1; frontend workflow passed 30/30; typecheck and production build passed. The Claim-focused suite passed 35/35, legacy Effect/Risk bridge passed 28/28, Recommendation passed 29/29, Review passed 7/7, Sampling passed 23/23, and Monitor passed 32/32. No live collection, external network, taxonomy expansion, schema change, or frozen-history rewrite occurred.

### 7.4 V2-6A HealthFunction and consistency design — Current

Acceptance requires:

- first-party official source metadata for both 2023 frameworks and the official transition table;
- all 24 current non-nutrient functions with stable IDs, verbatim official names, unique framework ordinals, and complete provenance;
- the nutrient-supplement framework remains a distinct identity and is never flattened into the 24 non-nutrient functions;
- every official transition alias references an existing function and source; current-name/alias ambiguity is forbidden;
- Registry normalization accepts exact current names and exact official transition names, while unknown, typo, punctuation variant, substring, fuzzy, semantic, embedding, and LLM guesses remain unresolved;
- raw Registry function strings remain preserved beside resolved/unresolved identities;
- Claim↔HealthFunction mappings are explicit, versioned `topic_related` project governance, never official equivalence;
- the four approved topic mappings resolve valid Claim and HealthFunction IDs; `male_function_related` remains an explicit no-mapping gap;
- official aliases normalize Registry strings only and cannot approve or directly normalize an identical page Claim expression;
- assessment eligibility requires `HealthFoodIdentity.state == verified_match`, complete Claim analysis, and sufficient framework/function resolution;
- top-level and per-Claim state contracts are non-adjudicative and preserve unavailable, zero, unresolved, not-recorded, and no-mapping states;
- ClaimExpressionAttention is Mention/expression-scoped and remains `dataset_pending_manual_governance`; no topic-level substring classification is fabricated;
- ClaimSignal, HealthFunction, ClaimHealthFunctionMapping, ClaimConsistencyAssessment, RiskSignal, and InspectionRecommendation remain separate;
- production runtime, schema 11, API, frontend, Claim taxonomy, Risk/Recommendation, Review/Sampling, and frozen history remain unchanged;
- governance tests, Claim taxonomy, HealthFoodIdentity, Claim runtime, Monitor, full Python, frontend workflow, typecheck, and build pass offline.

V2-6A exit validation passed: HealthFunction/mapping/normalization governance passed 17/17; Claim-focused regression passed 35/35; HealthFoodIdentity/Registry passed 22/22; Monitor/Query regression passed 46/46; Python full regression discovered 517 / passed 516 / skipped 1; frontend workflow passed 30/30; typecheck and production build passed. Validation was offline and schema remained 11.

### 7.5 V2-6B1 Claim Consistency runtime core — Current

Acceptance requires:

- strict, provenance-bearing HealthFunction and Claim↔HealthFunction config loaders with unique IDs and valid references;
- exact current-name and exact official-transition Registry resolution only; whitespace/punctuation variants, substring, descriptive wrappers, fuzzy, semantic, embedding and LLM guesses remain unresolved;
- explicit or exact-function-derived framework resolution that never uses Claim/legacy Effect, with nutrient and non-nutrient frameworks kept separate;
- the accepted V2-6A A–L state/relation matrix and frozen precedence;
- partial unresolved official strings preserve exact positive evidence, while an uncertain negative becomes `mapping_unresolved`, never `function_topic_not_recorded`;
- `mentionAttentions=[]` and the pending-manual-governance gap remain explicit;
- `claim_consistency.json` is the authority; failures write a degradable error sidecar and do not change processing, Review eligibility/status, Sampling, Risk or Recommendation;
- schema 11→12 is additive and preserves all prior domain/human state; artifact re-import is idempotent and invalid artifacts clear stale projections transactionally;
- Snapshot Detail/workspace expose `claimConsistencyStatus`, `claimConsistency`, and `paths.claimConsistency`; missing, complete and error remain distinct;
- frontend adds types only and has no visible consistency UI;
- no Taobao, Detail, OCR or live Registry provider is used during validation;
- full Python, frontend workflow, typecheck and build regressions pass offline.

V2-6B1 exit validation passed: targeted HealthFunction/Claim consistency/Identity/Claim/pipeline/legacy Risk/Recommendation/Review/Sampling/Monitor regression passed 187/187; Python full regression discovered 532 / passed 531 / skipped 1; frontend workflow passed 30/30; typecheck and production build passed. Validation used zero Taobao, Detail, OCR, live Registry or other network access.

### 7.6 V2-6B2 consistency UX and V2-6 exit gate — Current

Acceptance requires:

- Product Detail and Inspection Workspace reuse one presentation mapper/component and consume the B1 API without reconstructing consistency in React;
- operational `not_generated | complete | error` remains separate from all seven complete-artifact domain states; only an actual consistency error uses red;
- all four per-Claim relations use explicit non-adjudicative wording and non-score colors; `function_topic_recorded` never approves ClaimMention wording, while `mapping_unresolved` never becomes a false `not recorded` result;
- partial unresolved output preserves exact positive relations while retaining the unresolved banner, full Registry raw text, and explicit normalization basis;
- page controls locate the existing ClaimSignal/ClaimMention/Evidence path and official controls reuse the existing HealthFoodIdentity Registry modal; missing trace is explicit and page/official facts remain separate;
- ClaimExpressionAttention remains `dataset_pending_manual_governance`; empty `mentionAttentions` never means zero disease/treatment/regulatory attention;
- no consistency column/filter/score/verdict is added, and Risk/Recommendation, Review, Sampling, schema 12, governed config, and frozen history remain unchanged;
- deterministic state/relation/trace/boundary workflow tests, backend cross-domain regression, full Python, typecheck, build, and offline 1440px/1080px UI acceptance pass.

V2-6B2 exit validation passed: targeted HealthFunction/Claim consistency/Identity/Claim/Recommendation/Review/Sampling regression passed 124/124; Python full regression discovered 532 / passed 531 / skipped 1; frontend workflow passed 38/38; typecheck and production build passed. Offline Product Detail and Inspection Workspace acceptance covered identity-not-verified, no-page-claims, assessed multi-Claim relations, official transition alias, long unresolved official text, partial positive plus unresolved negative protection, and 1440px/1080px layouts without page-level horizontal overflow. Validation used zero Taobao, Detail collection, OCR, live Registry, or other network access.

## 8. Knowledge gate

Every governed dataset change tests:

- required provenance and dataset/version identity;
- stable unique IDs and referential integrity;
- lifecycle and supersession behavior;
- temporal/jurisdiction fields where supplied;
- only eligible lifecycle records drive runtime results;
- no implicit Claim, Risk, Substance, Method, applicability, origin, or identity mapping;
- group mappings are not silently expanded;
- UI/API reads the same runtime dataset;
- per-layer coverage metrics use correct denominators.

### 8.1 Monitor coverage gate — Current V2-4 accepted baseline

- `scope=reference` returns exactly 106 formal Reference targets; default/`scope=operational` returns only targets satisfying the strict operational predicate.
- Every enabled Query is `search_validated`; every enabled target has at least one enabled validated Query.
- Candidate, rejected, paused, disabled, and deprecated queries cannot reach Discovery or monitor task execution.
- Reference-only targets remain visible but task creation returns `monitor_target_not_operational`; Quick Task remains unaffected.
- Availability DTOs, candidate/validated counts, validated chips, 当归 pause, full-name search, and disabled CTA have deterministic backend/frontend coverage.
- Multi-Query Candidate hits deduplicate by stable Product ID and share one task-level analysis cap.
- The tracked ledger covers every existing validated/rejected/paused governed Query; the V2-4B dry run resolves the bounded plan without browser or network access.
- Wave 1 review metrics are calculated from preserved rank-ordered human labels, not inferred from titles; English enum values remain stable while human-readable artifacts use Chinese labels.
- 山楂、沙棘、罗汉果、黑芝麻、蜂蜜 are operational through enabled `search_validated` standard-name Queries. 乌梅 remains visible as disabled `paused_scope_issue` and cannot pass the server execution guard.
- The manifest hash and decision notes are retained in the ledger; collection Query/raw artifacts remain immutable when reviewed artifacts are finalized.
- 山药、赤小豆、枸杞子、莲子 are operational through enabled `search_validated` standard-name Queries; their ledger metrics are program-derived from the explicit Wave 2A human labels.
- The 莲子 review skips ambiguous Rank 4 and uses Rank 11 as the tenth assessable result.
- 菊花 is operational through its enabled `search_validated` standard-name Query. The standard-name 百合 Query is disabled `rejected_low_relevance`; the 百合 MonitorTarget remains Reference-visible, non-operational, and server-rejected for task creation.
- A rejected Query is never enabled. Rejecting a Query does not remove or mark invalid its MonitorTarget, and the UI presents the target as needing a usable search strategy rather than as unsupported.
- The refined `食用百合` Query is `manually_curated`, retains its Batch 02B provenance/rationale, and is independently promoted through Batch 02C at 90% observed relevance. It is the only executable Query for the operational 百合 Target.
- The standard-name `百合` Query retains its Batch 02B 50% result as disabled `rejected_low_relevance`; promotion of the refined strategy never rehabilitates or executes it.
- Batch 02C skips ambiguous Rank 8, uses Rank 11 as the tenth assessable item, and calculates 10 assessable / 9 relevant / 1 raw-scope / 90% from explicit human labels.
- Reference remains 106 while actual operational coverage is 16/106. Coverage presentation and API keep these denominators distinct.

### 8.2 Inspection knowledge coverage gate — V2-7A accepted design baseline

- the audit loads all three governed configs through the production validators and performs no network access;
- current inventory is derived rather than hardcoded by the tool: 5 methods, 117 Substances, 132 Method→Substance relations, 37 applicability records, 1 regulatory context, 5 Risk→Substance mappings, 3 Risk→Group mappings, and 3 bridge mappings;
- every Method→Substance, applicability, Risk→Substance, and bridge reference identity is non-dangling;
- lifecycle status and audit `knowledge_depth` are independent; a superseded deep method remains traceable but is not Recommendation-ready;
- all five current methods retain official reference provenance and pass the static deep gate only for their explicit relations;
- group mappings remain unexpanded even if a Substance or Method record has a similar group label;
- adding a Method→Substance relation cannot create a Risk mapping;
- a missing applicability path remains an explicit unknown/gap and never becomes `not_applicable` or a positive Recommendation;
- include, conditional and exclude source facts remain distinct, and product-level applicability still requires explicit context;
- Method Reference, Deep Verification, Substance→Method, Applicability, Risk→Substance, Group Resolution, and Recommendation Reachability metrics each record numerator, denominator and dataset versions;
- Recommendation fixtures remain byte-for-byte semantically compatible; no schema, API, frontend, config record, Phase3, D2–D6, Review, Sampling, frozen history or runtime business output changes;
- V2-7A candidate records remain planning-only; V2-7B1 establishes the depth-aware storage/resolver gate without promoting them.

V2-7A exit validation passed offline: audit/governance tests 9/9; Inspection config/Risk/bridge/knowledge/applicability/Recommendation/runtime targeted regression 210/210; Claim/Consistency 49/49; Review/Sampling 30/30; Monitor/Discovery/Task 39/39; Python full regression discovered 541 / passed 540 / skipped 1; frontend workflow 38/38; typecheck and production build passed. No external network, collection, schema/API/frontend runtime change, knowledge-record promotion, or historical rewrite occurred.

### 8.3 Inspection reference index boundary — V2-7B1

- schema 12→13 preserves existing rows and assigns old method rows the conservative `reference_only` depth rather than silently promoting them;
- config schema 2 validates `reference_only`, `analyte_verified`, `applicability_verified`, and `recommendation_ready` with depth-appropriate requirements independent of lifecycle;
- all five current methods explicitly declare and satisfy `recommendation_ready`, link to one of five normalized RegulatoryDocument records, and retain their existing analyte/applicability semantics;
- ordinary reference queries may inspect all indexed depths, while the production Recommendation resolver explicitly admits only `recommendation_ready` and independently lifecycle-valid methods;
- a deterministic lower-depth method remains reference-visible but cannot appear in any Recommendation bucket;
- the candidate manifest contains exactly `candidate-bjs-202405` and `candidate-gbt-5009-170-2003`, is marked non-runtime, has no DataStore importer, and is excluded from every method coverage denominator;
- RegulatoryDocument identity, source, lifecycle and bidirectional supersession references are validated; the GB/T predecessor remains an explicit unresolved edge;
- the explicit SubstanceGroup membership validator/projection supports provenance and partial/complete scope, while the governed baseline remains zero rows and 0/3 resolved group mappings;
- existing Recommendation fixtures remain semantically unchanged, and no candidate/method/analyte/Risk/group mapping is added by B1;
- full offline Python and frontend regression passes without collection or network access.

V2-7B1 exit validation passed offline: focused Inspection/Reference/Risk/Recommendation regression 193/193; Python full regression discovered 552 / passed 551 / skipped 1; frontend workflow 38/38; typecheck and production build passed. The deterministic audit reports 5 indexed methods, 2 non-runtime candidates, 5 `recommendation_ready` methods, 5 RegulatoryDocuments/links, 1 unresolved lifecycle/document edge and 0 group memberships. No external retrieval, collection, candidate promotion, historical rewrite or visible UI behavior change occurred.

### 8.4 Bounded official-method promotion — V2-7B2

- exactly the two approved candidates have first-party verification traces and formal promoted Method identities; no additional method is added;
- BJS 202405 uses the official title `食品中西地那非、他达拉非等化合物的测定`, is current, remains `reference_only`, and has no MethodSubstance/applicability/Risk relation;
- the former BJS `weight_loss`/sibutramine planning rationale is explicitly invalidated and cannot become a runtime fact;
- GB/T 5009.170-2003 uses its own title `保健食品中褪黑素含量的测定`, remains distinct from GB/T 45443-2025, is revoked, and has bidirectional method/document lifecycle links to the current successor;
- both lower-depth records remain visible to reference queries but cannot appear in Recommendation; the operational method set remains BJS 201701 and BJS 201710 for the currently bridged paths;
- the candidate manifest remains non-runtime, records completed promotion trace, contributes no duplicate method count and has zero pending candidates;
- the deterministic audit reports 7/7 Method Reference Coverage, 5/7 Method Deep-Verification Coverage, 0 unresolved lifecycle/document edges and 0 group memberships;
- substances, MethodSubstance relations, applicability, Risk mappings, group mappings, group memberships, bridge mappings and Recommendation reachability remain unchanged;
- schema 13, API, frontend, Phase3, D2–D6, Review/Sampling and frozen history remain unchanged.

V2-7B2 targeted validation passed offline: Inspection/Reference/candidate/audit/knowledge/applicability/Recommendation/runtime/signal-trace/Risk/bridge regression 223/223. Per the bounded phase Gate, no full Python or frontend suite and no live collection were run.

### 8.5 Deep Verified Subset and V2-7 Exit Gate — V2-7C

- exactly BJS 202405 is deepened; no additional Method identity, Risk mapping, Claim mapping, group mapping or group member is added;
- the official full text supports 95 explicit Appendix A compound relations and seven method-level product-category scopes, with source labels/CAS and qualitative/quantitative intent retained;
- 11 existing Substance identities are reused by CAS and 84 new identities are added without reverse-inference into Risk or SubstanceGroup membership;
- BJS 202405 passes `recommendation_ready`; revoked GB/T 5009.170-2003 remains `reference_only` and cannot enter Recommendation;
- the deterministic audit reports 7/7 Method Reference Coverage, 6/7 Method Deep-Verification Coverage, 201/201 Substance→Method Coverage, 227/227 Applicability Coverage, 0/3 Group Resolution Coverage and 3/6 context-corpus Recommendation reachability;
- the six context cases cover BJS 202405 applicable, not-applicable and insufficient-context outcomes, existing BJS 201701 regression behavior, and a group target that remains unresolved without expansion;
- candidate b7 promotion metadata remains an immutable historical trace while b8 is the current Inspection Reference authority;
- production validators, SQLite rebuild projection and the existing Recommendation builder consume the same governed facts;
- schema 13, API, frontend, Phase3, D2–D6, Risk/Claim/bridge semantics, Review/Sampling and frozen historical artifacts remain unchanged;
- focused and full offline regression pass, and no Taobao or other live collection is performed.

V2-7C exit validation passed offline: focused Inspection/Reference/candidate/audit/knowledge/applicability/Recommendation/runtime/Risk/bridge regression 195/195; Python full regression discovered 555 / passed 554 / skipped 1; frontend workflow passed 38/38; typecheck and production build passed. V2-7 is COMPLETE; V2-8 remains a separate NEXT gate.

### 8.6 Knowledge read API and UX contract — V2-8A

- the seven Knowledge endpoints are GET-only and have no knowledge mutation path;
- the summary reports separate explicit counts rather than a blended completeness score;
- collection endpoints apply deterministic server-side query/filter before offset/limit pagination, reject invalid bounded values and return `items/count/total/limit/offset/hasMore`;
- all 106 governed Reference MonitorTargets are visible with operational, query-pending or paused state; Reference membership is not presented as Operational Search readiness;
- all 25 governed HealthFunction records are loaded through the existing strict runtime validator, preserve framework separation and expose exact transition aliases only as detail provenance;
- all 201 Inspection Substances expose method counts and explicit recorded/not-recorded regulatory-context/group metadata without implying product content;
- all 8 Risk mappings are traceable; all 3 group mappings remain unresolved with zero automatic member expansion, and Method analytes create no Risk mapping;
- all 7 InspectionMethods are queryable with lifecycle and knowledge depth as independent fields; the revoked `reference_only` predecessor remains visible but excluded from operational Recommendation;
- all 7 RegulatoryDocuments preserve official governed source links and supersession identity;
- source dataset/version/status and record-level provenance remain available to future detail views;
- Knowledge GET requests do not change Task, Review or Sampling business rows;
- frontend DTO/client/mapper contracts typecheck without a Sidebar, route or page implementation;
- schema 13, governed configs and all existing business semantics remain unchanged.

V2-8A validation passed offline: Knowledge read API/domain tests 9/9; targeted Knowledge/Inspection/Recommendation/Risk/HealthFunction/Monitor/local-API regression 168/168; frontend typecheck passed. Full Python regression, frontend workflow and production build were not required by this contract-only Gate. V2-8 remains IN PROGRESS; V2-8B is NEXT.

### 8.7 Knowledge Base UI and V2-8 Exit Gate — V2-8B

- the first-level 知识库 route contains exactly the six canonical domains and consumes only the V2-8A API client;
- summary cards render API counts and keep denominators separate, with no completeness, coverage, accuracy or risk score;
- every tab uses server-side query/filter/offset pagination and keeps state in the hash URL;
- loading, filtered-empty, API-error and content states remain distinct;
- Reference membership and Operational Search readiness remain separate;
- HealthFunction remains explicitly separate from ClaimSignal, including the nutrient-supplement framework boundary;
- Substance method coverage is described only as a knowledge relation, never product presence or detection;
- group-level Risk mappings remain unresolved/partial/complete facts and are never expanded from Method analytes;
- Method lifecycle and project knowledge depth render independently; revoked `reference_only` GB/T 5009.170-2003 remains visible and states that it cannot drive Recommendation;
- RegulatoryDocument source links use only governed HTTP(S) references and preserve supersession identity;
- `not_recorded`, paused, unresolved, partial and depth gaps use distinct non-error presentations; red is reserved for API/runtime error;
- tabs, labeled filters, row actions, source links and focus-managed Drawer remain keyboard accessible;
- local acceptance at 1440px and 1080px covers long titles, 201-Substance pagination and Drawer without page-level horizontal overflow;
- no knowledge mutation, static catalog, browser relation inference, schema/config change or Discovery/Claim/Risk/Recommendation/Review/Sampling behavior change exists.

V2-8B exit validation passed offline: targeted Knowledge/API/domain regression 168/168; Python full regression discovered 564 / passed 563 / skipped 1; frontend workflow 43/43; typecheck and production build passed. V2-8 is COMPLETE; V2-9 Analytics is NEXT.

## 9. Pipeline and Review gate

- Search Candidate is not Detail success or Review eligibility.
- Detail, OCR input, OCR, analysis, recommendation and Review readiness are independently tested.
- No OCR inputs and zero successful OCR images are failures; partial success preserves failed manifest items.
- Analysis success with zero Evidence still counts as analysis-complete and Review-eligible.
- Recommendation error does not block an otherwise eligible Review.
- Detail/OCR/analysis failure cannot enter business pendingReview or accept Review mutation.
- Mixed-result integration contains successful, Detail-failed, OCR-failed, and search-only products and validates task-flow counts/states.
- Current Product Membership based on an old Snapshot does not mark a new pending Snapshot as reviewed.

## 10. Data migration/API gate

Any future schema change requires forward migration from the current schema, old-data preservation, invariant tests, import/rebuild behavior, transaction rollback tests, and an explicit downgrade/backup statement. API changes require DTO contract tests, compatibility decisions, filter/pagination tests, path containment, and N+1 review.

No roadmap entry by itself authorizes schema/API work.

## 11. Real collection gate

Live Taobao access requires explicit user authorization and a minimal bounded run. Never bypass CAPTCHA or verification. Record run ID, environment, task parameters, first failure, diagnostic artifacts, Detail/OCR/analysis/recommendation counts, and whether each acceptance artifact exists. Stop at the first new contract blocker rather than mass-retrying products.

## 12. Acceptance result

Use only:

```text
PASS — <phase-specific accepted baseline>
```

or:

```text
FAIL — <remaining contradictions or blockers>
```

A partial test run cannot support a full PASS unless the approved phase gate explicitly limits scope.
