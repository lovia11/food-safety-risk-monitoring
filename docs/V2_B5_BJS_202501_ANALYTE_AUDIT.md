# V2-B5-5A BJS 202501 Analyte / Applicability Audit

> Status: CONTENT VERIFIED WITH OFFICIAL-ATTACHMENT TRANSPORT GAP — runtime unchanged  
> Date: 2026-09-20  
> Scope: method identity / full-text content cross-check / analyte identity / applicability / lifecycle / current Risk overlap  
> Runtime decision: DO NOT PROMOTE in B5-5A

## 1. Why this audit exists

BJS 202501 is a current Method candidate whose title names three antihypertensive compounds:

```text
坎地沙坦酯
拉西地平
阿齐沙坦
```

The project already has a governed `blood_pressure` Risk direction, but a Method that detects antihypertensive compounds does not itself create a Risk relation.

Permanent boundary:

```text
MethodSubstance ≠ RiskSubstance
pharmacological use ≠ governed regulatory Risk relation
chemical identity ≠ Claim→Risk evidence
```

This audit therefore separates:

1. official Method identity/current database presence;
2. full-text Method content;
3. chemical Substance identity;
4. existing Risk governance.

## 2. Official Method identity — VERIFIED

Primary official announcement:

```text
市场监管总局关于发布《食品中坎地沙坦酯、拉西地平、阿齐沙坦的测定》
等6项食品补充检验方法的公告（2025年 第39号）

https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/spcjs/art/2025/art_0fa91ac2c946482894bb854d4f506c24.html
```

The announcement explicitly identifies:

```text
食品中坎地沙坦酯、拉西地平、阿齐沙坦的测定
BJS 202501
```

Official date:

```text
2025-09-29
```

Official SAMR method-database page:

```text
https://www.samr.gov.cn/spcjs/bcjyff/art/2025/art_0779e6b34a134108be09e205404db00d.html
```

The Method remains present in the current SAMR method database. No superseding Method was identified during this audit.

This proves Method identity/current database presence. It does not by itself prove complete CAS/applicability facts.

## 3. Official attachment transport gap

Current accepted B5 research workflow baseline:

```text
cff95b6388774f363f7b0a60fb0049c107bee4d6
Render SAMR BJS 202504 in B5 research browser
```

The same official-source fetch pipeline also queried the BJS 202501 page.

Observed official page facts:

```text
page URL = official SAMR BJS 202501 method-database page
page SHA-256 = D428B777FAD92AB6C981F0D260FB195622466659954A95D6FFBB1E9208D67429
AuthorizedRead attachment candidates = []
```

The reconstructed same-origin AuthorizedRead request returned an HTTP-success application payload equivalent to:

```json
{
  "success": false,
  "data": {},
  "message": "",
  "code": "200"
}
```

Recorded response SHA-256:

```text
97F2362471D993AC017DC13729E23B358AFB2679B03FD262656B38BF2277BDCA
```

Therefore:

```text
official Method identity = verified
official database presence = verified
official SAMR attachment URL / attachment SHA-256 = NOT recovered
```

Do not fabricate an official attachment URL.

## 4. Full-text content cross-check

A complete-document mirror was located at:

```text
https://www.998pdf.com/75945.html
```

A second document-distribution page also identifies a BJS 202501 PDF:

```text
https://www.instrument.com.cn/download/shtml/1388339.shtml
```

These are not SAMR transports. They are used only to cross-check Method body content. Regulatory provenance remains the official SAMR announcement/database.

Cross-checked Method role:

```text
LC-MS/MS
positive-ion MRM
external-standard quantitative determination
qualitative confirmation by retention time / ion-ratio criteria
```

The Method also includes a result-expression clause stating that results above the relevant quantification limits may indicate the possibility of illegal addition and should be combined with on-site enforcement evidence for comprehensive judgment. That clause belongs to the laboratory/enforcement Method; it must not be converted into a page-level automatic illegality conclusion.

## 5. Explicit applicability cross-check

The full-text mirror explicitly states applicability to:

### Foods

- 压片糖果
- 代用茶
- 固体饮料
- 茶饮料
- 饼干
- 果冻
- 配制酒

### Health foods

- 口服液
- 茶剂
- 片剂
- 硬胶囊
- 软胶囊

The Method distinguishes solid/semi-solid and liquid sample preparation.

Do not generalize this into “all foods” or “all health foods”.

## 6. Target analytes and chemical identities

The Method defines exactly three targets.

| Method source label | English identity | CAS | Current runtime Substance |
|---|---|---:|---|
| 坎地沙坦酯 | Candesartan cilexetil | 145040-37-5 | missing |
| 拉西地平 | Lacidipine | 103890-78-4 | missing |
| 阿齐沙坦 | Azilsartan | 147403-03-0 | missing |

The complete-document mirror's Appendix A gives the same CAS values.

Independent chemical-identity cross-check:

- PubChem Candesartan Cilexetil, CID 2540: CAS 145040-37-5  
  https://pubchem.ncbi.nlm.nih.gov/compound/2540
- PubChem Lacidipine, CID 5311217: CAS 103890-78-4  
  https://pubchem.ncbi.nlm.nih.gov/compound/Lacidipine
- PubChem Azilsartan: CAS 147403-03-0  
  https://pubchem.ncbi.nlm.nih.gov/compound/Azilsartan

These sources support chemical identity only. They do not create regulatory Risk relations.

## 7. Current runtime overlap

At `inspection-reference@2026.09-b10`:

```text
坎地沙坦酯 / 145040-37-5 → missing
拉西地平 / 103890-78-4 → missing
阿齐沙坦 / 147403-03-0 → missing
```

At `risk-substance-reference@2026.09-c7` there is no concrete Risk→Substance mapping for any of these three names/CAS values.

Therefore BJS 202501 must not automatically:

- create three `blood_pressure` Risk→Substance rows;
- infer that a page mentioning blood pressure should be tested for these three substances;
- treat known pharmacological antihypertensive use as regulatory mapping evidence;
- claim any product contains any of them.

## 8. B5-5A decision

B5-5A is complete as a content/identity/applicability audit, but BJS 202501 is **not promoted**.

Keep candidate state:

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

No changes in this subphase to:

- `config/inspection_reference.json`;
- `config/risk_substance_reference.json`;
- Claim→Risk;
- Risk→Substance;
- MethodSubstance;
- MethodApplicability.

## 9. Next subtask — B5-5B

Do only the BJS 202501 promotion-readiness/source-gap decision:

1. confirm whether the current “no orphan Substance” invariant should remain binding;
2. decide whether the three canonical Substance identities may be governed before a stable official SAMR attachment is recoverable;
3. if not, explicitly defer BJS 202501 as was done for BJS 202504;
4. if yes, require explicit provenance and zero Risk inference;
5. prepare MethodSubstance / MethodApplicability only if the provenance Gate is satisfied;
6. add zero Claim→Risk and zero Risk→Substance as a side effect;
7. decide promotion depth only after the above passes validation.

Do not weaken the official-source Gate merely because a complete third-party mirror exists.
