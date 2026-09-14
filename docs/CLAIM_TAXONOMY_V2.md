# Claim Taxonomy V2

> Status: CANONICAL DESIGN BASELINE
> Applies to: V2-5
> Design baseline: `90dbb484e2aa01b8dab7b3872723cd1f251eb5cf`
> Owner: Project

## 1. Purpose

This document freezes the V2 Claim domain boundary and the migration baseline for the current Phase3 Effect vocabulary. The Claim layer answers only:

> 页面在宣传什么？

It records observed page wording and its governed marketing topic. It does not verify efficacy, identify an Official Health Function, determine compliance or illegality, create a RiskSignal, assert that a substance is present, or select an inspection method.

The governed machine-readable baseline is [`config/claim_taxonomy_v2.json`](../config/claim_taxonomy_v2.json), version `claim-taxonomy-v2.0`. V2-5A froze its design contract; V2-5B1 now consumes the same file as the sole runtime Claim taxonomy without changing its five Claim types or 26 expressions.

## 2. Non-goals

V2-5 does not:

- change collector, OCR, Phase3, Recommendation, Review, Sampling, or visible frontend behavior;
- establish ClaimSignal-to-HealthFunction equivalence;
- create Claim consistency, RiskSignal, legality, compliance or probability results;
- add a Claim-to-Risk, Risk-to-Substance or inspection mapping;
- expand the 26-expression legacy lexicon;
- remove or reinterpret the legacy Effect compatibility fields.

## 3. Terminology and invariants

```text
Evidence
  ↓
ClaimMention
  ↓ normalization by governed expression entry
ClaimSignal
```

- **ClaimMention** is one Snapshot-specific, Evidence-backed occurrence of wording actually observed on the page. It preserves the source text and matched expression.
- **ClaimSignal** groups one or more ClaimMentions from the same Snapshot into one governed marketing topic.
- **Claim type** is the stable ID of a marketing topic in the governed V2 Claim taxonomy.
- **Expression** is an exact extraction-lexicon entry. An expression is not a claim type.
- **HealthFunction** is official function knowledge under an applicable official framework and record. It uses a separate identity and taxonomy.
- **RiskSignal** is a supported regulatory attention direction reached through a separately governed bridge.

The following equalities are always false:

```text
ClaimSignal == verified product effect
ClaimSignal == HealthFunction
ClaimSignal == RiskSignal
ClaimSignal == InspectionRecommendation
```

For example, `sleep_related` means “页面出现睡眠相关宣传”, not “商品具有助眠功效”.

## 4. ClaimMention domain contract

ClaimMention is an observation-level, Snapshot-scoped derived record. Its current runtime contract is:

| Field | Contract |
|---|---|
| `claim_mention_id` | Stable identity within the derived Claim artifact. |
| `snapshot_id` | The ProductSnapshot that supplied the observation. |
| `raw_text` | Exact preserved Evidence text containing the observed expression. |
| `normalized_text` | Deterministic formatting-normalized text; it never replaces `raw_text`. |
| `matched_expression` | Exact governed expression text that matched. |
| `evidence_id` | Existing Evidence record supporting this occurrence. |
| `source_scope` | Must be `seller_managed` for a formal ClaimMention. |
| `source_asset_type` | Bounded source type such as `title`, current-product DOM, or detail-image OCR. |
| `source_locator` | Reconstructable artifact location, including source path and current line/record locator. |
| `extraction_method` | Deterministic method such as `exact_keyword`; it is not a probability. |
| `taxonomy_version` | Governed taxonomy version used for extraction/normalization. |
| `created_at` | Derived-record creation timestamp. |

`start_offset` and `end_offset` are deliberately absent from the V2-5A minimum. Current Evidence reliably preserves source path and line number, but not a uniform character-offset contract across title, DOM, and OCR. A later gate may add offsets only when every supported source can reconstruct them safely.

