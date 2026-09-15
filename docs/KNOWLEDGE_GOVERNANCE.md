# Knowledge Governance

> Status: CANONICAL
> Applies to: V2
> Last verified phase: V2-7A
> Owner: Project

This document is the hard constraint for creating, changing, loading, presenting, and measuring regulated knowledge.

## 1. Knowledge layers

Each layer has separate identity, provenance, lifecycle, and coverage:

1. **Monitor Reference** — objects in an authoritative monitoring/reference catalog.
2. **Operational Search** — validated SearchQueries used to discover marketplace Candidates.
3. **Claim Taxonomy** — normalized page-marketing topics and provenance-bearing extraction expressions; it does not contain official functions, RiskSignals, or inspection mappings.
4. **HealthFunction Framework** — official functions and transition aliases under a named jurisdiction/framework/version.
5. **Claim-to-Official-Function Mapping** — explicit project-governed `topic_related` mapping between page ClaimSignal and HealthFunction; never official equivalence.
6. **ClaimConsistencyAssessment** — current Snapshot-scoped derived comparison under recorded identity, Registry, Claim, framework, and mapping versions.
7. **Evidence-to-Risk Bridge** — verified link from observed Evidence/ClaimSignal to a RiskCategory.
8. **Risk-to-Substance** — explicit mapping from RiskCategory to a Substance or authoritative SubstanceGroup.
9. **Substance-to-Method** — declared analyte coverage in an InspectionMethod.
10. **Method Applicability** — contextual suitability for product category/form and regulatory use.
11. **Regulatory Documents** — source documents with jurisdiction and temporal scope.
12. **Health Food Registry** — authoritative registration/filing records and verbatim official functions.

Reference membership never implies operational-query readiness. Method coverage never implies a Risk mapping.

## 2. Dataset lifecycle

Target V2 lifecycle values are:

```text
development_seed
reference_pending
verified_reference
deprecated
superseded
```

Current governed datasets use supported subsets of these semantics. V2-4A normalizes SearchQuery lifecycle separately without changing SQLite schema. Do not rewrite other status values without a compatibility and migration decision.

- `development_seed`: useful for development/tests; not verified production knowledge.
- `reference_pending`: sourced candidate awaiting verification.
- `verified_reference`: source and mapping have passed the relevant governance gate.
- `deprecated`: retained for traceability but not used for new resolution.
- `superseded`: replaced by a named newer dataset/record while historical derivations retain the old version.

Published dataset releases are immutable. Corrections create a new version or explicit supersession.

## 3. Minimum provenance contract

Every regulated knowledge record or its enclosing dataset must be able to supply:

```text
dataset_id
dataset_version
status
source_name
source_reference
source_date
collected_at
verified_at
effective_from
effective_to
jurisdiction
notes
```

This is the target minimum. Existing configs may not yet carry every temporal/jurisdiction field; that is a **FUTURE CHANGE**, not permission to fabricate values. Missing provenance remains explicit.

Mappings additionally record stable IDs, source basis text where available, scope, evidence grade or equivalent verification basis, and both endpoints. Downstream artifacts record the dataset/version actually used.

## 4. Layer-specific governance

### 4.1 Monitor Reference and Operational Search

- Reference objects come from authoritative catalogs and retain object-level source links.
- SearchQuery variants state their source as `standard_name`, `official_alias`, `observed_product_form`, or `manually_curated`; guessed synonyms and generated aliases are prohibited.
- Lifecycle is `candidate_unvalidated`, `search_validated`, `rejected_low_relevance`, `paused_scope_issue`, or `deprecated`. Each enabled query must be `search_validated`.
- The tracked ledger preserves review decision and artifact SHA-256. Legacy pilots without V2-4 food-scope labels keep null metrics rather than reconstructed precision.
- Expansion follows Pilot → Validated Batch → Expanded Operational Set.

The fixed V2-4 promotion gate is at least 10 unique assessable results, observed relevance at least 0.70, at least 5 relevant results, and no systematic scope issue. Small samples remain on hold. This is observed sample relevance, never a recall or model-accuracy claim. See [MONITOR_QUERY_VALIDATION_PROTOCOL.md](MONITOR_QUERY_VALIDATION_PROTOCOL.md).

V2-4 Wave 1 applied that gate to six standard-name Queries. 山楂、沙棘、罗汉果、黑芝麻、蜂蜜 were promoted after human review; 乌梅 remains disabled with `paused_scope_issue` because stable medicinal-material/medicinal-use scope mixing was observed despite meeting the 70% numeric floor. The reviewed record is [MONITOR_QUERY_VALIDATION_RESULTS_V2_4_BATCH_01A.md](MONITOR_QUERY_VALIDATION_RESULTS_V2_4_BATCH_01A.md). Product-form observations remain notes rather than implicit new Queries.

