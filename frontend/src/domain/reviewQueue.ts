import type { SnapshotSummary } from "../api/contracts";

export type QueueFilter =
  | "all"
  | "pending"
  | "current"
  | "reviewed_follow_up"
  | "no_further_action";

export const queueFilters: Array<{ value: QueueFilter; label: string }> = [
  { value: "all", label: "全部" },
  { value: "pending", label: "待复核" },
  { value: "current", label: "已纳入当前清单" },
  { value: "reviewed_follow_up", label: "已复核/当前未在清单" },
  { value: "no_further_action", label: "暂不纳入" },
];

export function queueMatches(
  item: Pick<SnapshotSummary, "sampling" | "readiness">,
  filter: QueueFilter,
) {
  return item.readiness.reviewEligible
    && (filter === "all" || item.sampling.decisionStatus === filter);
}