One Evidence text unit may yield multiple ClaimMentions when it contains multiple governed expressions. Each mention retains its exact `matched_expression`; normalization must not reduce the record to a boolean topic flag.

## 5. ClaimSignal domain contract

ClaimSignal is a Snapshot-scoped normalization result. Its current runtime contract is:

| Field | Contract |
|---|---|
| `claim_signal_id` | Stable identity within the derived Claim artifact. |
| `snapshot_id` | Snapshot that owns every linked ClaimMention. |
| `claim_type` | ID from the governed Claim taxonomy; arbitrary strings are invalid. |
| `display_label` | Taxonomy-provided presentation label, not free-form runtime wording. |
| `mention_ids` | Complete, deterministic set of supporting ClaimMention IDs. |
| `evidence_ids` | Complete, de-duplicated set of supporting Evidence IDs. |
| `taxonomy_version` | Version used to normalize the mentions. |
| `status` | Extraction/governance state only, such as `normalized` or `deprecated`. |
| `created_at` | Derived-record creation timestamp. |

All mentions in one signal must belong to the same Snapshot and resolve to the same `claim_type`. A signal preserves all `mention_ids` and `evidence_ids`; `sleep_related=true` is not a valid replacement. Status must never be `legal`, `illegal`, `compliant`, or `non_compliant`.

## 6. Evidence boundary

Formal ClaimMention and ClaimSignal input is limited to current-product, seller-managed primary Evidence:

| Content origin / source | Formal Claim eligibility | Rule |
|---|---|---|
| Product title | Eligible when represented as seller-managed Evidence | Preserve exact title source. |
| Current-product DOM | Eligible | Exclude other-product/recommendation regions. |
| Current-product detail-image OCR | Eligible | Preserve OCR Evidence and source image trace. |
| Reviews, Q&A, buyer comments | Not eligible | `user_generated`; auxiliary context only. |
| Recommendation area, 猜你喜欢, other-product ads | Forbidden | `excluded_other_product`; cannot describe the current Snapshot. |
| Search query/task keyword | Not Evidence | Discovery input cannot become a ClaimMention. |

OCR text cannot bypass Evidence. A detail-image occurrence must trace through the OCR Evidence record, original image/artifact path, and source locator before it can participate in a formal ClaimSignal.

## 7. Machine-readable taxonomy

`config/claim_taxonomy_v2.json` contains only:

- `version`, `status`, and a non-adjudicative description;
- `claim_types[]` marketing-topic terms;
- `expressions[]` exact lexicon entries with provenance and legacy trace;
- `migration[]` Effect-to-Claim type migration records;
- metadata, runtime status, source policy, and explicit taxonomy gaps.

It contains no risk, HealthFunction, legality, substance, method, or inspection mapping. Current `match_mode` is only `exact`; V2-5B1 implements deterministic formatting-normalized literal substring matching and introduces no fuzzy, embedding, semantic-similarity, or LLM classification.

Every matching occurrence is retained. Overlapping governed expressions are not arbitrated by length: for `高血压`, both `血压` and `高血压` produce Mentions in taxonomy-expression order. Repeated occurrences of one expression in one Evidence record receive separate stable IDs through an internal occurrence ordinal; offsets are not exposed. Mention order is Evidence canonical order, taxonomy expression order, then occurrence order. Signal order is Claim-type order in the taxonomy.

### 7.1 Initial claim types

| Claim Type | Chinese label | Expression count |
|---|---|---:|
| `sleep_related` | 睡眠相关宣传 | 10 |
| `blood_pressure_related` | 血压相关宣传 | 3 |
| `blood_lipid_related` | 血脂相关宣传 | 3 |
| `weight_management` | 体重管理相关宣传 | 4 |
| `male_function_related` | 男性功能相关宣传 | 6 |
| **Total** |  | **26** |

These five marketing topics are not a five-function Official Health Function model. In particular, `male_function_related` is not an official health-food function category.

## 8. Legacy inventory

