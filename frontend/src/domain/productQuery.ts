import type { ProductQuery } from "../api/contracts";

export function productQueryString(query: ProductQuery) {
  const params = new URLSearchParams();
  const values = {
    query: query.query,
    target_id: query.targetId,
    task_id: query.taskId,
    review_status: query.reviewStatus,
    effect: query.effect,
    sampling_status: query.samplingStatus,
    collected_from: query.collectedFrom,
    collected_to: query.collectedTo,
  };
  Object.entries(values).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  params.set("page", String(query.page));
  params.set("page_size", String(query.pageSize));
  return params.toString();
}
