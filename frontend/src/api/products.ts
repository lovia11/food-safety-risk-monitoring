import { apiRequest } from "./client";
import type {
  InspectionContextOptions,
  ProductFilterOptions,
  ProductPage,
  ProductQuery,
  Review,
  ReviewDecisionResult,
  ReviewStatus,
  SamplingList,
  SamplingMembership,
  SnapshotSummary,
  SnapshotWorkspace,
} from "./contracts";

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

export function getProducts(query: ProductQuery, signal?: AbortSignal) {
  return apiRequest<ProductPage>(`/api/products?${productQueryString(query)}`, {
    signal,
  });
}

export function getProductFilterOptions(signal?: AbortSignal) {
  return apiRequest<ProductFilterOptions>("/api/product-filter-options", { signal });
}

export async function getProductSnapshots(
  productId: string,
  signal?: AbortSignal,
) {
  const result = await apiRequest<{
    productId: string;
    snapshots: SnapshotSummary[];
    count: number;
  }>(`/api/products/${encodeURIComponent(productId)}/snapshots`, { signal });
  return result.snapshots;
}

export function getSnapshotWorkspace(snapshotId: string, signal?: AbortSignal) {
  return apiRequest<SnapshotWorkspace>(
    `/api/snapshots/${encodeURIComponent(snapshotId)}/workspace`,
    { signal },
  );
}

export async function updateReview(
  snapshotId: string,
  status: ReviewStatus,
  note: string,
) {
  const result = await apiRequest<{ snapshotId: string; review: Review }>(
    `/api/snapshots/${encodeURIComponent(snapshotId)}/review`,
    {
      method: "PUT",
      body: JSON.stringify({ status, note }),
    },
  );
  return result.review;
}

export function saveReviewDecision(
  snapshotId: string,
  decision: "recommend_follow_up" | "no_further_action",
  addedFrom: "product_overview" | "inspection_workspace",
  note: string,
) {
  return apiRequest<ReviewDecisionResult>(
    `/api/snapshots/${encodeURIComponent(snapshotId)}/review-decision`,
    {
      method: "POST",
      body: JSON.stringify({ decision, added_from: addedFrom, note }),
    },
  );
}

export function getSamplingList(signal?: AbortSignal) {
  return apiRequest<SamplingList>("/api/sampling-list", { signal });
}

export async function addSamplingItem(
  productId: string,
  snapshotId: string,
  addedFrom: "product_overview" | "inspection_workspace",
) {
  const result = await apiRequest<{ membership: SamplingMembership }>(
    "/api/sampling-list/items",
    {
      method: "POST",
      body: JSON.stringify({ product_id: productId, source_snapshot_id: snapshotId, added_from: addedFrom }),
    },
  );
  return result.membership;
}

export async function removeSamplingItem(productId: string) {
  const result = await apiRequest<{ membership: SamplingMembership }>(
    `/api/sampling-list/items/${encodeURIComponent(productId)}`,
    { method: "DELETE" },
  );
  return result.membership;
}

export function getInspectionContextOptions(signal?: AbortSignal) {
  return apiRequest<InspectionContextOptions>("/api/inspection-context-options", {
    signal,
  });
}

export function updateInspectionContext(
  runId: string,
  productId: string,
  context: {
    product_category: string | null;
    product_form: string | null;
    confirmed_ingredient_contexts: string[];
  },
) {
  return apiRequest(
    `/api/runs/${encodeURIComponent(runId)}/products/${encodeURIComponent(productId)}/inspection-context`,
    { method: "PUT", body: JSON.stringify(context) },
  );
}
