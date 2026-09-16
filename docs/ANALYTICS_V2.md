# Analytics V2

> Status: CANONICAL DESIGN BASELINE
> Applies to: V2-9
> Last verified phase: V2-9A
> Owner: Project

## 1. Purpose and boundary

V2 Analytics is a read-only interpretation layer over existing runtime facts and governed knowledge. It does not create Product, Snapshot, Claim, Review, Sampling, ProductFact, Risk, Recommendation or Knowledge facts. It does not assign risk, health, compliance or national-coverage scores.

V2-9A implements the governed Metric Dictionary, deterministic read model, GET API and frontend DTO/client contract. It does **not** add Sidebar navigation, an Analytics page, charts, CSS, materialized tables, cache jobs or ETL. Those visible surfaces require V2-9B.

Every metric response states its grain, time basis, dataset version, applied filters, missing-data rule, interpretation and forbidden interpretation. Counts from the current local index and project-governed datasets are not representative market or national statistics.

## 2. Fact audit — what the system can reliably calculate

| Domain | Reliable fact | Canonical grain | Time basis | Important limit |
|---|---|---|---|---|
| Search/discovery | deduplicated Candidate represented by a Task-scoped ProductSnapshot | ProductSnapshot | parent `tasks.created_at` | CandidateHit is query-level trace and is not required for Quick tasks; it is not a universal denominator |
| Product | unique Product observed by selected Snapshots | Product | parent `tasks.created_at` | Product count is not Snapshot count |
| Detail | attempted and `detailCollected` Snapshot | ProductSnapshot | parent `tasks.created_at` | success denominator is only actual Detail attempts |
| OCR | `ocrInputReady` and `ocrReady` | ProductSnapshot | parent `tasks.created_at` | `ocrReady` means at least one successful OCR input, not character accuracy |
| Phase3 | `analysisReady` | ProductSnapshot | parent `tasks.created_at` | Analysis success with zero Evidence remains complete |
| Claim | execution state and formal ClaimSignal | ProductSnapshot / ClaimSignal | parent `tasks.created_at` | only V2 formal seller-managed Claim; legacy Effect and UGC never substitute |
| Review | Review status for review-eligible Snapshot | Review | source Snapshot parent Task time | internal pending rows for ineligible Snapshots are excluded |
| Sampling | current Product Membership | SamplingMembership | source Snapshot parent Task time | non-membership is not low risk |
| Search geography | search-page region attached to Task-scoped Snapshot observation | ProductSnapshot | parent `tasks.created_at` | never Product origin |
| Declared origin | evidence-backed `declared_origin` ProductFact | ProductSnapshot | parent `tasks.created_at` | missing and conflict are explicit; no value is inferred |
| Knowledge | V2-7 audit and V2-8 Knowledge summary | governed record/mapping/corpus | dataset-version scoped | never national coverage |

Bounded runtime metrics use the parent Task `created_at` consistently. This includes search-only candidates that have no Detail `collected_at`. ISO dates select the inclusive calendar dates represented by each timestamp; ISO datetimes use their explicit offset and are compared consistently. Rows missing Task time remain visible in all-time results but are excluded from a bounded range.

## 3. Machine-readable Metric Dictionary

The authority is `config/analytics_metrics_v2.json`, version `analytics-metrics-v2.0`. It contains 32 implemented metrics:

| Domain | Count | Types |
|---|---:|---|
| pipeline | 12 | count, ratio, distribution |
| claims | 4 | count, distribution |
| geography | 3 | distribution |
| knowledge | 13 | count, coverage |

Each entry records `metric_id`, Chinese title, domain, type, grain, unit, numerator and denominator definitions, time basis, deduplication rule, missing-data rule, source entities, allowed filters, interpretation, forbidden interpretation, version and status. Dictionary validation rejects duplicates, unsupported domains/types, incomplete definitions and malformed unavailable metrics.

The dictionary explicitly marks these non-metrics:

- `search_discovery_recall`: `not_available`; the relevant marketplace universe denominator does not exist.
- `national_inspection_method_coverage`: `not_available`; the project Reference Index is not a national method census.
- `market_risk_distribution`: `not_available`; local tasks are not a representative sample and the system does not produce risk probability.
- `sampling_selection_rate`: `future_metric`; current Membership is a human workflow state without one meaningful risk/quality denominator.

## 4. Pipeline metric contract

The pipeline cohort is ProductSnapshots whose parent Task time and optional search region/ProductSnapshot status match the filters.

- Search candidate observation count uses Snapshot grain; unique Product count deduplicates `product_id`.
- Detail success numerator is `detailCollected`; denominator is Snapshots that actually entered Detail collection.
- OCR success numerator is `ocrReady`; denominator is `ocrInputReady` Snapshots.
- Analysis readiness numerator is `analysisReady`; denominator is `ocrReady` Snapshots.
- All readiness facts reuse `src.pipeline_contract.evaluate_pipeline_readiness`.
- Review distribution has three separate buckets: `pending`, `recommend_follow_up`, `no_further_action`. Only review-eligible Snapshots enter the denominator.
- Sampling reports current Membership count only. It does not infer risk from membership or non-membership.
- A zero ratio/coverage denominator returns `rate=null` and `reason=zero_denominator`, never `0%`.

