import type {
  Evidence,
  InspectionView,
  PipelineReadiness,
} from "../api/contracts";
import type { StatusTone } from "./presentation";

export type AnalysisStateCode =
  | "NOT_ANALYZED"
  | "ANALYZED_ZERO_EVIDENCE"
  | "EVIDENCE_UNMAPPED"
  | "RISK_MAPPED_NO_METHOD"
  | "RECOMMENDATION_AVAILABLE"
  | "RECOMMENDATION_UNAVAILABLE"
  | "RECOMMENDATION_ERROR";

export type AnalysisStatePresentation = {
  code: AnalysisStateCode;
  label: string;
  summary: string;
  message: string;
  tone: StatusTone;
};

type AnalysisStateInput = {
  readiness: PipelineReadiness;
  evidence: Evidence[];
  inspection: InspectionView;
};

function hasKnownMethod(inspection: InspectionView) {
  return inspection.riskFindings.some((finding) =>
    finding.substance_follow_ups.some(
      (substance) =>
        substance.suggested_methods.length > 0
        || substance.methods_needing_context.length > 0
        || substance.other_known_methods.length > 0,
    ),
  );
}

function unmappedClaimLabels(inspection: InspectionView) {
  const labels = inspection.unmappedEvidence
    .map((item) => item.claimDisplayLabel)
    .filter((value): value is string => typeof value === "string" && value.length > 0);
  return [...new Set(labels)];
}

export function analysisStatePresentation(
  input: AnalysisStateInput,
): AnalysisStatePresentation {
  if (!input.readiness.analysisReady) {
    return {
      code: "NOT_ANALYZED",
      label: "尚未完成线索分析",
      summary: "尚未分析",
      message: "该页面快照尚未成功完成 Phase3 线索分析。",
      tone: "neutral",
    };
  }
  if (input.inspection.recommendationStatus === "error") {
    return {
      code: "RECOMMENDATION_ERROR",
      label: "抽检辅助建议暂不可用",
      summary: "建议生成异常",
      message: "抽检辅助建议生成异常，但页面证据和人工复核仍然可用。",
      tone: "warning",
    };
  }
  if (input.evidence.length === 0) {
    return {
      code: "ANALYZED_ZERO_EVIDENCE",
      label: "已分析 · 未发现线索",
      summary: "当前规则未发现线索",
      message: "已完成分析，但当前规则未形成结构化页面 Evidence。",
      tone: "success",
    };
  }
  if (input.inspection.riskFindings.length > 0) {
    if (!hasKnownMethod(input.inspection)) {
      return {
        code: "RISK_MAPPED_NO_METHOD",
        label: "监管关注方向已形成",
        summary: "暂无已核验方法",
        message: "已形成监管关注方向，但当前暂无可用的已核验检测方法。",
        tone: "warning",
      };
    }
    return {
      code: "RECOMMENDATION_AVAILABLE",
      label: "抽检辅助建议可用",
      summary: "已有知识与方法支持",
      message: "已基于当前已核验知识形成抽检辅助建议。",
      tone: "success",
    };
  }
  if (input.inspection.available) {
    const claimLabels = unmappedClaimLabels(input.inspection);
    const subject = claimLabels.length > 0
      ? `“${claimLabels.join("、")}”`
      : "页面宣传线索";
    return {
      code: "EVIDENCE_UNMAPPED",
      label: "发现宣传线索 · 检测知识待补充",
      summary: "已发现宣传线索，暂无检测关注方向",
      message: `已发现并保留${subject}，但当前知识库尚未建立该宣传与检测关注方向之间的可靠关系（旧版界面称为“映射”）。建议结合原始页面证据人工复核。`,
      tone: "info",
    };
  }
  return {
    code: "RECOMMENDATION_UNAVAILABLE",
    label: "抽检辅助建议未生成",
    summary: "建议文件不可用",
    message: "该次快照已完成分析并保留页面证据，但暂无可读取的抽检辅助建议；人工复核仍然可用。",
    tone: "neutral",
  };
}
