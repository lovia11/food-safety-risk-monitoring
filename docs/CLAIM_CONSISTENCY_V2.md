# Claim Consistency V2

> Status: CANONICAL DESIGN BASELINE
> Applies to: V2-6A
> Design starting baseline: `696bf4178cbc018fca6d257ba156ec6f3a33fc1e`
> Owner: Project

## 1. Purpose

`ClaimConsistencyAssessment` is a future Snapshot-scoped, evidence-bearing comparison between the page's V2 Claim records and the verified product's official HealthFunctions. It supplies transparent comparison clues for human review. It does not decide legality, compliance, approval, efficacy, risk probability, substance presence, or an inspection method.

V2-6A freezes only the domain and governed knowledge contract. It creates no production assessment artifact, schema table, API, frontend section, Review side effect, RiskSignal, or InspectionRecommendation change.

## 2. Inputs and eligibility

Future assessment input is:

```text
ProductSnapshot
+ HealthFoodIdentity
+ HealthFoodRegistryRecord
+ ClaimAnalysis / ClaimSignals / ClaimMentions
+ health-functions-v2 dataset version
+ claim-health-function-mapping-v2 dataset version
```

Formal comparison is eligible only when `HealthFoodIdentity.state == verified_match`. Every other identity state produces `identity_not_verified` without comparing functions. A page Claim with an unverified identity is not an inconsistency result and is not a conclusion about ordinary food.

Claim analysis must be `complete`; `not_generated` and `error` remain distinct unavailable states and never fall back to legacy `detectedEffects`. The Registry framework and official function strings must resolve sufficiently through the exact rules in [HealthFunction Framework V2](HEALTH_FUNCTION_FRAMEWORK_V2.md).

## 3. Authority and scope

The future derived authority is `claim_consistency.json` in the ProductSnapshot artifact directory. SQLite may later provide a rebuildable projection only after a separate schema gate. The assessment identity is Snapshot + HealthFoodIdentity/Registry record identity + Claim/HealthFunction/mapping versions. A later knowledge release can produce a new assessment without rewriting page Evidence, Claim artifacts, Registry source artifacts, Review, Sampling, or frozen exports.

Every future artifact records at least:

```text
schemaVersion
assessmentVersion
snapshotId
state
claimTaxonomyVersion
healthFunctionDatasetVersion
claimHealthFunctionMappingVersion
healthFoodRegistryIdentifier
healthFoodRegistryRecordReferenceOrHash
healthFoodRegistryRetrievedAt
rawOfficialFunctions[]
resolvedHealthFunctions[]
unresolvedOfficialFunctions[]
claimSignalIds[]
claimMentionIds[]
perClaimAssessments[]
mentionAttentions[]
summary
gaps[]
generatedAt
```

Raw official strings and normalized IDs are both required. A topic boolean is insufficient: all ClaimSignal and ClaimMention identities remain available for trace.

## 4. Top-level state machine

| State | Eligibility/result meaning |
|---|---|
| `identity_not_verified` | Identity is not `verified_match`; no official-function comparison runs. |
| `claim_not_generated` | Identity is verified, but V2 Claim analysis has not run. Legacy Effect is not a fallback. |
| `claim_analysis_error` | Identity is verified, but the Claim sidecar failed; comparison is unavailable. |
| `framework_unresolved` | The applicable Registry function framework cannot be established from governed official data. |
| `official_function_unresolved` | One or more raw Registry function strings needed for comparison cannot be resolved exactly. |
| `no_page_claims` | Identity is verified and Claim analysis completed with zero governed Claims. This is not a positive consistency result because the Claim taxonomy is not full-language coverage. |
| `assessed` | Identity is verified, Claim analysis is complete, and official function resolution is sufficient; per-Claim topic relations are available. |

Required future wording includes:

- `identity_not_verified`: 保健食品身份尚未核验，无法进行官方功能一致性比较。
- `no_page_claims`: 当前已治理词表未发现可比较的页面宣传表达。
- `official_function_unresolved`: 官方功能原文暂无法通过已治理名称解析，需人工核对。

None of these states is a verdict.

## 5. Governed topic mapping

The machine-readable authority is [`config/claim_health_function_mapping_v2.json`](../config/claim_health_function_mapping_v2.json), version `claim-health-function-mapping-v2.0`. Its sole relation is `topic_related`.

| Claim type | Related HealthFunction | Relation | Status |
|---|---|---|---|
| `sleep_related` | `hf-non-nutrient-cn-2023-06` — 有助于改善睡眠 | `topic_related` | governed |
| `weight_management` | `hf-non-nutrient-cn-2023-09` — 有助于控制体内脂肪 | `topic_related` | governed |
| `blood_lipid_related` | `hf-non-nutrient-cn-2023-19` — 有助于维持血脂（胆固醇/甘油三酯）健康水平 | `topic_related` | governed |
| `blood_pressure_related` | `hf-non-nutrient-cn-2023-21` — 有助于维持血压健康水平 | `topic_related` | governed |
| `male_function_related` | — | no governed mapping | explicit gap |

These mappings are `project_governed_topic_mapping`, not official equivalence. They indicate that a page marketing topic has a comparable official-function topic. They do not say the concrete page wording is an approved official claim.

The nutrient-supplement framework has no V2 Claim mapping in this baseline. A Registry record in that framework cannot borrow a non-nutrient mapping.

