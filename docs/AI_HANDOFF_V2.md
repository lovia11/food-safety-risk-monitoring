# AI Development Handoff — V2 Current Truth

> Status: CANONICAL CURRENT-DEVELOPMENT HANDOFF  
> Prepared from branch: `ux-redesign-v1`  
> Last accepted runtime code/config/test state: `b7b99405ef1546a16e9ce01162ae408d18dd2aac` (`Surface layered screening recommendations`)  
> Current accepted B5 research-workflow state: `fe1cc7ee27b7897222448dc5ba2083c1843317a1` (`Parse legacy DOC files in B5 source research`)  
> Date: 2026-09-21  
> Important: handoff/document commits may advance HEAD after the commit above. Always refresh the branch HEAD before editing.

This is the **first document a new ChatGPT conversation or coding agent should read** before continuing development.

It exists because the repository contains many accepted historical phase documents whose counts and phase labels are intentionally preserved as snapshots. Those documents remain useful evidence, but they must not override the current code/configuration state described here.

---

## 0. Source priority and takeover procedure

When information conflicts, use this order:

1. **current code / tests / governed config on `ux-redesign-v1`**
2. **this file: `docs/AI_HANDOFF_V2.md`**
3. `docs/CURRENT_SYSTEM_STATUS.md`
4. `PROJECT_STATUS.md`
5. product/architecture/domain/UX/knowledge-governance canonical docs
6. accepted ADRs
7. phase-specific B2/B3/B4/B5 documents as historical implementation evidence
8. `docs/archive/**` is historical only and never current specification

Before any code change:

```text
refresh HEAD
→ inspect current config/tests relevant to the task
→ identify the layer where the problem actually lives
→ check whether the requested idea conflicts with existing design
→ make the smallest correct design-level change
→ syntax / targeted gate
→ full acceptance when the phase requires it
```

Do **not** continue from chat memory when current repository state differs.

---

# 1. Product positioning

Current positioning:

> 面向网络食品监管排查场景，以淘宝商品为当前数据源，通过可追溯页面证据、受治理页面宣传 Claim、监管知识关系和官方检验方法，为人工研判及抽检形成提供辅助信息的本地监管工作台。

The system is **not**:

- a crawler-only project;
- an AI legality classifier;
- an efficacy verification system;
- a detector proving that a substance exists in a product;
- a laboratory replacement;
- a risk-probability model;
- an automatic enforcement system.

Permanent semantic boundary:

```text
page observation
≠ regulatory interpretation
≠ governed knowledge
≠ inspection recommendation
≠ human decision
≠ laboratory finding
```

User-facing conclusions may say:

- 页面宣传线索；
- 监管关注方向；
- 建议关注/检测；
- 需补充商品信息；
- 需人工复核；
- 历史专项抽检/风险监测资料参考。

They must not say:

- “该商品违法”；
- “该商品含有某药物”；
- “已检出某物质”；
- “风险概率为 X%”；
- “历史清单就是当前统一法定抽检项目”。

---

# 2. Development collaboration rule — very important

The user explicitly rejected patch-driven development.

A new idea from the user is **not automatically a new design decision**.

For every new request or observation, first classify it:

```text
A. consistent with current design → absorb into the current phase
B. reasonable but belongs to a later phase → defer explicitly
C. exposes a real design defect → fix the underlying abstraction
D. local symptom only → do not redesign the whole system
E. benefit is lower than governance / engineering cost → do not adopt
```

Always diagnose the root layer first:

```text
collection
→ Evidence
→ Claim
→ Claim→Risk governance
→ Risk→Substance
→ Method / applicability
→ Recommendation
→ presentation
```

Do not see a screenshot problem and immediately edit the closest React component.

The user also asked that tasks be **split into small independently verifiable stages**. Avoid one response that mixes research, schema changes, runtime changes, CI, documentation, and the next phase.

Preferred cadence:

```text
one subtask
→ one explicit result
→ one Gate
→ stop
→ next subtask
```

---

# 3. Active branch, runtime and schema

Active development branch:

```text
ux-redesign-v1
```

Backend:

- Python 3.10.x
- `ThreadingHTTPServer`
- SQLite
- Playwright visible Chrome/CDP
- `ManualActionGate`
- local entry: `python -m src.local_api`

Frontend:

- React
- TypeScript
- Vite
- current source: `frontend/`

Current SQLite schema:

```text
SCHEMA_VERSION = 14
```

Historical status docs that still say schema 13 are stale for current development.

Local repository used by the user:

```powershell
D:\毕业设计-ux
```

Normal update:

```powershell
Set-Location "D:\毕业设计-ux"
git switch ux-redesign-v1
git pull origin ux-redesign-v1
```

---

# 4. Architecture and data authority

High-level runtime:

```text
React / Vite
→ /api
→ Local API / TaskManager
→ StandalonePipeline
→ output/<run_id>/
→ SQLite projection
→ Review / Sampling workflows
```

Data authority:

- `output/<run_id>/`: collection and processing facts
- `claim_analysis.json`: V2 Claim derived authority
- `claim_consistency.json`: ClaimConsistency derived authority
- `inspection_recommendation.json`: derived Recommendation under recorded knowledge/context versions
- `data/app.db`: query projection + current Review/Sampling business state
- `config/`: governed versioned runtime knowledge
- frozen Sampling exports: immutable historical list facts

Human decisions require more care than rebuildable run projections.

---

# 5. Collection and Evidence boundaries

Taobao collection uses browser-mediated normal interaction.

Allowed:

- visible Chrome;
- reuse a browser login profile;
- user manually handles login / slider / CAPTCHA / 2FA;
- low-scale local collection.