The current repository contains five Effect labels and 26 unique exact keywords in `config/effect_keywords.json`. There is no stable `effect_id`; the Chinese Effect label is the current identifier. The inventory was derived from current code/config/tests, not reconstructed from this design brief.

### 8.1 Runtime and storage surfaces

| Layer | Legacy source / field | Current behavior | V2 disposition |
|---|---|---|---|
| Phase3 config | `effect_categories: effect label → keywords[]` | Substring matching of exact configured expression text across title, DOM, and OCR text units. | Legacy extraction input. |
| Phase3 artifact | `analysis.json`: `detected_effects`, `matched_keywords`, `evidence_details[].effect` | Stores Effect summaries and source-specific matches. | Compatibility artifact; unchanged. |
| Batch/run artifact | `batch_state.json`, reports and web snapshot risk projection | Repeats `detected_effects`, match and review fields. | Compatibility projection; unchanged. |
| SQLite schema 11 | Legacy Effect fields plus `claim_mentions`, `claim_signals`, `claim_signal_mentions` and per-Snapshot Claim artifact status/path | Rebuildable query projections. | Claim tables are additive; legacy fields and human state remain. |
| API | `detectedEffects`, `effect`, `matchedKeywords`; `/api/products?effect=`; filter `effects[]` | Product/filter/workspace DTO compatibility contract. | Deprecated-future compatibility shape; unchanged. |
| Frontend | Former 页面功效线索 table/filter, badges, detail/review/sampling presentations | Primary active-Snapshot surfaces now use V2 Claim summaries/details; legacy Effect badges and matched-keyword presentation are hidden. | Migrated in V2-5B2; no Effect-to-Claim fallback. |
| Sampling export | `detectedEffects`, `pageEffectClues`, 页面功效线索 | Freezes legacy wording in historical lists. | Frozen history must not be rewritten. |
| Tests | Phase3, bridge, datastore/API, task/queue, recommendation, export, workflow fixtures | Lock legacy field names and exact bridge behavior. | Preserved compatibility tests. |

The current non-archived code/config inventory is:

- extraction and run assembly: `src/phase3_analysis.py`, `src/phase5_batch.py`, `src/main.py`, `src/task_runtime.py`;
- legacy Effect/Risk/Recommendation path: `src/effect_risk_bridge.py`, `src/inspection_signal_trace.py`, `src/inspection_recommendation.py`, `src/inspection_runtime.py`;
- SQLite/API/export projections: `src/data_store.py`, `src/web_contract.py`, `src/local_api.py`, `src/sampling_export.py`;
- governed legacy configs: `config/effect_keywords.json`, `config/effect_risk_bridge.json`;
- frontend DTO/presentation: `frontend/src/api/contracts.ts`, `frontend/src/domain/analysis.ts`, `frontend/src/domain/evidence.ts`, `frontend/src/domain/product.ts`, `frontend/src/domain/productQuery.ts`, `frontend/src/components/EvidenceGroupCard.tsx`, product list/detail pages, inspection workspace/review queue pages, and sampling list table/drawer;
- compatibility tests: Phase3, Effect/Risk bridge, signal trace, applicability, recommendation/runtime, DataStore/API/web contract, task/pipeline/queue, historical/real collector, Sampling export, and frontend workflow test modules under `tests/` and `frontend/tests/`.

SearchQuery/task `keyword` fields in Discovery and Task APIs were also audited. They are search strategy inputs, not members of the 26-expression extraction lexicon and not Claim Evidence.

### 8.2 Legacy bridge inventory

There are exactly three current exact `(effect_label, matched_keyword)` bridge mappings in `config/effect_risk_bridge.json`:

| Legacy Effect | Exact keyword | Current Risk category | Current behavior | Semantic problem | Future destination / action |
|---|---|---|---|---|---|
| 减脂 | 减肥 | `weight_loss` | Produces a legacy RiskSignal and enters current Risk→Substance→Method resolution. | Claim observation and risk interpretation are coupled in one Effect evidence record. | V2-5B first emits `ClaimSignal(weight_management)`; a later separately governed Claim/Risk bridge may emit RiskSignal. Keep current bridge only for compatibility until that gate. |
| 男性相关 | 壮阳 | `male_function` | Same path through the male-function Risk reference. | Marketing topic is not itself an official function or risk conclusion. | V2 ClaimSignal first; later explicit RiskSignal bridge. |
| 男性相关 | 补肾 | `male_function` | Same path through the male-function Risk reference. | Same coupling. | V2 ClaimSignal first; later explicit RiskSignal bridge. |

The bridge references two current group-level Risk mapping records. The complete Risk Reference contains eight Risk-to-substance/group mappings, and the Recommendation builder resolves RiskSignal → knowledge trace → applicability → method assistance. Those D2–D6 contracts remain unchanged in V2-5A and are not embedded into the Claim taxonomy.

### 8.3 Confirmed migration issue

Current `phase3_analysis.py` includes `user_generated` units in `evidence_details` and derives `detected_effects`/`review_required` from them. `effect_risk_bridge.py` also preserves and bridges a matching UGC Effect/keyword pair; downstream Recommendation downgrades it to auxiliary evidence rather than preventing the legacy RiskSignal. This conflicts with the V2 formal-Claim source boundary.

V2-5B1 blocks UGC occurrences before formal ClaimMention creation. UGC remains available as Evidence/legacy auxiliary context, and historical Evidence or frozen Sampling exports are not rewritten. Existing excluded-other-product units remain excluded and cannot create a current-Snapshot Claim.

## 9. Complete legacy migration

Every actual legacy keyword is covered exactly once. `migration confidence=exact_legacy_category` means the entry retains its audited legacy category while changing the category's semantics from an apparent Effect to a marketing topic. It is not a confidence probability or an official equivalence.

| Legacy Effect | Legacy keyword | New Claim Type | New display label | Migration confidence | Notes |
|---|---|---|---|---|---|
| 助眠 | 助眠 | `sleep_related` | 睡眠相关宣传 | exact_legacy_category | legacy_system exact expression |
| 助眠 | 入睡 | `sleep_related` | 睡眠相关宣传 | exact_legacy_category | legacy_system exact expression |
| 助眠 | 睡眠 | `sleep_related` | 睡眠相关宣传 | exact_legacy_category | legacy_system exact expression |
| 助眠 | 安睡 | `sleep_related` | 睡眠相关宣传 | exact_legacy_category | legacy_system exact expression |
| 助眠 | 好眠 | `sleep_related` | 睡眠相关宣传 | exact_legacy_category | legacy_system exact expression |
| 助眠 | 深睡 | `sleep_related` | 睡眠相关宣传 | exact_legacy_category | legacy_system exact expression |
| 助眠 | 失眠 | `sleep_related` | 睡眠相关宣传 | exact_legacy_category | legacy_system exact expression |
| 助眠 | 辗转反侧 | `sleep_related` | 睡眠相关宣传 | exact_legacy_category | legacy_system exact expression |
| 助眠 | 安神 | `sleep_related` | 睡眠相关宣传 | exact_legacy_category | legacy_system exact expression |
| 助眠 | 催眠 | `sleep_related` | 睡眠相关宣传 | exact_legacy_category | legacy_system exact expression |
| 降压 | 降压 | `blood_pressure_related` | 血压相关宣传 | exact_legacy_category | legacy_system exact expression |
| 降压 | 血压 | `blood_pressure_related` | 血压相关宣传 | exact_legacy_category | legacy_system exact expression |
| 降压 | 高血压 | `blood_pressure_related` | 血压相关宣传 | exact_legacy_category | legacy_system exact expression |
| 降脂 | 降脂 | `blood_lipid_related` | 血脂相关宣传 | exact_legacy_category | legacy_system exact expression |
| 降脂 | 血脂 | `blood_lipid_related` | 血脂相关宣传 | exact_legacy_category | legacy_system exact expression |
| 降脂 | 胆固醇 | `blood_lipid_related` | 血脂相关宣传 | exact_legacy_category | legacy_system exact expression |
| 减脂 | 减脂 | `weight_management` | 体重管理相关宣传 | exact_legacy_category | legacy_system exact expression |
| 减脂 | 减肥 | `weight_management` | 体重管理相关宣传 | exact_legacy_category | legacy_system exact expression; legacy bridge exists separately |
| 减脂 | 瘦身 | `weight_management` | 体重管理相关宣传 | exact_legacy_category | legacy_system exact expression |
| 减脂 | 燃脂 | `weight_management` | 体重管理相关宣传 | exact_legacy_category | legacy_system exact expression |
| 男性相关 | 壮阳 | `male_function_related` | 男性功能相关宣传 | exact_legacy_category | legacy_system exact expression; legacy bridge exists separately |
| 男性相关 | 补肾 | `male_function_related` | 男性功能相关宣传 | exact_legacy_category | legacy_system exact expression; legacy bridge exists separately |
| 男性相关 | 阳痿 | `male_function_related` | 男性功能相关宣传 | exact_legacy_category | legacy_system exact expression |
| 男性相关 | 早泄 | `male_function_related` | 男性功能相关宣传 | exact_legacy_category | legacy_system exact expression |
| 男性相关 | 遗精 | `male_function_related` | 男性功能相关宣传 | exact_legacy_category | legacy_system exact expression |
| 男性相关 | 男性功能 | `male_function_related` | 男性功能相关宣传 | exact_legacy_category | legacy_system exact expression |

