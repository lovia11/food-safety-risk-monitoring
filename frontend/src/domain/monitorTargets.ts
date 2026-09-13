import type { MonitorTarget } from "../api/contracts.ts";

export type MonitorAvailabilityFilter = "all" | MonitorTarget["availability"];

export const MONITOR_AVAILABILITY_LABELS = {
  operational: "可排查",
  query_pending: "搜索策略待验证",
  paused: "暂缓",
} as const;

export const QUERY_PENDING_MESSAGE =
  "该对象已纳入官方目录，但搜索策略尚未完成真实搜索验证，暂不能发起检测任务。";

export function filterMonitorTargets(
  targets: MonitorTarget[],
  query: string,
  availability: MonitorAvailabilityFilter,
) {
  const normalized = query.trim().toLocaleLowerCase("zh-CN");
  return targets.filter((target) => {
    const matchesAvailability = availability === "all" || target.availability === availability;
    const matchesQuery =
      !normalized ||
      target.standard_name.toLocaleLowerCase("zh-CN").includes(normalized) ||
      target.validated_queries.some((item) =>
        item.query_text.toLocaleLowerCase("zh-CN").includes(normalized),
      );
    return matchesAvailability && matchesQuery;
  });
}

export function canCreateMonitorTask(target: MonitorTarget | undefined) {
  return target?.availability === "operational" && target.validated_queries.length > 0;
}

export function monitorAvailabilityLabel(target: MonitorTarget) {
  if (
    target.availability === "paused" &&
    target.queries.some((query) => query.validation_status === "rejected_low_relevance")
  ) {
    return "搜索策略待完善";
  }
  return MONITOR_AVAILABILITY_LABELS[target.availability];
}

export function monitorAvailabilityMessage(target: MonitorTarget) {
  if (target.availability === "query_pending") return QUERY_PENDING_MESSAGE;
  if (target.availability === "paused") {
    return target.availability_reason || "该对象的现有搜索策略已暂缓，当前不能发起检测任务。";
  }
  return "将仅使用已经完成真实搜索验证并启用的搜索词。";
}
