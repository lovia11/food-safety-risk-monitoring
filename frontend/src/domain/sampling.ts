import type { SamplingItem, SamplingMethodSummary } from "../api/contracts";

export function samplingMethodLabel(method: SamplingMethodSummary) {
  return [method.methodNo, method.methodName].filter(Boolean).join(" · ");
}

function visibleMethods(methods: SamplingMethodSummary[] | undefined) {
  return (methods ?? []).filter(
    (method) => method.methodNo || method.methodName,
  );
}

export function samplingMethodGroups(item: SamplingItem) {
  return {
    suggested: visibleMethods(item.summary.suggestedMethods),
    needsContext: visibleMethods(item.summary.methodsNeedingContext),
    otherKnown: visibleMethods(item.summary.otherKnownMethods),
    legacyUnclassified: visibleMethods(
      item.summary.legacyUnclassifiedMethods ?? item.summary.methods,
    ),
  };
}

export function suggestedSamplingMethods(item: SamplingItem) {
  return samplingMethodGroups(item).suggested;
}

export function evidenceQualificationLabel(value: string) {
  if (value === "seller_managed_primary") return "商家管理内容主要线索";
  if (value === "user_generated_auxiliary_only") return "用户生成内容辅助线索";
  if (value === "not_recorded") return "未记录";
  return value || "未记录";
}

export function frozenAssetLabel(kind: string) {
  const labels: Record<string, string> = {
    evidence_source: "查看证据原文",
    evidence_image: "查看证据原图",
    ocr_text: "查看 OCR 全文",
    ocr_json: "查看 OCR 结构",
    page_overview: "查看页面截图",
  };
  return labels[kind] || "查看冻结证据";
}
