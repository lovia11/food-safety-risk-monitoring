# Monitor Query Validation Results — V2-4 Batch 02C

> Status: VALIDATION RECORD
>
> Applies to: V2-4 Lily refinement
>
> Owner: Project

## Batch record

- Batch: `v2-4b-batch-02c`
- Protocol: [Monitor SearchQuery Validation Protocol](MONITOR_QUERY_VALIDATION_PROTOCOL.md), V2-4
- Collection: 2026-09-14 02:30:08–02:30:16 (Asia/Shanghai)
- Human review: 2026-09-14 02:47:03 (Asia/Shanghai)
- Reviewer identity: `human_review`
- Query source: `manually_curated`
- Provenance: `derived_from_validation_batch=v2-4b-batch-02b`
- Execution boundary: visible-browser, bounded, serial, search-only collection; no Detail, OCR, Phase3, ProductFact, HealthFoodIdentity, business Review, Recommendation, or Sampling
- Immutable manifest SHA-256: `230b3f7ecf1be2160b21a1cb4a22ba5f457e0828ebb34139466bdc2f234b204f`

## Reviewed result

| 监测对象 | 搜索词 | 可评估样本 | 食品相关 | 药材/范围外 | 非食品 | 信息不足跳过 | 观察相关率 | 决策 | 当前可排查 |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| 百合 | 食用百合 | 10 | 9 | 1 | 0 | 1 | 90% | 通过验证，可启用 | 是 |

评价样本严格采用原始排序中前 10 个唯一、可评估结果，即 Rank 1、2、3、4、5、6、7、9、10、11。Rank 8 同时包含食用与种植材料语境，仅凭 Search Result Card 无法可靠判断，因此标记为 `ambiguous` 并按协议跳过；Rank 11 顺延成为第 10 个可评估结果。

“观察相关率”仅表示本批次固定评价样本中的 **observed Search Result relevance**。它不是模型准确率、召回率、搜索平台全量覆盖率、商品违法率、风险概率或监管命中率。

## Decision and lineage

标准名称 `百合` 在 Batch 02B 的观察相关率仅为 50%，因此进入 `rejected_low_relevance` 并保持禁用。该结果触发一次 governed query refinement，而不是修改官方 MonitorTarget identity 或创建官方别名。

独立候选 `食用百合` 保留 `manually_curated` 来源及 Batch 02B provenance，在 Batch 02C 中按完全相同的阈值重新采集和人工复核。其前 10 个可评估结果中 9 个属于食品相关、1 个属于中药材/药用销售语境，未发现系统性范围问题，满足固定 Promotion Gate，因此晋级为 enabled `search_validated` Query。

最终治理链为：

```text
MonitorTarget 百合
├─ 百合      standard_name      rejected_low_relevance  disabled  observed relevance 50%
└─ 食用百合  manually_curated   search_validated        enabled   observed relevance 90%

Target availability: operational
```

`食用百合` 是受治理的搜索策略，不是新的 MonitorTarget、官方名称或官方别名。后续以百合作为检测对象创建任务时，只解析并执行 `食用百合`；被拒绝的裸词 `百合` 不进入 Discovery。

## Governance boundary

本记录关闭 V2-4 的 Lily refinement Gate。Reference 仍保持完整 106 项，当前 operational coverage 为实际 governed config 推导的 16/106；这不表示 106 项均已具有可执行搜索策略。
