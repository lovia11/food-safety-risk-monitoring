import { apiRequest } from "./client";
import type {
  KnowledgeHealthFunction,
  KnowledgeInspectionMethod,
  KnowledgeMonitorTarget,
  KnowledgePage,
  KnowledgeRegulatoryDocument,
  KnowledgeRiskMapping,
  KnowledgeSubstance,
  KnowledgeSummary,
} from "./contracts";

export type KnowledgeListQuery = {
  query?: string;
  limit?: number;
  offset?: number;
};

function withQuery(
  path: string,
  query: KnowledgeListQuery & Record<string, string | number | undefined>,
) {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== "") params.set(key, String(value));
  });
  const suffix = params.toString();
  return suffix ? `${path}?${suffix}` : path;
}

export function getKnowledgeSummary(signal?: AbortSignal) {
  return apiRequest<KnowledgeSummary>("/api/knowledge/summary", { signal });
}

export function getKnowledgeMonitorTargets(
  query: KnowledgeListQuery & { availability?: string } = {},
  signal?: AbortSignal,
) {
  return apiRequest<KnowledgePage<KnowledgeMonitorTarget>>(
    withQuery("/api/knowledge/monitor-targets", query),
    { signal },
  );
}

export function getKnowledgeHealthFunctions(
  query: KnowledgeListQuery & { framework?: string; status?: string } = {},
  signal?: AbortSignal,
) {
  return apiRequest<KnowledgePage<KnowledgeHealthFunction>>(
    withQuery("/api/knowledge/health-functions", query),
    { signal },
  );
}

export function getKnowledgeSubstances(
  query: KnowledgeListQuery = {},
  signal?: AbortSignal,
) {
  return apiRequest<KnowledgePage<KnowledgeSubstance>>(
    withQuery("/api/knowledge/substances", query),
    { signal },
  );
}

export function getKnowledgeRiskMappings(
  query: KnowledgeListQuery & { target_type?: string; status?: string } = {},
  signal?: AbortSignal,
) {
  return apiRequest<KnowledgePage<KnowledgeRiskMapping>>(
    withQuery("/api/knowledge/risk-mappings", query),
    { signal },
  );
}

export function getKnowledgeInspectionMethods(
  query: KnowledgeListQuery & { status?: string; knowledge_depth?: string } = {},
  signal?: AbortSignal,
) {
  return apiRequest<KnowledgePage<KnowledgeInspectionMethod>>(
    withQuery("/api/knowledge/inspection-methods", query),
    { signal },
  );
}

export function getKnowledgeRegulatoryDocuments(
  query: KnowledgeListQuery & { status?: string; document_type?: string } = {},
  signal?: AbortSignal,
) {
  return apiRequest<KnowledgePage<KnowledgeRegulatoryDocument>>(
    withQuery("/api/knowledge/regulatory-documents", query),
    { signal },
  );
}
