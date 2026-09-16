import type { AnalyticsMetric } from "../api/contracts";

export const ANALYTICS_SECTION_TITLES = {
  pipeline: "运营流程",
  claims: "页面宣传线索",
  geography: "地区分布",
  knowledge: "知识覆盖",
} as const;

export const ANALYTICS_GEOGRAPHY_TITLES = {
  collected_product_search_region_distribution: "已采集商品搜索地区分布",
  claim_product_search_region_distribution: "页面宣传线索商品搜索地区分布",
  declared_origin_distribution: "商品标称产地分布",
} as const;

export function analyticsRateLabel(value: number | null) {
  return value === null ? "分母为零，暂不可计算" : `${(value * 100).toFixed(1)}%`;
}

export function analyticsMetricValueLabel(metric: AnalyticsMetric) {
  if (metric.metricType === "ratio" || metric.metricType === "coverage") {
    return analyticsRateLabel(metric.rate ?? null);
  }
  return metric.value === null ? "尚不可用" : String(metric.value);
}
