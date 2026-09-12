import type {
  Evidence,
  InspectionView,
  PipelineReadiness,
  SnapshotSummary,
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
  detectedEffects: string[];
  inspection: InspectionView;
};

function quotedEffects(effects: string[]) {
  const unique = [...new Set(effects.filter(Boolean))];
  return unique.length ? unique.map((effect) => `“${effect}”`).join("、") : "相关";
}
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
      message: "已完成分析，暂未发现当前规则覆盖范围内的明确页面功效线索。",
      tone: "success",
    };
  }
  if (input.inspection.riskFindings.length > 0) {
    if (!hasKnownMethod(input.inspection)) {
      return {
        code: "RISK_MAPPED_NO_METHOD",
        label: "风险方向已形成",
        summary: "暂无已核验方法",
        message: "已形成风险方向，但暂无可用的已核验检测方法。",
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
    const effects = quotedEffects(input.detectedEffects);
    return {
      code: "EVIDENCE_UNMAPPED",
      label: "发现线索 · 知识未映射",
      summary: "已发现线索，暂无映射",
      message: `已发现${effects}相关页面表达，但当前已核验知识库尚未建立该线索到抽检风险方向的映射。`,
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

export function productCluePresentation(
  snapshot: Pick<SnapshotSummary, "readiness" | "detectedEffects">,
) {
  if (!snapshot.readiness.analysisReady) {
    return "尚未完成线索分析";
  }
  if (snapshot.detectedEffects.length === 0) {
    return "已分析，未发现当前规则线索";
  }
  return snapshot.detectedEffects.join("、");
}
