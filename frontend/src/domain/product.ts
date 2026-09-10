import type { ProductQuery } from "../api/contracts";
import type { StatusTone } from "./presentation";

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

export function productAnalysisPresentation(status: string): {
  label: string;
  tone: StatusTone;
} {
  if (status === "success") return { label: "已完成详情和线索分析", tone: "success" };
  if (status === "failed_processing") return { label: "详情已采集，分析异常", tone: "danger" };
  if (status === "detail_collected" || status === "processing_ocr_analysis") {
    return { label: "详情已采集，等待完成分析", tone: "info" };
  }
  if (status === "collecting_detail") return { label: "正在采集详情", tone: "info" };
  if (status === "failed_collection") return { label: "详情采集异常", tone: "danger" };
  if (status === "pending_detail_collection") {
    return { label: "仅搜索发现，尚未分析", tone: "neutral" };
  }
  return { label: "处理状态待确认", tone: "neutral" };
}
