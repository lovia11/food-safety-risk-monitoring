# V2-B5-9A/B BJS 202409 Identity / Source-Gap Audit

> Status: B5-9B DEFERRED — official identity/current page verified; official Method body/attachment provenance unresolved; runtime unchanged  
> Date: 2026-09-21  
> Scope: official Method identity / current lifecycle / source transport / 19-analyte candidate inventory / formal scope cross-check / current Risk overlap  
> Runtime decision: DO NOT PROMOTE in B5-9A

## 1. Official Method identity — VERIFIED

Primary official announcement:

```text
市场监管总局关于发布《食品中动物源性成分定性检测》等13项食品补充检验方法和2项修改单的公告
（2024年第51号）
https://www.samr.gov.cn/spcjs/xxfb/art/2024/art_4e2c7543a9d6488fa91081db6f003a36.html
```

The announcement explicitly lists:

```text
食品中托拉塞米等19种利尿剂的测定（BJS 202409）
```

Official date: `2024-12-22`.

Official method-database page:

```text
https://www.samr.gov.cn/spcjs/bcjyff/art/2025/art_cdd8ef0105224416941014b8b150fa13.html
```

The Method remains present in the current SAMR database.

## 2. Official fulltext transport gap

Current B5 research workflow recorded:

```text
official page SHA-256 =
1889293DAE36340D05FECE79C96ACFC3AC4C7D5E8EB4571DB201D98D8D0CD4DF

AuthorizedRead response SHA-256 =
1A3EC034F40A7DA334888CF812CA09ECEC435181411545F111C278465664A1D0

attachment_candidates = []
```

AuthorizedRead returned effectively:

```json
{"success": false, "data": {}, "message": "", "code": "200"}
```

So the official Method body and attachment URL/SHA-256 remain unresolved.

## 3. Secondary Method-content cross-check

Foodmate and 食典通 expose matching standard-summary text for BJS 202409.

Cross-checked Method role:

```text
高效液相色谱-串联质谱
HPLC-MS/MS
```

Cross-checked explicit product categories:

1. 压片糖果
2. 蜜饯
3. 果冻
4. 饮料
5. 果蔬粉
6. 饼干
7. 代用茶
8. 配制酒
9. 发酵酒

These are not encoded as runtime MethodApplicability because the official body is still unavailable.

## 4. Secondary 19-analyte / CAS cross-check

| # | Candidate label | CAS |
|---:|---|---:|
| 1 | 精磺胺 | 121-30-2 |
| 2 | 氯噻嗪 | 58-94-6 |
| 3 | 氢氯噻嗪 | 58-93-5 |
| 4 | 乙酰唑胺 | 59-66-5 |
| 5 | 氯噻酮 | 77-36-1 |
| 6 | 甲氯噻嗪 | 135-07-9 |
| 7 | 依匹噻嗪 | 1764-85-8 |
| 8 | 呋塞米 | 54-31-9 |
| 9 | 苄氟噻嗪 | 73-48-3 |
| 10 | 泊利噻嗪 | 346-18-9 |
| 11 | 环噻嗪 | 2259-96-3 |
| 12 | 苄噻嗪 | 91-33-8 |
| 13 | 环戊噻嗪 | 742-20-1 |
| 14 | 丙磺舒 | 57-66-9 |
| 15 | 美托拉宗 | 17560-51-9 |
| 16 | 依普利酮 | 107724-20-9 |
| 17 | 托拉塞米 | 56211-40-6 |
| 18 | 托伐普坦 | 150683-30-0 |
| 19 | 坎利酮 | 976-71-6 |

These remain candidate identities, not official-fulltext-governed runtime identities.

### 4.1 Secondary-name inconsistency

Accessible summary text is not perfectly stable:

```text
one summary occurrence: 依善利酮
scope/reference-material cross-check: 依普利酮
CAS candidate: 107724-20-9
```

Do not resolve this into a canonical runtime identity from secondary pages alone.

## 5. Current runtime overlap

At `inspection-reference@2026.09-b11`, only:

```text
氯噻嗪   58-94-6
氢氯噻嗪 58-93-5
呋塞米   54-31-9
```

already exist.

Exact structured Risk overlap at `risk-substance-reference@2026.09-c7`:

```text
氢氯噻嗪 / 58-93-5
→ historical blood_pressure

呋塞米 / 54-31-9
→ historical weight_loss
```

`氯噻嗪 / 58-94-6` has no concrete Risk mapping.

Therefore:

```text
19 Method targets ≠ 19 blood_pressure / weight_loss Risk targets
```

## 6. B5-9A decision

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
```

No new Substance, MethodSubstance, MethodApplicability, Risk mapping or group membership is added in B5-9A.

Candidate manifest records this at `inspection_method_candidates_v2@2026.09-b16`.

## 7. B5-9B official-source recheck

B5-9B repeated the provenance check against the official publication chain:

1. SAMR 2024年第51号公告 still identifies BJS 202409 and states that Method text is available through the supplementary-method database;
2. the current SAMR database still lists the Method;
3. the specific Method page still exposes only stable title/date metadata to the public fetch path;
4. the governed research workflow still has no official attachment candidate and its AuthorizedRead response remains `success=false / data={}`;
5. web search can locate third-party PDF mirrors, but those are user/third-party uploads and cannot become official runtime authority.

Therefore the existence of a likely full PDF outside SAMR does **not** close the provenance Gate.

## 8. B5-9B decision — DEFERRED

Decision:

```text
BJS 202409
status = verification
expected_depth = reference_only
promoted_method_id = null
promoted_dataset_version = null
runtime = unchanged
decision = deferred pending stable official Method body / attachment provenance
```

Do not add in B5-9B:

- the 16 missing canonical Substance identities from secondary text;
- MethodSubstance rows, including for the three already-existing overlapping Substance identities;
- MethodApplicability rows from third-party scope summaries;
- Claim→Risk mappings;
- Risk→Substance mappings;
- substance-group memberships.

The `依善利酮 / 依普利酮` conflict for CAS `107724-20-9` remains unresolved rather than being normalized from secondary material.

Promotion may be reconsidered only when a stable official SAMR Method body/attachment is recoverable with reproducible provenance (URL plus content hash) and the official text closes analyte identity, determination role and formal applicability.

Candidate manifest records the final B5-9B decision at:

```text
inspection_method_candidates_v2@2026.09-b17
```

Runtime remains:

```text
inspection-reference@2026.09-b11
risk-substance-reference@2026.09-c7
```

B5-9 is complete. The next independent candidate task is B5-10A / BJS 202502; it is not started by this audit.

## 9. B5-9B bounded governance Gate — SUCCESS

Current-head deterministic checks confirm:

```text
candidate manifest = 2026.09-b17
candidate records = 12 = 6 promoted + 6 verification
BJS 202409 runtime method = absent

inspection-reference = 2026.09-b11
methods = 11
Substance = 219
MethodSubstance = 263
MethodApplicability = 61

risk-substance-reference = 2026.09-c7
Risk mappings = 83

claim-inspection-bridge = claim-inspection-bridge-v2.6
bridge mappings = 25
```

Therefore B5-9B changes candidate governance/documentation only and does not alter the accepted runtime knowledge graph.
