# V2-B5-10A/B BJS 202502 Identity / Content Audit

> Status: B5-10B DEFERRED — official identity/current page and official-institution method role verified; official SAMR fulltext/attachment provenance unresolved; runtime unchanged  
> Date: 2026-09-21  
> Scope: official Method identity / current database presence / method-role cross-check / 25-analyte candidate inventory / formal-scope cross-check / current Risk overlap  
> Runtime decision: DO NOT PROMOTE; B5-10B deferred

## 1. Official Method identity — VERIFIED

Primary SAMR announcement:

```text
市场监管总局关于发布《食品中坎地沙坦酯、拉西地平、阿齐沙坦的测定》等6项食品补充检验方法的公告
（2025年第39号）
https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/spcjs/art/2025/art_0fa91ac2c946482894bb854d4f506c24.html
```

The announcement explicitly lists:

```text
食品中普萘洛尔等25种β-受体阻滞剂类化合物的测定（BJS 202502）
```

Official date: `2025-09-29`.

Current SAMR Method database page:

```text
https://www.samr.gov.cn/spcjs/bcjyff/art/2025/art_4b021e01684943c5a34c8f929d6a4182.html
```

The Method remains present in the current database. The public page currently exposes a stable title and database publication timestamp, but this audit did not recover a stable official Method attachment/body URL plus reproducible content hash.

## 2. Official-institution method-role cross-check

Nanjing Municipal Administration for Market Regulation reported that the Method was led by the municipal food/drug inspection institute and uses:

```text
液相色谱-三重四极杆串联质谱
```

The same official local-regulator source states that it can perform:

```text
25种β-受体阻滞剂类化学药物
→ 定性
→ 定量
```

This is strong official institutional corroboration of the analytical role, but it is not a substitute for the formal SAMR Method body when governing runtime MethodSubstance / MethodApplicability rows.

## 3. Secondary formal-scope cross-check

China Food Safety Network and 食典通 expose matching standard-summary text.

Cross-checked Method type:

```text
高效液相色谱-串联质谱
HPLC-MS/MS
```

Cross-checked scope:

1. 饮料
2. 固体饮料
3. 代用茶
4. 保健食品 / 口服液
5. 保健食品 / 片剂
6. 保健食品 / 胶囊

A Xi'an product-quality inspection institute interpretation also states that BJS 202502 applies to beverages (including solid beverages), substitute tea and health foods (oral liquid, tablets, capsules), and performs qualitative and quantitative determination.

These scope facts are useful cross-check evidence only. They are not encoded as runtime MethodApplicability until the formal SAMR Method body/attachment provenance is recovered.

## 4. Candidate 25-analyte inventory

Secondary standard summaries consistently list the following 25 target labels. A BJS 202502 mixed-standard page supplies the following CAS candidates.

| # | Standard-summary label | Candidate CAS |
|---:|---|---:|
| 1 | 吲哚洛尔 | 13523-86-9 |
| 2 | 阿普洛尔 | 13655-52-2 |
| 3 | 普萘洛尔 | 525-66-6 |
| 4 | 氧烯洛尔 | 6452-71-7 |
| 5 | 阿替洛尔 | 29122-68-7 |
| 6 | 美托洛尔 | 37350-58-6 |
| 7 | 索他洛尔 | 3930-20-9 |
| 8 | 左布诺洛尔 | 47141-42-4 |
| 9 | 喷布洛尔 | 36507-48-9 |
| 10 | 卡替洛尔 | 51781-06-7 |
| 11 | 艾司洛尔 | 81147-92-4 |
| 12 | 卡拉洛尔 | 57775-29-8 |
| 13 | 倍他洛尔 | 63659-18-7 |
| 14 | 美替洛尔 | 22664-55-7 |
| 15 | 纳多洛尔 | 42200-33-9 |
| 16 | 噻吗洛尔 | 26839-75-8 |
| 17 | 比索洛尔 | 66722-44-9 |
| 18 | 拉贝洛尔 | 36894-69-6 |
| 19 | 醋丁洛尔 | 37517-30-9 |
| 20 | 贝凡洛尔 | 59170-23-9 |
| 21 | 阿罗洛尔 | 68377-92-4 |
| 22 | 塞利洛尔 | 56980-93-9 |
| 23 | 奈必洛尔 | 99200-09-6 |
| 24 | 卡维地洛 | 72956-09-3 |
| 25 | 兰地洛尔 | 133242-30-5 |

