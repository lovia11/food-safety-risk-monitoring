import type {
  KnowledgeHealthFunction,
  KnowledgeInspectionMethod,
  KnowledgeMonitorTarget,
  KnowledgeRegulatoryDocument,
  KnowledgeRiskMapping,
  KnowledgeSubstance,
} from "../../api/contracts";
import type { KnowledgeTabId } from "../../domain/knowledge";

export type KnowledgeRecord =
  | KnowledgeMonitorTarget
  | KnowledgeHealthFunction
  | KnowledgeSubstance
  | KnowledgeRiskMapping
  | KnowledgeInspectionMethod
  | KnowledgeRegulatoryDocument;

export function knowledgeRecordId(
  tab: KnowledgeTabId,
  record: KnowledgeRecord,
) {
  switch (tab) {
    case "monitor-targets":
      return (record as KnowledgeMonitorTarget).targetId;
    case "health-functions":
      return (record as KnowledgeHealthFunction).functionId;
    case "substances":
      return (record as KnowledgeSubstance).substanceId;
    case "risk-mappings":
      return (record as KnowledgeRiskMapping).mappingId;
    case "inspection-methods":
      return (record as KnowledgeInspectionMethod).methodId;
    case "regulatory-documents":
      return (record as KnowledgeRegulatoryDocument).documentId;
  }
}

export function knowledgeRecordTitle(
  tab: KnowledgeTabId,
  record: KnowledgeRecord,
) {
  switch (tab) {
    case "monitor-targets":
      return (record as KnowledgeMonitorTarget).standardName;
    case "health-functions":
      return (record as KnowledgeHealthFunction).officialName;
    case "substances":
      return (record as KnowledgeSubstance).canonicalName;
    case "risk-mappings":
      return (record as KnowledgeRiskMapping).riskLabel;
    case "inspection-methods":
      return (record as KnowledgeInspectionMethod).methodName;
    case "regulatory-documents":
      return (record as KnowledgeRegulatoryDocument).title;
  }
}

export const KNOWLEDGE_EMPTY_TITLES: Record<KnowledgeTabId, string> = {
  "monitor-targets": "当前筛选下没有食药物质目录记录。",
  "health-functions": "当前筛选下没有保健功能记录。",
  substances: "当前筛选下没有已治理物质记录。",
  "risk-mappings": "当前筛选下没有风险映射记录。",
  "inspection-methods": "当前筛选下没有检验方法记录。",
  "regulatory-documents": "当前筛选下没有官方文件记录。",
};