The `stage` API filter is the governed ProductSnapshot processing status, not the Task business-status vocabulary.

## 5. Claim and Evidence metric contract

Claim metrics read only `claim_signals` and their source Snapshot. They never derive Claim from legacy `detectedEffects`, Evidence keywords, SearchQuery or UGC.

Claim analysis state has four explicit buckets:

1. `complete_with_claims`;
2. `complete_zero`;
3. `not_generated`;
4. `error`.

Claim type distribution counts distinct `snapshot_id × claim_type`. Its denominator is Claim Analysis `complete` Snapshots, including governed zero. It is multi-label: bucket counts and rates may sum above the total Snapshot count or 100%.

UGC is available only in `evidence_source_scope_distribution`, which separately reports seller-managed, user-generated, excluded-other-product and unknown Evidence records. There is no “UGC Claim” metric.

## 6. Geography contract

The future UI titles are frozen as:

- **已采集商品搜索地区分布** — ProductSnapshot search-page region in the Task observation context.
- **页面宣传线索商品搜索地区分布** — search-page region for Snapshots containing at least one formal V2 ClaimSignal.
- **商品标称产地分布** — Snapshot-level evidence-backed `declared_origin` ProductFact.

Search region and declared origin never substitute for each other. A Product may be observed in multiple task regions across Snapshots. Declared-origin facts retain `unknown/not_recorded`; multiple distinct explicit values produce `conflict` and are never silently arbitrated. Seller, shipping, warehouse, manufacturer and raw-material locations remain outside declared origin.

## 7. Knowledge coverage contract

Knowledge metrics do not use runtime date filters. They are dataset-version scoped and expose numerator, denominator and the governing versions.

- Monitor Reference and Operational counts reuse the V2-8 Knowledge summary.
- Indexed, recommendation-ready and reference-only Method counts reuse the V2-8 summary.
- Method Reference/deep coverage, Risk→explicit Substance coverage, group resolution, Recommendation structural/end-to-end reachability, RiskCategory reachability and fixed context-corpus reachability reuse `scripts/audit_inspection_knowledge.load_and_build_audit`.
- No second reachability algorithm exists in Analytics.
- Seven indexed methods and 201 indexed Substances remain project Reference facts, not national coverage.

## 8. Read API

All endpoints are GET-only:

```text
GET /api/analytics/metrics
GET /api/analytics/summary
GET /api/analytics/pipeline
GET /api/analytics/claims
GET /api/analytics/geography
GET /api/analytics/knowledge
```

Runtime endpoints support the relevant subset of `from`, `to`, `region`, `stage` and `claim_type`. Knowledge metrics reject runtime date/region filters because their time basis is dataset version.

Every calculated metric returns at least:

```text
metricId
value
metricType
grain
timeBasis
datasetVersion
filters
missingRule
interpretation
forbiddenInterpretation
```

Ratio and coverage add `numerator`, `denominator`, `rate` and `reason`. Distribution adds `denominator` and `buckets[]`; each bucket returns key, label, count, denominator, rate and zero-denominator reason.

## 9. Future V2-9B UX contract

The future first-level page title is `统计分析`. It is organized by evidence domain rather than risk level:

1. **运营流程** — factual cards and explicitly denominated stage ratios;
2. **页面宣传线索** — status facts and multi-label bar chart;
3. **地区分布** — three separate bar-chart sections using the frozen titles above; no forced map;
4. **知识覆盖** — numerator/denominator cards or bars with dataset-version trace.

The page should prefer bars and compact factual cards. It must not create risk heatmaps, national coverage, compliance score, health score, pie-chart clutter or a blended “system quality” score.

## 10. Deterministic local baseline

One read-only run against the current development `data/app.db` was executed twice with identical canonical JSON output. SHA-256: `df6e729b744e8a9b7387c836227d48d6053a06842a490e19eb5bef8f1177580e`.

Observed local facts at that moment:

- 7 Snapshot candidate observations / 7 unique Products;
- Detail 7/7, OCR 7/7, Analysis 7/7 under their respective real denominators;
- Review: pending 0, recommend follow-up 3, no further action 4;
- current Sampling Membership: 1;
- Claim Analysis: complete zero 2, not generated 5, error 0, with formal Claim 0;
- Evidence: seller-managed 12, UGC 6;
- seven search-region buckets; formal-Claim search-region denominator 0;
- declared origin: five single-value Snapshots and two conflict Snapshots;
- Knowledge: Reference MonitorTarget 106, Operational 16/106, indexed Methods 7, Recommendation-ready 6/7, reference-only 1, group resolution 0/3, structural reachability 5/5, end-to-end reachability 3/5, context corpus 3/6.

This baseline validates determinism only. It is mutable development data and must not be described as market prevalence, production performance or national coverage.

## 11. V2-9A acceptance result

V2-9A passes when the dictionary is complete and validated, every implemented read metric follows its stated numerator/denominator/time/grain contract, zero and missing remain distinct, formal Claim and UGC remain separate, search region and declared origin cannot conflate, V2-7 knowledge calculations are reused, GET requests leave business state unchanged, TypeScript contracts typecheck, and repeated reads are deterministic.

V2-9A is **COMPLETE** after its targeted gate passes. V2-9 remains **IN PROGRESS**; V2-9B Analytics UI & V2-9 Exit Gate is the next independent phase.
