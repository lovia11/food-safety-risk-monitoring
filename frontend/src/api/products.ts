import { apiRequest } from "./client";
import type {
  InspectionContextOptions,
  ProductFilterOptions,
  ProductPage,
  ProductQuery,
  Review,
  ReviewDecisionResult,
  ReviewStatus,
  SnapshotSummary,
  SnapshotWorkspace,
} from "./contracts";
import { productQueryString } from "../domain/productQuery";

export { productQueryString } from "../domain/productQuery";

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
