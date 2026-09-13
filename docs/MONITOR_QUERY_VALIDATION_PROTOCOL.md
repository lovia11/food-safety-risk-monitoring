# Monitor SearchQuery Validation Protocol

> Status: CANONICAL
>
> Applies to: V2-4 and later Monitor coverage work
>
> Execution mode: visible-browser, bounded, search-only, human reviewed

## 1. Scope and boundary

This protocol governs whether a SearchQuery may become operational for one formal MonitorTarget. Reference membership and operational readiness are independent:

```text
Reference MonitorTarget
  ≠ operational MonitorTarget
  ≠ evidence about a Product
```

Validation collects Search Result cards only. It must not start Detail collection, OCR, Phase3, Review, or Sampling. It measures observed relevance within the reviewed sample; it does not establish recall and does not prove full marketplace coverage.

## 2. Lifecycle and provenance

`validation_status` uses:

- `candidate_unvalidated`: proposed but not yet accepted for task execution;
- `search_validated`: passed review and may run only when `enabled=true`;
- `rejected_low_relevance`: reviewed result quality is too low;
- `paused_scope_issue`: retained but paused because the observed result scope conflicts with the project scope or an explicit restriction;
- `deprecated`: historical strategy retained for traceability and no longer used.

Every enabled Query must be `search_validated`. A MonitorTarget is operational only when the target is enabled and at least one Query is both enabled and `search_validated`.

`query_source` uses `standard_name`, `official_alias`, `observed_product_form`, or `manually_curated`. An official alias must be literal official source text. An observed product form requires an earlier real result observation and a note identifying that evidence. Generated semantic synonyms are not accepted provenance.

## 3. Result labels

Each unique reviewed Search Result receives exactly one primary scope label:

- `relevant_food`: sufficient card-level basis that the result is a food, edible product, food ingredient, or clearly processed food, and that the target is an important component or description;
- `raw_medicinal_or_nonfood_scope`: primarily raw medicinal material, decoction piece, medical/drug context, or otherwise outside the current food-supervision scope;
- `non_food`: clearly not a food product;
- `ambiguous`: the Search Result card alone is insufficient for a reliable scope judgment.

`duplicate` is an additional deduplication label and is excluded from unique assessable results. Ambiguous results are never counted as relevant.

## 4. Metrics and decision gate

The reviewed record preserves result count, unique result count, duplicate count, block/template anomalies, scope issues, candidate product forms, and:

```text
assessableCount = relevant_food + raw_medicinal_or_nonfood_scope + non_food
relevantCount   = relevant_food
relevanceRate   = relevantCount / assessableCount
```

Normal promotion requires all of:

1. at least the first 10 unique assessable results reviewed;
2. `relevanceRate >= 0.70`;
3. `relevantCount >= 5`;
4. no systematic scope issue.

A query with fewer than 10 unique assessable results remains `hold` even if its observed rate is 100%, pending explicit human judgment. The decisions are `promote`, `hold`, and `reject`. Thresholds must not be relaxed ad hoc to improve coverage figures.

## 5. Artifact contract

Runtime output is ignored by Git and lives at:

```text
output/query_validation/<batch_id>/
  manifest.json
  queries/<query_id>.json
  review/<query_id>.json
  review/<query_id>.md
  review/finalization_summary.json
  pilot_queries/<query_id>/search/...
```

`manifest.json` records batch ID, contract version, timestamps, search-only scope, requested sample size, execution status, and per-Query artifact references. Each Query artifact records:

- `batchId`, `targetId`, `queryId`, `queryText`;
- `startedAt`, `completedAt`, `executionStatus`;
- `resultCount`, `uniqueResultCount`;
- all five label collections;
- `assessableCount`, `relevantCount`, `relevanceRate`;
- final `decision` and `reviewedAt`;
- raw source artifact references and any execution error.

Before human review, metrics, decision, and `reviewedAt` remain explicit `null`; they are never inferred from title matching. Partial failure preserves completed Query artifacts. A resumed batch skips Query artifacts already marked execution-complete.

The Query artifact and all raw Search artifacts are immutable collection facts. Human labels are written only to the corresponding `review/` artifact. Each reviewed item preserves `rank`, `productId`, `reviewedLabel`, `reviewedLabelZh`, `reviewNote`, `reviewedAt`, and `reviewedBy`. Stable machine enums remain English; Markdown and other human-readable presentation use Chinese labels while retaining the machine value for traceability. Metrics and decisions are calculated from the explicit human labels by the governed finalization tool, never copied into the ledger by hand.

## 6. Tracked validation ledger

Raw results stay in runtime output. Accepted/rejected governance evidence is summarized in `config/monitor_query_validation.json`, including Query/Target/batch IDs, date, sample metrics, decision, note, artifact reference, and SHA-256. The ledger never fabricates labels absent from a legacy run: old title-relevance pilots retain explicit `null` V2-4 food-scope metrics until revalidation.

Config promotion is a reviewed change after artifact completion. It updates lifecycle/enabled state and ledger together, preserves prior evidence, and reruns governance and execution tests. Candidate records never become enabled merely because a search completed.

## 7. Batch procedure

1. Freeze a bounded candidate set and sample size in the batch plan.
2. Run the tool with `--dry-run`; verify Target, Query, sample size, and destination.
3. Obtain the explicit live-validation authorization for that batch.
4. Use visible Chrome and the existing signed-in profile. The user handles login or verification manually.
5. Execute serial, low-frequency, search-only collection. Stop on a new contract blocker; preserve partial artifacts.
6. Deduplicate by stable product ID, label manually, calculate metrics, and record anomalies.
7. Apply the fixed decision gate. Review any `hold` explicitly.
8. Update the ledger and governed config in one reviewed change; rerun all Monitor governance tests.

## 8. Safety and revalidation

Never bypass CAPTCHA/security verification, use stealth/proxy evasion, or perform high-frequency batch scraping. A batch boundary is a human gate. Revalidation uses a new batch ID and does not overwrite old artifacts or frozen decisions. Revalidate when result templates materially change, a query develops a systematic scope issue, official naming changes, or an operational strategy is being reconsidered after pause/deprecation.
