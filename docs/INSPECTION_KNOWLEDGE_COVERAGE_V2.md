# Inspection Knowledge Coverage V2

> Status: CANONICAL DESIGN BASELINE
> Applies to: V2-7
> Baseline datasets: `inspection-reference@2026.09-b7`, `inspection-method-candidates-v2@2026.09-b2`, `risk-substance-reference@2026.09-c3`, `phase3-effect-risk-bridge@2026.09-d2`
> Owner: Project

## 1. Purpose

This contract separates the size of the project's official-method index from the depth required to drive an Inspection Recommendation. It defines auditable denominators and promotion gates without claiming coverage of every official Chinese inspection method.

V2-7A changed no runtime output. V2-7B1 implemented the additive schema/validation/resolver boundary. V2-7B2 adds exactly two first-party-verified Method identities at `reference_only` while preserving API/frontend behavior, Recommendation output, Risk mapping, Claim mapping, group membership and every existing analyte/applicability fact. The committed baseline is calculated offline by `scripts/audit_inspection_knowledge.py`.

## 2. Two knowledge sets

### 2.1 Wide Reference Index

The Wide Reference Index is the governed set of official InspectionMethod identities known to the project. An indexed method may be `reference_only`: its official number, title, publisher, source and lifecycle are sufficiently reliable for search, inventory and coverage reporting, while analytes, scope, applicability or risk relevance are not yet deep enough for Recommendation.

A reference-only method may be shown as indexed knowledge in a future Knowledge Base. It must not be exposed to the Recommendation resolver merely because it is current or because its title names a Substance.

The project has not defined the universe of every official method. Therefore an indexed count is valid, but a claim such as “5% of all official methods” is not.

### 2.2 Deep Verified Subset

The Deep Verified Subset contains indexed methods whose source-backed analyte relations, scope and applicability handling have passed the promotion gate. It is a subset of the Wide Reference Index.

Membership in the Deep Verified Subset means that a method may participate in a Recommendation path when every independent Risk, Substance, lifecycle and product-context condition is also satisfied. It does not mean the method applies to every product, that a target Substance is present, or that a Risk mapping exists.

## 3. Lifecycle and knowledge depth are independent

`method_status` describes official lifecycle:

- `current`
- `superseded`
- `revoked`
- `verification_pending`

`knowledge_depth` describes project parsing/verification depth:

- `reference_only`: official identity/source/lifecycle are indexed; analyte or scope depth is incomplete.
- `analyte_verified`: one or more explicit, source-backed Method→Substance relations exist; scope/applicability depth is incomplete.
- `applicability_verified`: analyte relations and source-backed applicability are parsed; the method may still be non-current.
- `recommendation_ready`: all static deep-verification gates pass and `method_status=current`.

These dimensions must never be collapsed. In particular:

- `current` does not mean deep verified.
- deeply parsed does not mean current.
- `verified_reference` at dataset level does not prove that a future reference-only row is Recommendation-capable.
- `recommendation_ready` is a static knowledge classification, not a product-level recommendation result.

Schema 13 persists `knowledge_depth` independently from `method_status`. The production validator applies conditional gates by depth, and the Recommendation resolver explicitly requests only `recommendation_ready` methods while lifecycle remains a separate check. Schema 12→13 migration assigns pre-existing rows the conservative `reference_only` default. The non-runtime candidate manifest remains outside DataStore and Recommendation; completed promotion traces point to the formal Method records without importing or counting them a second time.

## 4. Promotion gate

Promotion from `reference_only` into the Deep Verified Subset requires all of the following:

1. stable official method identity and number;
2. official title, publisher and retained first-party source/reference;
3. lifecycle status with publication/effective/supersession facts separated and gaps explicit;
4. each promoted Method→Substance relation backed by the official source label and identity evidence;
5. method scope parsed from an official basis;
6. product category/form/ingredient applicability represented by explicit source scope or explicit unknown;
7. negative and conditional scope retained rather than flattened into a positive relation;
8. dataset/version and record provenance retained;
9. deterministic validation with no dangling identity;
10. no Risk mapping inferred from analyte coverage.

Missing any gate leaves the method at its highest evidenced lower depth. A missing applicability record is `unknown`, not `not_applicable`.

## 5. Recommendation gate

A product-context Recommendation path requires:

1. a governed Evidence→Risk bridge for the observed legacy evidence pair;
2. a current verified Risk→explicit Substance mapping;
3. an explicit Method→Substance relation in the Deep Verified Subset;
4. a current method lifecycle;
5. a product-context applicability result from source-backed rules.

`applicable` or `conditional` may produce a suggested method under the existing D5 semantics. `insufficient_context` remains a context-review result. `not_applicable`, non-current methods and integrity gaps do not become primary suggested methods.

Recommendation availability is not proof that a Substance is present, a laboratory result, a risk probability, or an illegality conclusion.

## 6. Directionality boundaries

The allowed graph direction remains:

```text
Observed legacy Evidence
  → governed Risk category
  → governed Risk→Substance or Risk→SubstanceGroup mapping
  → explicit Method→Substance relation
  → applicability under confirmed Product Context
  → Inspection Recommendation
```

The following reverse or shortcut inferences are forbidden:

- Method detects Substance → create Risk→Substance.
- Substance exists in Inspection Reference → make it a member of a Risk group.
- Risk maps to Substance and Method detects Substance → recommend without applicability.
- ClaimSignal → RiskSignal, Substance or Method without a separately governed future bridge.
- method coverage → Substance presence in a product.

## 7. SubstanceGroup boundary

A Risk→SubstanceGroup mapping retains the source-native group label. It is distinct from:

- an explicit Risk→Substance mapping;
- a known Method→Substance relation;
- a governed group-membership relation;
- the unknown/unverified remainder of the group.

