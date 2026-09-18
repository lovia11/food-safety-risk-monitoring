import type {
  ClaimAnalysisStatus,
  ClaimSignalDTO,
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
  claimAnalysisStatus: ClaimAnalysisStatus;
  claimSignals: ClaimSignalDTO[];
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

function hasPageClues(input: AnalysisStateInput) {
  if (input.claimAnalysisStatus === "complete") {
    return input.claimSignals.length > 0;
  }
  // Historical snapshots may predate V2 Claim artifacts.
  return input.evidence.length > 0;
}

export function analysisStatePresentation(
  input: AnalysisStateInput,
): AnalysisStatePresentation {
  if (!input.readiness.analysisReady) {
    return {
      code: "NOT_ANALYZED",
      label: "尚未完成分析",
      summary: "等待分析",
      message: "该页面尚未完成线索分析。",
      tone: "neutral",
    };
  }
  if (input.inspection.recommendationStatus === "error") {
    return {
      code: "RECOMMENDATION_ERROR",
      label: "抽检建议生成失败",
      summary: "建议暂不可用",
      message: "抽检建议生成失败，可继续查看页面线索并人工复核。",
      tone: "warning",
    };
  }
  if (!hasPageClues(input)) {
    return {
      code: "ANALYZED_ZERO_EVIDENCE",
      label: "未发现重点宣传线索",
      summary: "未发现重点线索",
      message: "本次分析未识别到当前关注的页面宣传线索。",
      tone: "success",
    };
  }
  if (input.inspection.riskFindings.length > 0) {
    if (!hasKnownMethod(input.inspection)) {
      return {
        code: "RISK_MAPPED_NO_METHOD",
        label: "已识别抽检关注方向",
        summary: "暂无适用检测方法",
        message: "已识别抽检关注方向，但暂未找到适用的检测方法。",
        tone: "warning",
      };
    }
    return {
      code: "RECOMMENDATION_AVAILABLE",
      label: "抽检辅助建议可用",
      summary: "已有具体建议",
      message: "已形成抽检辅助建议。",
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
      label: "已发现宣传线索",
      summary: "暂无对应抽检建议",
      message: `已识别${subject}，但当前暂无对应的抽检建议。`,
      tone: "info",
    };
  }
  return {
    code: "RECOMMENDATION_UNAVAILABLE",
    label: "抽检建议暂不可用",
    summary: "建议暂不可用",
    message: "分析已完成，但抽检建议暂不可用。",
    tone: "neutral",
  };
}