## 10. Taxonomy gaps

**NONE.** All 26 current expressions fit the five audited marketing-topic categories without adding a new Claim type. This does not claim that the taxonomy covers all marketplace language. New expressions or topics require a later governed dataset change with provenance; model knowledge must not silently expand this baseline.

## 11. HealthFunction, RiskSignal, and inspection separation

The 2023 official health-function framework is not the legacy five-Effect vocabulary and is not modeled by this taxonomy. Official registry strings remain verbatim current facts. A future HealthFunction dataset must carry its own framework/version and explicit mappings; lexical similarity is insufficient.

Likewise, a ClaimSignal does not automatically create regulatory attention. Future RiskSignal logic requires a separate mapping record with provenance and lifecycle. Inspection knowledge consumes a supported RiskSignal plus context; the Claim taxonomy must never contain a substance or method shortcut.

```text
ClaimSignal
  → [future governed Claim/Risk mapping]
  → RiskSignal
  → [existing governed risk and inspection knowledge]
  → InspectionRecommendation
```

V2-5A freezes only the first node and explicitly leaves the later mapping future.

## 12. Authority, storage, and current schema/API contract

Authority is divided as follows:

| Record | Authority | Responsibility |
|---|---|---|
| Raw OCR/DOM/title artifact | `output/<run_id>/...` source files | Immutable captured text/image facts. |
| Evidence | Current Evidence artifact/index and exact source trace | Source-preserving observation; not a normalized Claim. |
| Claim taxonomy | `config/claim_taxonomy_v2.json` | Governed Claim type/expression meaning and version. |
| ClaimMention/ClaimSignal | Current `claim_analysis.json` under the product Snapshot artifact directory | Rebuildable derived Claim domain authority using a recorded taxonomy version. |
| Claim query projection | SQLite schema 11 Claim tables | Rebuildable index only; never sole authority for source wording. |

Schema 11 adds `claim_mentions`, `claim_signals`, and `claim_signal_mentions`, with Evidence and Snapshot references plus taxonomy version. Import transactionally replaces one Snapshot's Claim projection from the artifact and preserves prior schema 10 data and human Review/Sampling state.

Snapshot/detail workspace DTOs now add:

```text
claimAnalysisStatus
claimMentions[]
claimSignals[]
```

