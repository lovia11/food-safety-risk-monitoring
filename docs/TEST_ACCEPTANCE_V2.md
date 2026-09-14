# Test and Acceptance V2

> Status: CANONICAL
> Applies to: V2
> Last verified phase: V2-6A
> Owner: Project

Testing is proportional to changed risk. A phase must pass targeted checks before broad regression. Real-world validation supplements deterministic tests; it never replaces them.

## 1. Universal gate

Every implementation report states the starting commit, changed files, schema/API/domain impact, targeted tests, broad tests required by the phase, real validation performed, known gaps, new commit, and git status. Do not change historical fixture hashes to force a pass.

## 2. Documentation gate

- All canonical files declare `Status: CANONICAL`, `Applies to: V2`, verified commit, and `Owner: Project`.
- Links resolve and canonical documents link to the right authority.
- Terminology matches the registry in Product Requirements.
- Current implementation and Future changes are distinguishable.
- Active docs identify schema 11 as the sole current schema; prior-version details remain only in archived or explicit migration history.
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

### 7.5 Future V2-6B runtime gate

At minimum test the accepted V2-6A A–L state/relation matrix, Snapshot isolation, version changes, artifact authority/rebuild, exact raw/resolved preservation, unresolved and unavailable sources, API/presentation wording, and independence from Review, Sampling, Risk, and Recommendation. Runtime output must expose compared Claims/functions, Evidence/source trace and gaps rather than pass/fail.

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
