# Domain Model V2

> Status: CANONICAL
> Applies to: V2
> Last verified against commit: `bbe992e54f9fc583b312f919f32f91f43e53fb06`
> Owner: Project

This is the domain-design prerequisite for future schema and API work. ProductFact and HealthFoodIdentity are current in schema 10; entities explicitly labeled “Future” remain proposals rather than migration authorization.

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
| MonitorTarget | Governed object eligible for monitoring, identified by dataset + `target_id`. | Dataset-scoped; versioned, not silently edited in place. | Has source provenance and zero or more SearchQueries. | **Current.** Governed JSON imported/indexed in SQLite. |
| SearchQuery | Search expression identified by `query_id`. | MonitorTarget/version scope; lifecycle and enablement mutable through governance. | Belongs to one MonitorTarget; records source, validation and assessment. | **Current.** Governed JSON and SQLite read model. |
| CandidateHit | Search-result observation identified within task/query/result ordering. | Run/query-scoped, immutable observation. | Links Task, SearchQuery and potential Product identity; is not Detail success. | **Current.** Run artifacts and SQLite monitor tables. |
| Product | Stable marketplace item identity, normally marketplace product ID. | Cross-run; mutable presentation aggregates, stable identity. | Has many ProductSnapshots and at most one current SamplingMembership. | **Current.** SQLite. |
| ProductSnapshot | One concrete observation, identified by `snapshot_id`. | Product + Task + observed-time scoped; source facts immutable after capture. | Owns Evidence, analysis, ProductFacts, ClaimSignals, Review, and recommendation. | **Current** core; future relations extend it. SQLite index + run artifacts. |
| Evidence | Source-preserving observation, identified by `evidence_id`. | Snapshot-scoped; immutable historical observation. | Points to exact artifact/source text, origin class and analysis hit. | **Current.** SQLite index with underlying run artifact authority. |
| ProductFact | Normalized page fact with raw source and verification state. | Snapshot-scoped; derived projection is rebuildable, source immutable. | Derived from exact DOM/OCR artifact; future context and identity logic may consume it only through separately approved contracts. | **Current V2-2.** `product_facts.json` authority + generic SQLite table/read model; only `declared_origin` exists. |
| ClaimSignal | Actual page expression classified into a claim concept, identified per source occurrence/group. | Snapshot-scoped; derived and versioned. | Comes from Evidence/ProductFact; may map to taxonomy, function, or risk only through governed links. | **Future.** Domain records plus provenance; current Effect hits are legacy operational clues. |
| ClaimTaxonomyTerm | Governed normalized claim concept. | Knowledge-dataset scoped; versioned lifecycle. | May represent official, marketing, risk, or disease/treatment vocabularies without conflating them. | **Future.** Governed dataset + query index. |
| HealthFoodIdentity | Resolution for whether a Snapshot matches an official health-food product. | Snapshot-scoped assessment; re-evaluable under recorded sources. | Uses page identity clues and registry records; never logo/number-only. | **Current V2-3.** `health_food_identity.json` authority + SQLite read projection. |
| HealthFoodRegistryRecord | Official registration/filing record, identified by authoritative registry identifier. | Identifier/retrieval-time scoped; cached with freshness metadata. | Provides official product identity and verbatim official functions with source provenance. | **Current V2-3.** Raw official artifact/cache + normalized SQLite projection. |
| HealthFunction | Official normalized function under a defined framework/version. | Knowledge-dataset and jurisdiction scope. | Linked to registry records and only to ClaimSignals through explicit mappings. | **Future.** Governed dataset. |
| ClaimConsistencyAssessment | Evidence-bearing comparison result for one Snapshot. | Snapshot + identity/knowledge version scope; derived, reproducible. | Compares verified identity/functions with page claims and retains matches, mismatches, disease expressions and gaps. | **Future.** Derived artifact + read index. |
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

`health_food_identity.json` records `clues[]`, `identifierCandidates[]`, provider lookup, product-match assessment, gaps and diagnostics. Each page candidate keeps source type/path/text, content origin and extraction method. The raw official response remains an artifact with source, retrieval time and SHA-256; SQLite schema 10 stores only normalized record fields, JSON arrays and artifact references in `health_food_registry_records` and `health_food_identities`.

Official health functions are preserved verbatim as `officialHealthFunctions[]`. They are not a current HealthFunction taxonomy and are not compared with page claims until V2-5/V2-6. Identity enrichment has no Review/Sampling side effect and is not part of `reviewEligible`.

## 6. Claim separation

```text
ClaimSignal ≠ HealthFunction ≠ RiskSignal
```

- ClaimSignal records what the page says and how it was classified.
- HealthFunction records what an applicable official record permits as a normalized function.
- RiskSignal records a supported risk direction reached through a governed Evidence-to-Risk bridge.

Mappings between these entities are first-class governed knowledge with provenance and lifecycle. Lexical similarity is not a mapping.

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
- Immutable frozen-list content must not depend on long-lived foreign keys to runtime Snapshots or Tasks.
