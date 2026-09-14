# Domain Model V2

> Status: CANONICAL
> Applies to: V2
> Last verified phase: V2-6B1
> Owner: Project

This document governs current and future schema/API domain work. ProductFact, HealthFoodIdentity, ClaimMention, ClaimSignal, and the ClaimConsistencyAssessment read projection are current in schema 12. HealthFunction, HealthFunctionAlias, and ClaimHealthFunctionMapping retain the V2-6A governed knowledge baseline and are consumed by the V2-6B1 runtime without becoming mutable business entities. Entities explicitly labeled “Future runtime” remain proposals rather than migration authorization.

## 1. Modeling rules

- Product is a stable marketplace identity; ProductSnapshot is one time-scoped observation.
- Page claims, declared origin, health-food identifiers, Evidence, and analysis belong to the Snapshot that supplied them.
- All derived facts retain provenance to source artifacts and knowledge versions.
- Observation, normalized fact, risk interpretation, recommendation, Review, and Sampling are separate states.
- Missing or conflicting information is represented explicitly, not filled by inference.

## 2. Entity catalog

| Entity | Purpose and identity | Scope / mutability | Provenance and relationships | Lifecycle / implementation / storage |
|---|---|---|---|---|
| Task | One execution/request, identified by `task_id`/run identity. | Task-scoped; runtime state mutable, historical config stable. | Owns queries, Candidates and Snapshots; display name also belongs in persistent run metadata. | **Current.** SQLite index plus run artifacts. |
| MonitorTarget | Governed Reference object identified by dataset + `target_id`; operational availability is derived separately. | Dataset-scoped; versioned, not silently edited in place. | Has source provenance and zero or more SearchQueries. | **Current V2-4A.** Governed JSON imported/indexed in SQLite; availability is a read projection. |
| SearchQuery | Search strategy identified by `query_id`, not a synonym dictionary entry. | MonitorTarget/version scope; reviewed lifecycle and enablement mutable through governance. | Belongs to one MonitorTarget; records source, validation and assessment. | **Current V2-4A.** Governed JSON, tracked validation ledger and SQLite read model. |
| CandidateHit | Search-result observation identified within task/query/result ordering. | Run/query-scoped, immutable observation. | Links Task, SearchQuery and potential Product identity; is not Detail success. | **Current.** Run artifacts and SQLite monitor tables. |
| Product | Stable marketplace item identity, normally marketplace product ID. | Cross-run; mutable presentation aggregates, stable identity. | Has many ProductSnapshots and at most one current SamplingMembership. | **Current.** SQLite. |
| ProductSnapshot | One concrete observation, identified by `snapshot_id`. | Product + Task + observed-time scoped; source facts immutable after capture. | Owns Evidence, analysis, ProductFacts, ClaimMentions/ClaimSignals, Review, and recommendation. | **Current** core; future relations extend it. SQLite index + run artifacts. |
| Evidence | Source-preserving observation, identified by `evidence_id`. | Snapshot-scoped; immutable historical observation. | Points to exact artifact/source text, origin class and analysis hit. | **Current.** SQLite index with underlying run artifact authority. |
| ProductFact | Normalized page fact with raw source and verification state. | Snapshot-scoped; derived projection is rebuildable, source immutable. | Derived from exact DOM/OCR artifact; future context and identity logic may consume it only through separately approved contracts. | **Current V2-2.** `product_facts.json` authority + generic SQLite table/read model; only `declared_origin` exists. |
| ClaimMention | One observed page expression occurrence, identified by `claim_mention_id`. | Snapshot- and Evidence-scoped; derived and versioned without replacing source text. | Retains raw/normalized text, exact matched expression, seller-managed source scope, asset type/locator, extraction method and taxonomy version. | **Current V2-5.** `claim_analysis.json` authority plus the schema 11 Claim projection retained in schema 12 and Evidence-linked presentation. |
| ClaimSignal | One governed marketing topic aggregated from one or more ClaimMentions, identified by `claim_signal_id`. | Snapshot-scoped; derived and versioned. | References complete same-Snapshot mention/Evidence sets and a governed `claim_type`; it is neither an Effect fact, HealthFunction nor RiskSignal. | **Current V2-5.** Current Effect hits remain a separate legacy operational path. |
| ClaimTaxonomyTerm | Governed page-marketing topic identified by stable `claim_type`. | Knowledge-dataset scoped; versioned lifecycle. | V2 Claim terms are separate from official HealthFunction, Risk and disease/treatment vocabularies; any cross-layer relation requires an explicit governed mapping. | **Current V2-5 runtime/filter/presentation authority.** `config/claim_taxonomy_v2.json`. |
| HealthFoodIdentity | Resolution for whether a Snapshot matches an official health-food product. | Snapshot-scoped assessment; re-evaluable under recorded sources. | Uses page identity clues and registry records; never logo/number-only. | **Current V2-3.** `health_food_identity.json` authority + SQLite read projection. |
| HealthFoodRegistryRecord | Official registration/filing record, identified by authoritative registry identifier. | Identifier/retrieval-time scoped; cached with freshness metadata. | Provides official product identity and verbatim official functions with source provenance. | **Current V2-3.** Raw official artifact/cache + normalized SQLite projection. |
| HealthFunction | Official current function identified by stable `function_id` under a stable `framework_id`. | Knowledge-dataset, jurisdiction and framework-version scope. | Preserves verbatim official name/source; never contains Claim, Risk, substance or method meaning. | **Current governed runtime input V2-6B1.** `config/health_functions_v2.json`; no mutable schema table. |
| HealthFunctionAlias | Exact officially documented historical/transition name for one HealthFunction. | Knowledge-dataset and official-source scope. | Used only to normalize Registry strings while preserving raw text; never a marketing synonym. | **Current governed runtime input V2-6B1.** Governed in the HealthFunction dataset. |
| ClaimHealthFunctionMapping | Explicit project-governed topic relation between one Claim type and one HealthFunction. | Mapping-dataset/version scope. | Relation is `topic_related`, never official equivalence, approval, Risk or inspection knowledge. | **Current governed runtime input V2-6B1.** `config/claim_health_function_mapping_v2.json`; no mutable schema table. |
| ClaimConsistencyAssessment | Non-adjudicative comparison result for one Snapshot. | Snapshot + verified identity/Registry record + Claim/knowledge-version scope; derived and reproducible. | Retains raw/resolved/unresolved official functions, Claim/Mention IDs, per-Claim topic relations, empty governed attention output and explicit gaps. | **Current V2-6B1 runtime.** `claim_consistency.json` authority + schema 12 rebuildable read projection; UI is future V2-6B2. |
| RiskSignal | Supported risk direction derived from Evidence through a verified bridge. | Snapshot-scoped; derived and versioned. | Links ClaimSignal/Evidence to RiskCategory; does not assert substance presence. | **Future explicit entity;** current bridge result is embedded in analysis/recommendation projections. |
| RiskCategory | Governed risk direction, identified by stable category ID. | Knowledge-dataset scope; versioned lifecycle. | Links through verified mappings to Substance or SubstanceGroup. | **Current knowledge concept.** Governed config + SQLite knowledge index. |
| Substance | Specific analyte/compound, identified by governed `substance_id`. | Knowledge-dataset scope; versioned. | Linked to groups, methods and regulatory context. | **Current.** Governed inspection config + SQLite. |
| SubstanceGroup | Governed group named by authoritative source. | Knowledge/version scope; must not be expanded by assumption. | Risk mappings may target a group without implying every member. | **Current concept** in risk mappings; future normalized storage may be required. |
| InspectionMethod | Official or governed method, identified by `method_id`. | Knowledge/version/effective-time scope. | Links to analytes and source documents. | **Current.** Governed config + SQLite. |
| InspectionApplicability | Contextual rule for whether a method is suitable. | Method + product-context scope; versioned. | Requires explicit method/product-form/category basis and provenance. | **Current.** Governed config + SQLite. |
| InspectionRecommendation | Derived method assistance for one Snapshot/context/knowledge version. | Snapshot-scoped derived artifact; regenerable, not adjudicative. | Uses Evidence, context, risk mapping and applicability; records gaps. | **Current.** `inspection_recommendation.json` + SQLite/workspace projection. |
| Review | Human judgment identified by Snapshot. | Snapshot-scoped; mutable until business workflow freezes it. | May be pending, follow-up, or no-further-action; independent repository from Sampling. | **Current.** SQLite. |
| SamplingMembership | Membership of one Product in the current working list. | Product/current-list scoped; mutable. | Records source Snapshot; does not own a separate MVP note and does not rewrite Review. | **Current.** SQLite. |
| SamplingFrozenList | Immutable exported list, identified by `list_id`. | Export-time snapshot, immutable. | Contains frozen JSON/XLSX/evidence and item-index text identifiers. | **Current.** Files are historical fact; SQLite indexes list ownership. |
| RegulatoryDocument | Authoritative source document and version/effective metadata. | Jurisdiction/time scoped; versioned. | Supports registry, taxonomy, risk, method, and applicability knowledge. | **Future normalized entity;** current configs preserve source fields inline. |
| KnowledgeDataset | Versioned governed collection, identified by dataset ID/version. | Dataset scope; immutable releases with lifecycle. | Owns provenance and entries; downstream artifacts record the version used. | **Current concept, partially represented** in governed JSON and SQLite imports. |