Do not implement authentication bypass or CAPTCHA evasion.

Evidence rules:

- DOM determines current-product ownership.
- Network responses can help preserve original assets.
- Screenshot preserves page context.
- Seller-managed content can become formal Claim evidence.
- UGC comments/Q&A are auxiliary only.
- recommendation cards / other products are `excluded_other_product`.
- SearchQuery is a discovery input, not Evidence.

Evidence should retain provenance such as IDs, source type/path, text, asset locator/origin, timestamps and artifact linkage.

---

# 6. OCR

OCR implementation is in `src/phase2_ocr.py`.

Current code should be treated as authority if older README/OCR text conflicts.

Known implementation direction from the active branch history:

- device `auto`
- GPU preferred if Paddle CUDA is available
- CPU fallback
- PP-OCRv6 medium detector/recognizer
- explicit diagnostic behavior for unavailable GPU

Do not redesign OCR into Redis/Celery/microservices merely for throughput.

---

# 7. Domain separations that must never collapse

Core invariants:

```text
ClaimSignal ≠ HealthFunction ≠ RiskSignal
Reference membership ≠ operational search availability
Method detects Substance ≠ Claim maps to Substance
SearchQuery ≠ Evidence
UGC ≠ formal seller Claim
logo / registration-number clue ≠ verified health-food identity
search region ≠ declared origin
```

A Method cannot create a Risk mapping.

A pharmacological relationship cannot create a regulatory relationship.

A substance group cannot be expanded to every plausible member without explicit governed membership/source support.

---

# 8. Monitor / search governance

The project has a formal Monitor Reference catalog.

Existing accepted model:

- official reference objects are separate from operational queries;
- Quick Task free text does not write governed SearchQuery;
- SearchQuery provenance includes:
  - `standard_name`
  - `official_alias`
  - `observed_product_form`
  - `manually_curated`
- lifecycle examples:
  - candidate_unvalidated
  - search_validated
  - rejected_low_relevance
  - paused_scope_issue
  - deprecated

Do not invent synonyms to improve recall.

Historical V2-4 validation docs contain the exact operational-query results; do not infer current query status from this handoff if a code/config check can answer it.

---

# 9. ProductFact / health-food identity / ClaimConsistency

## 9.1 ProductFact

Implemented explicit fact type includes:

```text
declared_origin
```

Do not infer declared origin from:

- search region;
- seller address;
- manufacturer address;
- warehouse/shipping;
- title wording;
- UGC;
- raw-material origin.

Missing stays unknown/—. Conflicting explicit values are preserved as conflict.

## 9.2 HealthFoodIdentity

Path:

```text
page identity clues
→ candidate
→ authoritative registry lookup
→ verified match
→ official functions
```

Only an authoritative record + conservative current-product match may produce `verified_match`.

Logo/OCR registration number alone is not enough.

## 9.3 ClaimConsistency

Non-adjudicative states include concepts equivalent to:

- function topic recorded
- function topic not recorded
- no governed mapping
- mapping unresolved

Do not convert this into pass/fail/compliance/legality scoring.

---

# 10. V2 Claim current state

Current Claim taxonomy contains:

```text
7 Claim types
42 exact governed expressions
```

Claim types:

1. `sleep_related` — 睡眠相关宣传
2. `blood_pressure_related` — 血压相关宣传
3. `blood_lipid_related` — 血脂相关宣传
4. `weight_management` — 体重管理相关宣传
5. `male_function_related` — 男性功能相关宣传
6. `blood_glucose_related` — 血糖相关宣传
7. `anti_fatigue_related` — 体力疲劳相关宣传

Do not bulk-expand a Claim type into Risk.

Exact expression governance remains intentional.

---

# 11. B3 temporal governance — accepted design

Historical central sampling/risk-monitoring material may support **screening reference**, but it may not masquerade as a current mandatory inspection list.

The Claim Inspection Bridge now supports three temporal policies:

```text
current_only

historical_reference_allowed

current_plus_historical_reference_allowed
```

Rules:

- historical mappings require explicit allowlists;
- no global “open all historical for this category” behavior in V2 Claim production;
- historical rows must remain `historical_sampling_plan / historical`;
- current+historical keeps current primary provenance and selectively adds one governed historical cohort.

Historical UI disclosure must remain visible when historical references contribute.

---

# 12. B4 — seven regulatory directions are implemented and accepted

B4 is no longer pending.

Seven directions:

1. `weight_loss`
2. `male_function`
3. `sleep_aid`
4. `blood_pressure`
5. `blood_lipid`
6. `blood_glucose`
7. `anti_fatigue`

Current Risk knowledge:

```text
config/risk_substance_reference.json
dataset_version = 2026.09-c7
total mappings = 83
current = 13
historical = 70
```

Current Claim→Risk bridge:

```text
config/claim_inspection_bridge_v2.json
bridge_version = claim-inspection-bridge-v2.6
bridge mappings = 25
```

Important: c7 added two blood-glucose historical concrete relationships after KJ201902 resolved identity/name normalization:

- source “格列本脲” → canonical `格列苯脲`
- source “马来酸罗格列酮” → canonical parent `罗格列酮`

The **Risk basis remains the 2018 central sampling material**. KJ201902 was only used to resolve identity/salt normalization. This is explicitly **not Method→Risk inference**.

---

# 13. Sleep / cardiometabolic / weight / male / anti-fatigue expression policy

Do not rebuild these from scratch. Read current bridge config first.

Accepted examples:

## Sleep

Explicit functional expressions such as:

- 改善睡眠
- 有助于改善睡眠
- 助眠
- 安睡
- 好眠
- 深睡
- 催眠

