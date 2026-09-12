import type { Evidence, ProductAssets } from "../api/contracts";

export type EvidenceSnippet = {
  text: string;
  effects: string[];
  matchedKeywords: string[];
  evidenceIds: string[];
  lineNumbers: number[];
};

export type EvidenceSourceGroup = {
  key: string;
  sourceType: string;
  sourceLabel: string;
  contentOrigin: string;
  sourcePaths: string[];
  assetKey: string | null;
  recordCount: number;
  snippets: EvidenceSnippet[];
};

export type EvidencePartitions = {
  seller: EvidenceSourceGroup[];
  ugc: EvidenceSourceGroup[];
  excluded: EvidenceSourceGroup[];
};

function normalizedPath(value: string | null | undefined) {
  return (value || "").replaceAll("\\", "/").replace(/^\/+/, "").toLowerCase();
}
function sourceContextPath(value: string) {
  return normalizedPath(value).split("#", 1)[0];
}

export function evidenceAssetKey(value: string | null | undefined) {
  const normalized = normalizedPath(value);
  const filename = normalized.split("/").at(-1) || "";
  const stem = filename.replace(/\.(txt|json|png|jpe?g|webp|bmp)$/i, "");
  return /^original_\d+$/i.test(stem) ? stem : null;
}

function groupTitle(evidence: Evidence, assetKey: string | null) {
  if (evidence.sourceType === "ocr") {
    return assetKey ? `详情图 OCR · ${assetKey}` : "详情图 OCR";
  }
  if (evidence.sourceType === "title") return "商品标题";
  if (evidence.sourceType === "dom_product") return "当前商品页面文字";
  return evidence.sourceLabel || (
    evidence.contentOrigin === "user_generated" ? "用户生成内容" : "页面线索"
  );
}

function unique<T>(values: T[]) {
  return [...new Set(values)];
}

function normalizedSnippet(value: string) {
  return value.replace(/\s+/g, " ").trim().toLocaleLowerCase("zh-CN");
}

export function groupEvidence(evidence: Evidence[]): EvidenceSourceGroup[] {
  const groups = new Map<string, EvidenceSourceGroup>();
  for (const item of evidence) {
    const assetKey = item.sourceType === "ocr"
      ? evidenceAssetKey(item.sourcePath)
      : null;
    const sourceKey = assetKey || sourceContextPath(item.sourcePath) || item.sourceLabel;
    const key = [item.contentOrigin, item.sourceType, sourceKey].join("|");
    let group = groups.get(key);
    if (!group) {
      group = {
        key,
        sourceType: item.sourceType,
        sourceLabel: groupTitle(item, assetKey),
        contentOrigin: item.contentOrigin,
        sourcePaths: [],
        assetKey,
        recordCount: 0,
        snippets: [],
      };
      groups.set(key, group);
    }
    group.recordCount += 1;
    group.sourcePaths = unique([...group.sourcePaths, item.sourcePath].filter(Boolean));
    const snippetKey = normalizedSnippet(item.text || "该条证据未保存可展示原文。");
    const existing = group.snippets.find(
      (snippet) => normalizedSnippet(snippet.text) === snippetKey,
    );
    if (existing) {
      existing.effects = unique([...existing.effects, item.effect].filter(Boolean));
      existing.matchedKeywords = unique([
        ...existing.matchedKeywords,
        ...item.matchedKeywords,
      ].filter(Boolean));
      existing.evidenceIds = unique([...existing.evidenceIds, item.evidenceId]);
      existing.lineNumbers = unique([
        ...existing.lineNumbers,
        ...(item.lineNumber ? [item.lineNumber] : []),
      ]).sort((left, right) => left - right);
    } else {
      group.snippets.push({
        text: item.text || "该条证据未保存可展示原文。",
        effects: [item.effect].filter(Boolean),
        matchedKeywords: unique(item.matchedKeywords.filter(Boolean)),
        evidenceIds: [item.evidenceId],
        lineNumbers: item.lineNumber ? [item.lineNumber] : [],
      });
    }
  }
  return [...groups.values()];
}

export function partitionEvidenceGroups(groups: EvidenceSourceGroup[]): EvidencePartitions {
  return {
    seller: groups.filter((group) => group.contentOrigin === "seller_managed"),
    ugc: groups.filter(
      (group) => group.contentOrigin !== "seller_managed"
        && group.contentOrigin !== "excluded_other_product",
    ),
    excluded: groups.filter(
      (group) => group.contentOrigin === "excluded_other_product",
    ),
  };
}

function sameAsset(left: string | null | undefined, right: string | null | undefined) {
  const leftKey = evidenceAssetKey(left);
  const rightKey = evidenceAssetKey(right);
  if (leftKey && rightKey) return leftKey === rightKey;
  const leftPath = normalizedPath(left);
  const rightPath = normalizedPath(right);
  return Boolean(
    leftPath && rightPath
    && (leftPath === rightPath || leftPath.endsWith(`/${rightPath}`)
      || rightPath.endsWith(`/${leftPath}`)),
  );
}

export function evidenceGroupAssets(
  group: EvidenceSourceGroup,
  assets: ProductAssets,
) {
  const ocrAsset = group.sourceType === "ocr"
    ? assets.ocrItems.find((item) =>
        group.sourcePaths.some(
          (path) => sameAsset(item.textPath, path) || sameAsset(item.jsonPath, path),
        ),
      )
    : undefined;
  return {
    imagePath: ocrAsset?.imagePath || (group.sourceType === "ocr" ? null : assets.overview),
    textPath: ocrAsset?.textPath || null,
  };
}