## 3. Product and Snapshot boundary

Product answers “which marketplace listing is this?” ProductSnapshot answers “what did that listing show at this observation time?” Product-level aggregation may show the latest or a filtered representative Snapshot, but it must not move Snapshot facts into Product identity.

The following are observations and therefore Snapshot-scoped unless a future reviewed projection explicitly promotes them:

- page Claim and OCR hit;
- search-page region and declared origin;
- health-food logo or registration-number clue;
- ingredients, category and form;
- Evidence, analysis, recommendation and Review.

Current Sampling Membership is intentionally Product-scoped. Its `source_snapshot_id` explains the evidentiary basis and may differ from the Snapshot currently being reviewed.

## 3.1 MonitorTarget and SearchQuery availability — CURRENT V2-4A

```text
Operational MonitorTarget = target.enabled
  AND exists(query.enabled AND query.validation_status == search_validated)
```

Reference targets without a runnable Query are `query_pending`; targets retained with an explicit low-relevance, scope, or deprecation decision are `paused`. Query lifecycle is `candidate_unvalidated`, `search_validated`, `rejected_low_relevance`, `paused_scope_issue`, or `deprecated`. `query_source` is `standard_name`, `official_alias`, `observed_product_form`, or `manually_curated`. Historical SQLite defaults `unvalidated`/`manual` are compatibility-only and project to current read semantics; no schema migration is introduced.