These are **candidate CAS identities**, not official-fulltext-governed runtime identities.

### 4.1 Secondary-label discrepancies

The mixed-standard supplier page uses two Chinese labels that differ from the standard-summary labels:

```text
CAS 36507-48-9
standard summary: 喷布洛尔
supplier page: 喷布特罗

CAS 57775-29-8
standard summary: 卡拉洛尔
supplier page: 咔唑心安
```

Independent chemical references support:

```text
36507-48-9 = Penbutolol
57775-29-8 = Carazolol
```

The second pair can plausibly be an alias relation, while the first supplier Chinese label is especially unsafe to treat as canonical normalization without formal Method/source verification.

Also, a commercial mixed standard may list parent-compound CAS while the formal Method may use salt-form standards. Therefore B5-10A does not create canonical Substance rows from this secondary CAS table.

## 5. Current runtime overlap

At `inspection-reference@2026.09-b11`, only one of the 25 candidate CAS identities already exists:

```text
阿替洛尔 / Atenolol
CAS 29122-68-7
substance-cas-29122-68-7
```

The other 24 candidate CAS identities are absent from the current inspection Substance inventory.

At `risk-substance-reference@2026.09-c7`, 阿替洛尔 has one exact historical mapping:

```text
blood_pressure
basis_type = historical_sampling_plan
temporal_status = historical
```

Source context:

```text
《食品保健食品欺诈和虚假宣传整治问答》
辅助降血压类样品检验项目表
```

Therefore:

```text
25 Method targets
≠
25 automatic blood_pressure Risk targets
```

and:

```text
official discussion of antihypertensive use
≠
permission to create 24 new Risk→Substance relations
```

## 6. B5-10A decision

Keep:

```text
status = verification
expected_depth = reference_only
promoted_method_id = null
promoted_dataset_version = null
runtime_consumed = false
```

Runtime remains:

```text
inspection-reference@2026.09-b11
risk-substance-reference@2026.09-c7
claim-inspection-bridge-v2.6
```

No B5-10A changes to:

- canonical Substance;
- MethodSubstance;
- MethodApplicability;
- Claim→Risk;
- Risk→Substance;
- substance-group membership.

Candidate manifest records the audit at:

```text
inspection_method_candidates_v2@2026.09-b18
```

## 7. B5-10B official-source recheck

B5-10B repeated the final provenance Gate.

Confirmed:

1. SAMR 2025年第39号公告 formally publishes BJS 202502 and states that the six Method texts will be exposed through the supplementary-method database;
2. the current SAMR database still exposes a dedicated BJS 202502 Method page;
3. the public Method page still exposes stable title/date metadata only;
4. current site search does not expose a reproducible SAMR PDF/DOC/DOCX attachment URL for BJS 202502;
5. secondary PDF/summary/material pages remain cross-check evidence only and cannot substitute for official Method provenance.

Therefore the official-source Gate remains unresolved.

## 8. B5-10B decision — DEFERRED

Final decision:

```text
BJS 202502
status = verification
expected_depth = reference_only
promoted_method_id = null
promoted_dataset_version = null
runtime = unchanged
decision = deferred pending stable official Method body / attachment provenance
candidate manifest = 2026.09-b19
```

Do not add from BJS 202502 at this stage:

- the 24 missing canonical Substance identities;
- MethodSubstance rows;
- MethodApplicability rows;
- Claim→Risk mappings;
- Risk→Substance mappings;
- substance-group memberships.

`阿替洛尔 / 29122-68-7` remains an existing overlap only. Its historical `blood_pressure` mapping does not authorize expansion to the other 24 β-blocker candidates.

The `喷布洛尔 / 喷布特罗` and `卡拉洛尔 / 咔唑心安` source-label discrepancies remain source-level differences rather than canonical normalizations.

Promotion may be reconsidered only when a stable SAMR formal Method body/attachment is recoverable with reproducible URL + content hash and the official text closes analyte identity, standard-material form, determination role and formal applicability.

## 9. B5-10B bounded governance Gate

Required end-state:

```text
inspection-reference = 2026.09-b11
BJS 202502 runtime method = absent
risk-substance-reference = 2026.09-c7 / 83 mappings
claim-inspection-bridge = v2.6 / 25 mappings
candidate manifest = 2026.09-b19
```

B5-10 is complete.
