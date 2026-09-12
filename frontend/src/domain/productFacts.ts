import type { DeclaredOrigin, ProductFact } from "../api/contracts";

export function productFactSourceLabel(sourceType: string) {
  if (sourceType === "dom_parameter") return "详情参数";
  if (sourceType === "ocr_detail_image") return "详情图 OCR";
  return "页面来源";
}

export function declaredOriginText(origin: DeclaredOrigin) {
  if (origin.state === "none" || origin.values.length === 0) return "—";
  if (origin.state === "conflict") return "存在多个声明";
  return origin.values[0];
}

export function productFactArtifactPath(source: ProductFact) {
  return source.sourcePath.replaceAll("\\", "/").split("#", 1)[0];
}

export function productFactSourcesForValue(
  origin: DeclaredOrigin,
  value: string,
) {
  return origin.sources.filter((source) => source.normalizedValue === value);
}