## 4. ProductFact contract — CURRENT V2-2

Generic fields:

```text
fact_id
snapshot_id
fact_type
normalized_value
raw_value
source_type
content_origin
source_path
source_text
extraction_method
verification_state
created_at
```

Schema 9 added only the generic `product_facts` table and its indexes. `product_facts.json` is the derived artifact authority; SQLite rows are deleted and rebuilt for each imported Snapshot without modifying Review, Sampling, Evidence, Analysis or source artifacts.

The current cardinality is one retained fact per explicit source occurrence. A normalized value can therefore have multiple DOM/OCR sources. Equal values present as `single` with multiple sources; distinct values present as `conflict`. The system does not choose a winner. Missing facts present as `none`/`—` and never create placeholder rows.

Only `fact_type=declared_origin` is implemented. `verification_state=extracted` records a conservative page extraction, not independent geographic verification. New fact types, human fact editing/supersession, and official-registry facts require separate gates.

`source_type` currently distinguishes seller-managed DOM parameters and detail-image OCR. `content_origin` remains explicit. A value without an exact source is not a ProductFact. Search region, title-only wording, UGC/Q&A, shipping/seller/manufacturer/warehouse location and raw-material origin are explicit non-sources for `declared_origin`.

## 5. Health-food identity contract — CURRENT V2-3

