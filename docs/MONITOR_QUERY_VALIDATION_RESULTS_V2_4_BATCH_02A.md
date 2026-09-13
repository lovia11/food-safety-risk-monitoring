# Monitor Query Validation Results — V2-4 Batch 02A

> Status: VALIDATION RECORD
>
> Applies to: V2-4 Wave 2A
>
> Owner: Project

## Batch record

- Batch: `v2-4b-batch-02a`
- Protocol: [Monitor SearchQuery Validation Protocol](MONITOR_QUERY_VALIDATION_PROTOCOL.md), V2-4
- Collection: 2026-09-13 22:03–22:04 (Asia/Shanghai)
- Human review: 2026-09-14 01:54:24 (Asia/Shanghai)
- Reviewer identity: `human_review`
- Execution boundary: visible-browser, bounded, serial, search-only collection; no Detail, OCR, Phase3, ProductFact, HealthFoodIdentity, business Review, Recommendation, or Sampling
- Immutable manifest SHA-256: `b5acfc84635c4f5103ac2a10e0524b90bd065f68d26830f8b07464c25094fe54`

## Reviewed results

| 监测对象 | 搜索词 | 可评估样本 | 食品相关 | 药材/范围外 | 非食品 | 信息不足跳过 | 相关率 | 决策 | 当前可排查 |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| 山药 | 山药 | 10 | 8 | 2 | 0 | 0 | 80% | 通过验证，可启用 | 是 |
| 赤小豆 | 赤小豆 | 10 | 10 | 0 | 0 | 0 | 100% | 通过验证，可启用 | 是 |
| 枸杞子 | 枸杞子 | 10 | 9 | 1 | 0 | 0 | 90% | 通过验证，可启用 | 是 |
| 莲子 | 莲子 | 10 | 9 | 1 | 0 | 1 | 90% | 通过验证，可启用 | 是 |

“相关率”仅表示本批次固定评价样本中的 **observed Search Result relevance**。它不是模型准确率、召回率、全淘宝覆盖率或监管命中率。

## Decisions

- 山药：前 10 个可评估结果中 8 个属于食品相关，2 个明确表现为中药材销售语境。食品召回占明显主导，未达到需要暂缓的系统性范围混杂程度。
- 赤小豆：前 10 个可评估结果均明确属于赤小豆、杂粮、粗粮、粥料或其它食品语境，标准名搜索结果稳定。卡片中的功效宣传不改变本轮食品范围判断。
- 枸杞子：前 10 个可评估结果中 9 个属于食用枸杞、枸杞干、泡水或其它食品语境，仅 1 个明确表现为中药材销售，未发现系统性范围问题。
- 莲子：前 10 个可评估结果中 9 个属于莲子干货、新鲜食用莲子或煲汤煮粥等食品语境，1 个明确属于中药材语境；另有 1 个用途混合结果按协议跳过，并以 Rank 11 补足评价样本。

## Observed product forms

这些词只记录为本批次人工观察，不构成新的 SearchQuery，也不具有独立的 `search_validated` 状态：

- 山药：山药片、山药粉
- 赤小豆：赤小豆薏米类食品
- 枸杞子：枸杞干、枸杞茶
- 莲子：莲子干、莲子羹

## Governance boundary

本记录只关闭 V2-4 Wave 2A：4 条标准名称 Query 晋级。Wave 1 的 5 条晋级与乌梅暂缓结论保持不变；百合、菊花仍需独立的 bounded Wave 2B collection、人工复核与治理 Gate。V2-4 整体保持 `IN PROGRESS`。
