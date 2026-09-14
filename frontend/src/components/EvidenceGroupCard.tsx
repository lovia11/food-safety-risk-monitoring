import { Eye, FileText } from "lucide-react";

import type { ProductAssets } from "../api/contracts";
import {
  evidenceGroupAssets,
  type EvidenceSourceGroup,
} from "../domain/evidence";
import { evidenceAnchorId } from "../domain/claims";
import { runFileUrl } from "../domain/product";
import { ProductThumbnail } from "./ProductThumbnail";

type EvidenceGroupCardProps = {
  group: EvidenceSourceGroup;
  assets: ProductAssets;
  runId: string;
  secondary?: boolean;
  onPreview: (path: string) => void;
  onReadText: (url: string, title: string) => void;
};

function EvidenceSnippetView({
  snippet,
}: {
  snippet: EvidenceSourceGroup["snippets"][number];
}) {
  return (
    <li className="evidence-snippet">
      {snippet.evidenceIds.map((evidenceId) => (
        <span
          className="evidence-anchor"
          id={evidenceAnchorId(evidenceId)}
          key={evidenceId}
          tabIndex={-1}
        />
      ))}
      <blockquote>“{snippet.text}”</blockquote>
    </li>
  );
}

export function EvidenceGroupCard({
  group,
  assets,
  runId,
  secondary = false,
  onPreview,
  onReadText,
}: EvidenceGroupCardProps) {
  const linked = evidenceGroupAssets(group, assets);
  const imageUrl = runFileUrl(runId, linked.imagePath);
  const textUrl = runFileUrl(runId, linked.textPath);
  const visibleSnippets = group.snippets.slice(0, 3);
  const remainingSnippets = group.snippets.slice(3);

  return (
    <article className="evidence-group-card" data-secondary={secondary}>
      <div className="evidence-group-visual">
        <ProductThumbnail
          src={imageUrl}
          alt={group.sourceLabel}
          variant="evidence"
          onPreview={linked.imagePath ? () => onPreview(linked.imagePath!) : undefined}
        />
      </div>
      <div className="evidence-group-content">
        <header>
          <div>
            <h4>{group.sourceLabel}</h4>
            <span>{group.recordCount} 条命中</span>
          </div>
          {secondary && <small>辅助线索</small>}
        </header>
        <ul className="evidence-snippets">
          {visibleSnippets.map((snippet) => (
            <EvidenceSnippetView
              key={snippet.evidenceIds.join("|")}
              snippet={snippet}
            />
          ))}
        </ul>
        {remainingSnippets.length > 0 && (
          <details className="evidence-more">
            <summary>展开其余 {remainingSnippets.length} 条</summary>
            <ul className="evidence-snippets">
              {remainingSnippets.map((snippet) => (
                <EvidenceSnippetView
                  key={snippet.evidenceIds.join("|")}
                  snippet={snippet}
                />
              ))}
            </ul>
          </details>
        )}
        {group.sourcePaths.length > 0 && (
          <p className="evidence-group-source">
            来源：{group.sourcePaths.join(" · ")}
          </p>
        )}
        {(linked.imagePath || textUrl) && (
          <div className="evidence-group-actions">
            {linked.imagePath && (
              <button type="button" onClick={() => onPreview(linked.imagePath!)}>
                <Eye size={14} /> 预览原图
              </button>
            )}
            {textUrl && (
              <button
                type="button"
                onClick={() => onReadText(textUrl, `${group.sourceLabel} · OCR 全文`)}
              >
                <FileText size={14} /> 查看 OCR 全文
              </button>
            )}
          </div>
        )}
      </div>
    </article>
  );
}