can enter `sleep_aid` under their governed policies.

Broad/symptom/traditional expressions such as:

- 睡眠
- 入睡
- 失眠
- 辗转反侧
- 安神

remain Claim-only unless separately governed.

## Cardiometabolic

Blood-pressure/blood-lipid/blood-glucose official/transition function wording and separately governed explicit result expressions can enter their directions.

Broad topic/disease words do not automatically trigger Risk.

## Weight

Current admitted production scope includes:

- 减肥
- 有助于控制体内脂肪

Do not automatically admit all `weight_management` words such as 减脂/瘦身/燃脂 without a new governance decision.

## Male

Current production emphasis remains exact governed expressions such as:

- 壮阳
- 补肾

Do not bulk-admit 阳痿/早泄/遗精/男性功能.

## Anti-fatigue

Current official/current-transition expressions include:

- 抗疲劳
- 缓解体力疲劳

---

# 14. Presentation language contract

Do not expose architecture jargon as primary user language.

Avoid user-facing wording such as:

- “结构化页面 Evidence”
- “Phase3”
- “V2”
- “KnowledgeTrace”
- “治理映射” as implementation jargon

Preferred business language:

```text
未发现重点宣传线索
已发现宣传线索，暂无对应抽检建议
已识别抽检关注方向，暂无适用检测方法
已形成抽检辅助建议
需补商品信息
需核对商品信息
```

Keep one clear page-level boundary statement rather than repeating defensive disclaimers in every card.

The complete rule is in:

```text
docs/PRESENTATION_LANGUAGE_CONTRACT_V2.md
```

---

# 15. B5 current truth

B5 Inspection Method governance is **COMPLETE / ACCEPTED**. Do not reopen Method expansion by default; deferred candidates are evidence-bounded backlog items, not current blockers.

Goal:

```text
existing Risk / Substance
→ official Method candidate
→ official full-text verification
→ MethodSubstance
→ MethodApplicability
→ lifecycle / provenance
→ controlled promotion
```

Do not expand Claim/Risk merely because a Method exists.

## 15.1 Inspection Reference

Current accepted runtime:

```text
config/inspection_reference.json
dataset_version = 2026.09-b11
methods = 11
recommendation_ready current methods = 10
revoked reference_only methods = 1
substances = 219
method-substance relations = 263
method applicability records = 61
regulatory documents = 9
substance regulatory contexts = 1
substance group memberships = 0
```

Indexed methods:

- BJS 202209 — recommendation_ready
- BJS 201701 — recommendation_ready
- BJS 201710 — recommendation_ready
- KJ201903 — recommendation_ready
- GB/T 45443-2025 — recommendation_ready
- BJS 202405 — recommendation_ready
- GB/T 5009.170-2003 — revoked / reference_only
- KJ201901 — recommendation_ready
- KJ201902 — recommendation_ready
- BJS 201808 — recommendation_ready
- BJS 201901 — recommendation_ready

BJS201901 was promoted only after the official SAMR legacy DOC was reproducibly parsed. Its 14 newly governed Substance identities are Method analytes only; the Risk reference remains `2026.09-c7` with 83 mappings.

## 15.2 Candidate manifest

Current B5 exit state:

```text
config/inspection_method_candidates_v2.json
manifest_version = 2026.09-b19
records = 12
promoted traces = 6
deferred verification/reference_only = 6
open undecided candidates = 0
runtime_consumed = false
```

The candidate manifest never becomes runtime merely because a candidate is listed. All six non-promoted records now have explicit provenance/identity reasons for deferral; none is an unfinished B5 decision.

## 15.3 KJ201901 / KJ201902 are already promoted

Do not repeat their promotion.

KJ201901 official full text:

- target: 西地那非、他达拉非
- role: rapid screen
- health-food applicability
- positive screening result requires confirmation
- runtime keeps the already-governed `anti_fatigue` Risk; Method scope must not create new “调节免疫”等 Risk directions
- cross-reactants are not automatically MethodSubstance rows

KJ201902 official full text:

- target: 罗格列酮、格列苯脲
- role: rapid screen
- risk scope: `blood_glucose`
- positive result requires confirmation
- official source salt/name normalization is preserved instead of collapsing source provenance

Their production state remains part of `inspection-reference@2026.09-b11`; their individual promotion trace remains `@ b9`.

---

# 16. Official-source research workflow

Repository workflow:

```text
.github/workflows/b5-official-source-fetch.yml
```

Purpose:

- fetch SAMR official attachments;
- retain SHA-256;
- extract DOCX/PDF text;
- parse legacy Word `.doc` reproducibly through `antiword`;
- upload a research artifact.

This workflow is **research-only**.

It must never automatically write facts into `inspection_reference.json`.

Known official files fetched/located include:

- KJ201901 DOCX
- KJ201902 DOCX
- BJS 201808 DOCX
- BJS 201901 legacy DOC — downloaded and reproducibly parsed with `antiword`

For newer 2025/2026 SAMR method pages the workflow now also records the AuthorizedRead dynamic-body transport, session cookies, AJAX headers, raw API responses and diagnostic scripts. BJS202504 currently demonstrates an **official attachment transport gap**: the official announcement/database identity is verified, but the reconstructed official dynamic-body request still returns `success:false` with no attachment body. Do not invent an official attachment URL.

The B5 candidate doc records hashes and current status.

---

# 17. BJS 201808 — B5-3B accepted

The latest specific development work is BJS 201808.

Canonical audit:

```text
docs/V2_B5_BJS_201808_ANALYTE_AUDIT.md
```

Status:

```text
B5-3A VERIFIED
official SAMR fulltext parsed

B5-3B ACCEPTED
parent Substance identity governed
MethodSubstance / MethodApplicability committed
BJS 201808 promoted to recommendation_ready
inspection-reference@2026.09-b10
```

Accepted baseline:

```text
7e71c41ad6f7ada85df061fcbb1787e2725c2fae
Python syntax gate: success
B3 B4 governance regression: success
V2 full acceptance: success
```

Method:

```text
BJS 201808
食品中5种α-受体阻断类药物的测定
```

Official DOCX SHA-256:

```text
45D85B389553925AF01FCB5EEAB6DE7113E898ED998FCDEE44EBD3476DB696B9
```

Verified target analytes:

1. 酚妥拉明
2. 哌唑嗪
3. 特拉唑嗪
4. 育亨宾
5. 妥拉唑林

Verified method role:

```text
HPLC-MS/MS
quantitative determination
+ qualitative confirmation
```

Verified applicability:

Foods:

- 硬质糖果
- 凝胶糖果
- 酒
- 茶饮料
- similar matrices may refer to the method

Health foods:

- 片剂
- 口服液
- 胶囊剂

## 17.1 Parent analyte vs salt standard

The method targets parent analytes but uses salt standards.

| Parent target | Official standard | Official standard CAS | Canonical parent status |
|---|---|---|---|
| 酚妥拉明 | 甲磺酸酚妥拉明 | 65-28-1 | governed: 50-60-2 |
| 哌唑嗪 | 盐酸哌唑嗪 | 19237-84-4 | parent exists: 19216-56-9 |
| 特拉唑嗪 | 盐酸特拉唑嗪 | 63074-08-8 | governed: 63590-64-7 |
| 育亨宾 | 盐酸育亨宾 | 65-19-0 | governed: 146-48-5 |
| 妥拉唑林 | 盐酸妥拉唑林 | 59-97-2 | governed: 59-98-3 |

Candidate parent identities identified by the audit:

- 酚妥拉明 / Phentolamine — parent CAS 50-60-2
- 哌唑嗪 / Prazosin — parent CAS 19216-56-9 — already exists
- 特拉唑嗪 / Terazosin — parent CAS 63590-64-7
- 育亨宾 / Yohimbine — parent CAS 146-48-5
- 妥拉唑林 / Tolazoline — parent CAS 59-98-3

These parent CAS identities are **chemical identity evidence**, not regulatory Risk evidence.

## 17.2 Current Risk effect of these analytes

- 哌唑嗪 already has an explicit historical `blood_pressure` Risk mapping.
- 育亨宾 currently exists only through a current male-function **group**:
  `育亨宾及其系列衍生物`.
  There is no concrete yohimbine Risk mapping.
- 酚妥拉明 / 特拉唑嗪 / 妥拉唑林 currently have no governed Risk mapping.

Therefore BJS201808 promotion must **not** create any new Risk relation.

## 17.3 B5-3B accepted result

Completed in `inspection-reference@2026.09-b10`:

1. governed the four missing canonical parent Substance identities and preserved existing 哌唑嗪;
2. retained independent chemical-identity provenance;
3. added five MethodSubstance rows with official salt `source_label` / `source_cas_no` and explicit normalization notes;
4. added seven conservative MethodApplicability rows for the explicitly listed categories/forms;
5. retained “其他类似基质可参照本方法” as source scope text only, not an unconditional runtime include;
6. added **zero** Claim→Risk mappings, **zero** Risk→Substance mappings and **zero** yohimbine group memberships;
7. promoted BJS 201808 to current `recommendation_ready`.

Canonical Yohimbine now exists in the Method index, but there is still no concrete male-function Risk→Yohimbine mapping.

---

# 18. BJS 202504 — B5-4A audited, runtime unchanged

Canonical audit:

```text
docs/V2_B5_BJS_202504_ANALYTE_AUDIT.md
```

Status:

```text
B5-4A CONTENT AUDIT COMPLETE
official Method identity/current database presence verified
full-text content cross-checked
5 candidate chemical identities cross-checked
official SAMR attachment URL/SHA-256 unresolved
runtime unchanged
candidate remains verification/reference_only
```

Verified official Method identity:

```text
BJS 202504
食品中酚丁、双丙酚丁、双酚沙丁、双酚沙丁醋酸酯和酚丁双环丙甲酸酯的测定
official date = 2025-09-29
```

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

Candidate chemical identities:

| Method source label | Candidate CAS | Runtime status |
|---|---:|---|
| 酚丁 | 125-13-3 | missing |
| 双丙酚丁 | 2943075-86-1 | missing |
| 双酚沙丁 | 17692-24-9 | missing |
| 双酚沙丁醋酸酯 | 14008-48-1 | missing |
| 酚丁双环丙甲酸酯 | 2943075-87-2 | missing; source-label normalization still needs explicit governance |

Current Risk has a `weight_loss` **group** reference to “酚汀（酚丁）、酚酞及其酯类衍生物或类似物”, but there are no concrete Risk→Substance mappings for these five CAS and no `substance_group_memberships`.

Therefore B5-4A creates **zero** runtime Risk/Method facts.

## 18.1 B5-4B source-gap result — deferred, runtime unchanged

The current Inspection Reference has no orphan Substance rows:

```text
205 Substance
205 referenced by MethodSubstance
0 orphan
```

A real Playwright/Chromium load of the official SAMR BJS202504 page at research baseline `cff95b6388774f363f7b0a60fb0049c107bee4d6` still produced:

```text
page HTTP 200
correct Method title
no Method body scope text
no attachment links
AuthorizedRead API success=false / data={}
```

Therefore:

- do not preload five orphan Substance identities;
- do not promote BJS202504 from third-party fulltext transport alone;
- keep it `verification/reference_only`;
- resume only if a stable official attachment/body source becomes available.

