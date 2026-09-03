"use strict";

export const API_ROOT = "/api";

export const $ = (selector, root = document) => root.querySelector(selector);
export const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function safeExternalUrl(value) {
  try {
    const url = new URL(String(value || ""));
    return ["http:", "https:"].includes(url.protocol) ? url.href : "#";
  } catch (_) {
    return "#";
  }
}

function encodedPath(path) {
  return String(path || "").split("/").filter(Boolean).map(encodeURIComponent).join("/");
}

export function assetUrl(runId, path) {
  if (!runId || !path) return "";
  return `${API_ROOT}/runs/${encodeURIComponent(runId)}/files/${encodedPath(path)}`;
}

export function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date).replaceAll("/", "-");
}

export function showToast(message) {
  const toast = $("#toast");
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove("show"), 2200);
}

export function productThumb(product, runId) {
  const images = product.assets?.originalImages || [];
  const path = images[0]?.path || product.assets?.overview;
  return path ? assetUrl(runId, path) : "";
}

export function analysisState(product) {
  const review = product.risk?.reviewRequired;
  if (review === true) {
    return { label: "建议人工复核", tone: "orange", statusClass: "status-warning" };
  }
  if (review === false) {
    return { label: "未发现明显线索", tone: "blue", statusClass: "status-info" };
  }
  return { label: "待OCR分析", tone: "gray", statusClass: "status-neutral" };
}

export function reviewPresentation(status) {
  if (status === "recommend_follow_up") {
    return { label: "建议进一步关注", tone: "orange" };
  }
  if (status === "no_further_action") {
    return { label: "暂不进一步关注", tone: "green" };
  }
  return { label: "待复核", tone: "gray" };
}

export function monitorTargetPresentation(target) {
  const status = target?.dataset_status || target?.datasetStatus || target?.dataset?.dataset_status;
  if (status === "verified_reference") return { label: "正式", tone: "blue" };
  if (status === "development_seed") return { label: "开发", tone: "gray" };
  return { label: "未标注", tone: "gray" };
}

export function stopReasonPresentation(value) {
  const raw = String(value || "");
  const labels = {
    candidate_limit_reached: "达到候选数量上限",
    all_queries_completed: "所有搜索词执行完成",
    stagnant: "页面结果连续无新增",
    stagnant_no_new_products: "页面结果连续无新增",
  };
  return labels[raw] || raw || "—";
}

export function taskPresentation(snapshot) {
  const stage = snapshot.task?.stage;
  if (stage === "completed") return { label: "已完成", tone: "green" };
  if (stage === "failed" || stage === "completed_with_errors") {
    return { label: "失败", tone: "red" };
  }
  if (stage === "interrupted") return { label: "已中断", tone: "orange" };
  if (stage === "manual_action_required") {
    return { label: "需要人工操作", tone: "orange" };
  }
  if (["searching", "collecting_details", "processing_ocr_analysis"].includes(stage)) {
    return { label: "进行中", tone: "green" };
  }
  return { label: "待继续", tone: "orange" };
}
