import type { HealthFoodIdentityState } from "../api/contracts";

export const healthFoodIdentityPresentation: Record<
  HealthFoodIdentityState,
  { label: string; message: string; tone: "neutral" | "success" | "warning" | "danger" | "info"; summary: string }
> = {
  no_indicator: {
    label: "—",
    message: "当前页面未发现可用的保健食品身份线索。",
    tone: "neutral",
    summary: "普通 / 未确认",
  },
  candidate_indicator_only: {
    label: "检测到身份线索",
    message: "检测到保健食品标识文字，尚未识别到可查询的注册或备案号。",
    tone: "info",
    summary: "保健食品待核验",
  },
  candidate_identifier: {
    label: "注册信息待核验",
    message: "已识别注册或备案号候选，尚未完成官方核验。",
    tone: "info",
    summary: "保健食品待核验",
  },
  identifier_ambiguous: {
    label: "编号字符待确认",
    message: "OCR 编号存在易混淆字符，系统未自动纠正或查询。",
    tone: "warning",
    summary: "身份信息待复核",
  },
  registry_lookup_unavailable: {
    label: "官方查询暂不可用",
    message: "页面候选已保存；官方查询当前不可用，不影响其他分析与人工复核。",
    tone: "warning",
    summary: "保健食品待核验",
  },
  registry_record_not_found: {
    label: "官方记录未找到",
    message: "当前官方查询源未找到与页面候选编号对应的记录。",
    tone: "warning",
    summary: "身份信息待复核",
  },
  registry_record_found_identity_unverified: {
    label: "官方记录存在 · 对应关系待确认",
    message: "注册信息已查询到官方记录，但当前页面商品与该记录的对应关系仍需人工确认。",
    tone: "warning",
    summary: "身份信息待复核",
  },
  verified_match: {
    label: "官方记录已核验",
    message: "页面明确产品名称与该编号的官方登记产品名称一致。",
    tone: "success",
    summary: "保健食品 · 已核验",
  },
  identity_mismatch: {
    label: "页面与官方记录存在差异",
    message: "页面标识信息与官方登记记录存在差异，建议人工复核。",
    tone: "danger",
    summary: "身份信息待复核",
  },
  conflict: {
    label: "身份候选存在冲突",
    message: "当前页面存在多个编号或多个明确产品名称，系统未自动选择。",
    tone: "danger",
    summary: "身份信息待复核",
  },
};

export function isVerifiedHealthFoodIdentity(state: HealthFoodIdentityState) {
  return state === "verified_match";
}

export function healthFoodSourceLabel(sourceType: string | null | undefined) {
  if (sourceType === "ocr_detail_image") return "详情图 OCR";
  if (sourceType === "dom_parameter") return "详情参数";
  if (sourceType?.startsWith("dom")) return "当前商品页面";
  return "页面依据";
}

export function healthFoodArtifactPath(sourcePath: string | null | undefined) {
  if (!sourcePath) return null;
  return sourcePath.replaceAll("\\", "/").split("#", 1)[0] || null;
}
