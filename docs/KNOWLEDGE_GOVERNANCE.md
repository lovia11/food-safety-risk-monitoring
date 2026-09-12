# Knowledge Governance

> Status: CANONICAL
> Applies to: V2
> Last verified against commit: `bbe992e54f9fc583b312f919f32f91f43e53fb06`
> Owner: Project

This document is the hard constraint for creating, changing, loading, presenting, and measuring regulated knowledge.

## 1. Knowledge layers

Each layer has separate identity, provenance, lifecycle, and coverage:

1. **Monitor Reference** — objects in an authoritative monitoring/reference catalog.
2. **Operational Search** — validated SearchQueries used to discover marketplace Candidates.
3. **Claim Taxonomy** — normalized official, marketing, risk, and disease/treatment terms.
4. **Claim-to-Official-Function Mapping** — explicit mapping between page expression and official health function.
5. **Evidence-to-Risk Bridge** — verified link from observed Evidence/ClaimSignal to a RiskCategory.
6. **Risk-to-Substance** — explicit mapping from RiskCategory to a Substance or authoritative SubstanceGroup.
7. **Substance-to-Method** — declared analyte coverage in an InspectionMethod.
8. **Method Applicability** — contextual suitability for product category/form and regulatory use.
9. **Regulatory Documents** — source documents with jurisdiction and temporal scope.
10. **Health Food Registry** — authoritative registration/filing records and official functions.

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

Current governed datasets already use supported subsets of these semantics; **FUTURE CHANGE** phases may normalize lifecycle handling. Until then, do not rewrite status values without a compatibility and migration decision.

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
- SearchQuery variants state their source (standard name, official alias, or reviewed operational expression).
- Each enabled operational query has a validation state and retrieval assessment.
- Expansion follows Pilot → Validated Batch → Expanded Operational Set.

### 4.2 Claims and official functions

- Page expressions, official functions, risk-related claims, and disease/treatment expressions remain distinct.
- Synonyms and marketing paraphrases require reviewed mapping records.
- Official-function mappings require the applicable official framework/version.
- A claim-consistency assessment exposes matches, unmatched claims, evidence, official source, and gaps; it is not pass/fail adjudication.

### 4.3 Evidence-to-Risk and Risk-to-Substance

- Search keywords are not Evidence.
- A Bridge requires an observed Snapshot Evidence/ClaimSignal and a verified mapping.
- Risk-to-group may remain group-level; it does not authorize expanding all possible members.
- A risk mapping signals an inspection direction, never actual product content.

### 4.4 Methods and applicability

- A method record states its official number/name, publisher, source, dates, status, and analyte facts.
- Substance-to-Method means a method covers an analyte; it does not create a Risk mapping.
- Applicability requires explicit product context and basis. Unknown context stays “needs context,” not silently suitable.

### 4.5 Health-food registry

- Official records retain registration/filing identifier, product identity, holder/manufacturer where applicable, official functions, source, status, and temporal scope.
- Page logo or OCR number creates only a candidate.
- Verification requires authoritative lookup and documented matching; unavailable and mismatch states remain distinct.

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
Reference Coverage
Operational Query Coverage
Claim Coverage
Bridge Coverage
Risk→Substance Coverage
Substance→Method Coverage
Applicability Coverage
Official Identity Verification Coverage
```

Every metric defines numerator, denominator, dataset version, lifecycle inclusion, and observation period. A single blended “知识库覆盖率” is prohibited.

## 8. Runtime and UI alignment

Knowledge UI and APIs must read the same governed runtime datasets used for derivation. No separate static UI knowledge copy or mock coverage is allowed. Presentation may summarize, but must preserve source links, version, status, scope, and Knowledge Gaps.