HealthFoodIdentity uses the following exhaustive presentation states:

```text
no_indicator
candidate_indicator_only
candidate_identifier
identifier_ambiguous
registry_lookup_unavailable
registry_record_not_found
registry_record_found_identity_unverified
verified_match
identity_mismatch
conflict
```

A boolean `is_health_food` cannot represent unverified clues, mismatched registration numbers, unavailable official records, or ambiguous names. `verified_match` requires one valid unambiguous identifier candidate, an authoritative record match, and an explicit page product name equal to the official product name after formatting-only normalization. A marketplace marketing title is auxiliary and cannot satisfy this condition.

`health_food_identity.json` records `clues[]`, `identifierCandidates[]`, provider lookup, product-match assessment, gaps and diagnostics. Each page candidate keeps source type/path/text, content origin and extraction method. The raw official response remains an artifact with source, retrieval time and SHA-256; the identity tables introduced in schema 10 and retained by schema 12 store only normalized record fields, JSON arrays and artifact references.

Official health functions are preserved verbatim as `officialHealthFunctions[]`. V2-6A defines the separate governed HealthFunction/official-transition dataset and project-governed topic-mapping contract; V2-6B1 resolves those Registry strings by exact governed identity and compares formal Claim topics without rewriting the Registry record. Identity and consistency enrichment have no Review/Sampling side effect and are not part of `reviewEligible`.

## 6. Claim domain contract — CURRENT V2-5 runtime and primary presentation

```text
ProductSnapshot
  → seller-managed Evidence
  → ClaimMention
  → ClaimSignal
```

ClaimMention preserves one actually observed expression occurrence. Its minimum fields are `claim_mention_id`, `snapshot_id`, `raw_text`, `normalized_text`, `matched_expression`, `evidence_id`, `source_scope`, `source_asset_type`, `source_locator`, `extraction_method`, `taxonomy_version`, and `created_at`. Character offsets are not required until supported uniformly by the Evidence locator contract.

ClaimSignal normalizes same-Snapshot ClaimMentions into a governed marketing topic. Its minimum fields are `claim_signal_id`, `snapshot_id`, `claim_type`, `display_label`, `mention_ids`, `evidence_ids`, `taxonomy_version`, `status`, and `created_at`. Arbitrary `claim_type` strings are invalid, and every linked Mention/Evidence identity must be retained.

Formal Claim input is seller-managed Evidence only. UGC remains auxiliary and `excluded_other_product` is forbidden. OCR-derived mentions must retain their Evidence/image trace. Search keywords are discovery input, not Evidence. See [CLAIM_TAXONOMY_V2.md](CLAIM_TAXONOMY_V2.md).

`claim_analysis.json` is the Snapshot-derived authority. Mention identity is a deterministic hash of Snapshot ID, Evidence ID, governed expression ID, and same-expression occurrence ordinal. Signal identity is a deterministic hash of Snapshot ID, Claim type, and taxonomy version. Every literal occurrence is retained, including overlaps between governed expressions; output order is Evidence order → taxonomy expression order → occurrence order, followed by taxonomy Claim-type order for signals.

Schema 11 introduced Claims in `claim_mentions`, `claim_signals`, and `claim_signal_mentions`; schema 12 retains them unchanged. Re-import transactionally replaces one Snapshot's derived projection without modifying Review, Sampling, ProductFact, HealthFoodIdentity, Evidence authority, or legacy Phase3 fields. A complete artifact with empty arrays is a successful zero-Claim result. Missing artifact is `not_generated`; invalid or failed sidecar is `error`. Claim availability is not a Review eligibility gate.

V2-5B2 projects compact ClaimSignal summaries from those SQLite rows for Product lists, Review Queue, and current Sampling without reading per-row artifacts. Every summary remains tied to the representative/source Snapshot; Claim history is not aggregated across a Product. Primary UI never synthesizes ClaimSignal from the separate legacy Effect fields.

### 6.1 Cross-domain separation

