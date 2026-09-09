import { apiRequest } from "./client";
import type { MonitorTarget, TaskDetail, TaskList } from "./contracts";

export function getTasks(signal?: AbortSignal) {
  return apiRequest<TaskList>("/api/tasks", { signal });
}

export function getTask(taskId: string, signal?: AbortSignal) {
  return apiRequest<TaskDetail>(`/api/tasks/${encodeURIComponent(taskId)}`, { signal });
}

export async function getMonitorTargets(signal?: AbortSignal) {
  const result = await apiRequest<{ targets: MonitorTarget[]; count: number }>(
    "/api/monitor-targets",
    { signal },
  );
  return result.targets;
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