All four workflows at `cff95b6...` passed: syntax, B3/B4 governance, B5 research, V2 full acceptance.

## 18.2 B5-5A BJS202501 audit — complete, runtime unchanged

Canonical audit:

```text
docs/V2_B5_BJS_202501_ANALYTE_AUDIT.md
```

Verified/cross-checked facts:

```text
BJS 202501
食品中坎地沙坦酯、拉西地平、阿齐沙坦的测定
official identity/current database presence = verified
official SAMR dynamic body/attachment = unresolved
complete-document mirror = available for content cross-check
runtime = unchanged
```

Targets:

| Source label | CAS | Runtime |
|---|---:|---|
| 坎地沙坦酯 | 145040-37-5 | missing |
| 拉西地平 | 103890-78-4 | missing |
| 阿齐沙坦 | 147403-03-0 | missing |

Explicit applicability cross-check:

- 压片糖果
- 代用茶
- 固体饮料
- 茶饮料
- 饼干
- 果冻
- 配制酒
- 保健食品：口服液、茶剂、片剂、硬胶囊、软胶囊

Current `risk-substance-reference@2026.09-c7` has no concrete `blood_pressure` Risk→Substance mapping for the three targets.

Therefore B5-5A creates **zero** runtime Method/Risk facts.

## 18.3 B5-5B BJS202501 decision — deferred, runtime unchanged

The decision is now explicit and code-backed.

`src/inspection_reference.py` enforces, for a `verified_reference` dataset:

```text
every Substance
→ referenced by MethodSubstance
   OR SubstanceRegulatoryContext
otherwise validation fails as orphan Substance
```

Therefore “preload the three canonical Substance identities now and attach them to the Method later” is not a valid current-runtime pattern.

For BJS202501 the only available full Method body/CAS/applicability transport is currently a non-SAMR mirror, while the official SAMR announcement/database confirms Method identity but the AuthorizedRead body/attachment remains unavailable.

Decision:

```text
BJS 202501
status = verification
expected_depth = reference_only
runtime = unchanged
deferred pending stable official SAMR body/attachment
```

Do not:

- add the three Substance rows as orphan entities;
- use the mirror alone to create runtime MethodSubstance;
- infer three concrete `blood_pressure` Risk mappings from pharmacology;
- promote merely to improve Method coverage.

Candidate manifest records this at `2026.09-b9`.

## 18.4 B5-6A BJS202601 audit — partial verified, runtime unchanged

Canonical audit:

```text
docs/V2_B5_BJS_202601_ANALYTE_AUDIT.md
```

Verified:

```text
BJS 202601
食品中布噻嗪和美布噻嗪的测定
official identity/current database presence = verified
official SAMR regulatory scene = 减肥食品 / 降压食品
布噻嗪 = 2043-38-1
美布噻嗪 = 3568-00-1
```

Official fulltext status:

```text
SAMR Method page present
AuthorizedRead success=false / data={}
official attachment candidates = none
stable complete Method body = not recovered
```

Therefore Method-level determination role and applicability are still unresolved.

Current runtime has neither concrete Substance and no concrete Risk→Substance mapping for either CAS.

The SAMR news article is recorded as a **future independent Risk-governance evidence candidate**, not written into Risk during B5-6A.

## 18.5 B5-6B BJS202601 decision — deferred, Risk evidence backlogged

Decision:

```text
BJS 202601
status = verification
expected_depth = reference_only
runtime = unchanged
deferred pending stable official Method body/attachment
```

Why:

- official announcement/database proves Method identity/current presence;
- official SAMR news proves a real regulatory scene involving `减肥食品 / 降压食品`;
- chemical identities for 布噻嗪 / 美布噻嗪 are independently verified;
- but official Method body/attachment remains unavailable;
- therefore determination role and formal MethodApplicability cannot be governed;
- `verified_reference` still must not receive orphan Substance rows.

The SAMR news article is now explicitly retained as an **independent Risk-governance backlog candidate**.

This does **not** yet create:

```text
weight_loss → 布噻嗪
weight_loss → 美布噻嗪
blood_pressure → 布噻嗪
blood_pressure → 美布噻嗪
```

Any future Risk mapping must independently decide:

- exact risk_category;
- exact product_scope;
- concrete Substance vs group semantics;
- current evidence grade/basis_type;
- presentation boundary.

Candidate manifest records this at `2026.09-b11`.

## 18.6 B5-7A BJS202602 audit — partial verified, runtime unchanged

Canonical audit:

```text
docs/V2_B5_BJS_202602_ANALYTE_AUDIT.md
```

Verified:

```text
BJS 202602
食品中伐地那非杂质30的测定
official identity/current database presence = verified
official SAMR scene = 功能性食品中隐蔽添加的壮阳药物衍生物
```

Official Method transport:

```text
official page SHA-256 = 674D85F7A65D03E58939515203CCD41BF2410C4723CC3DC0C49F3C752A981F4C
AuthorizedRead = success=false / data={}
official attachment candidates = none
```

Third-party Method reproduction cross-checks UPLC-MS/MS and six matrices, but is not runtime authority.

Chemical identity remains unresolved for governance:

- commercial sources commonly use O-Propyl Vardenafil / CAS 2840532-32-1;
- PubChem indexes that CAS under a different impurity synonym;
- at least one supplier uses a different CAS/structure for “Vardenafil Impurity 30”;
- an official standard-sample project exists for O-propyl vardenafil, but the visible record does not explicitly equate it with BJS202602's target.

Current `male_function` already has a current group relation for `那非类、拉非类物质`, but `substance_group_memberships = 0`; B5-7A does not expand the group.

