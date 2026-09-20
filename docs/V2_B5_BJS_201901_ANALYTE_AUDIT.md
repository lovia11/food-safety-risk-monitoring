# V2-B5-8A BJS 201901 Official Fulltext Audit

> Status: FULLTEXT VERIFIED — official SAMR legacy DOC parsed reproducibly; runtime unchanged  
> Date: 2026-09-21  
> Scope: official DOC parsing / complete analyte-CAS inventory / method role / formal scope / current Risk-Substance overlap  
> Runtime decision: DO NOT PROMOTE in B5-8A

## 1. Official source and reproducible parsing

Method:

```text
BJS 201901
食品中二甲双胍等非食品用化学物质的测定
```

Primary SAMR announcement:

```text
市场监管总局关于发布《食品中二甲双胍等非食品用化学物质的测定》等4项食品补充检验方法的公告
（2019年第4号）
```

Official attachment:

```text
https://www.samr.gov.cn/cms_files/filemanager/1647978232/attach/20235/P020190516389935220036.doc
```

Research artifact facts:

```text
SHA-256 =
C4A697A35F4171516C06947C937F0C10D01FDC3AFC671D7780154A5AD9936EE9

bytes = 381952
format = legacy Word .doc
extraction = antiword
extracted text chars = 18305
```

The B5 research workflow now installs `antiword`, preserves the original binary and records the extraction method/hash. This makes the old Word 97-2003 source reproducibly auditable.

## 2. Formal scope

The official scope states that the Method covers 27 non-food-use chemical substances in food, including special food.

Explicit examples:

- 茶叶
- 奶粉
- 饼干
- 酒
- 饮料

The scope further includes similar matrices in special-food forms such as:

- 片剂
- 胶囊剂

The sample-preparation section explicitly separates:

1. 茶叶、奶粉、饼干、片剂、胶囊；
2. 饮料、口服液；
3. 酒。

Governance consequence:

```text
“等食品 / 上述类似基质”
≠ unrestricted all-food include
```

Future MethodApplicability should encode explicit categories/forms conservatively and preserve the open-ended wording only as source scope text.

## 3. Method role

The official Method is:

```text
高效液相色谱-串联质谱
HPLC-MS/MS
ESI
MRM
positive / negative ion modes
```

Principle:

```text
methanol ultrasonic extraction
→ HPLC-MS/MS
→ external-standard quantitative determination
```

Qualitative confirmation is also explicit:

- retention time must match the standard peak within ±2.5%;
- relative ion abundance must remain within specified tolerance bands.

Therefore a future runtime Method can use:

```text
determination_role = quantitative
```

with Method notes preserving the additional qualitative-confirmation role.

## 4. Complete 27-analyte inventory

| # | Official source label | English | CAS |
|---:|---|---|---|
| 1 | 苯乙双胍 | Phenformin | 114-86-3 |
| 2 | 丁二胍 | Buformin | 692-13-7 |
| 3 | 二甲双胍 | Metformin | 657-24-9 |
| 4 | 伏格列波糖 | Voglibose | 83480-29-9 |
| 5 | 阿卡波糖 | Acarbose | 56180-94-0 |
| 6 | 维达列汀 | Vildagliptin | 274901-16-5 |
| 7 | 罗格列酮 | Rosiglitazone | 122320-73-4 |
| 8 | 西他列汀 | Sitagliptin | 486460-32-6 |
| 9 | 吡格列酮 | Pioglitazone | 111025-46-8 |
| 10 | 氯磺丙脲 | Chlorpropamide | 94-20-2 |
| 11 | 达格列净 | Dapagliflozin | 461432-26-8 |
| 12 | 格列吡嗪 | Glipizide | 29094-61-9 |
| 13 | 甲苯磺丁脲 | Tolbutamide | 64-77-7 |
| 14 | 醋磺己脲 | Acetohexamide | 968-81-0 |
| 15 | 妥拉磺脲 | Tolazamide | 1156-19-0 |
| 16 | 瑞格列奈 | Repaglinide | 135062-02-1 |
| 17 | 卡格列净 | Canagliflozin | 842133-18-0 |
| 18 | 格列齐特 | Gliclazide | 21187-98-4 |
| 19 | 格列波脲 | Glibornuride | 26944-48-9 |
| 20 | 格列本脲 | Glibenclamide | 10238-21-8 |
| 21 | 那格列奈 | Nateglinide | 105816-04-4 |
| 22 | 格列美脲 | Glimepiride | 93479-97-1 |
| 23 | 曲格列酮 | Troglitazone | 97322-87-7 |
| 24 | 格列喹酮 | Gliquidone | 33342-05-1 |
| 25 | 莫格他唑 | Muraglitazar | 331741-94-7 |
| 26 | GW501516 | GW501516 | 317318-70-0 |
| 27 | 环格列酮 | Ciglitazone | 74772-77-3 |

