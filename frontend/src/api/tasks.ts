import { apiRequest } from "./client";
import type { MonitorTargetList, TaskDetail, TaskList } from "./contracts";

export type CandidateSelection = {
  productId: string;
  selectedForDetail: boolean;
  group: "exposure" | "visible_clue" | "exploration" | "fill" | null;
  reasons: string[];
  order: number | null;
  rank: number | null;
  titleClueTerms: string[];
};

type CandidateSearchPayload = {
  candidates?: Array<{
    product_id?: string;
    selected_for_detail?: boolean;
    selection_group?: CandidateSelection["group"];
    selection_reasons?: string[];
    selection_order?: number | null;
    rank?: number | null;
    title_clue_terms?: string[];
  }>;
};

export function getTasks(signal?: AbortSignal) {
  return apiRequest<TaskList>("/api/tasks", { signal });
}

export function getTask(taskId: string, signal?: AbortSignal) {
  return apiRequest<TaskDetail>(`/api/tasks/${encodeURIComponent(taskId)}`, { signal });
}

export async function getTaskCandidateSelections(
  taskId: string,
  signal?: AbortSignal,
): Promise<Record<string, CandidateSelection>> {
  const payload = await apiRequest<CandidateSearchPayload>(
    `/api/runs/${encodeURIComponent(taskId)}/files/search/search_candidates.json`,
    { signal },
  );
  const result: Record<string, CandidateSelection> = {};
  for (const item of payload.candidates || []) {
    const productId = String(item.product_id || "").trim();
    if (!productId || item.selected_for_detail !== true) continue;
    result[productId] = {
      productId,
      selectedForDetail: true,
      group: item.selection_group || null,
      reasons: (item.selection_reasons || []).map(String).filter(Boolean),
      order: typeof item.selection_order === "number" ? item.selection_order : null,
      rank: typeof item.rank === "number" ? item.rank : null,
      titleClueTerms: (item.title_clue_terms || []).map(String).filter(Boolean),
    };
  }
  return result;
}

export function getMonitorTargets(
  scope: "operational" | "reference" = "operational",
  signal?: AbortSignal,
) {
  return apiRequest<MonitorTargetList>(`/api/monitor-targets?scope=${scope}`, { signal });
}

export function createTask(payload: Record<string, unknown>) {
  return apiRequest<TaskDetail>("/api/tasks", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function resumeTask(taskId: string) {
  return apiRequest<TaskDetail>(`/api/tasks/${encodeURIComponent(taskId)}/resume`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function acknowledgeManualAction(taskId: string, generation: number) {
  return apiRequest<TaskDetail>(
    `/api/tasks/${encodeURIComponent(taskId)}/manual-action/acknowledge`,
    { method: "POST", body: JSON.stringify({ generation }) },
  );
}
