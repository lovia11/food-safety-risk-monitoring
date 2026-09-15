import {
  AlertCircle,
  ArrowUpRight,
  FileWarning,
  GitCompareArrows,
  Info,
  ShieldQuestion,
} from "lucide-react";
import { useMemo } from "react";

import type {
  ClaimConsistencyAssessment,
  ClaimConsistencyStatus,
  ClaimMentionDTO,
  ClaimSignalDTO,
  Evidence,
} from "../api/contracts";
import {
  claimConsistencyCountSummary,
  claimConsistencyPresentation,
  claimConsistencyRelationViewModels,
  hasClaimAttentionGovernanceGap,
  healthFunctionFrameworkLabel,
  officialFunctionViewModels,
} from "../domain/claimConsistency";
import { claimSignalAnchorId } from "../domain/claims";
import { StatusBadge } from "./StatusBadge";

type Props = {
  status: ClaimConsistencyStatus;
  assessment: ClaimConsistencyAssessment | null;
  claimSignals: ClaimSignalDTO[];
  claimMentions: ClaimMentionDTO[];
  evidence: Evidence[];
  identityAnchorId: string;
  officialSourceControlId: string;
  officialSourceAvailable: boolean;
};

function focusTarget(id: string) {
  const target = document.getElementById(id);
  if (!(target instanceof HTMLElement)) return;
  target.scrollIntoView({ behavior: "auto", block: "center" });
  target.focus({ preventScroll: true });
}

function openOfficialSource(controlId: string) {
  const control = document.getElementById(controlId);
  if (control instanceof HTMLButtonElement) control.click();
}

export function ClaimConsistencySection({
  status,
  assessment,
  claimSignals,
  claimMentions,
  evidence,
  identityAnchorId,
  officialSourceControlId,
  officialSourceAvailable,
}: Props) {
  const presentation = claimConsistencyPresentation(status, assessment);
  const officialFunctions = useMemo(
    () => assessment ? officialFunctionViewModels(assessment) : [],
    [assessment],
  );
  const relationRows = useMemo(
    () => assessment
      ? claimConsistencyRelationViewModels(
        assessment,
        claimSignals,
        claimMentions,
        evidence,
      )
      : [],
    [assessment, claimSignals, claimMentions, evidence],
  );

  return (
    <section
      className="detail-section claim-consistency-section"
      data-state={presentation.code}
    >
      <div className="claim-consistency-heading">
        <h3><GitCompareArrows size={17} />保健功能一致性</h3>
        <StatusBadge tone={presentation.tone}>{presentation.label}</StatusBadge>
      </div>
      <p className="section-description">
        比较已核验保健食品官方功能记录与当前页面宣传主题。结果用于人工研判，不构成合法性、合规性或功效真实性判断。
      </p>

      <div
        className="claim-consistency-state"
        data-tone={presentation.tone}
        role={presentation.code === "error" ? "alert" : "status"}
      >
        {presentation.code === "error"
          ? <AlertCircle size={18} />
          : presentation.tone === "warning"
            ? <FileWarning size={18} />
            : <Info size={18} />}
        <div>
          <strong>{presentation.label}</strong>
          <p>{presentation.description}</p>
        </div>
        {presentation.showIdentityAction && (
          <button
            type="button"
            onClick={() => focusTarget(identityAnchorId)}
            aria-label="查看当前快照的保健食品身份"
          >
            查看保健食品身份 <ArrowUpRight size={13} />
          </button>
        )}
      </div>

      {assessment && presentation.showOfficialFunctions && (
        <section className="claim-consistency-panel official-function-panel">
          <header>
            <div>
              <h4>官方核验功能</h4>
              <p>
                官方功能框架：{healthFunctionFrameworkLabel(assessment.registryFrameworkId)}
              </p>
            </div>
            {officialSourceAvailable ? (
              <button
                type="button"
                onClick={() => openOfficialSource(officialSourceControlId)}
                aria-label="打开当前快照的保健食品官方登记依据"
              >
                查看官方依据 <ArrowUpRight size={13} />
              </button>
            ) : (
              <span className="claim-consistency-trace-unavailable">
                官方来源信息暂不可用
              </span>
            )}
          </header>
          {officialFunctions.length > 0 ? (
            <div className="official-function-list">
              {officialFunctions.map((item, index) => (
                <article
                  key={`${item.rawText}-${index}`}
                  data-resolution={item.resolutionStatus}
                >
                  <div>
                    {item.resolutionStatus === "unresolved"
                      ? <ShieldQuestion size={16} />
                      : <Info size={16} />}
                    <span>{item.resolutionLabel}</span>
                  </div>
                  {item.currentName && <strong>{item.currentName}</strong>}
                  {item.showRawText && (
                    <p>
                      官方记录原文：<span>{item.rawText}</span>
                    </p>
                  )}
                </article>
              ))}
            </div>
          ) : (
            <p className="claim-consistency-empty">官方记录未提供保健功能原文。</p>
          )}
        </section>
      )}

      {assessment && presentation.showRelations && relationRows.length > 0 && (
        <section className="claim-consistency-panel claim-relation-panel">
          <header>
            <div>
              <h4>页面宣传主题与官方功能记录</h4>
              <p>{claimConsistencyCountSummary(assessment)}</p>
            </div>
          </header>
          <div className="claim-consistency-relations">
            {relationRows.map((row) => (
              <article
                key={row.assessment.claimSignalId}
                data-relation={row.assessment.relation}
              >
                <div className="claim-relation-heading">
                  <div>
                    <strong>{row.displayLabel}</strong>
                    <small>{row.mentionCount} 处页面表达</small>
                  </div>
                  <StatusBadge tone={row.presentation.tone}>
                    {row.presentation.label}
                  </StatusBadge>
                </div>
                <p>{row.presentation.description}</p>
                {row.assessment.healthFunctionOfficialName && (
                  <dl>
                    <div>
                      <dt>治理对应主题</dt>
                      <dd>{row.assessment.healthFunctionOfficialName}</dd>
                    </div>
                  </dl>
                )}
                {row.pageTraceAvailable ? (
                  <button
                    type="button"
                    onClick={() => focusTarget(
                      claimSignalAnchorId(row.assessment.claimSignalId),
                    )}
                    aria-label={`查看${row.displayLabel}的页面宣传依据`}
                  >
                    查看页面宣传依据 <ArrowUpRight size={13} />
                  </button>
                ) : (
                  <span className="claim-consistency-trace-unavailable">
                    页面依据暂不可用
                  </span>
                )}
              </article>
            ))}
          </div>
        </section>
      )}

      {assessment && hasClaimAttentionGovernanceGap(assessment) && (
        <aside className="claim-consistency-gap">
          <Info size={15} />
          <span>
            具体页面措辞的监管关注分类尚未建立完整治理数据，当前不自动判断；空结果不表示没有需关注表达。
          </span>
        </aside>
      )}
    </section>
  );
}
