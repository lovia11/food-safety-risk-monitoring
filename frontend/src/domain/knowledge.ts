import type {
  KnowledgeSourceTrace,
  MethodKnowledgeDepth,
} from "../api/contracts";
import type { StatusTone } from "./presentation";

export const KNOWLEDGE_TAB_IDS = [
  "monitor-targets",
  "health-functions",
  "substances",
  "risk-mappings",
  "inspection-methods",
  "regulatory-documents",
] as const;

export type KnowledgeTabId = (typeof KNOWLEDGE_TAB_IDS)[number];

export type KnowledgeRouteState = {
  tab: KnowledgeTabId;
  query: string;
  offset: number;
  availability: string;
  framework: string;
  status: string;
  targetType: string;
  knowledgeDepth: string;
  documentType: string;
};

export const DEFAULT_KNOWLEDGE_ROUTE: KnowledgeRouteState = {
  tab: "monitor-targets",
  query: "",
  offset: 0,
  availability: "",
  framework: "",
  status: "",
  targetType: "",
  knowledgeDepth: "",
  documentType: "",
};

export const KNOWLEDGE_TAB_LABELS: Record<KnowledgeTabId, string> = {
  "monitor-targets": "食药物质目录",
  "health-functions": "保健功能",
  substances: "风险物质",
  "risk-mappings": "风险映射",
  "inspection-methods": "检验方法",
  "regulatory-documents": "官方文件",
};

export const METHOD_KNOWLEDGE_DEPTH_LABELS: Record<MethodKnowledgeDepth, string> = {
  reference_only: "仅供参考",
  analyte_verified: "分析物已核验",
  applicability_verified: "适用范围已核验",
  recommendation_ready: "可用于抽检建议",
};

export const KNOWLEDGE_GAP_LABELS: Record<string, string> = {
  validated_search_query_not_available: "尚无已验证搜索策略",
  operational_search_paused: "当前搜索策略已暂缓",
  framework_catalog_detail_not_governed: "该框架的细分目录尚未治理",
  regulatory_context_not_recorded: "监管语境尚未记录",
  substance_group_membership_unresolved: "物质组成员尚未解析",
  substance_group_membership_partial: "物质组成员仅部分解析",
  analyte_depth_not_verified: "分析物尚未完成深度核验",
  applicability_not_verified: "适用范围尚未完成深度核验",
  applicability_not_recorded: "适用范围尚未记录",
  regulatory_document_not_linked: "尚未关联官方文件",
  effective_date_not_recorded: "生效日期尚未记录",
};

export const KNOWLEDGE_LIFECYCLE_LABELS: Record<string, string> = {
  current: "现行",
  historical: "历史",
  superseded: "已被替代",
  revoked: "废止",
  verification_pending: "待核验",
  verified_reference: "已核验参考",
};

export const KNOWLEDGE_AVAILABILITY_LABELS: Record<string, string> = {
  operational: "当前可排查",
  query_pending: "搜索策略待验证",
  paused: "已暂停",
};

export function knowledgeLifecyclePresentation(status: string): {
  label: string;
  tone: StatusTone;
} {
  return {
    label: KNOWLEDGE_LIFECYCLE_LABELS[status] || status || "尚未记录",
    tone:
      status === "verification_pending"
        ? "warning"
        : status === "current" || status === "verified_reference"
          ? "info"
          : "neutral",
  };
}

export function knowledgeAvailabilityPresentation(status: string): {
  label: string;
  tone: StatusTone;
} {
  return {
    label: KNOWLEDGE_AVAILABILITY_LABELS[status] || status,
    tone:
      status === "operational"
        ? "info"
        : status === "query_pending"
          ? "warning"
          : "neutral",
  };
}

export function knowledgeDepthTone(depth: MethodKnowledgeDepth): StatusTone {
  if (depth === "recommendation_ready") return "success";
  if (depth === "reference_only") return "neutral";
  return "info";
}

export function knowledgeGapTone(gap: string): "neutral" | "warning" {
  return gap.includes("unresolved") || gap.includes("partial")
    ? "warning"
    : "neutral";
}

export type KnowledgeSourceViewModel = {
  authority: string;
  version: string;
  status: string;
  reference: string | null;
  date: string | null;
};

export function mapKnowledgeSource(
  source: KnowledgeSourceTrace,
): KnowledgeSourceViewModel {
  return {
    authority: source.sourceName || source.datasetId,
    version: source.datasetVersion,
    status: source.datasetStatus,
    reference: source.sourceReference,
    date: source.sourceDate,
  };
}

export function knowledgeGapLabel(gap: string) {
  return KNOWLEDGE_GAP_LABELS[gap] || "存在尚未补齐的知识信息";
}

export function parseKnowledgeRoute(search: string): KnowledgeRouteState {
  const params = new URLSearchParams(search.replace(/^\?/, ""));
  const requestedTab = params.get("tab") || "";
  const parsedOffset = Number(params.get("offset") || "0");
  return {
    tab: KNOWLEDGE_TAB_IDS.includes(requestedTab as KnowledgeTabId)
      ? (requestedTab as KnowledgeTabId)
      : DEFAULT_KNOWLEDGE_ROUTE.tab,
    query: params.get("query") || "",
    offset:
      Number.isInteger(parsedOffset) && parsedOffset >= 0 ? parsedOffset : 0,
    availability: params.get("availability") || "",
    framework: params.get("framework") || "",
    status: params.get("status") || "",
    targetType: params.get("target_type") || "",
    knowledgeDepth: params.get("knowledge_depth") || "",
    documentType: params.get("document_type") || "",
  };
}

export function knowledgeRouteHash(state: KnowledgeRouteState): string {
  const params = new URLSearchParams();
  if (state.tab !== DEFAULT_KNOWLEDGE_ROUTE.tab) params.set("tab", state.tab);
  if (state.query) params.set("query", state.query);
  if (state.offset) params.set("offset", String(state.offset));
  if (state.availability) params.set("availability", state.availability);
  if (state.framework) params.set("framework", state.framework);
  if (state.status) params.set("status", state.status);
  if (state.targetType) params.set("target_type", state.targetType);
  if (state.knowledgeDepth) {
    params.set("knowledge_depth", state.knowledgeDepth);
  }
  if (state.documentType) params.set("document_type", state.documentType);
  const query = params.toString();
  return query ? `#/knowledge?${query}` : "#/knowledge";
}

export function safeKnowledgeSourceUrl(value: string | null | undefined) {
  if (!value) return null;
  try {
    const parsed = new URL(value);
    return parsed.protocol === "http:" || parsed.protocol === "https:"
      ? parsed.toString()
      : null;
  } catch {
    return null;
  }
}