Each mention supplies raw text and source trace; each signal supplies its governed type, display label, mention IDs, Evidence IDs, version, and status. `claimAnalysisStatus=complete` with empty arrays is a successful zero-Claim analysis. `not_generated` means no artifact exists; `error` means sidecar generation or artifact validation failed. Existing `detectedEffects`/`effect` fields remain legacy compatibility fields and are neither removed nor used as Claim authority.

### 12.1 V2-5B1 implementation status

V2-5B1 is implemented as a degradable parallel sidecar in `src/claim_analysis.py`. The pipeline derives Claims only from the ordered, canonical-ID Evidence records persisted through the Phase3 analysis artifact. It writes `claim_analysis.json` atomically; failure writes `claim_analysis_error.json` and cannot alter Product status, Analysis/Review readiness, Review, Sampling, or Recommendation.

The artifact contains `schemaVersion`, `status`, `taxonomyVersion`, `snapshotId`, `generatedAt`, formal `claimMentions[]`, aggregated `claimSignals[]`, `sourcePolicy`, and summary counts. SQLite is not authority and can rebuild the three Claim projection tables from the artifact without rerunning Detail, OCR, or Phase3.

### 12.2 V2-5B2 implementation status

V2-5B2 makes the Snapshot Claim projection visible as 页面宣传线索 in Product Overview, Product Detail, Review Queue, Inspection Workspace, and current Sampling. List and filter reads use batched SQLite `claim_signals` projections; detail reads the full Snapshot-scoped Mentions/Signals and resolves each Mention to its existing Evidence identity. The additive `claim_type` filter matches exact governed types only and never maps back to legacy Effect.

Legacy `detectedEffects`, Evidence `effect`/`matchedKeywords`, `effect=`, and `effects[]` remain backend compatibility contracts for Phase3 and the legacy Risk/Recommendation bridge. Historical Sampling JSON/XLSX remains frozen and is presented only as 旧版冻结分析结果. No historical Evidence or export was rewritten.

## 13. UX language

V2-5B2 Claim UI uses the section title **页面宣传线索**. A summary is phrased, for example:

```text
睡眠相关宣传
发现 3 处表达
```

Expansion shows the exact original wording before the matched expression, a friendly source type, and the existing Evidence location. Complete-with-Claims is informational blue; complete-zero and not-generated are distinct neutral states; only analysis error is red. The UI must not say “具有助眠功效” or “存在违法助眠宣传”. Risk/compliance language may appear only when a separately approved later stage has produced that distinct assessment.

## 14. Versioning and change process

`claim-taxonomy-v2.0` is the initial design baseline and follows the repository's simple named-version convention. A change must:

1. identify the layer and stable IDs affected;
2. preserve expression provenance and lifecycle;
3. retain or explicitly deprecate old IDs rather than silently changing their meaning;
4. pass uniqueness, referential-integrity, legacy-coverage, source-boundary, and forbidden-mapping tests;
5. record the taxonomy version in derived Claim artifacts;
6. never rewrite historical Evidence or frozen exports.

## 15. Examples

### Seller-managed exact expression

Seller-managed OCR Evidence contains `帮助安睡`. Exact expression `安睡` can produce a ClaimMention retaining the full raw text, OCR Evidence ID, image path, line locator, and taxonomy version. It may normalize into `ClaimSignal(claim_type=sleep_related)` together with other same-Snapshot sleep mentions. This does not verify a sleep benefit.

### UGC-only expression

A buyer review contains `感觉更好睡`. Even if a governed expression were present, the occurrence remains auxiliary UGC context. It cannot create a formal ClaimMention or ClaimSignal for the current product.

### Other-product recommendation

A recommendation card contains `减肥`. Its origin is `excluded_other_product`, so it cannot generate a current-Snapshot ClaimMention.

### No mapping

A seller-managed expression normalizes to a ClaimSignal but has no later verified Claim/Risk mapping. The result remains a ClaimSignal plus an explicit Knowledge Gap; no RiskSignal, substance, or method is invented.
