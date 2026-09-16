import type {
  KnowledgeSourceTrace,
  MethodKnowledgeDepth,
} from "../api/contracts";

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
