export type StatusTone = "neutral" | "info" | "warning" | "success" | "danger";

export const reviewPresentation: Record<
  "pending" | "recommend_follow_up" | "no_further_action",
  { label: string; tone: StatusTone }
> = {
  pending: { label: "待复核", tone: "warning" },
  recommend_follow_up: { label: "建议跟进", tone: "info" },
  no_further_action: { label: "暂不纳入", tone: "neutral" },
};