## 18.7 B5-7B BJS202602 decision — deferred, canonical identity unresolved

Decision:

```text
BJS 202602
status = verification
expected_depth = reference_only
runtime = unchanged
deferred pending official Method identity detail / canonical target equivalence
```

The official national reference-material project:

```text
食品检测用O-丙基伐地那非纯度标准样品
CRM of purity O-propyl vardenafil for Food Testing
```

is retained as an **identity clue only**.

It does not currently prove:

```text
O-丙基伐地那非
==
BJS 202602 伐地那非杂质30
```

because the visible official project record does not state that equivalence, while commercial impurity numbering is inconsistent.

Therefore B5-7B adds no:

- canonical Substance;
- MethodSubstance;
- MethodApplicability;
- substance_group_membership;
- concrete Risk→Substance mapping.

The existing `male_function → 那非类、拉非类物质` group remains unexpanded.

Candidate manifest records the defer decision at `2026.09-b13`.

## 18.8 B5-8A/B BJS201901 — PROMOTED / ACCEPTED

Canonical audit:

```text
docs/V2_B5_BJS_201901_ANALYTE_AUDIT.md
```

Official legacy DOC provenance:

```text
SHA-256 =
C4A697A35F4171516C06947C937F0C10D01FDC3AFC671D7780154A5AD9936EE9
bytes = 381952
extraction = antiword
text chars = 18305
```

B5-8B accepted runtime promotion:

```text
BJS 201901
→ inspection-reference@2026.09-b11
→ current / recommendation_ready
→ 27 MethodSubstance
→ 8 conservative MethodApplicability
```

Promotion facts:

- reused 13 existing canonical Substance identities;
- added 14 canonical Substance identities from official Appendix A;
- added zero Claim→Risk / Risk→Substance mappings;
- source `格列本脲 / 10238-21-8` normalizes to canonical `格列苯脲 / 10238-21-8` with source provenance;
- `吡格列酮 / 111025-46-8` matches the existing canonical identity directly and requires no normalization;
- “等食品 / 类似基质 / 等形式” was not converted into unrestricted applicability;
- 口服液 is conservatively `conditional`.

Accepted current inventory:

```text
methods = 11
recommendation_ready = 10
reference_only revoked = 1
substances = 219
MethodSubstance = 263
MethodApplicability = 61
RegulatoryDocument = 9
SubstanceRegulatoryContext = 1
SubstanceGroupMembership = 0
```

Candidate manifest:

```text
2026.09-b19
12 records
6 promoted
6 verification
0 open undecided candidates
runtime_consumed = false
```

Accepted Gate baseline:

```text
b7b99405ef1546a16e9ce01162ae408d18dd2aac
Python syntax gate = success
B3/B4 governance regression = success
V2 full acceptance = success
```

## 18.9 B5-9A BJS202409 audit — partial verified, runtime unchanged

Canonical audit:

```text
docs/V2_B5_BJS_202409_ANALYTE_AUDIT.md
```

Verified:

```text
official identity/current database page = verified
official SAMR Method body = unresolved
AuthorizedRead = success=false / data={}
attachment_candidates = none
```

Secondary content cross-check:

```text
HPLC-MS/MS
19 diuretic targets
9 explicit product categories
```

Current runtime overlap:

```text
3 / 19 candidate Substance already exist
2 / 19 have exact governed historical Risk overlap:
  氢氯噻嗪 → blood_pressure
  呋塞米 → weight_loss
氯噻嗪 exists but has no concrete Risk mapping
```

A secondary summary has a `依善利酮 / 依普利酮` inconsistency, so no canonical identity is governed from secondary text.

## 18.10 B5-9B BJS202409 decision — DEFERRED

B5-9B repeated the official-source Gate.

Confirmed:

```text
SAMR 2024年第51号公告 = official Method identity
current SAMR database = Method still listed
specific Method page = stable title/date only
AuthorizedRead = success=false / data={}
official attachment candidate = none
third-party PDF mirrors = available, cross-check only
```

Decision:

```text
status = verification
expected_depth = reference_only
runtime = unchanged
promotion = deferred
candidate manifest = 2026.09-b17
```

No canonical Substance, MethodSubstance, MethodApplicability, Claim→Risk, Risk→Substance or group membership is added from BJS202409 in B5-9B.

The secondary `依善利酮 / 依普利酮` inconsistency remains unresolved. Promotion requires stable official SAMR fulltext/attachment provenance with a reproducible content hash and official closure of analyte identity, determination role and formal applicability.

B5-9 is complete.

Bounded B5-9B governance Gate:

```text
candidate manifest validation/invariants = success
inspection-reference unchanged = 2026.09-b11
BJS202409 runtime method = absent
Risk mappings unchanged = 2026.09-c7 / 83
Claim bridge unchanged = v2.6 / 25
```

## 18.10A B5-10A BJS202502 audit — PARTIAL VERIFIED, runtime unchanged

Canonical audit:

```text
docs/V2_B5_BJS_202502_ANALYTE_AUDIT.md
```

Verified from first-party / official-institution sources:

```text
SAMR 2025年第39号公告 = BJS 202502 official identity
current SAMR database page = present
南京市市场监督管理局 = LC-triple-quadrupole tandem MS
南京市市场监督管理局 = qualitative + quantitative / 25 β-blocker targets
```

Secondary content cross-check:

```text
25 standard-summary analyte labels
beverages including solid beverages
substitute tea
health foods: oral liquid / tablet / capsule
25 candidate CAS values from a BJS 202502 mixed-standard page
```

Important unresolved source issues:

