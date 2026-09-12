# UX Specification V2

> Status: CANONICAL
> Applies to: V2
> Last verified against commit: `bbe992e54f9fc583b312f919f32f91f43e53fb06`
> Owner: Project

This specification governs the V2 interaction model. Sections labeled Future V2-1 or later are requirements, not current implementation claims.

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
页面功效线索
人工复核
抽检清单
最近采集
历史记录
操作
```

最近采集 means the latest Snapshot time. 历史记录 means Product Snapshot count. Task/source traceability stays in Product Detail and Snapshot timeline rather than occupying a main cross-task table column.

### 3.2 Future V2-1 interaction

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

## 4. Product Detail

The workspace uses an independently scrollable product list and right detail panel. Snapshot selection controls every Snapshot-bound section: Evidence, recommendation, context, and Review must all correspond to the selected Snapshot.

### 4.1 Future V2-1 summary

The header pairs a product image with product identity and presents four ordered summaries:

```text
页面线索
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

## 6. Image preview — Future V2-1

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

## 8. Review and Sampling interaction

Review controls depend on the selected Snapshot's Review/eligibility state, not merely Product Membership.

If a pending Snapshot belongs to a Product already sampled from another Snapshot, show:

> 该商品已在当前抽检清单中，当前清单依据来自另一条页面快照；本次页面快照仍需单独复核。

The analyst may complete the Snapshot Review without silently replacing the Membership source. After a follow-up decision, state that the current list still uses the original Snapshot. Updating the source is a separate future design decision.

Atomic “加入抽检清单” and “暂不纳入” application operations follow the Product Requirements. Standalone “移出当前清单” changes Membership only.

## 9. Loading, empty and error behavior

- Product total zero: show 尚无已索引商品 and a path to 排查档案.
- API failure: show an error state and retry; never inject production mock products.
- Loading: preserve layout and avoid suggesting stale status.
- Candidate/Detail/OCR failure: show its real pipeline state rather than ordinary pending Review.
- Recommendation unavailable: keep Evidence, context, and Review functional when analysis is ready.

## 10. Responsive acceptance

The primary acceptance widths are 1440px and 1080px. Both must cover list-only and split detail modes, expanded/collapsed sidebar, long title, missing image, zero Evidence, unmapped Evidence, recommendation error, historical Snapshot, loading, empty, and API-error states.
