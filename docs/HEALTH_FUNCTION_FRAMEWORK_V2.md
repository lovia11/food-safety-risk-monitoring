# HealthFunction Framework V2

> Status: CANONICAL DESIGN BASELINE
> Applies to: V2-6
> Design starting baseline: `696bf4178cbc018fca6d257ba156ec6f3a33fc1e`
> Owner: Project

## 1. Purpose

This document governs official HealthFunction identity and exact official-name normalization for health-food Claim consistency. A HealthFunction is an official function within a named jurisdiction, framework, and version. It is not a page Claim, marketing synonym, RiskSignal, legality result, substance, method, or InspectionRecommendation.

The machine-readable authority is [`config/health_functions_v2.json`](../config/health_functions_v2.json), version `health-functions-v2.0`. V2-6A established this design/governance baseline without changing production behavior. V2-6B1 consumes it through a strict production loader while preserving Registry records verbatim; schema 12 adds only a rebuildable consistency projection. V2-6B2 consumes that read contract in the primary Product Detail and Inspection Workspace presentation without changing the governed dataset or comparison semantics.

## 2. Current-project inventory

Current `HealthFoodIdentity` states are:

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

`verified_match` requires one valid, unambiguous identifier, an authoritative Registry record, and formatting-normalized exact equality between an explicit page product name and the official product name. A logo, OCR identifier, marketplace title, found record without a strong name, mismatch, or conflict is not sufficient.

`HealthFoodRegistryRecord` currently preserves identifier/type, product name, registrant or filer, address, issue/filing date, validity, record status, `officialHealthFunctions[]`, functional/marker ingredients, populations, specification, official source, retrieval time, and raw artifact path/hash. `officialHealthFunctions[]` remains a verbatim string array in the artifact, SQLite projection, and API. V2-6 normalization must never replace those strings.

The governed offline positive fixture currently contains:

> 本品经动物实验评价，具有对化学性肝损伤有辅助保护作用的保健功能

That full Registry wording is not an exact current name or transition alias in this dataset, so it remains `unresolved_official_function`. Substring extraction is prohibited. Current providers are a best-effort online SAMR adapter plus a hash-checked imported official-record provider; no existing provider, cache, import, SQLite, or API path performs Claim↔HealthFunction or legacy Effect↔official-function mapping.

## 3. Official source authority

The project verified the following first-party sources:

1. SAMR, National Health Commission, and National Administration of Traditional Chinese Medicine, Announcement No. 38 of 2023, dated 2023-08-15 and published 2023-08-31: [non-nutrient catalog announcement](https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/tssps/art/2023/art_491d5c9de75e425c8cd0203027af1d93.html) and its [24-function catalog PDF](https://www.samr.gov.cn/cms_files/filemanager/1647978232/attach/20239/18ab87cb32744e16bb2cbd6953ae272d.pdf).
2. The same authorities' official [supporting interpretation and complete old/new transition table](https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/tssps/art/2023/art_bfffccd97e6e4dfaa9d353318487e670.html), dated 2023-08-15 and published 2023-08-31.
3. Announcement No. 22 of 2023, dated 2023-06-02 and effective 2023-10-01: [nutrient-supplement catalog announcement](https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/tssps/art/2023/art_dedd4b97c0cd4d6298203a559c56d3e9.html) and its [catalog PDF](https://www.samr.gov.cn/cms_files/filemanager/1647978232/attach/20236/e5bca4166cc8480580bb9a3c97fecd79.pdf).

Official wording is stored verbatim. UI shortening, model memory, lexical similarity, and the V2 Claim taxonomy are not source authorities for this dataset.

## 4. Framework identity

| `framework_id` | Official framework | Coverage in V2-6A |
|---|---|---|
| `hf-framework-non-nutrient-cn-2023` | 允许保健食品声称的保健功能目录 非营养素补充剂（2023年版） | Complete 24/24 current functions and complete official transition table. |
| `hf-framework-nutrient-supplement-cn-2023` | 允许保健食品声称的保健功能目录 营养素补充剂（2023年版） | Separate framework identity plus its catalog-root function. Registry-string normalization below that root remains a declared gap. |

The nutrient-supplement framework is never flattened into the 24 non-nutrient functions. An unknown Registry framework remains `framework_unresolved`; it is never defaulted from a Claim topic.

## 5. HealthFunction contract

Every governed function contains:

```text
function_id
framework_id
official_name
jurisdiction
framework_version
ordinal
status
source_name
source_reference
source_date
effective_date (when the official source supplies one)
```

Stable IDs are independent of display names. For example, `hf-non-nutrient-cn-2023-06` remains the identity for ordinal 6 even though historical Registry records may contain an older official name.

## 6. Complete 2023 non-nutrient catalog

| Ordinal | Stable ID | Official current name |
|---:|---|---|
| 1 | `hf-non-nutrient-cn-2023-01` | 有助于增强免疫力 |
| 2 | `hf-non-nutrient-cn-2023-02` | 有助于抗氧化 |
| 3 | `hf-non-nutrient-cn-2023-03` | 辅助改善记忆 |
| 4 | `hf-non-nutrient-cn-2023-04` | 缓解视觉疲劳 |
| 5 | `hf-non-nutrient-cn-2023-05` | 清咽润喉 |
| 6 | `hf-non-nutrient-cn-2023-06` | 有助于改善睡眠 |
| 7 | `hf-non-nutrient-cn-2023-07` | 缓解体力疲劳 |
| 8 | `hf-non-nutrient-cn-2023-08` | 耐缺氧 |
| 9 | `hf-non-nutrient-cn-2023-09` | 有助于控制体内脂肪 |
| 10 | `hf-non-nutrient-cn-2023-10` | 有助于改善骨密度 |
| 11 | `hf-non-nutrient-cn-2023-11` | 改善缺铁性贫血 |
| 12 | `hf-non-nutrient-cn-2023-12` | 有助于改善痤疮 |
| 13 | `hf-non-nutrient-cn-2023-13` | 有助于改善黄褐斑 |
| 14 | `hf-non-nutrient-cn-2023-14` | 有助于改善皮肤水份状况 |
| 15 | `hf-non-nutrient-cn-2023-15` | 有助于调节肠道菌群 |
| 16 | `hf-non-nutrient-cn-2023-16` | 有助于消化 |
| 17 | `hf-non-nutrient-cn-2023-17` | 有助于润肠通便 |
| 18 | `hf-non-nutrient-cn-2023-18` | 辅助保护胃粘膜 |
| 19 | `hf-non-nutrient-cn-2023-19` | 有助于维持血脂（胆固醇/甘油三酯）健康水平 |
| 20 | `hf-non-nutrient-cn-2023-20` | 有助于维持血糖健康水平 |
| 21 | `hf-non-nutrient-cn-2023-21` | 有助于维持血压健康水平 |
| 22 | `hf-non-nutrient-cn-2023-22` | 对化学性肝损伤有辅助保护作用 |
| 23 | `hf-non-nutrient-cn-2023-23` | 对电离辐射危害有辅助保护作用 |
| 24 | `hf-non-nutrient-cn-2023-24` | 有助于排铅 |

The spelling and punctuation above follow the official catalog, including `水份`, `胃粘膜`, and the parenthesized blood-lipid wording.

## 7. Official transition aliases

`HealthFunctionAlias` contains `alias_id`, `function_id`, `alias_text`, `alias_type`, source metadata, and lifecycle status. V2-6A has 40 unique aliases after excluding five transition-table strings that are identical to their current official names.

| Current ordinal | Official historical/transition names retained as aliases |
|---:|---|
| 1 | 免疫调节；增强免疫力 |
| 2 | 延缓衰老；抗氧化 |
| 3 | 改善记忆 |
| 4 | 改善视力；缓解视疲劳 |
| 5 | 清咽 |
| 6 | 改善睡眠 |
| 7 | 抗疲劳 |
| 8 | 提高缺氧耐受力 |
| 9 | 减肥 |
| 10 | 改善骨质疏松；增加骨密度 |
| 11 | 改善营养性贫血 |
| 12 | 美容（祛痤疮）；祛痤疮 |
| 13 | 美容（祛黄褐斑）；祛黄褐斑 |
| 14 | 美容（改善皮肤水分/油分)；改善皮肤水分 |
| 15 | 改善胃肠功能（调节肠道菌群）；调节肠道菌群 |
| 16 | 改善胃肠功能（促进消化）；促进消化 |
| 17 | 改善胃肠功能（润肠通便）；通便 |
| 18 | 改善胃肠功能（对胃黏膜损伤有辅助保护作用）；对胃粘膜损伤有辅助保护功能 |
| 19 | 调节血脂（降低总胆固醇、降低甘油三酯）；辅助降血脂 |
| 20 | 调节血糖；辅助降血糖 |
| 21 | 调节血压；辅助降血压 |
| 22 | 对化学性肝损伤有保护作用；对化学性肝损伤有辅助保护功能 |
| 23 | 抗辐射；对辐射危害有辅助保护作用 |
| 24 | 促进排铅 |

The mixed-width closing parenthesis in `美容（改善皮肤水分/油分)` is retained exactly as published in the official transition table. An official transition alias is not a marketing synonym. `改善睡眠` may normalize an official Registry string to function 06; `安睡`, `好眠`, and `深睡` may not. Aliases apply only to Registry normalization. The page expression `减肥` remains a `weight_management` ClaimMention and does not become approved wording merely because `减肥` is also an official transition name.

## 8. Registry string normalization

Normalization preserves both raw and resolved values:

```text
rawOfficialFunction
resolutionStatus
resolutionSource: current_official_name | official_transition_alias | explicit_governed_mapping
frameworkId
healthFunctionId
```

Only these sources are eligible:

1. exact current official name;
2. exact officially documented transition name;
3. a future explicit governed mapping with independent provenance.

No punctuation trimming, substring match, fuzzy similarity, embedding, LLM, edit distance, or ungoverned semantic synonym is permitted. Unknown strings remain in `unresolvedOfficialFunctions[]`. They are never dropped or guessed.

## 9. Versioning and lifecycle

The HealthFunction dataset, Claim taxonomy, Claim↔HealthFunction mapping, and derived assessment each have independent version and provenance. A published dataset correction creates a new version or explicit supersession. Derived assessments record every version used and retain the original Registry strings and retrieval identity/time.

The governed dataset status remains `design_baseline`. The V2-6B1 production loader validates and consumes it for exact Registry resolution; schema 12 stores only rebuildable assessment projections and does not duplicate the governed function catalog as business data.

## 10. Non-goals

V2-6 does not:

- change HealthFoodIdentity or its `verified_match` gate;
- rewrite `officialHealthFunctions[]` or Registry artifacts;
- infer a framework from page Claims;
- classify page wording as an official alias;
- turn the V2-6B2 visible topic-comparison presentation into a pass/fail, legality, compliance, efficacy, probability, or risk verdict;
- create RiskSignal, substance, method, Recommendation, legality, compliance, or probability output;
- expand the five Claim types or 26 expressions.

See [Claim Consistency V2](CLAIM_CONSISTENCY_V2.md) for the implemented runtime and presentation boundary.