Wave 2A applied the same unchanged gate to 山药、赤小豆、枸杞子、莲子; all four standard-name Queries were promoted after explicit human review. Their record is [MONITOR_QUERY_VALIDATION_RESULTS_V2_4_BATCH_02A.md](MONITOR_QUERY_VALIDATION_RESULTS_V2_4_BATCH_02A.md).

Wave 2B promoted the standard-name 菊花 Query and rejected the standard-name 百合 Query at 50% observed relevance. This rejects only the Query strategy; the official 百合 MonitorTarget remains in the Reference and may receive a new provenance-backed `manually_curated` candidate under a separate collection/review gate. The record is [MONITOR_QUERY_VALIDATION_RESULTS_V2_4_BATCH_02B.md](MONITOR_QUERY_VALIDATION_RESULTS_V2_4_BATCH_02B.md).

The refined `食用百合` Query records `derived_from_validation_batch=v2-4b-batch-02b` and the explicit scope-disambiguation rationale. Batch `v2-4b-batch-02c` independently reviewed the strategy at 90% observed relevance and promoted it as enabled `search_validated`. The standard-name `百合` Query remains disabled `rejected_low_relevance` with its 50% result intact, while the 百合 MonitorTarget is operational through the refined strategy. This is a governed chain from low-relevance standard name, to provenance-backed human refinement, to independent revalidation; `食用百合` is neither an official alias nor a new MonitorTarget. See [MONITOR_QUERY_VALIDATION_RESULTS_V2_4_BATCH_02C.md](MONITOR_QUERY_VALIDATION_RESULTS_V2_4_BATCH_02C.md).

### 4.2 Claims and official functions

- Page ClaimMentions, normalized ClaimSignals, official functions, RiskSignals, and disease/treatment vocabularies remain distinct.
- `config/claim_taxonomy_v2.json` version `claim-taxonomy-v2.0` is the governed design, runtime, filter-option, and presentation-label authority for page-marketing topics and the 26 audited legacy exact expressions. V2-5 consumes it for deterministic ClaimMention/ClaimSignal derivation and primary UI labels only. It contains no HealthFunction, Risk, substance, method, or inspection mapping.
- Every expression records stable identity, exact text, Claim type, match mode, source, status, and legacy trace where applicable. The migrated legacy entries use `source=legacy_system`, never `official_source`.
- Formal ClaimMention/ClaimSignal sources are current-product `seller_managed` Evidence only. UGC remains auxiliary; `excluded_other_product` is forbidden; a search keyword is not Evidence.
- Synonyms and marketing paraphrases require reviewed mapping records. V2-5 implements literal exact-expression occurrence matching only and no semantic-similarity equivalence.
- `config/health_functions_v2.json` version `health-functions-v2.0` is the V2-6A official framework design authority. Its non-nutrient catalog is complete 24/24; the nutrient-supplement framework is separate. Official transition aliases are exact Registry-normalization inputs, not marketing synonyms.
- `config/claim_health_function_mapping_v2.json` version `claim-health-function-mapping-v2.0` is an independent project-governed topic-mapping design authority. Every mapping records both endpoint versions, provenance, lifecycle, and relation `topic_related`; `male_function_related` remains an explicit no-mapping gap.
- Claim Taxonomy, HealthFunction Framework, ClaimHealthFunctionMapping, and ClaimConsistencyAssessment have independent identities, versions, provenance, and lifecycle. Updating one never silently updates another or a historical assessment.
- Future normalization preserves raw Registry functions plus resolved and unresolved sets. It accepts exact current/official-transition names only; fuzzy, embedding, LLM, edit-distance, substring, and ungoverned synonym resolution are prohibited.
- A claim-consistency assessment exposes recorded/not-recorded topic relations, evidence, official source, unresolved values, and gaps; it is not pass/fail adjudication and cannot emit RiskSignal or Recommendation.
- The legacy exact Effect-to-Risk bridge remains a separate compatibility runtime dataset. It must not be copied into the Claim taxonomy; replacement requires a later explicit Claim/Risk governance gate.

### 4.3 Evidence-to-Risk and Risk-to-Substance

- Search keywords are not Evidence.
- A Bridge requires an observed Snapshot Evidence/ClaimSignal and a verified mapping.
- Risk-to-group may remain group-level; it does not authorize expanding all possible members.
- A risk mapping signals an inspection direction, never actual product content.

