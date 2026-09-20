# V2-B5-7A BJS 202602 Identity / Source-Gap Audit

> Status: B5-7A PARTIAL VERIFIED；B5-7B DEFERRED — official fulltext/canonical target equivalence unresolved; runtime unchanged  
> Date: 2026-09-21  
> Scope: Method identity / official source transport / regulatory scene / candidate chemical identity / applicability cross-check / current male_function overlap  
> Runtime decision: DO NOT PROMOTE in B5-7A

## 1. Why this audit exists

BJS 202602 is:

```text
食品中伐地那非杂质30的测定
```

The title is adjacent to the project's current `male_function` knowledge, but the permanent boundary remains:

```text
Method title ≠ canonical Substance identity
drug derivative wording ≠ concrete group membership
Method detection ≠ automatic Risk→Substance
```

## 2. Official Method identity — VERIFIED

Primary official announcement:

```text
市场监管总局关于发布《食品中布噻嗪和美布噻嗪的测定》等6项食品补充检验方法的公告
（2026年第24号）

https://www.samr.gov.cn/spcjs/xxfb/art/2026/art_9bd68f8517924598baf560008a034baf.html
```

It explicitly lists:

```text
食品中伐地那非杂质30的测定（BJS 202602）
```

Official date:

```text
2026-06-25
```

Official SAMR Method-database page:

```text
https://www.samr.gov.cn/spcjs/bcjyff/art/2026/art_e0645ab3645943919cf87a9d71a7c7ac.html
```

The database index shows the page as published on 2026-07-16.

No superseding Method was identified during B5-7A.

## 3. Official regulatory scene — VERIFIED

SAMR official news:

```text
市场监管总局发布6项食品补充检验方法
https://www.samr.gov.cn/xw/sj/art/2026/art_3d3b9f60d6d3413fa5c8cb6d0a545a1d.html
```

states that BJS 202602 can detect:

```text
功能性食品中隐蔽添加的壮阳药物衍生物
```

This is current official regulatory context, not a pharmacological guess.

It aligns semantically with the existing current `male_function` direction, but it still does not by itself create a concrete Substance mapping.

## 4. Official fulltext transport gap

Accepted B5 research workflow recorded:

```text
official page SHA-256 =
674D85F7A65D03E58939515203CCD41BF2410C4723CC3DC0C49F3C752A981F4C

AuthorizedRead response SHA-256 =
C63B888DAC262CBD5C19FED9C96AB0246A8EAF6240826AA045855F573153C2C4

attachment_candidates = []
```

AuthorizedRead returned effectively:

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
official Method body = NOT recovered
official attachment URL/SHA-256 = NOT recovered
```

## 5. Third-party Method reproduction — cross-check only

Dikma published a BJS 202602 reproduction:

```text
https://dikma.com.cn/details/Default2-102880.html
```

It reports:

```text
method = UPLC-MS/MS
target = 伐地那非杂质30
matrices =
  压片糖果
  咖啡
  苹果汁饮料
  白酒
  胶基糖果
  果冻
