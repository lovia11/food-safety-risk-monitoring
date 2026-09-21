import type { InspectionView, SubstanceFollowUp } from "../api/contracts";

export const KNOWLEDGE_GAP_MESSAGE =
  "现有信息不足以给出具体检测成分或方法，需人工判断。";

export function followUpStatusLabel(status: string) {
  if (status === "suggest_testing") return "建议关注";
  if (status === "needs_context_review") return "需补商品信息";
  if (status === "regulatory_context_review") return "需核对商品信息";
  if (status === "auxiliary_evidence_only") return "仅辅助线索";
  if (status === "knowledge_integrity_gap") return "知识待补充";
  if (status === "no_applicable_verified_method") return "筛查参考";
  return "需人工判断";
}

export function substanceFollowUpMessage(substance: SubstanceFollowUp) {
  if (substance.follow_up_status === "suggest_testing") {
    return `可重点关注“${substance.canonical_name}”。`;
  }
  if (substance.follow_up_status === "needs_context_review") {
    return "补充商品类别、剂型或配料信息后，再判断是否适用。";
  }
  if (substance.follow_up_status === "regulatory_context_review") {
    return "先核对商品身份、注册备案及配料信息，再判断是否需要检测。";
  }
  if (substance.follow_up_status === "auxiliary_evidence_only") {
    return "当前线索仅来自用户内容，建议先核对商家页面。";
  }
  if (substance.follow_up_status === "knowledge_integrity_gap") {
    return "当前知识关系不完整，暂不生成具体建议。";
  }
  if (substance.follow_up_status === "no_applicable_verified_method") {
    return `可将“${substance.canonical_name}”作为筛查关注成分；当前尚未找到满足现行状态和适用性条件的检测方法。`;
  }
  return "当前需人工判断。";
}

export function screeningAttentionLabels(inspection: InspectionView) {
  const labels = inspection.unmappedEvidence
    .map((item) => item.claimDisplayLabel)
    .filter((value): value is string =>
      typeof value === "string" && value.trim().length > 0
    );
  return [...new Set(labels)];
}

export function historicalReferenceMessage(
  finding: InspectionView["riskFindings"][number],
) {
  if (finding.temporal_basis === "historical_reference_only") {
    return "参考依据包含历史专项抽检/风险监测资料，不代表当前统一抽检要求。";
  }
  if (finding.temporal_basis === "current_and_historical") {
    return "当前资料与历史专项抽检/风险监测资料共同提供参考；历史资料不代表当前统一抽检要求。";
  }
  return "";
}

export function needsProductContext(inspection: InspectionView) {
  return inspection.riskFindings.some((finding) =>
    finding.substance_follow_ups.some(
      (substance) =>
        substance.methods_needing_context.length > 0
        || substance.follow_up_status === "regulatory_context_review",
    ),
  );
}
