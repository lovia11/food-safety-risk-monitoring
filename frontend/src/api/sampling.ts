import { apiRequest } from "./client";
import type {
  HistoricalSamplingList,
  HistoricalSamplingListMetadata,
  HistoricalSamplingListPage,
  SamplingList,
  SamplingMembership,
} from "./contracts";

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
      body: JSON.stringify({
        product_id: productId,
        source_snapshot_id: snapshotId,
        added_from: addedFrom,
      }),
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

export async function exportSamplingList() {
  const result = await apiRequest<{ list: HistoricalSamplingListMetadata }>(
    "/api/sampling-list/export",
    { method: "POST", body: JSON.stringify({ confirmed: true }) },
  );
  return result.list;
}

export function getSamplingHistories(signal?: AbortSignal) {
  return apiRequest<HistoricalSamplingListPage>("/api/sampling-lists", {
    signal,
  });
}

export function getSamplingHistory(listId: string, signal?: AbortSignal) {
  return apiRequest<HistoricalSamplingList>(
    `/api/sampling-lists/${encodeURIComponent(listId)}`,
    { signal },
  );
}
