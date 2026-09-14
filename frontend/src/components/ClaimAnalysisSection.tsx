import { AlertCircle, Info, LocateFixed, MessageSquareQuote } from "lucide-react";
import { useMemo } from "react";

import type {
  ClaimAnalysisStatus,
  ClaimMentionDTO,
  ClaimSignalDTO,
  Evidence,
} from "../api/contracts";
import {
  claimMentionEvidence,
  claimPresentation,
  claimSignalViewModels,
  claimSourceLabel,
  evidenceAnchorId,
} from "../domain/claims";
import { StatusBadge } from "./StatusBadge";

type ClaimAnalysisSectionProps = {
  status: ClaimAnalysisStatus;
  signals: ClaimSignalDTO[];
  mentions: ClaimMentionDTO[];
  evidence: Evidence[];
};

export function ClaimAnalysisSection({
  status,
  signals,
  mentions,
  evidence,
}: ClaimAnalysisSectionProps) {
  const presentation = claimPresentation(status, signals);
  const viewModels = useMemo(
    () => claimSignalViewModels(signals, mentions),
    [signals, mentions],
  );

  const locateEvidence = (evidenceId: string) => {
    const anchor = document.getElementById(evidenceAnchorId(evidenceId));
    if (!anchor) return;
    const collapsedGroup = anchor.closest("details");
    if (collapsedGroup instanceof HTMLDetailsElement) collapsedGroup.open = true;
    anchor.scrollIntoView({ behavior: "auto", block: "center" });
    anchor.focus({ preventScroll: true });
  };

  return (
    <section className="detail-section claim-analysis-section">
      <div className="claim-section-heading">
        <h3><MessageSquareQuote size={17} />页面宣传线索</h3>
        <StatusBadge tone={presentation.tone}>{presentation.summary}</StatusBadge>
      </div>
      <p className="section-description">{presentation.description}</p>

      {presentation.code !== "with_claims" ? (
        <div
          className="claim-state-message"
          data-state={presentation.code}
          role={presentation.code === "error" ? "alert" : "status"}
        >
          {presentation.code === "error"
            ? <AlertCircle size={17} />
            : <Info size={17} />}
          <strong>{presentation.label}</strong>
        </div>
      ) : (
        <div className="claim-signal-list">
          {viewModels.map((signal) => (
            <details className="claim-signal-card" key={signal.claimType}>
              <summary>
                <span>
                  <strong>{signal.displayLabel}</strong>
                  <small>{signal.mentionCount} 处表达</small>
                </span>
                <StatusBadge tone="info">页面观察</StatusBadge>
              </summary>
              <div className="claim-mention-list">
                {signal.mentions.map((mention) => {
                  const sourceEvidence = claimMentionEvidence(mention, evidence);
                  const sourcePath = sourceEvidence
                    ? mention.sourceLocator.sourcePath || sourceEvidence.sourcePath
                    : "";
                  const lineNumber = sourceEvidence
                    ? mention.sourceLocator.lineNumber ?? sourceEvidence.lineNumber
                    : null;
                  return (
                    <article className="claim-mention" key={mention.claimMentionId}>
                      <blockquote>“{mention.rawText}”</blockquote>
                      <div className="claim-mention-meta">
                        <span>命中：{mention.matchedExpression}</span>
                        {sourceEvidence ? (
                          <>
                            <span>来源：{claimSourceLabel(mention.sourceAssetType, sourceEvidence)}</span>
                            <button
                              type="button"
                              onClick={() => locateEvidence(mention.evidenceId)}
                              aria-label={`定位“${mention.matchedExpression}”对应的页面证据`}
                            >
                              <LocateFixed size={13} />定位页面证据
                            </button>
                          </>
                        ) : (
                          <span className="claim-source-unavailable">来源信息不可用</span>
                        )}
                      </div>
                      {sourceEvidence && sourcePath && (
                        <code>
                          {sourcePath}{lineNumber ? ` · 第 ${lineNumber} 行` : ""}
                        </code>
                      )}
                    </article>
                  );
                })}
              </div>
            </details>
          ))}
        </div>
      )}
    </section>
  );
}
