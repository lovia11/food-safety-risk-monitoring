# V2-B5-4A BJS 202504 Analyte / Applicability Audit

> Status: CONTENT VERIFIED WITH OFFICIAL-ATTACHMENT TRANSPORT GAP — runtime unchanged  
> Date: 2026-09-20  
> Scope: method identity / full-text content cross-check / analyte identity / applicability / lifecycle / current Risk overlap  
> Runtime decision: DO NOT PROMOTE in B5-4A

## 1. Why this audit exists

BJS 202504 is a high-value current Method candidate because the existing governed Risk knowledge already contains a current `weight_loss` substance-group reference for:

```text
酚汀（酚丁）、酚酞及其酯类衍生物或类似物
```

That does **not** mean the Method may create concrete Risk mappings.

Permanent boundary:

```text
MethodSubstance ≠ RiskSubstance
Method existence ≠ group membership
chemical identity ≠ regulatory Risk relation
```

This audit therefore separates:

1. official regulatory Method identity;
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
食品中酚丁、双丙酚丁、双酚沙丁、双酚沙丁醋酸酯和酚丁双环丙甲酸酯的测定
BJS 202504
```

Official date:

```text
2025-09-29
```

Official SAMR method-database page:

```text
https://www.samr.gov.cn/spcjs/bcjyff/art/2025/art_ac5b02f639a7455baa31b55e60e7ce80.html
```

The method remains present in the current official database. No superseding Method was identified during this audit.

This establishes Method identity and current database presence. It does **not** by itself establish complete analyte CAS / applicability facts.

## 3. Official attachment transport gap

The repository research workflow is:

```text
.github/workflows/b5-official-source-fetch.yml
```

Research baseline:

```text
a8e9b78d88c4a7ea3f4eeb616be34553b7239d52
Reproduce SAMR AJAX session in B5 research
```

At that baseline all normal repository Gates were green and the B5 research workflow completed successfully.

Newer SAMR Method pages do not expose the article body or attachment as static HTML. They use:

```text
/cms_files/default/script/AuthorizedRead/unitbuild.js
→ GET /api-gateway/jpaas-publish-server/front/page/build/unit
```

The research workflow now preserves:

- page HTML;
- AuthorizedRead loader;
- same-origin session cookies;
- article Referer;
- AJAX request headers;
- raw JSON response;
- same-origin diagnostic scripts;
- SHA-256 metadata.

For BJS 202504 the reconstructed AJAX request still returns an HTTP-success response whose application payload is effectively:

```json
{
  "success": false,
  "data": {},
  "message": "",
  "code": "200"
}
```

Therefore:

```text
official Method identity = verified
official database presence = verified
official SAMR attachment URL / attachment SHA-256 = NOT recovered
```

Do not fabricate an attachment URL, and do not label the third-party mirror as an official SAMR attachment.

## 4. Full-text content cross-check

A complete-document mirror was located at:

```text
https://img.antpedia.com/standard/pdf/3/2601/1769586731-8536.pdf
```

The mirror displays the BJS 202504 cover, SAMR issuer and 2025-09-29 release date, and provides the Method body.

Because this is not a `samr.gov.cn` transport, it is used only to cross-check Method content. Regulatory provenance remains the official SAMR announcement/database.

Cross-checked Method role:

```text
HPLC-MS/MS
external-standard quantitative determination
```

Cross-checked explicit applicability:

- 糖果
- 果冻
- 蜜饯
- 果蔬汁饮料
- 固体饮料
- 饼干
- 代用茶

The Method text uses different sample preparation for:

- 蜜饯 / 果蔬汁饮料 / 固体饮料 / 饼干 / 代用茶;
- 糖果 / 果冻.

No broad “all foods” applicability is encoded by this audit.

## 5. Target analytes and candidate chemical identities

The Method title/full-text cross-check identifies exactly five targets:

1. 酚丁
2. 双丙酚丁
3. 双酚沙丁
4. 双酚沙丁醋酸酯
5. 酚丁双环丙甲酸酯

Independent chemical-identity / analytical-literature cross-checks support the following candidate identities:

| Method source label | Candidate canonical / English identity | Candidate CAS | Current runtime Substance |
|---|---|---:|---|
| 酚丁 | Oxyphenisatin / Oxyphenisatine | 125-13-3 | missing |
| 双丙酚丁 | Oxyphenisatin dipropionate | 2943075-86-1 | missing |
| 双酚沙丁 | Bisoxatin | 17692-24-9 | missing |
| 双酚沙丁醋酸酯 | Bisoxatin acetate | 14008-48-1 | missing |
| 酚丁双环丙甲酸酯 | candidate alias: 双环丙酚丁 | 2943075-87-2 | missing |

Identity cross-check sources include:

```text
Journal of Instrumental Analysis
UPLC-MS/MS测定食品及保健食品中酚汀等23种致泻性成分
DOI: 10.12452/j.fxcsxb.240705194
https://www.fxcsxb.com/zh/article/doi/10.12452/j.fxcsxb.240705194/
```

and, for 双丙酚丁, the National Reference Material Resource Sharing Platform certificate:

```text
NIM-RM 5085
CAS 2943075-86-1
https://www.ncrm.org.cn/Repository/e8b017f3-7291-49bb-977c-977da382df42.pdf
```

These are **chemical identity evidence**, not Risk regulatory evidence.

The fifth source label requires explicit normalization care:

```text
酚丁双环丙甲酸酯
↔ candidate canonical alias 双环丙酚丁
↔ CAS 2943075-87-2
```

If it is later governed into MethodSubstance, preserve the exact Method `source_label` and record a normalization note. Do not silently rename the official source label.

## 6. Current runtime overlap

At `inspection-reference@2026.09-b10` none of the five candidate CAS identities exists as a concrete Substance.

Current related runtime Substance examples include:

- 双醋酚丁 / CAS 115-33-3
- 酚酞 / CAS 77-09-8

These are distinct identities and must not be substituted for the BJS 202504 targets.

Current `risk-substance-reference` has no concrete Risk→Substance mapping for any of the five candidate CAS identities.

It does contain the current governed `weight_loss` group mapping:

```text
酚汀（酚丁）、酚酞及其酯类衍生物或类似物
```

However:

```text
inspection_reference.substance_group_memberships = 0
```

Therefore BJS 202504 must not automatically:

- turn the five Method analytes into group members;
- create five concrete `weight_loss` Risk→Substance rows;
- claim that a specific product contains any of them.

## 7. B5-4A decision

B5-4A is complete as an audit, but BJS 202504 is **not promoted**.

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
```

No changes in this subphase to:

- `config/inspection_reference.json`;
- `config/risk_substance_reference.json`;
- Claim→Risk;
- Risk→Substance;
- substance-group membership.

## 8. Next subtask — B5-4B

Next work should be limited to **BJS 202504 canonical Substance identity governance and source-gap resolution**:

1. confirm/goven the five canonical Substance identities without creating Risk relations;
2. resolve the exact source-label normalization for `酚丁双环丙甲酸酯` vs `双环丙酚丁`;
3. continue official SAMR attachment/Appx-A recovery if a stable source becomes available;
4. only after provenance is sufficient, prepare MethodSubstance rows;
5. encode only the seven explicitly verified applicability categories;
6. add zero Claim→Risk, zero Risk→Substance and zero implicit group memberships;
7. decide promotion depth only after the above passes validation.

Do not promote merely because the full-text mirror is available.
