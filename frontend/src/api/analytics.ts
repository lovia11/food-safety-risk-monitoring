import { apiRequest } from "./client";
import type {
  AnalyticsMetricDictionary,
  AnalyticsResponse,
} from "./contracts";

export type AnalyticsTimeFilters = {
  from?: string;
  to?: string;
  region?: string;
};

function analyticsPath(
  endpoint: string,
  filters: AnalyticsTimeFilters & {
    stage?: string;
    claimType?: string;
  } = {},
) {
  const params = new URLSearchParams();
  if (filters.from) params.set("from", filters.from);
  if (filters.to) params.set("to", filters.to);
  if (filters.region) params.set("region", filters.region);
  if (filters.stage) params.set("stage", filters.stage);
  if (filters.claimType) params.set("claim_type", filters.claimType);
  const query = params.toString();
  return `/api/analytics/${endpoint}${query ? `?${query}` : ""}`;
}

export function getAnalyticsMetricDictionary(signal?: AbortSignal) {
  return apiRequest<AnalyticsMetricDictionary>("/api/analytics/metrics", {
    signal,
  });
}

export function getAnalyticsSummary(
  filters: AnalyticsTimeFilters = {},
  signal?: AbortSignal,
) {
  return apiRequest<AnalyticsResponse>(analyticsPath("summary", filters), {
    signal,
  });
}

export function getAnalyticsPipeline(
  filters: AnalyticsTimeFilters & { stage?: string } = {},
  signal?: AbortSignal,
) {
  return apiRequest<AnalyticsResponse>(analyticsPath("pipeline", filters), {
    signal,
  });
}

export function getAnalyticsClaims(
  filters: AnalyticsTimeFilters & { claimType?: string } = {},
  signal?: AbortSignal,
) {
  return apiRequest<AnalyticsResponse>(analyticsPath("claims", filters), {
    signal,
  });
}

export function getAnalyticsGeography(
  filters: AnalyticsTimeFilters & { claimType?: string } = {},
  signal?: AbortSignal,
) {
  return apiRequest<AnalyticsResponse>(analyticsPath("geography", filters), {
    signal,
  });
}

export function getAnalyticsKnowledge(signal?: AbortSignal) {
  return apiRequest<AnalyticsResponse>("/api/analytics/knowledge", { signal });
}