```text
ClaimSignal ≠ HealthFunction ≠ RiskSignal
```

- ClaimMention records the exact page wording and source; ClaimSignal records how one or more mentions were normalized into a marketing topic.
- HealthFunction records what an applicable official record permits as a normalized function.
- RiskSignal records a supported risk direction reached through a governed Evidence-to-Risk bridge.

Mappings between these entities are first-class governed knowledge with provenance and lifecycle. Lexical similarity is not a mapping.

The initial five Claim types are not a five-class official health-function model. Claim status describes extraction/governance only and cannot express legality or compliance.

### 6.2 HealthFunction and Claim consistency — CURRENT V2-6B1 RUNTIME CORE

`health-functions-v2.0` defines two independent framework identities: the complete 24-function 2023 non-nutrient catalog and the separate 2023 nutrient-supplement catalog root. Stable IDs are decoupled from official display names. Forty exact, source-backed transition aliases resolve historical Registry strings to current non-nutrient function identities. Exact current name, exact official transition name, and a future explicit governed mapping are the only normalization sources; unresolved strings remain explicit.

`claim-health-function-mapping-v2.0` establishes four `topic_related` project mappings for sleep, weight management, blood lipid, and blood pressure. `male_function_related` remains `no_governed_health_function_mapping`. Topic relation is not wording approval or official equivalence.

`ClaimConsistencyAssessment` performs formal comparison only for `HealthFoodIdentity.state == verified_match`, complete Claim analysis, and sufficient framework/function resolution. Its top-level states are `identity_not_verified`, `claim_not_generated`, `claim_analysis_error`, `framework_unresolved`, `official_function_unresolved`, `no_page_claims`, and `assessed`. Per-Claim relations are `function_topic_recorded`, `function_topic_not_recorded`, `no_governed_function_mapping`, and `mapping_unresolved`. Partial unresolved official strings preserve an exact positive relation but prevent an uncertain negative from becoming `function_topic_not_recorded`. `mentionAttentions` remains empty with an explicit pending-governance gap. See [HEALTH_FUNCTION_FRAMEWORK_V2.md](HEALTH_FUNCTION_FRAMEWORK_V2.md) and [CLAIM_CONSISTENCY_V2.md](CLAIM_CONSISTENCY_V2.md).

Schema 12 adds `claim_consistency_status`/`claim_consistency_path` to ProductSnapshot plus `claim_consistency_assessments`, `claim_consistency_official_functions`, and `claim_consistency_claims`. These rows are rebuildable from the sidecar and are transactionally cleared when the artifact is invalid. The governed HealthFunction and mapping datasets remain versioned config authorities rather than mutable SQLite knowledge tables.

## 7. Review and Sampling invariants

1. Only `reviewEligible` Snapshots enter the business pending queue or accept Review decisions.
2. A Review decision never implicitly changes historical Reviews on other Snapshots.
3. `recommend_follow_up` can coexist with no current Membership after export or manual removal; it remains an already reviewed decision.
4. A current Membership may coexist with a newly pending Snapshot of the same Product.
5. Creating/reaffirming a Membership from a Review is an application transaction, not coupled repository behavior.
6. Restoring Membership requires its source Snapshot Review to remain `recommend_follow_up` in the same transaction.
7. A frozen list remains reconstructable from frozen content even if source runtime entities disappear.

## 8. Storage guidance

- Raw observation and processing artifacts remain under the run directory.
- SQLite stores queryable identities, relations, current business state, and indexes.
- Governed knowledge is released as versioned datasets and may be imported into read tables.
- Derived artifacts record source and dataset versions and can be regenerated without rewriting source Evidence.
- `claim_analysis.json` is the derived authority for ClaimMention/ClaimSignal; schema 12 retains the schema 11 Claim tables as rebuildable indexes only.
- `claim_consistency.json` is the derived authority for ClaimConsistencyAssessment; schema 12 consistency tables are rebuildable indexes only.
- Immutable frozen-list content must not depend on long-lived foreign keys to runtime Snapshots or Tasks.
