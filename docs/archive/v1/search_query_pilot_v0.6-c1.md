> **ARCHIVED / NON-NORMATIVE**
> Original baseline: V1 SearchQuery pilot
> Archived at: 2026-09-12 (V2-0B)
> Superseded by: `docs/CURRENT_SYSTEM_STATUS.md`, `docs/KNOWLEDGE_GOVERNANCE.md`, and `docs/IMPLEMENTATION_ROADMAP_V2.md`

# v0.6-C1 SearchQuery Pilot 验证记录

验证日期：2026-09-03  
方式：项目自身 `LiveSearchCollector`，真实淘宝 search-only，单浏览器会话内低频串行；每个 Query 最多保留 10 个候选，不进入详情、OCR 或风险分析。

原始结果：

- `output/20260903_query_validation_c1_base/query_validation_results.json`
- `output/20260903_query_validation_c1_forms/query_validation_results.json`

| MonitorTarget | Query | query_source | 候选数 | stop_reason | 前10标题相关性结论 | validation_status | 最终Target状态 |
| --- | --- | --- | ---: | --- | --- | --- | --- |
| 酸枣仁 | 酸枣仁 | standard_name | 10 | candidate_limit_reached | 10/10包含酸枣仁，形态包含原料、粉、膏、茶 | search_validated | enabled |
| 酸枣仁 | 酸枣仁茶 | observed_product_form | 10 | candidate_limit_reached | 基础结果中约5/10重复出现；复验10/10相关 | search_validated | enabled |
| 茯苓 | 茯苓 | standard_name | 10 | candidate_limit_reached | 10/10包含茯苓，兼有食用与中药材场景 | search_validated | enabled |
| 茯苓 | 茯苓粉 | observed_product_form | 10 | candidate_limit_reached | 基础结果中3/10重复出现；复验9/10直接相关，1条为含茯苓四神汤粉 | search_validated | enabled |
| 龙眼肉（桂圆） | 龙眼肉 | standard_name | 10 | candidate_limit_reached | 10/10为龙眼肉/桂圆肉干等相关商品 | search_validated | enabled |
| 龙眼肉（桂圆） | 桂圆 | official_alias | 10 | candidate_limit_reached | 10/10为桂圆、龙眼干或桂圆组合食品 | search_validated | enabled |
| 当归 | 当归 | standard_name | 10 | candidate_limit_reached | 10/10含当归，但几乎全部为中药材/饮片场景 | search_validated | disabled |
| 铁皮石斛 | 铁皮石斛 | standard_name | 10 | candidate_limit_reached | 10/10相关，主要为枫斗、干条、粉和礼盒 | search_validated | enabled |
| 化橘红 | 化橘红 | standard_name | 10 | candidate_limit_reached | 10/10相关，主要为化州橘红胎果或切片 | search_validated | enabled |

当归保持停用：其 Query 能稳定召回当归商品，但当前样本几乎均为中药材/饮片，并且 2019 年公告规定当归等 6 种仅作为香辛料和调味品使用。在产品场景分类能力建立前，不把“能召回”误认为“适合当前食品监测”。

本轮共执行 9 次真实搜索，无登录、人工验证、失败或重试。所有 Query 的 title/shop/region 选择器健康状态均为 `healthy`。
