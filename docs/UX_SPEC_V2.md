# UX Specification V2

> Status: CANONICAL
> Applies to: V2
> Last verified phase: V2-6B1
> Owner: Project

This specification governs the V2 interaction model. V2-1 through V2-5 sections marked current describe implemented behavior; later Future sections remain requirements rather than implementation claims.

## 1. Global UI principles

- Present a B2B regulatory workstation: dense enough for analysis, calm, and evidence-led.
- Use visual hierarchy to separate observed facts, derived clues, knowledge support, human decisions, and errors.
- Color carries consistent status meaning; it is never the sole carrier of meaning.
- Interactive regions need practical hit targets and visible focus/hover states.
- The same business action uses the same label and behavior across pages.
- Empty, unavailable, failed, and not-yet-analyzed states remain distinct.
- Do not expose developer controls such as `candidate_limit` and `detail_limit` in the ordinary workflow.
- Preserve readable 13–14px body/table type, 12px auxiliary text, and 11–12px IDs; do not use 10px as general body text.

## 2. Navigation and shell

Current navigation is 商品总览、排查档案、抽检清单. Future V2 navigation adds 统计分析 and 知识库 after their domain and API gates.

The sidebar expands for the product list, automatically collapses when a Product Detail is opened, and respects the user's session choice. Collapsed navigation keeps icons, tooltip, active state, and Sampling badge support. It never expands on hover. Motion is approximately 180–220ms and respects `prefers-reduced-motion`.

## 3. Product Overview

### 3.1 Current business columns

```text
商品
地区信息
页面宣传线索
人工复核
抽检清单
最近采集
历史记录
操作
```

最近采集 means the latest Snapshot time. 历史记录 means Product Snapshot count. Task/source traceability stays in Product Detail and Snapshot timeline rather than occupying a main cross-task table column.

### 3.2 Current V2-1 interaction

- Restore a product thumbnail of approximately 48–56px.
- Make the row clickable while preserving explicit keyboard and action affordances.
- Long titles wrap or truncate predictably without displacing status controls.
- Missing images use a deliberate placeholder, not a broken image icon.

### 3.3 Region presentation

Region is a key/value presentation with independent meanings:

```text
搜索页地区     <observed search result region or —>
商品标称产地   <explicit product-page fact or —>
```

Never label the existing search `region` as 产地、商品产地, or 生产地. Never write or show `商品产地待采集`. A missing declared origin is `—`.

`商品标称产地` is Snapshot-scoped. A single explicit value displays the value plus its page-source type. Equal values from multiple sources display one value with a source count; different explicit values display `存在多个声明` and every value/source without choosing one. `查看依据` shows the exact source text and artifact path. OCR sources can open their existing saved original in the same Lightbox used by Evidence.

## 4. Product Detail

The workspace uses an independently scrollable product list and right detail panel. Snapshot selection controls every Snapshot-bound section: Evidence, recommendation, context, and Review must all correspond to the selected Snapshot.

### 4.1 Current V2-1 summary

The header pairs a product image with product identity and presents four ordered summaries:

```text
页面宣传线索
主要证据
知识桥接
人工状态
```

The header also retains shop, product ID, real product URL, latest collection time, Snapshot count, and Task/source traceability.

### 4.2 Snapshot timeline

- With one Snapshot, compress the timeline into a simple observation summary.
- With multiple Snapshots, show a full timeline and default to the latest.
- Switching a Snapshot never substitutes the latest recommendation, Review, or Evidence.

## 5. Evidence presentation

Backend Evidence records remain separate. The frontend groups them by **Evidence Source Group** for reading.

For one OCR image with N hits, show one source group with N evidence hits, not N duplicate cards. Preserve each record's identifier and exact source for inspection/audit.

Seller-managed Evidence is primary and expanded by default. UGC Evidence is auxiliary and collapsed by default. Excluded-other-product Evidence must not appear as primary evidence for the current Product.

