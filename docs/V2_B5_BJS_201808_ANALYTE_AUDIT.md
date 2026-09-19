# V2-B5-3A / B5-3B BJS 201808 Analyte & Promotion Audit

> Status: ACCEPTED — B5-3A official-fulltext audit verified; B5-3B parent identity governance and runtime promotion completed  
> Date: 2026-09-20  
> Scope: analyte identity / applicability / salt→parent normalization / controlled promotion

## 1. Official source

Method:

```text
BJS 201808
食品中5种α-受体阻断类药物的测定
```

SAMR database page:

```text
https://www.samr.gov.cn/spcjs/bz/cs/art/2018/art_304e4c4a5f9d4e8d988c1b30ce408825.html
```

SAMR official DOCX:

```text
https://www.samr.gov.cn/cms_files/filemanager/1647978232/attach/20235/P020190516383836747775.docx
```

Research workflow downloaded and parsed the original DOCX.

```text
SHA-256:
45D85B389553925AF01FCB5EEAB6DE7113E898ED998FCDEE44EBD3476DB696B9

bytes: 141730
extraction: docx_xml
text_chars: 4642
```

## 2. Method scope verified from official fulltext

BJS 201808 explicitly targets:

- 酚妥拉明
- 哌唑嗪
- 特拉唑嗪
- 育亨宾
- 妥拉唑林

Method role:

```text
HPLC-MS/MS
quantitative determination
+ qualitative confirmation
```

Applicability stated by the method:

### Foods

- 硬质糖果
- 凝胶糖果
- 酒
- 茶饮料
- other similar matrices may refer to the method

### Health foods

- 片剂
- 口服液
- 胶囊剂

Therefore the eventual MethodApplicability can be governed from explicit source scope instead of inference.

## 3. Standard salt versus canonical analyte

The official method's target analytes are parent compounds, while section 3.2 / Appendix A uses salt standards.

| Target analyte | Official standard | Standard CAS | Canonical parent state in project |
|---|---|---:|---|
| 酚妥拉明 | 甲磺酸酚妥拉明 | 65-28-1 | governed: 50-60-2 |
| 哌唑嗪 | 盐酸哌唑嗪 | 19237-84-4 | existing: 哌唑嗪 / 19216-56-9 |
| 特拉唑嗪 | 盐酸特拉唑嗪 | 63074-08-8 | governed: 63590-64-7 |
| 育亨宾 | 盐酸育亨宾 | 65-19-0 | governed: 146-48-5 |
| 妥拉唑林 | 盐酸妥拉唑林 | 59-97-2 | governed: 59-98-3 |

The method itself confirms this parent/salt relationship because standard solutions are weighed as salts and explicitly converted to the corresponding parent analytes using conversion factors.

## 4. Canonical parent identity candidates

Secondary chemical-identity cross-checks support the following parent identities:

| Canonical analyte | Proposed parent CAS | Identity note |
|---|---:|---|
| 酚妥拉明 / Phentolamine | 50-60-2 | 甲磺酸盐 65-28-1 points to parent Phentolamine |
| 哌唑嗪 / Prazosin | 19216-56-9 | already present in Inspection Reference |
| 特拉唑嗪 / Terazosin | 63590-64-7 | 盐酸盐 63074-08-8 points to parent Terazosin |
| 育亨宾 / Yohimbine | 146-48-5 | 盐酸盐 65-19-0 points to parent Yohimbine |
| 妥拉唑林 / Tolazoline | 59-98-3 | 盐酸盐 59-97-2 points to parent Tolazoline |

These parent-CAS identities are chemical-identity evidence, not regulatory evidence. Before runtime promotion they should be recorded as canonical Substance identities with provenance, while the BJS source salt name/CAS remains on MethodSubstance.

## 5. Existing schema already supports the required normalization

Current project precedent:

```text
KJ201902:
马来酸罗格列酮 / source CAS
→ 罗格列酮 canonical parent
→ source_label + source_cas_no retained
→ normalization_note required
```

BJS 201808 should follow the same structure:

```text
canonical Substance = parent analyte

MethodSubstance:
source_label = official salt standard name
source_cas_no = official salt CAS
normalization_note = source method measures parent analyte while using salt standard
```

The validator already requires a non-empty normalization_note whenever source name/CAS differs from the canonical Substance.

## 6. Current Risk impact

Current Risk Reference does not justify auto-linking all five analytes.

### 哌唑嗪

Already has explicit historical `blood_pressure` Risk mapping:

```text
blood-pressure-cas-19216-56-9-historical-cn-2018
```

If BJS 201808 is later promoted, this existing Risk path may resolve to the new method subject to Product Context / applicability.

### 育亨宾

Current Risk contains only:

```text
育亨宾及其系列衍生物
→ substance_group
→ current male_function
```

There is no concrete yohimbine Risk mapping.

Therefore adding a canonical Yohimbine Substance or BJS 201808 MethodSubstance must NOT expand the group automatically.

### 酚妥拉明 / 特拉唑嗪 / 妥拉唑林

No current governed Risk mapping exists.

They may exist in the Method index after future promotion, but Recommendation must not surface them until an independent Risk→Substance relation is verified.

## 7. B5-3A decision and B5-3B completion

B5-3A correctly stopped before promotion until canonical parent identities were governed.

B5-3B then completed the controlled promotion in `inspection-reference@2026.09-b10`:

1. added canonical parent Substance identities for 酚妥拉明、特拉唑嗪、育亨宾、妥拉唑林;
2. preserved the existing 哌唑嗪 / 19216-56-9 entity;
3. added five MethodSubstance rows retaining official salt names/CAS and normalization notes;
4. added seven explicit include rows for 硬质糖果、凝胶糖果、酒、茶饮料 and 保健食品片剂/口服液/胶囊剂;
5. retained “其他类似基质可参照本方法” as source text only, not an unconditional runtime include;
6. added no Claim→Risk mapping, no Risk→Substance mapping and no yohimbine group membership;
7. promoted BJS 201808 to current `recommendation_ready`.

Accepted code/config/test baseline: `7e71c41ad6f7ada85df061fcbb1787e2725c2fae`.

Gates: Python syntax success; B3/B4 governance regression success; V2 full acceptance success.

## 8. Boundary

This audit establishes:

```text
official method identity
+ official analyte list
+ official method scope
+ salt-standard → parent-analyte normalization need
```

It does NOT establish:

- a new Claim→Risk relation;
- a new Risk→Substance relation;
- automatic membership of the yohimbine group;
- product illegality;
- actual detection in any product.


## 9. Current runtime inventory effect

After B5-3B:

```text
inspection-reference = 2026.09-b10
methods = 10
recommendation_ready current methods = 9
revoked reference_only methods = 1
substances = 205
method_substances = 236
method_applicabilities = 53
regulatory_documents = 8
```

Risk inventory and Claim→Risk governance remain unchanged.
