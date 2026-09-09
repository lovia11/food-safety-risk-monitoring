import { FileImage, FileText, Image } from "lucide-react";

import type { Evidence, ProductAssets } from "../api/contracts";
import { runFileUrl } from "../domain/product";

type EvidenceCardProps = {
  evidence: Evidence;
  assets: ProductAssets;
  runId: string;
};

function normalized(value: string | null) {
  return (value || "").replaceAll("\\", "/").toLowerCase();
}

function matchesPath(candidate: string | null, sourcePath: string) {
  const left = normalized(candidate);
  const right = normalized(sourcePath).replace(/^\//, "");
  return Boolean(left && right && (left === right || left.endsWith(`/${right}`)));
}

export function EvidenceCard({ evidence, assets, runId }: EvidenceCardProps) {
  const ocrAsset = assets.ocrItems.find(
    (item) =>
      matchesPath(item.textPath, evidence.sourcePath) ||
      matchesPath(item.jsonPath, evidence.sourcePath),
  );
  const ocrTextUrl = runFileUrl(runId, ocrAsset?.textPath || null);
  const ocrImageUrl = runFileUrl(runId, ocrAsset?.imagePath || null);
  const screenshotUrl = runFileUrl(runId, assets.overview);

  return (
    <article className="evidence-card">
      <div className="evidence-meta">
        <span>{evidence.sourceLabel || "页面线索"}</span>
        {evidence.effect && <span className="evidence-effect">{evidence.effect}</span>}
      </div>
      <blockquote>{evidence.text || "该条证据未保存可展示原文。"}</blockquote>
      {(evidence.sourcePath || evidence.lineNumber) && (
        <p className="evidence-source">
          来源：{evidence.sourcePath || "未记录"}
          {evidence.lineNumber ? ` · 第 ${evidence.lineNumber} 行` : ""}
        </p>
      )}
      {(ocrImageUrl || ocrTextUrl || screenshotUrl) && (
        <div className="evidence-actions">
          {ocrImageUrl && (
            <a href={ocrImageUrl} target="_blank" rel="noreferrer">
              <FileImage size={14} /> 查看原图
            </a>
          )}
          {ocrTextUrl && (
            <a href={ocrTextUrl} target="_blank" rel="noreferrer">
              <FileText size={14} /> 查看OCR全文
            </a>
          )}
          {screenshotUrl && (
            <a href={screenshotUrl} target="_blank" rel="noreferrer">
              <Image size={14} /> 查看页面截图
            </a>
          )}
        </div>
      )}
    </article>
  );
}
