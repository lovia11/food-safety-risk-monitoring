import type { DeclaredOrigin, ProductFact } from "../api/contracts";

const PROVINCE_TOKENS = [
  "北京", "天津", "上海", "重庆", "河北", "山西", "辽宁", "吉林", "黑龙江",
  "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南", "湖北", "湖南",
  "广东", "海南", "四川", "贵州", "云南", "陕西", "甘肃", "青海", "台湾",
  "内蒙古", "广西", "西藏", "宁夏", "新疆", "香港", "澳门",
] as const;

const TITLE_LOCALITY_STOP_WORDS = new Set([
  "特产", "正宗", "野生", "有机", "新鲜", "天然", "精选", "地道", "农家",
  "原产", "高山", "深山", "传统", "手工", "优质", "精品", "一级", "无硫",
]);

export function productFactSourceLabel(sourceType: string) {
  if (sourceType === "dom_parameter") return "详情参数";
  if (sourceType === "ocr_detail_image") return "详情图 OCR";
  if (sourceType === "title") return "商品标题";
  return "页面来源";
}

export function declaredOriginText(origin: DeclaredOrigin) {
  if (origin.state === "none" || origin.values.length === 0) return "—";
  if (origin.state === "conflict") return "存在多个声明";
  return origin.values[0];
}

function titleRegionClues(productName: string) {
  const title = productName.replace(/\s+/g, "");
  const values: string[] = [];
  for (const province of PROVINCE_TOKENS) {
    const index = title.indexOf(province);
    if (index < 0) continue;
    values.push(province);
    const rest = title.slice(index + province.length);
    const locality = rest.match(/^([\u3400-\u9fff]{2,3})/)?.[1] || "";
    if (locality && !TITLE_LOCALITY_STOP_WORDS.has(locality.slice(0, 2))) {
      values.push(locality);
    }
    break;
  }
  return values;
}

export function pageRegionClueFacts(facts: ProductFact[]) {
  return facts.filter((fact) => (fact.factType as string) === "page_region_clue");
}

export function pageRegionClueValues(facts: ProductFact[], productName = "") {
  const stored = pageRegionClueFacts(facts).map((fact) => fact.normalizedValue);
  return [...new Set([...stored, ...titleRegionClues(productName)].filter(Boolean))];
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
