import type { StatusTone } from "./presentation";
import type { TaskBusinessStatus, TaskSummary } from "../api/contracts";

export const taskStatusPresentation: Record<
  TaskBusinessStatus,
  { label: string; tone: StatusTone }
> = {
  running: { label: "排查中", tone: "info" },
  waiting_for_manual_action: { label: "等待淘宝验证", tone: "warning" },
  awaiting_review: { label: "待人工复核", tone: "warning" },
  completed: { label: "已完成", tone: "success" },
  partial_error: { label: "部分异常", tone: "danger" },
  interrupted: { label: "已中断", tone: "neutral" },
};

export const flowSteps = ["搜索商品", "采集详情", "线索识别", "人工复核"];

export function shouldResumeTask(
  task: Pick<TaskSummary, "businessStatus" | "resumable">,
) {
  return task.businessStatus === "interrupted" && task.resumable;
}

export function taskFlowIndex(stage: string) {
  if (stage === "searching" || stage === "initializing" || stage === "waiting_for_manual_action" || stage === "manual_action_required") return 0;
  if (stage === "collecting_details") return 1;
  if (stage === "processing_ocr_analysis") return 2;
  return 3;
}

export function buildWebTaskRequest(input: {
  mode: "quick" | "monitor";
  name: string;
  keyword: string;
  targetId: string;
  analysisLimit: number;
}) {
  const common = { name: input.name };
  if (input.mode === "quick") {
    return {
      ...common,
      task_type: "quick",
      keyword: input.keyword,
      candidate_limit: input.analysisLimit,
      detail_limit: input.analysisLimit,
    };
  }
  return {
    ...common,
    task_type: "monitor",
    target_id: input.targetId,
    per_query_candidate_limit: input.analysisLimit,
    detail_limit: input.analysisLimit,
  };
}