### 4.4 Methods and applicability

- A method record states its official number/name, publisher, source, dates, status, and analyte facts.
- The Wide Reference Index is distinct from the Deep Verified Subset. `method_status` describes official lifecycle; `knowledge_depth` describes project verification depth. Neither substitutes for the other.
- The depth progression is `reference_only` → `analyte_verified` → `applicability_verified` → `recommendation_ready`. V2-7A uses it as an audit/design projection only; schema 12 does not persist it.
- Deep promotion requires official identity/source, explicit source-backed analyte relations, parsed scope, lifecycle, applicability handling and dataset/version provenance.
- Substance-to-Method means a method covers an analyte; it does not create a Risk mapping.
- Applicability requires explicit product context and basis. Include, conditional and exclude facts stay distinct. Unknown context or a missing applicability record stays “needs context”/unknown, not silently suitable or not applicable.
- Risk-to-Substance plus Substance-to-Method is still insufficient for a Recommendation until method depth, current lifecycle and product-context applicability pass.
- A Risk-to-SubstanceGroup mapping is not expanded from MethodSubstance, a matching name, CAS data, pharmacology or model knowledge.
- The current five methods are a small deep-parsed corpus, not a wide or nationally complete method index. Future reference-only candidates must remain outside Recommendation runtime until an explicit depth-aware storage/resolver gate exists.

### 4.5 Health-food registry

- Official records retain registration/filing identifier, product identity, holder/manufacturer where applicable, official functions, source, status, and temporal scope.
- Page logo or OCR number creates only a candidate.
- Verification requires authoritative lookup and documented matching; unavailable and mismatch states remain distinct.
- Current V2-3 online support is best-effort and governed by [HEALTH_FOOD_REGISTRY_SOURCE_AUDIT.md](HEALTH_FOOD_REGISTRY_SOURCE_AUDIT.md). Raw responses retain retrieval time and SHA-256; normalized records retain the source URL. A governed imported official snapshot is an allowed fallback, while third-party databases are not authoritative.
- Official function strings are preserved verbatim. No synonym, 24-function taxonomy, Claim equivalence, risk mapping or legality inference is created by registry import.

## 5. Forbidden inference

Never:

- infer a Risk mapping because a method detects a Substance;
- create Claim mapping from semantic similarity alone;
- write a regulatory mapping from general industry knowledge;
- generalize one historical product's substance to all similar products;
- use an LLM's medical knowledge to generate `verified_reference`;
- substitute a search keyword for page Evidence;
- use UGC-only Evidence as the sole basis for a formal `suggest_testing` recommendation;
- lower exactness or provenance requirements to improve hit rate;
- infer origin from search region, seller/manufacturer location, or surrounding products;
- infer official identity from a logo or unverified OCR identifier.

When a required link is absent, the output is `unknown`, `insufficient`, `unmapped`, or another explicit Knowledge Gap.

## 6. Change process

1. Identify the layer and stable IDs affected.
2. Capture authoritative source and temporal/jurisdiction metadata.
3. Add a new dataset version or scoped record; do not edit historical released meaning in place.
4. Validate schema, referential integrity, lifecycle and prohibited implicit mappings.
5. Run unit fixtures for positive, negative, ambiguous and missing cases.
6. Run an approved real-world validation set when required.
7. Record coverage change by layer and preserve prior derived/frozen history.

## 7. Coverage metrics

Report independently:

```text
Method Reference Coverage
Method Deep-Verification Coverage
Operational Query Coverage
Claim Coverage
Bridge Coverage
Risk→Substance Coverage
Substance→Method Coverage
Applicability Coverage
Recommendation Structural Reachability
Recommendation End-to-End Reachability
Official Identity Verification Coverage
```

Every metric defines numerator, denominator, dataset version, lifecycle inclusion, and observation period. The method Reference denominator is the committed project index unless an external official corpus has itself been governed; it is never an unstated universe of all methods. Context-applicable coverage requires a defined Product/Snapshot context corpus. A single blended “知识库覆盖率” is prohibited. The canonical Inspection formulas and V2-7A values are defined in [INSPECTION_KNOWLEDGE_COVERAGE_V2.md](INSPECTION_KNOWLEDGE_COVERAGE_V2.md).

## 8. Runtime and UI alignment

Knowledge UI and APIs must read the same governed runtime datasets used for derivation. No separate static UI knowledge copy or mock coverage is allowed. Presentation may summarize, but must preserve source links, version, status, scope, and Knowledge Gaps.