## 6. Per-Claim relations

| Relation | Meaning |
|---|---|
| `function_topic_recorded` | The governed related HealthFunction is present in the verified Registry function set. Future wording: 页面宣传主题在该产品官方功能记录中找到对应主题。 |
| `function_topic_not_recorded` | A governed topic mapping exists, but its HealthFunction is absent from the verified Registry function set. Future wording: 该页面宣传主题未在当前核验的官方功能记录中找到对应项。 |
| `no_governed_function_mapping` | The Claim type has no governed HealthFunction mapping. Future wording: 当前无已核验的官方功能主题映射，需人工研判。 |
| `mapping_unresolved` | A mapping or function identity required for one Claim cannot be resolved under the recorded dataset versions. |

`function_topic_recorded` is not wording approval. For example, a `blood_pressure_related` ClaimMention containing `高血压` can have a recorded function topic while the concrete disease wording still requires separate human attention.

## 7. Mention-level attention contract

`ClaimExpressionAttention` is a separate future, ClaimMention/expression-scoped dimension. Its proposed states are:

```text
disease_or_treatment_wording_attention
wording_scope_review
none
```

The production attention dataset status is `dataset_pending_manual_governance`. V2-6A does not label the 26 expressions using model knowledge, substring rules, or Claim topic. `血压` and `高血压` cannot inherit one topic-level legal classification. Any future entry requires an explicit source, expression identity, provenance, lifecycle, and review.

The first-party rule sources and their exact non-adjudication boundary are recorded in the [Health-food Registry Source Audit](HEALTH_FOOD_REGISTRY_SOURCE_AUDIT.md): labels/instructions must not involve disease prevention or treatment, while this system may only present a wording attention clue and recommend human review. It cannot determine the legal nature of marketplace content, advertising approval, or an enforcement outcome.

## 8. Official-function resolution

Each assessment retains:

```text
rawOfficialFunctions[]
resolvedHealthFunctions[]
unresolvedOfficialFunctions[]
```

Exact current names and exact official transition aliases may resolve Registry strings. Unknown, typo, punctuation-modified, descriptive wrapper, fuzzy, or semantically similar strings remain unresolved. Framework assignment comes from governed official record/framework evidence, never from a page Claim topic.

The relationship is intentionally asymmetric:

```text
Registry raw “减肥”
  → exact official transition alias
  → hf-non-nutrient-cn-2023-09

Page ClaimMention “减肥”
  → weight_management ClaimSignal
  → topic_related comparison only
  ↛ approved official wording
```

## 9. Deterministic contract examples

The design fixture [`contract_cases.json`](../tests/fixtures/claim_consistency_v2/contract_cases.json) freezes these cases:

| Case | Expected state/relation |
|---|---|
| Unverified identity + Claims | `identity_not_verified` |
| Verified + Claim not generated | `claim_not_generated` |
| Verified + Claim error | `claim_analysis_error` |
| Verified + complete zero Claims | `no_page_claims` |
| Verified + sleep Claim + official sleep function | `assessed` / `function_topic_recorded` |
| Verified + sleep Claim + no official sleep function | `assessed` / `function_topic_not_recorded` |
| Verified + male-function Claim | `assessed` / `no_governed_function_mapping` |
| Verified + Registry raw `改善睡眠` | resolves by official transition alias, then `function_topic_recorded`; raw retained |
| Verified + unresolved Registry string | `official_function_unresolved` |
| Verified + multiple Claims/functions | independent per-Claim relations |
| Verified nutrient-supplement framework + sleep Claim | `assessed` / `no_governed_function_mapping`; no non-nutrient mapping is borrowed |
| Verified + unknown framework | `framework_unresolved` |

## 10. Summary contract

Future summaries may count:

```text
claimSignalCount
functionTopicRecordedCount
functionTopicNotRecordedCount
noMappingCount
attentionMentionCount
unresolvedOfficialFunctionCount
```

They must not calculate a total risk score, probability, or binary verdict.

## 11. Future API, storage, and UX draft

V2-6B may add a Snapshot-scoped derived artifact and additive read projection only after schema/API review. It may expose raw/resolved official functions, per-Claim relations, attention items, official/page Evidence references, versions, and gaps. It must not mutate Review eligibility/status, Sampling Membership, RiskSignal, or Recommendation.

A future UI section titled 保健功能一致性 may show 官方核验功能、页面宣传主题、对应关系、未找到对应项、知识缺口、需要关注的具体页面表达. It must preserve `identity_not_verified`, unavailable, unresolved, zero, and assessed states and link to the existing page and official Evidence viewers. No V2-6A UI is implemented.

## 12. Non-adjudication and gaps

The assessment state and relations must never use `pass`, `fail`, `compliant`, `non_compliant`, `legal`, `illegal`, `violation`, `high_risk`, `low_risk`, or probability/confidence percentages as conclusions.

Current explicit gaps are:

- nutrient-supplement Registry function-string normalization below the separate framework root is not governed;
- `male_function_related` has no governed HealthFunction mapping;
- ClaimExpressionAttention production entries await manual source governance;
- existing Registry strings with descriptive wrappers may remain unresolved;
- no production artifact, loader, schema, API, or UI exists until V2-6B.

ClaimConsistencyAssessment remains separate from Claim Taxonomy, HealthFunction Framework, RiskSignal, and InspectionRecommendation.
