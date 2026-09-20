# V2-B5-6A BJS 202601 Identity / Source-Gap Audit

> Status: B5-6A PARTIAL VERIFIED；B5-6B DEFERRED — official Method body/applicability unresolved; official news scene retained as separate Risk-governance backlog; runtime unchanged  
> Date: 2026-09-20  
> Scope: Method identity / official source transport / analyte identity / regulatory-scene separation / runtime overlap  
> Runtime decision: DO NOT PROMOTE in B5-6A

## 1. Why this audit exists

BJS 202601 is a current Method candidate:

```text
食品中布噻嗪和美布噻嗪的测定
BJS 202601
```

Its title names only two targets, making it a small candidate for deep verification.

The permanent boundary still applies:

```text
Method detects Substance ≠ governed Risk→Substance
pharmacological role ≠ regulatory mapping
official news context ≠ automatic runtime mapping
```

## 2. Official Method identity — VERIFIED

Primary official announcement:

```text
市场监管总局关于发布《食品中布噻嗪和美布噻嗪的测定》等6项食品补充检验方法的公告
（2026年第24号）

https://www.samr.gov.cn/spcjs/xxfb/art/2026/art_9bd68f8517924598baf560008a034baf.html
```

The announcement explicitly identifies:

```text
食品中布噻嗪和美布噻嗪的测定（BJS 202601）
```

Announcement date:

```text
2026-06-25
```

Official SAMR method-database page:

```text
https://www.samr.gov.cn/spcjs/bcjyff/art/2026/art_6ece5af221c5468aa3c846c0644ac093.html
```

The database page was published on 2026-07-16 and remains present in the current official database.

No superseding Method was identified during this audit.

## 3. Official regulatory scene — VERIFIED, but separate from runtime Risk governance

SAMR's official news article:

```text
市场监管总局发布6项食品补充检验方法
https://www.samr.gov.cn/xw/sj/art/2026/art_3d3b9f60d6d3413fa5c8cb6d0a545a1d.html
```

states that BJS 202601 can detect diuretic/antihypertensive drugs illicitly added to:

```text
减肥食品
降压食品
```

This is stronger than inferring a scene from pharmacology alone.

However B5-6A does not write this directly into `risk-substance-reference`.

Reason:

```text
official regulatory scene evidence
→ candidate input for separate Risk governance
≠ automatic Method→Risk side effect
```

If a future Risk-governance subphase uses this source, it must independently decide exact risk_category, product_scope, concrete-vs-group target semantics and presentation boundary.

## 4. Official fulltext transport gap

Accepted B5 research workflow queried the BJS 202601 official database page.

Recorded page facts:

```text
official page SHA-256 =
11D74FC5B4647FF6A7385161B70256E9CEB8BEBD57C98EEB53E3E10B213EEB33

AuthorizedRead response SHA-256 =
029F3523535C4B50C6EBC7EFC0FDB03C2D9697FB954ACEA8C32F39E467F12520

attachment_candidates = []
```

