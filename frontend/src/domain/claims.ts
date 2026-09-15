import type {
  ClaimAnalysisStatus,
  ClaimMentionDTO,
  ClaimSignalDTO,
  ClaimSignalSummaryDTO,
  Evidence,
} from "../api/contracts";
import type { StatusTone } from "./presentation";

export type ClaimSignalViewModel = {
  claimSignalId: string;
  claimType: string;
  displayLabel: string;
  mentionCount: number;
  mentions: ClaimMentionDTO[];
  status: "normalized";
};

export type ClaimPresentation = {
  code: "with_claims" | "zero" | "not_generated" | "error";
  label: string;
  summary: string;
  description: string;
  tone: StatusTone;
  signalCount: number;
  mentionCount: number;
};

type ClaimSignalLike = ClaimSignalDTO | ClaimSignalSummaryDTO;

function signalMentionCount(signal: ClaimSignalLike) {
  return "mentionCount" in signal ? signal.mentionCount : signal.mentionIds.length;
}

export function claimPresentation(
  status: ClaimAnalysisStatus,
  signals: ClaimSignalLike[],
): ClaimPresentation {
  if (status === "error") {
    return {
      code: "error",
      label: "页面宣传线索分析失败",
      summary: "分析失败",
      description: "本次页面宣传线索分析未成功；页面证据和其它分析结果仍可查看。",
      tone: "danger",
      signalCount: 0,
      mentionCount: 0,
    };
  }
  if (status === "not_generated") {
    return {
      code: "not_generated",
      label: "尚未生成页面宣传线索",
      summary: "尚未生成",
      description: "该页面快照尚未运行 V2 Claim Analysis。",
      tone: "neutral",
      signalCount: 0,
      mentionCount: 0,
    };
  }
  if (signals.length === 0) {
    return {
      code: "zero",
      label: "未发现已治理词表中的页面宣传表达",
      summary: "已生成 · 零条线索",
      description: "分析已完成，但当前已治理词表未命中页面宣传表达；这不表示无风险、无问题或宣传合规。",
      tone: "neutral",
      signalCount: 0,
      mentionCount: 0,
    };
  }
  const mentionCount = signals.reduce(
    (total, signal) => total + signalMentionCount(signal),
    0,
  );
  return {
    code: "with_claims",
    label: "页面宣传线索已生成",
    summary: `检测到 ${signals.length} 类页面宣传线索，共 ${mentionCount} 处表达`,
    description: "以下内容记录页面出现的宣传表达，不验证功效，也不构成风险或合规结论。",
    tone: "info",
    signalCount: signals.length,
    mentionCount,
  };
}

export function claimSignalLabels(
  signals: ClaimSignalLike[],
  limit = 2,
) {
  const labels = signals.slice(0, limit).map((signal) => signal.displayLabel);
  const remaining = Math.max(0, signals.length - labels.length);
  return { labels, remaining };
}

export function claimSignalViewModels(
  signals: ClaimSignalDTO[],
  mentions: ClaimMentionDTO[],
): ClaimSignalViewModel[] {
  const mentionsById = new Map(
    mentions.map((mention) => [mention.claimMentionId, mention]),
  );
  return signals.map((signal) => {
    const linked = signal.mentionIds
      .map((mentionId) => mentionsById.get(mentionId))
      .filter((mention): mention is ClaimMentionDTO => Boolean(mention));
    return {
      claimSignalId: signal.claimSignalId,
      claimType: signal.claimType,
      displayLabel: signal.displayLabel,
      mentionCount: signal.mentionIds.length,
      mentions: linked,
      status: signal.status,
    };
  });
}

export function claimSourceLabel(sourceAssetType: string, evidence?: Evidence) {
  if (sourceAssetType === "title") return "商品标题";
  if (sourceAssetType === "ocr") return "详情图片 OCR";
  if (sourceAssetType === "dom_product" || sourceAssetType === "dom") {
    return "商品详情文本";
  }
  return evidence?.sourceLabel || "页面证据";
}

export function claimMentionEvidence(
  mention: ClaimMentionDTO,
  evidence: Evidence[],
) {
  return evidence.find((item) => item.evidenceId === mention.evidenceId) || null;
}

export function evidenceAnchorId(evidenceId: string) {
  return `evidence-${evidenceId.replace(/[^A-Za-z0-9_-]/g, "-")}`;
}

export function claimSignalAnchorId(claimSignalId: string) {
  return `claim-signal-${claimSignalId.replace(/[^A-Za-z0-9_-]/g, "-")}`;
}
