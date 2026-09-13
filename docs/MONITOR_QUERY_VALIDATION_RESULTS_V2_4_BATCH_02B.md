# Monitor Query Validation Results — V2-4 Batch 02B

> Status: VALIDATION RECORD
>
> Applies to: V2-4 Wave 2B
>
> Owner: Project

## Batch record

- Batch: `v2-4b-batch-02b`
- Protocol: [Monitor SearchQuery Validation Protocol](MONITOR_QUERY_VALIDATION_PROTOCOL.md), V2-4
- Collection: 2026-09-14 02:10:22–02:10:41 (Asia/Shanghai)
- Human review: 2026-09-14 02:21:21 (Asia/Shanghai)
- Reviewer identity: `human_review`
- Execution boundary: visible-browser, bounded, serial, search-only collection; no Detail, OCR, Phase3, ProductFact, HealthFoodIdentity, business Review, Recommendation, or Sampling
- Immutable manifest SHA-256: `c130bb453df91397bab926a722ef759d56fee038def2bdeb12dcfc145cb3b16e`

## Reviewed results

| 监测对象 | 搜索词 | 可评估样本 | 食品相关 | 药材/范围外 | 非食品 | 信息不足跳过 | 观察相关率 | 决策 | 当前可排查 |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| 百合 | 百合 | 10 | 5 | 5 | 0 | 0 | 50% | 不采用 | 否 |
| 菊花 | 菊花 | 10 | 10 | 0 | 0 | 0 | 100% | 通过验证，可启用 | 是 |

“观察相关率”仅表示本批次固定评价样本中的 **observed Search Result relevance**。它不是模型准确率、召回率、全淘宝覆盖率、商品违法率或监管命中率。

## Decisions

- 百合：标准名称“百合”前 10 个可评估搜索结果中，5 个属于食品相关，5 个明确表现为中药材/药用销售语境，观察相关率为 50%，未达到既定搜索策略晋级门槛，因此不采用该标准名作为可执行 SearchQuery。被拒绝的是该搜索策略，不是官方 MonitorTarget；百合继续保留在完整 Reference 中。
- 菊花：前 10 个可评估搜索结果均明确属于食用菊花、菊花茶或其它菊花冲泡食品语境，观察相关率为 100%，标准名搜索结果稳定。卡片中的清火、去火、下火、养生或去热宣传不改变本轮食品范围判断。

## Governance boundary

本记录关闭标准名称 Query 的 V2-4 Wave 2B 治理：菊花晋级为可执行搜索策略；百合标准名 Query 进入 `rejected_low_relevance` 且保持禁用。百合 MonitorTarget 仍属于 106 项官方 Reference，后续可在独立 Gate 中验证更精确、具有明确来源的食品搜索策略。V2-4 整体保持 `IN PROGRESS`。