```text
stable SAMR formal Method body/attachment URL + hash = unresolved
CAS table = secondary only
formal standard material may use parent or salt forms = unresolved
36507-48-9 label discrepancy = 喷布洛尔 / 喷布特罗
57775-29-8 label discrepancy = 卡拉洛尔 / 咔唑心安
```

Current runtime overlap:

```text
1 / 25 existing canonical Substance:
  阿替洛尔 / 29122-68-7

exact governed Risk overlap:
  阿替洛尔 → historical blood_pressure
```

Therefore B5-10A adds no canonical Substance, MethodSubstance, MethodApplicability, Claim→Risk, Risk→Substance or group membership.

Candidate manifest:

```text
2026.09-b18
BJS 202502 = verification / reference_only
runtime unchanged
```

Bounded B5-10A governance Gate:

```text
candidate manifest validation/invariants = success
inspection-reference unchanged = 2026.09-b11
BJS202502 runtime method = absent
Risk mappings unchanged = 2026.09-c7 / 83
Claim bridge unchanged = v2.6 / 25
```

## 18.10B B5-10B BJS202502 decision — DEFERRED

Final provenance result:

```text
SAMR 2025年第39号公告 = official Method identity
current SAMR Method page = present
public Method page = stable title/date only
stable official PDF/DOC/DOCX URL + content hash = unresolved
secondary 25-target/scope/CAS sources = cross-check only
```

Decision:

```text
BJS 202502
status = verification
expected_depth = reference_only
promotion = deferred
runtime = unchanged
candidate manifest = 2026.09-b19
```

No canonical Substance, MethodSubstance, MethodApplicability, Claim→Risk, Risk→Substance or group membership is added from BJS202502. `阿替洛尔 / 29122-68-7` remains an existing overlap only; its historical `blood_pressure` mapping does not authorize expansion to the remaining β-blocker candidates.

B5-10 is complete.

## 18.11 B5 phase exit — COMPLETE / ACCEPTED

B5 candidate governance is closed.

```text
candidate records = 12
promoted traces = 6
deferred verification/reference_only = 6
open undecided candidates = 0
runtime_consumed = false
```

Promoted traces:

- BJS 202405;
- GB/T 5009.170-2003;
- KJ201901;
- KJ201902;
- BJS 201808;
- BJS 201901.

Deferred non-runtime records:

- BJS 202409;
- BJS 202501;
- BJS 202502;
- BJS 202504;
- BJS 202601;
- BJS 202602.

These deferred records are **resolved B5 decisions**, not unfinished tasks. Reopen one only if its missing first-party provenance / canonical-identity condition is actually resolved.

Runtime remains:

```text
inspection-reference@2026.09-b11
11 methods
219 Substance
263 MethodSubstance
61 MethodApplicability
9 RegulatoryDocument
10 current recommendation_ready + 1 revoked reference_only

risk-substance-reference@2026.09-c7
83 mappings

claim-inspection-bridge-v2.6
25 mappings
```

Permanent B5 exit boundary:

```text
MethodSubstance ≠ RiskSubstance
Method cannot create Risk
pharmacology cannot create regulatory mapping
third-party mirror cannot replace missing first-party provenance
deferred candidate ≠ runtime gap that must be force-filled
```

B5 Exit Gate — **SUCCESS**:

```text
candidate manifest = 2026.09-b19
12 = 6 promoted + 6 explicitly deferred
open undecided candidates = 0
inspection-reference unchanged = 2026.09-b11
11 methods / 219 Substance / 263 MethodSubstance / 61 MethodApplicability / 9 RegulatoryDocument
Risk unchanged = 2026.09-c7 / 83
Claim bridge unchanged = v2.6 / 25
all deferred B5 Method numbers absent from runtime
```

GitHub connector note: push-triggered Actions runs/statuses are not visible through the current connector, so do not claim a fresh full-suite CI run for this documentation/candidate-governance closeout. The deterministic B5 Exit Gate above is the verified current-head result.

## 18.12 Post-B5 direction

The next development program is **end-to-end system closure and validation**, not further Method-count expansion.

### Recommendation presentation closure Phase 1 — ACCEPTED

Accepted baseline:

```text
b7b99405ef1546a16e9ce01162ae408d18dd2aac
```

The product-level presentation now separates four user-facing states without changing governed Risk/Method knowledge:

```text
formal recommendation
→ at least one current/applicable suggested Method

needs product context
→ a governed Risk/Method path exists but category/form/ingredient context must be confirmed

screening attention
→ a governed Risk direction exists without a formally usable Method
   OR a V2 Claim topic exists but has no governed Claim→Risk bridge

no clear direction
→ analysis completed with zero current Claim signals
```

Important boundaries:

- Claim-only screening attention is **not** a new Risk mapping.
- Screening attention does not name a Substance unless a governed Risk→Substance relation already exists.
- Historical references retain their disclosure and do not become current requirements.
- `Method → Risk` reverse inference remains forbidden.
- The old dead-end primary copy “当前暂无对应的抽检建议” is no longer used for a recognized Claim topic.

Next subtask should be **representative real-sample validation of these four states** before introducing any new semantic/LLM layer.

Default priorities:

1. validate the governed Evidence → Claim → Risk → Substance → Method → Recommendation chain on representative real/sample cases;
2. identify remaining semantic-understanding gaps separately from knowledge-governance gaps;
3. keep LLM/semantic interpretation upstream of governed Claim/Risk mapping rather than allowing it to invent regulatory relations;
4. stabilize Review / 已纳入 / 暂不纳入 workflow and Recommendation explanations;
5. freeze schema/config/API/UI once the validation corpus passes;
6. then prepare thesis/demo/report evidence.

