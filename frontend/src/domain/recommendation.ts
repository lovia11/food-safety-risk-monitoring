import type { InspectionView } from "../api/contracts";

export const KNOWLEDGE_GAP_MESSAGE =
  "暂无已核验的检测建议。当前页面发现相关宣传线索，但现有知识库暂无足够核验依据关联至具体检测成分。页面证据仍可供人工复核。";

export function needsProductContext(inspection: InspectionView) {
  return inspection.riskFindings.some((finding) =>
    finding.substance_follow_ups.some(
      (substance) => substance.methods_needing_context.length > 0,
    ),
  );
}