The reconstructed AuthorizedRead response is effectively:

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
official fulltext body = NOT recovered
official attachment URL / SHA-256 = NOT recovered
```

Public third-party standard indexes checked during B5-6A also did not expose a complete Method text; Foodmate marks BJS 202601 as having no downloadable text.

Do not invent Method-level applicability from summary/news wording.

## 5. Target chemical identities — VERIFIED independently

The two title targets are:

| Method source label | Canonical English identity | CAS | Current runtime Substance |
|---|---|---:|---|
| 布噻嗪 | Butizide / Buthiazide | 2043-38-1 | missing |
| 美布噻嗪 | Mebutizide | 3568-00-1 | missing |

Independent identity sources:

### 布噻嗪

PubChem CID 16274:

```text
BUTHIAZIDE / Butizide
CAS 2043-38-1
https://pubchem.ncbi.nlm.nih.gov/compound/Buthiazide
```

### 美布噻嗪

PubChem CID 71652 / NLM MeSH / FDA GSRS support:

```text
Mebutizide
CAS 3568-00-1
https://pubchem.ncbi.nlm.nih.gov/compound/Mebutizide
https://meshb.nlm.nih.gov/record/ui?ui=C008338
```

These are chemical-identity sources only.

They do not prove Method matrix/applicability and do not create regulatory Risk mappings.

## 6. Method role and applicability — UNRESOLVED

Because the official Method body is not available through the current SAMR transport and no stable complete mirror was located during B5-6A, do not encode or claim:

- chromatographic / mass-spectrometric determination role;
- qualitative/quantitative confirmation rules;
- complete food categories;
- product forms;
- sample preparation branches;
- include / conditional / exclude applicability;
- limits or result-expression clauses.

An industry article mentions use in weight-loss products such as pressed candy, but this is not sufficient to become MethodApplicability.

The official SAMR news phrase “减肥、降压食品” is a regulatory scene description, not a formal Method matrix list.

## 7. Current runtime overlap

At `inspection-reference@2026.09-b10`:

```text
布噻嗪 / 2043-38-1 → missing
美布噻嗪 / 3568-00-1 → missing
```

At `risk-substance-reference@2026.09-c7`:

```text
no concrete mapping for 布噻嗪 / 2043-38-1
no concrete mapping for 美布噻嗪 / 3568-00-1
```

The existing historical `blood_pressure` data contains other thiazide/antihypertensive substances, but that does not authorize extrapolation to these two compounds.

## 8. B5-6A decision

B5-6A is complete as an identity/source-gap audit, not as a full Method-content verification.

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

- Substance;
- MethodSubstance;
- MethodApplicability;
- Claim→Risk;
- Risk→Substance;
- group membership.

Candidate manifest records the B5-6A findings at `inspection_method_candidates_v2@2026.09-b10`.

## 9. Next subtask — B5-6B

Do only the BJS 202601 provenance/promotion-readiness decision:

1. decide whether the official news context should remain audit-only or enter a separate Risk-governance backlog;
2. preserve the no-orphan-Substance invariant;
3. determine whether any official Method body/attachment can be recovered by a stable route;
4. if not, defer BJS202601 at `verification/reference_only`;
5. do not create MethodSubstance or MethodApplicability without verified Method content;
6. do not create Risk mappings merely because the two compounds are diuretics/antihypertensives;
7. if future Risk governance uses the SAMR news source, do so independently of Method promotion.


## 10. B5-6B provenance / promotion-readiness decision

B5-6B separates two questions that must not be collapsed.

### 10.1 Method promotion

Decision:

```text
DO NOT PROMOTE BJS 202601
```

Reason:

- official announcement/database prove Method identity;
- official news proves a meaningful regulatory scene;
- target chemical identities are independently verified;
- but official Method body/attachment is still unavailable;
- formal determination role and MethodApplicability are unresolved;
- current `verified_reference` does not support preloading orphan Substance rows.

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

### 10.2 Risk-governance evidence

The SAMR news source is stronger than a pharmacological inference because it explicitly describes BJS 202601 as detecting diuretic/antihypertensive drugs illegally added to:

```text
减肥食品
降压食品
```

Therefore B5-6B classifies it as:

```text
independent Risk-governance backlog candidate
```

It is **not** written into `risk-substance-reference` during B5.

A future Risk-governance subphase must independently decide whether the source supports any of:

```text
weight_loss → 布噻嗪
weight_loss → 美布噻嗪
blood_pressure → 布噻嗪
blood_pressure → 美布噻嗪
```

and must define exact product_scope, target semantics, evidence grade/basis type and presentation boundary.

No such concrete mapping is asserted by B5-6B.

### 10.3 Resume condition

Resume BJS202601 Method promotion only after a stable official Method body/attachment becomes available, or after an explicit project-level provenance-policy change.

Do not repeat the chemical-identity audit from scratch.

Candidate governance records this decision in `inspection_method_candidates_v2@2026.09-b11`.