## 5. Current inspection-reference overlap

At `inspection-reference@2026.09-b10`, 13 of the 27 canonical identities already exist:

- 苯乙双胍
- 丁二胍
- 二甲双胍
- 罗格列酮
- 吡格列酮
- 格列吡嗪
- 甲苯磺丁脲
- 瑞格列奈
- 格列齐特
- 格列波脲
- 格列苯脲
- 格列美脲
- 格列喹酮

The remaining 14 are missing:

- 伏格列波糖
- 阿卡波糖
- 维达列汀
- 西他列汀
- 氯磺丙脲
- 达格列净
- 醋磺己脲
- 妥拉磺脲
- 卡格列净
- 那格列奈
- 曲格列酮
- 莫格他唑
- GW501516
- 环格列酮

These 14 may become canonical Substance candidates in B5-8B because the official Method now provides complete source identity/CAS. Their presence in BJS201901 still does not create a Risk relation.

## 6. Current blood_glucose Risk overlap

At `risk-substance-reference@2026.09-c7`, 13 Method targets have existing historical `blood_glucose` overlap.

Nine have concrete historical Substance mappings:

- 罗格列酮
- 格列吡嗪
- 甲苯磺丁脲
- 瑞格列奈
- 格列齐特
- 格列波脲
- 格列苯脲
- 格列美脲
- 格列喹酮

Four are represented through the existing historical screening-group evidence:

- 苯乙双胍
- 丁二胍
- 二甲双胍
- 吡格列酮

The other 14 Method targets do not currently have a governed Risk relation.

Permanent boundary:

```text
BJS201901 detects 27 targets
≠
blood_glucose automatically maps to all 27 targets
```

B5-8A adds zero Risk mappings.

## 7. Source-label normalization issue

The official BJS201901 source uses:

```text
格列本脲
CAS 10238-21-8
```

Current runtime canonical identity is:

```text
格列苯脲
CAS 10238-21-8
```

These refer to the same governed CAS identity.

A future MethodSubstance row must therefore preserve:

```text
canonical Substance = 格列苯脲 / 10238-21-8
source_label = 格列本脲
source_cas_no = 10238-21-8
normalization_note = required
```

Do not create a duplicate Substance merely because the Chinese source label differs.

## 8. B5-8A decision

B5-8A is complete as a full official Method-content audit.

Keep candidate state for this subphase:

```text
status = verification
expected_depth = reference_only
promoted_method_id = null
promoted_dataset_version = null
runtime_consumed = false
```

Runtime remains:

```text
inspection-reference@2026.09-b10
risk-substance-reference@2026.09-c7
```

No changes in B5-8A to:

- Substance;
- MethodSubstance;
- MethodApplicability;
- Claim→Risk;
- Risk→Substance.

Candidate manifest records the verified fulltext facts at `inspection_method_candidates_v2@2026.09-b14`.

## 9. Next subtask — B5-8B promotion preparation / decision

Do only BJS201901:

1. govern the 14 missing canonical Substance identities from the official Method table;
2. reuse the 13 existing canonical identities;
3. normalize official `格列本脲` to canonical `格列苯脲` without duplication;
4. prepare 27 MethodSubstance rows;
5. prepare conservative MethodApplicability from the explicit formal scope/sample-preparation branches;
6. add zero new Risk mappings merely because the Method detects the substance;
7. validate that BJS201901 can reach `recommendation_ready`;
8. run all current Gates before accepting promotion.