The current baseline has three group mappings, two unique group labels and zero governed group-membership relations. The audit and runtime must not expand those groups from similar names, method analytes, CAS identities, pharmacology or model knowledge. A category may retain an unresolved group gap while separately using source-backed explicit Substance mappings.

## 8. Applicability contract

Applicability source records have three current scope types:

- `include`: an explicit potentially applicable source scope; product context must match.
- `conditional`: a source-backed scope requiring the stated context/condition.
- `exclude`: an explicit negative fact for the stated Method/Substance/context.

For coverage reporting, the corresponding record classes are `explicit_applicable`, `requires_context`, and `explicitly_not_applicable`. A Method→Substance path with no applicable method-level or substance-level record is `unknown`.

These are source-scope classes, not a claim that an arbitrary product is applicable. Product-level output continues to use the existing `applicable`, `conditional`, `not_applicable`, and `insufficient_context` evaluator states.

## 9. RegulatoryDocument contract

Normalized `RegulatoryDocument` records include at least:

| Field | Meaning |
|---|---|
| `document_id` | Stable project identity. |
| `document_type` | Official method, standard, announcement, guidance, registry entry or other governed type. |
| `document_no` | Official document or standard number, if assigned. |
| `title` | Verbatim official title. |
| `publisher` | Official publisher. |
| `published_date` | Publication date, separate from effective date. |
| `effective_date` | Effective date when explicitly known. |
| `status` | Current, superseded, revoked, pending verification or equivalent governed lifecycle. |
| `source_reference` | Retained first-party source locator. |
| `jurisdiction` | Jurisdiction, normally `CN` for the current corpus. |
| `supersedes` / `superseded_by` | Directed document lifecycle links. |
| dataset/version provenance | Governing dataset identity and version. |

InspectionMethod references the document/database entry that defines it rather than relying only on a URL string. The current index normalizes seven source records and links all seven indexed methods. GB/T 5009.170-2003 and GB/T 45443-2025 retain distinct titles, lifecycle states and bidirectional predecessor/successor links.

## 10. Coverage metrics

Every metric is version-scoped and keeps its denominator. Percentages describe only the committed governed universe named below.

| Metric | Numerator | Denominator |
|---|---|---|
| Method Reference Coverage | Indexed methods passing the reference metadata/provenance gate | Methods in the committed Inspection Reference Index |
| Method Deep-Verification Coverage | Indexed methods at `recommendation_ready` static depth | Methods in the committed Inspection Reference Index |
| Substance→Method Coverage | Indexed Substances with at least one explicit Method relation | Substances in the committed Inspection Reference dataset |
| Applicability Coverage | Method→Substance paths with at least one relevant method-level or substance-level scope record | Method→Substance paths in the committed dataset |
| Risk→Substance Coverage | Explicit current Risk→Substance mappings | All current governed Risk target mappings, including group mappings |
| Group Resolution Coverage | Group mappings with separately governed complete member resolution | Current governed Risk→SubstanceGroup mappings |
| Recommendation Structural Reachability | Explicit current Risk→Substance mappings having a current deep method and applicability facts | Current explicit governed Risk→Substance mappings |
| Recommendation End-to-End Reachability | Structurally reachable explicit mappings whose Risk category also has a current Evidence→Risk bridge | Current explicit governed Risk→Substance mappings |
| Risk-category End-to-End Reachability | Governed Risk categories with at least one end-to-end explicit path | Risk categories in the current Risk mapping dataset |

Context-applicable coverage is evaluated only over a defined Product/Snapshot context corpus. It must not be reported from static knowledge alone.

## 11. Current V2-7B2 baseline

For `inspection-reference@2026.09-b7`, `inspection-method-candidates-v2@2026.09-b2`, `risk-substance-reference@2026.09-c3`, and `phase3-effect-risk-bridge@2026.09-d2`:

| Metric | Result |
|---|---:|
| Method Reference Coverage | 7 / 7 (100%) |
| Method Deep-Verification Coverage | 5 / 7 (71.4%) |
| Substance→Method Coverage | 117 / 117 (100%) |
| Applicability Coverage | 132 / 132 (100%) |
| Risk→Substance Coverage | 5 / 8 (62.5%) |
| Group Resolution Coverage | 0 / 3 (0%) |
| Recommendation Structural Reachability | 5 / 5 explicit mappings (100%) |
| Recommendation End-to-End Reachability | 3 / 5 explicit mappings (60%) |
| Risk-category End-to-End Reachability | 2 / 3 categories (66.7%) |

The reference percentage describes a deliberately bounded seven-method project index, not national coverage. Five methods form the Deep Verified Subset; BJS 202405 and revoked GB/T 5009.170-2003 intentionally remain `reference_only`. The operational bottlenecks remain group resolution and the independently governed Evidence→Risk boundary, not the raw number of identities or analyte links.

## 12. Versioning and reproducibility

- Each report records the audit contract and all three input versions.
- Changing a denominator requires a versioned dataset or contract change.
- Candidate-manifest records are always excluded from indexed-method denominators. After promotion, their formal Method records participate exactly once through the versioned Inspection Reference Index at their verified depth.
- Historical derived output retains its recorded knowledge version; no audit rewrites Evidence, Recommendation or frozen Sampling history.
- The offline audit validates configs through the production validators before calculating counts.

## 13. Non-goals

This contract does not add group members, analyte/applicability facts, Risk mappings, Claim→Risk mappings, Product Context inference, method ranking, a Knowledge Base UI, Analytics, legality judgments, laboratory findings, or risk probabilities. V2-7B2 adds two bounded reference identities but does not alter D2–D6 or existing Recommendation output.