Do not assign a new phase number until this post-B5 program is explicitly scoped.

---

# 19. Test and CI discipline

The repository now has explicit automated gates.

## 19.1 Syntax

```text
.github/workflows/python-syntax.yml
```

Runs:

```bash
python -m compileall -q src tests scripts
```

This was added after a syntax error escaped into the branch. Do not remove it.

## 19.2 B3/B4 governance regression

```text
.github/workflows/b3-b4-governance.yml
```

Covers Claim bridge, Risk data, temporal governance, knowledge resolver, signal trace, recommendation, runtime, API and audit.

## 19.3 Full acceptance

```text
.github/workflows/v2-full-acceptance.yml
```

Backend:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Frontend:

```bash
npm run test:workflow
npm run typecheck
npm run build
```

Do not mark a major subphase Accepted until the required current-HEAD Gate is green.

## 19.4 Research workflow

```text
.github/workflows/b5-official-source-fetch.yml
```

Research only; never runtime authority.

---

# 20. Testing lessons from B3/B4/B5

Avoid brittle duplicate magic-number assertions.

Test responsibilities should be separated:

```text
data contract tests
→ exact inventory/version where inventory itself is the subject

governance tests
→ what is admitted, rejected, historical/current, allowlisted

runtime E2E tests
→ Claim → Risk → Substance → Method behavior

HTTP tests
→ filtering, read-only semantics, pagination, status codes
→ do not duplicate exact inventory counts unless count is the API contract
```

Other accepted lessons:

- text fixture hashes should normalize line endings before content hashing if the contract is textual identity;
- tests should preserve invariants rather than old one-group/one-substance assumptions;
- when production data legitimately expands, first decide whether a failure means stale test or real business regression.

---

# 21. UI / product workflow constraints

Task creation modes remain:

1. 快速任务（单搜索词）
2. 检测任务（对象词组 / MonitorTarget）

Do not invent a third task paradigm without a product decision.

Review/product handling should remain direct where already accepted:

```text
已纳入 / 暂不纳入
```

Do not reinsert an unnecessary “建议进一步关注” intermediate decision layer.

UI should remain a regulatory/B2B evidence-led workstation.

Do not perform wholesale redesign because of one screenshot or one user comment.

---

# 22. Known documentation drift

Some historical/canonical-looking files still contain counts from earlier V2 phases, for example schema 13, 5 Claim types, 7 methods, or “V2-9 next”.

Those facts are historical snapshots, not current B5 truth.

Current development numbers must come from:

```text
src/data_store.py
config/claim_taxonomy_v2.json
config/claim_inspection_bridge_v2.json
config/risk_substance_reference.json
config/inspection_reference.json
config/inspection_method_candidates_v2.json
```

This handoff intentionally supersedes stale counts until the older long-form status documents are fully rebaselined.

---

# 23. New-conversation startup checklist

A new ChatGPT conversation should do exactly this:

1. Read `AGENTS.md`.
2. Read this file completely.
3. Refresh `ux-redesign-v1` HEAD.
4. Read:
   - `docs/V2_B_METHOD_CANDIDATES.md`
   - `docs/V2_B5_BJS_201808_ANALYTE_AUDIT.md`
   - `docs/V2_B5_BJS_202504_ANALYTE_AUDIT.md`
   - `docs/V2_B5_BJS_202501_ANALYTE_AUDIT.md`
   - `docs/V2_B5_BJS_202601_ANALYTE_AUDIT.md`
   - `docs/V2_B5_BJS_202602_ANALYTE_AUDIT.md`
   - `docs/V2_B5_BJS_201901_ANALYTE_AUDIT.md`
   - `docs/V2_B5_BJS_202409_ANALYTE_AUDIT.md`
   - `docs/V2_B5_BJS_202502_ANALYTE_AUDIT.md`
5. Inspect current:
   - `config/inspection_reference.json`
   - `config/inspection_method_candidates_v2.json`
   - `config/risk_substance_reference.json`
   - `config/claim_inspection_bridge_v2.json`
6. Check current GitHub Actions before claiming a Gate is closed.
7. Treat **B5 as complete**. Do not reopen deferred Method candidates unless a missing first-party provenance/identity condition is actually resolved. Resume with post-B5 end-to-end system closure/validation, scoped from current runtime rather than by adding more Method records.
8. Do not repeat KJ201901/KJ201902/BJS201808 promotion, and do not revisit B4 unless a test or concrete bug demonstrates a B4 regression.

Suggested first prompt in a new conversation:

> 读取仓库 `ux-redesign-v1` 的 `AGENTS.md`、`docs/AI_HANDOFF_V2.md`、`docs/PRESENTATION_LANGUAGE_CONTRACT_V2.md`，以当前代码/测试/config 为最高事实源。B5已COMPLETE；Recommendation presentation closure Phase 1已ACCEPTED：正式建议/筛查关注/需补商品信息/未发现重点线索已分层，且没有修改Risk知识。下一步先用代表性真实商品验证四类状态，再决定是否需要独立RiskHypothesis/LLM语义层；不要继续扩Method数量。

---

# 24. Immediate stop condition

If the current branch differs materially from the state above, stop and re-audit before editing.

Especially stop if:

- `inspection_reference` version is newer than b11;
- `inspection_method_candidates_v2` is newer than b19;
- any deferred B5 candidate has been legitimately advanced by new first-party evidence;
- current HEAD has a failing full acceptance Gate;
- current code/config materially changes the B5 candidate lifecycle or Method/Risk separation;
- a post-B5 task would implicitly reopen B5 Method expansion without an explicit scope decision.

In that case, current repository truth supersedes this handoff and the handoff must be updated before continuing.
