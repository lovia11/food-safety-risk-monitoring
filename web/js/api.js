"use strict";

import { API_ROOT, assetUrl } from "./utils.js";

async function requestJson(url, options = {}) {
  const response = await fetch(url, { cache: "no-store", ...options });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(body.error?.message || `请求失败：${response.status}`);
    error.code = body.error?.code;
    error.activeTaskId = body.error?.activeTaskId;
    throw error;
  }
  return body;
}

function jsonOptions(method, payload) {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: payload === undefined ? undefined : JSON.stringify(payload),
  };
}

export function buildProductQuery(queryState) {
  const filters = queryState.filters || {};
  const parameters = new URLSearchParams();
  if (filters.targetId) parameters.set("target_id", filters.targetId);
  if (filters.query) parameters.set("query", filters.query);
  if (filters.reviewStatus) parameters.set("review_status", filters.reviewStatus);
  if (filters.effect) parameters.set("effect", filters.effect);
  if (filters.taskId) parameters.set("task_id", filters.taskId);
  parameters.set("page", String(queryState.page || 1));
  parameters.set("page_size", String(queryState.pageSize || 20));
  return parameters.toString();
}

export function getProducts(queryState) {
  return requestJson(`${API_ROOT}/products?${buildProductQuery(queryState)}`);
}

export function getMonitorTargets() {
  return requestJson(`${API_ROOT}/monitor-targets`);
}

export function getProductSnapshots(productId) {
  return requestJson(`${API_ROOT}/products/${encodeURIComponent(productId)}/snapshots`);
}

export function getSnapshot(snapshotId) {
  return requestJson(`${API_ROOT}/snapshots/${encodeURIComponent(snapshotId)}`);
}

export function getInspectionContextOptions() {
  return requestJson(`${API_ROOT}/inspection-context-options`);
}

export function updateInspectionContext(runId, productId, payload) {
  return requestJson(
    `${API_ROOT}/runs/${encodeURIComponent(runId)}/products/${encodeURIComponent(productId)}/inspection-context`,
    jsonOptions("PUT", payload),
  );
}

export function updateReview(snapshotId, payload) {
  return requestJson(
    `${API_ROOT}/snapshots/${encodeURIComponent(snapshotId)}/review`,
    jsonOptions("PUT", payload),
  );
}

export function getTasks() {
  return requestJson(`${API_ROOT}/tasks`);
}

export function createTask(payload) {
  return requestJson(`${API_ROOT}/tasks`, jsonOptions("POST", payload));
}

export function resumeTaskRequest(taskId) {
  return requestJson(
    `${API_ROOT}/tasks/${encodeURIComponent(taskId)}/resume`,
    jsonOptions("POST"),
  );
}

export function getRun(taskId) {
  return requestJson(`${API_ROOT}/tasks/${encodeURIComponent(taskId)}`);
}

export async function getRunFileText(runId, path) {
  const response = await fetch(assetUrl(runId, path), { cache: "no-store" });
  if (!response.ok) throw new Error(`文件读取失败：${response.status}`);
  return response.text();
}
