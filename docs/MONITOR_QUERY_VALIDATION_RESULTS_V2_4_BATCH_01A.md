# Monitor Query Validation Results — V2-4 Batch 01A

> Status: VALIDATION RECORD
>
> Applies to: V2-4 Wave 1
>
> Owner: Project

## Batch record

- Batch: `v2-4b-batch-01a`
- Protocol: [Monitor SearchQuery Validation Protocol](MONITOR_QUERY_VALIDATION_PROTOCOL.md), V2-4
- Collection: 2026-09-13 21:09–21:10 (Asia/Shanghai)
- Human review: 2026-09-13 21:36:04 (Asia/Shanghai)
- Reviewer identity: `human_review`
- Execution boundary: visible-browser, bounded, serial, search-only collection; no Detail, OCR, Phase3, ProductFact, HealthFoodIdentity, business Review, or Sampling
- Immutable manifest SHA-256: `6998093f127fa09d342c396c61018b512e6d0a4606b216230e4383d3d89afa57`

## Reviewed results

| 监测对象 | 搜索词 | 可评估样本 | 食品相关 | 药材/范围外 | 非食品 | 信息不足跳过 | 相关率 | 决策 | Operational |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| 山楂 | 山楂 | 10 | 9 | 1 | 0 | 0 | 90% | 通过验证，可启用 | 是 |
| 乌梅 | 乌梅 | 10 | 7 | 3 | 0 | 1 | 70% | 暂缓启用 | 否 |
| 沙棘 | 沙棘 | 10 | 10 | 0 | 0 | 1 | 100% | 通过验证，可启用 | 是 |
| 罗汉果 | 罗汉果 | 10 | 9 | 1 | 0 | 0 | 90% | 通过验证，可启用 | 是 |
| 黑芝麻 | 黑芝麻 | 10 | 10 | 0 | 0 | 1 | 100% | 通过验证，可启用 | 是 |
| 蜂蜜 | 蜂蜜 | 10 | 10 | 0 | 0 | 0 | 100% | 通过验证，可启用 | 是 |

“相关率”仅表示本批次固定评价样本中的 **observed Search Result relevance**。它不是模型准确率、召回率或全平台覆盖率。

## Decisions

- 山楂：前 10 个可评估结果中 9 个属于食品相关，仅 1 个明显为中药材销售语境，未发现系统性范围问题。
- 乌梅：前 10 个可评估结果中 7 个属于食品相关、3 个明确表现为中药材/药用销售语境。虽然相关率达到 70% 的最低数值门槛，但存在稳定的范围混杂，因此暂缓启用；该结果不是 `reject`。
- 沙棘：前 10 个可评估结果均属于食品或明确食用产品语境；1 个信息不足结果已按协议跳过并顺延。
- 罗汉果：前 10 个可评估结果中 9 个属于食品相关，1 个主要表现为中药材销售语境，整体搜索范围稳定。
- 黑芝麻：前 10 个可评估结果均属于食品相关；首个结果因标题未明确包含黑芝麻而标记信息不足并按协议顺延。
- 蜂蜜：前 10 个可评估结果均明确属于蜂蜜或蜂蜜食品商品；深排位存在轻微漂移，不影响当前评价样本。

## Observed product forms

这些词只记录为本批次人工观察，不构成新的 SearchQuery，也不具有 `search_validated` 状态：

- 山楂：山楂干、山楂片、山楂零食
- 乌梅：乌梅干、酸梅汤原料
- 沙棘：沙棘原浆、沙棘汁
- 罗汉果：罗汉果干果、罗汉果茶
- 黑芝麻：黑芝麻、黑芝麻糊、黑芝麻丸、黑芝麻粉
- 蜂蜜：蜂蜜、百花蜜、洋槐蜜

## Governance boundary

本记录只关闭 V2-4 Wave 1：5 条标准名称 Query 晋级，1 条标准名称 Query 暂缓。山药、百合、赤小豆、枸杞子、莲子、菊花仍需下一次独立人工 Gate；V2-4 整体保持 `IN PROGRESS`。