Only offer 查看原图、查看OCR全文, or 查看页面截图 when the underlying asset is available and safe. Do not show inert buttons.

## 6. Image preview — Current V2-1

The primary evidence-browsing flow uses:

- inline thumbnail;
- modal/lightbox;
- `Esc` close;
- zoom controls;
- previous/next navigation;
- a side Evidence list tied to the active source.

Opening every image with `target="_blank"` is not the primary experience. A direct-file fallback may remain when appropriate.

## 7. Knowledge and analysis states

The UI must distinguish:

| State | Presentation meaning |
|---|---|
| Not analyzed | The Snapshot has not completed Phase3; it is not pending Review. |
| Analysis complete / 0 Evidence | Analysis succeeded but the current clue vocabulary found no Evidence. It can still be reviewed. |
| Evidence found / Unmapped | Page clues exist, but verified knowledge has no mapping; show a Knowledge Gap. |
| Risk mapped / No method | A supported risk direction exists but no applicable/verified method is available. |
| Recommendation available | Show the supported inspection assistance and its basis. |
| Recommendation error | Keep Evidence and Review available; state that the recommendation is unavailable. |

The recommendation title is 抽检辅助建议. Do not expose internal D1–D6, Knowledge Trace, or mapping IDs as primary UI language. Method sections are 相关已核验方法, 需补充商品信息后判断, and collapsed 其他已知方法. Never invent a substance or method to avoid an empty state.

### 7.1 Claim presentation — Current V2-5B2

The V2 Claim section is titled **页面宣传线索**, not 商品功效. It appears after Evidence and before legacy Risk/Recommendation interpretation so that observation, interpretation, and human decision remain visibly separate. A normalized summary uses wording such as:

```text
睡眠相关宣传
发现 3 处表达
```

Each ClaimSignal card uses its governed `displayLabel`, an informational blue treatment, and its number of supporting expressions. The native disclosure control is keyboard-operable. Expansion shows the ClaimMention `rawText` first, then the exact matched expression, a friendly source label such as 商品标题、商品详情文本 or 详情图片 OCR, and a control that locates the existing Evidence item. Missing Evidence resolution is displayed as 来源信息不可用; no locator is fabricated.

The Claim state machine is:

| Runtime state | Required primary wording | Visual role |
|---|---|---|
| `complete` with signals | `检测到 N 类页面宣传线索，共 M 处表达` | Informational blue; never a risk grade. |
| `complete` with `[]` | `未发现已治理词表中的页面宣传表达` | Neutral; explicitly not “无风险/合规”. |
| `not_generated` | `尚未生成页面宣传线索` | Neutral and different from complete-zero. |
| `error` | `页面宣传线索分析失败` | Error red; the rest of Product Detail remains available. |

Product Overview and Review Queue use only same-Snapshot `claimSignalSummaries`; the compact row shows at most two labels plus an overflow count. The primary filter is 页面宣传线索 and queries exact governed `claim_type`. It never maps back to legacy Effect. Current Sampling items use the Membership source Snapshot's V2 Claim projection.

Formal Claim UI is seller-managed only. UGC stays visible in the Evidence section but never appears in 页面宣传线索; `excluded_other_product` and SearchQuery/task keywords are also forbidden Claim sources. The section must not say “具有助眠功效”, “确认能够减肥”, “存在违法助眠宣传”, or use Claim count as a risk score. ClaimSignal, Official Health Function, RiskSignal, and Recommendation remain visibly separate sections/states.

Legacy `detectedEffects`, Evidence `effect`/`matchedKeywords`, and the `effect=` API remain compatibility data but are hidden from the current primary Claim presentation. Historical frozen Sampling exports are not rewritten: when their legacy `pageEffectClues` are displayed, the section is labeled 旧版冻结分析结果 and states that it is not V2 页面宣传线索.

## 8. Review and Sampling interaction

Review controls depend on the selected Snapshot's Review/eligibility state, not merely Product Membership.