external-standard calculation
```

It also states BJS 202602 fills a screening gap because BJS 202405 does not include this target.

These are useful content cross-checks, but the page is not SAMR and does not expose the target CAS. Do not convert these matrices into runtime MethodApplicability before the official-source Gate is resolved.

## 6. Chemical identity — candidate evidence exists, canonical identity unresolved

Commercial chemical sources commonly map:

```text
伐地那非杂质30
Vardenafil Impurity 30
O-Propyl Vardenafil
CAS 2840532-32-1
formula C24H34N6O4S
```

However the naming environment is not stable enough for runtime governance.

### 6.1 2840532-32-1 is not an unambiguous BJS identity proof

PubChem CID 172560681 indexes CAS `2840532-32-1`, but its depositor-supplied synonym is:

```text
Sildenafil Impurity 72
```

rather than an official BJS identification of “Vardenafil Impurity 30”.

### 6.2 Commercial impurity numbering conflicts

At least one commercial supplier labels a completely different compound/CAS `1792190-72-7` as “Vardenafil Impurity 30”.

That CAS corresponds to a small protected aminopiperidine structure, not the C24H34N6O4S structure associated with O-propyl vardenafil in other sources.

Therefore commercial “Impurity 30” numbering is vendor-dependent and cannot establish BJS202602 canonical identity.

### 6.3 Official standard-sample project is a useful clue, not equivalence proof

The National Public Service Platform for Standards has a 2026 project:

```text
食品检测用O-丙基伐地那非纯度标准样品
CRM of purity O-propyl vardenafil for Food Testing
https://std.samr.gov.cn/gsm/search/gsmDetailed?id=4A9C0BCC7AFC9E65E06397BE0A0A3B06
```

This is highly relevant context, but the visible project record does not explicitly state:

```text
O-丙基伐地那非 == BJS 202602 伐地那非杂质30
```

So B5-7A does not create a canonical Substance from it.

## 7. Current male_function overlap

Current `risk-substance-reference@2026.09-c7` already contains:

```text
male_function
→ substance_group: 那非类、拉非类物质
→ current_official_guidance
```

The underlying 2025 SAMR source defines the group as including sildenafil, tadalafil and other drugs and their derivatives, and links it to food marketed with “补肾壮阳”等功效.

Current runtime also has many concrete PDE5-related Substance entities from BJS 202405, including:

```text
伐地那非
伪伐地那非
乙酰伐地那非
N-去乙基伐地那非
羟基伐地那非
伐地那非-N-氧化物
伐地那非哌嗪酮
...
```

But:

```text
substance_group_memberships = 0
```

The project intentionally does not expand the group to every plausible chemical member.

Therefore BJS 202602 does not automatically add “伐地那非杂质30” to the group.

## 8. B5-7A decision

B5-7A is complete as a Method identity / regulatory-scene / source-gap audit.

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
inspection-reference@2026.09-b10
risk-substance-reference@2026.09-c7
```

No new:

- canonical Substance;
- MethodSubstance;
- MethodApplicability;
- substance_group_membership;
- Claim→Risk;
- Risk→Substance.

Candidate governance records B5-7A at `inspection_method_candidates_v2@2026.09-b12`.

## 9. Next subtask — B5-7B

Do only the BJS 202602 promotion-readiness / identity decision:

1. decide whether BJS202602 should be deferred pending stable official fulltext;
2. decide whether the O-propyl-vardenafil clue is sufficient for a governed candidate identity or remains unresolved;
3. preserve `substance_group_memberships = 0` unless an explicit source supports membership;
4. do not turn the existing male_function group relation into a concrete mapping merely because BJS202602 detects a “壮阳药物衍生物”;
5. do not encode third-party matrices as runtime MethodApplicability unless the provenance policy explicitly allows it;
6. if deferred, advance to the next verification candidate without weakening the Gate.


## 10. B5-7B promotion-readiness / identity decision

Decision:

```text
DO NOT PROMOTE BJS 202602
```

Keep:

```text
status = verification
expected_depth = reference_only
promoted_method_id = null
promoted_dataset_version = null
runtime_consumed = false
```

### 10.1 O-propyl-vardenafil evidence

The official national reference-material project:

```text
食品检测用O-丙基伐地那非纯度标准样品
CRM of purity O-propyl vardenafil for Food Testing
```

confirms that O-propyl vardenafil is an official food-testing reference-material development target.

It does **not** currently state that:

```text
O-丙基伐地那非
==
BJS 202602 伐地那非杂质30
```

The project is therefore an identity clue, not an equivalence authority.

### 10.2 Why canonical identity stays unresolved

The following combination is insufficient for runtime governance:

```text
commercial impurity numbering
+ third-party method reproduction
+ official O-propyl-vardenafil standard-sample project
```

because commercial “Impurity 30” numbering is inconsistent and the stable SAMR Method body remains unavailable.

B5-7B therefore creates no:

- canonical Substance;
- MethodSubstance;
- MethodApplicability;
- substance_group_membership;
- concrete Risk→Substance.

The current `male_function → 那非类、拉非类物质` group remains unexpanded.

### 10.3 Resume condition

Resume BJS202602 only when at least one of the following becomes available:

1. stable SAMR official Method body/attachment explicitly identifying the target; or
2. another first-party source explicitly establishing the equivalence between O-propyl vardenafil and BJS202602's “伐地那非杂质30”.

Candidate governance records this decision in `inspection_method_candidates_v2@2026.09-b13`.

Next B5 target: BJS 201901, whose official SAMR `.doc` attachment is already available and should be parsed rather than continuing to weaken the provenance Gate on blocked 2026 pages.
