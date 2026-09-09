import type { ProductQuery } from "../api/contracts";

export const DEFAULT_PRODUCT_QUERY: ProductQuery = {
  query: "",
  targetId: "",
  taskId: "",
  reviewStatus: "",
  effect: "",
  samplingStatus: "",
  collectedFrom: "",
  collectedTo: "",
  page: 1,
  pageSize: 20,
};

export function formatDateTime(value: string | null) {
  if (!value) return "暂无记录";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

export function safeHttpUrl(value: string | null | undefined) {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
}

export function runFileUrl(runId: string, relativePath: string | null) {
  if (!relativePath) return null;
  const encodedPath = relativePath
    .replaceAll("\\", "/")
    .split("/")
    .filter(Boolean)
    .map(encodeURIComponent)
    .join("/");
  return `/api/runs/${encodeURIComponent(runId)}/files/${encodedPath}`;
}