If a pending Snapshot belongs to a Product already sampled from another Snapshot, show:

> 该商品已在当前抽检清单中，当前清单依据来自另一条页面快照；本次页面快照仍需单独复核。

The analyst may complete the Snapshot Review without silently replacing the Membership source. After a follow-up decision, state that the current list still uses the original Snapshot. Updating the source is a separate future design decision.

Atomic “加入抽检清单” and “暂不纳入” application operations follow the Product Requirements. Standalone “移出当前清单” changes Membership only.

## 8.1 Health-food identity — Current V2-3

Product Detail and Inspection Workspace include a calm, secondary `保健食品身份` section. Summary presentation is limited to `普通 / 未确认`, `保健食品待核验`, `保健食品 · 已核验`, or `身份信息待复核`; only backend state `verified_match` receives the verified label.

The detail section distinguishes all backend states: no indicator, indicator only, identifier candidate, ambiguous OCR, lookup unavailable, record not found, record found/relation unverified, verified match, mismatch and conflict. It never uses `假蓝帽`, `假保健食品` or `违法产品`.

`查看页面依据` opens an in-app source trace and reuses the existing OCR Lightbox/source viewer. `查看官方依据` opens a separate in-app official-record modal with identifier, official product name, registration/filing subject, dates, official health-function text and query time; opening the official source is secondary. Page evidence is never merged into Phase3 Evidence, and official evidence is never presented as page content.

## 8.2 Health-function consistency — Future V2-6B2 presentation contract

V2-6B1 provides typed backend data but no visible consistency UI. A future V2-6B2 Product Detail/Inspection Workspace section may be titled **保健功能一致性** and follow this order:

```text
官方核验功能
页面宣传主题
对应关系 / 未找到对应项
知识缺口
需要关注的具体页面表达
```

The section appears only as a comparison aid. It must distinguish `identity_not_verified`, `claim_not_generated`, `claim_analysis_error`, `framework_unresolved`, `official_function_unresolved`, `no_page_claims`, and `assessed`. It must show Registry raw function wording alongside normalized HealthFunction identity and retain links to the existing page and official source viewers.

Per-Claim presentation uses 页面宣传主题在官方功能记录中找到对应主题、未在当前核验的官方功能记录中找到对应项, or 当前无已核验的官方功能主题映射. It must never use 合法/违法、合规/不合规、通过/不通过, a risk grade, or probability. A recorded topic does not approve the concrete ClaimMention wording. Mention-level disease/treatment attention remains a separately governed future dimension.

## 9. Loading, empty and error behavior

- Product total zero: show 尚无已索引商品 and a path to 排查档案.
- API failure: show an error state and retry; never inject production mock products.
- Loading: preserve layout and avoid suggesting stale status.
- Candidate/Detail/OCR failure: show its real pipeline state rather than ordinary pending Review.
- Recommendation unavailable: keep Evidence, context, and Review functional when analysis is ready.

## 9.1 New Monitor inspection — Current V2-4A

The Monitor mode selector searches all 106 formal Reference objects and states `官方目录 106项 · 当前可排查 X项`. It supports 全部、可排查、待验证、暂停 filters. Each row shows the official standard name and one of 可排查、搜索策略待验证、暂缓.

Operational rows show only enabled, validated SearchQuery chips. Query-pending and paused rows remain searchable and selectable for explanation, but the primary action is disabled. Query-pending guidance is:

> 该对象已纳入官方目录，但搜索策略尚未完成真实搜索验证，暂不能发起检测任务。

Paused rows show the governed short reason. The Quick Task flow is unchanged and never writes its free text back into formal SearchQuery governance.

## 10. Responsive acceptance

The primary acceptance widths are 1440px and 1080px. Both must cover list-only and split detail modes, expanded/collapsed sidebar, long title, missing image, zero Evidence, unmapped Evidence, recommendation error, all four Claim states, historical Snapshot, loading, empty, and API-error states.
