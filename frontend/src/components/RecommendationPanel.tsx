import { AlertCircle, BookOpenCheck, ExternalLink, FlaskConical } from "lucide-react";

import type {
  FollowUpMethod,
  InspectionView,
  SubstanceFollowUp,
} from "../api/contracts";
import type { AnalysisStatePresentation } from "../domain/analysis";
import {
  KNOWLEDGE_GAP_MESSAGE,
  followUpStatusLabel,
  historicalReferenceMessage,
  substanceFollowUpMessage,
} from "../domain/recommendation";
import { safeHttpUrl } from "../domain/product";
import { StatusBadge } from "./StatusBadge";

type TemporalRiskFinding = InspectionView["riskFindings"][number] & {
  temporal_basis?: "current_only" | "current_and_historical" | "historical_reference_only";
  historical_reference_mapping_ids?: string[];
  historical_reference_note?: string;
};

function MethodItem({
  method,
  secondary = false,
}: {
  method: FollowUpMethod;
  secondary?: boolean;
}) {
  const sourceUrl = safeHttpUrl(method.source_reference);
  const lifecycle =
    method.method_status === "current"
      ? "现行"
      : method.method_status === "revoked"
        ? "已废止"
        : method.method_status === "superseded"
          ? "已替代"
          : "待核验";
  return (
    <li className="method-item" data-secondary={secondary}>
      <div>
        <strong>{method.method_name}</strong>
        <span>{method.method_no}</span>
      </div>
      <p>
        {method.source_name}
        {method.source_date ? ` · ${method.source_date}` : ""}
      </p>
      {secondary && (
        <p className="method-reason">
          {lifecycle} · {method.applicability_reason}
        </p>
      )}
      {sourceUrl && (
        <a href={sourceUrl} target="_blank" rel="noreferrer">
          官方来源 <ExternalLink size={13} />
        </a>
      )}
    </li>
  );
}

function MethodGroup({
  title,
  methods,
  secondary = false,
}: {
  title: string;
  methods: FollowUpMethod[];
  secondary?: boolean;
}) {
  if (!methods.length) return null;
  return (
    <div className="method-group">
      <h5>{title}</h5>
      <ul>
        {methods.map((method) => (
          <MethodItem key={method.method_id} method={method} secondary={secondary} />
        ))}
      </ul>
    </div>
  );
}

function SubstanceCard({ substance }: { substance: SubstanceFollowUp }) {
  return (
    <article className="substance-card">
      <div className="substance-heading">
        <div>
          <h4>{substance.canonical_name}</h4>
          <p>
            {substance.english_name || "暂无英文名称"}
            {substance.cas_no ? ` · CAS ${substance.cas_no}` : ""}
          </p>
        </div>
        <StatusBadge
          tone={
            substance.follow_up_status === "suggest_testing" ? "info" : "neutral"
          }
        >
          {followUpStatusLabel(substance.follow_up_status)}
        </StatusBadge>
      </div>
      <p className="substance-reason">{substanceFollowUpMessage(substance)}</p>
      <MethodGroup title="可参考检测方法" methods={substance.suggested_methods} />
      <MethodGroup
        title="补充商品信息后可判断"
        methods={substance.methods_needing_context}
        secondary
      />
      {substance.other_known_methods.length > 0 && (
        <details className="other-methods">
          <summary>其他方法记录（{substance.other_known_methods.length}）</summary>
          <MethodGroup
            title=""
            methods={substance.other_known_methods}
            secondary
          />
        </details>
      )}
      {substance.regulatory_context_note && (
        <p className="context-note">该成分需结合商品身份、注册备案和配料信息判断。</p>
      )}
    </article>
  );
}

export function RecommendationPanel({
  inspection,
  analysis,
}: {
  inspection: InspectionView;
  analysis: AnalysisStatePresentation;
}) {
  if (analysis.code === "RECOMMENDATION_ERROR") {
    return (
      <section className="detail-section">
        <h3><FlaskConical size={17} />抽检辅助建议</h3>
        <div className="inline-message" data-tone="warning">
          <AlertCircle size={17} />
          <span>{analysis.message}{inspection.error?.message ? `（${inspection.error.message}）` : ""}</span>
        </div>
      </section>
    );
  }
  if (analysis.code !== "RECOMMENDATION_AVAILABLE" && analysis.code !== "RISK_MAPPED_NO_METHOD") {
    return (
      <section className="detail-section">
        <h3><FlaskConical size={17} />抽检辅助建议</h3>
        <div className="inline-message" data-tone={analysis.tone}>
          <BookOpenCheck size={17} />
          <span>{analysis.message}</span>
        </div>
      </section>
    );
  }

  const hasSubstances = inspection.riskFindings.some(
    (finding) => finding.substance_follow_ups.length > 0,
  );
  const hasKnowledgeGap =
    inspection.knowledgeGaps.length > 0 || inspection.compositionGaps.length > 0;

  return (
    <section className="detail-section recommendation-section">
      <h3><FlaskConical size={17} />抽检辅助建议</h3>
      {analysis.code === "RISK_MAPPED_NO_METHOD" && (
        <div className="inline-message" data-tone="warning">
          <BookOpenCheck size={17} />
          <span>{analysis.message}</span>
        </div>
      )}
      {inspection.riskFindings.length === 0 ? (
        <div className="inline-message">
          <BookOpenCheck size={17} />
          <span>已发现页面宣传线索，但当前暂无对应的抽检建议。</span>
        </div>
      ) : (
        inspection.riskFindings.map((baseFinding) => {
          const finding = baseFinding as TemporalRiskFinding;
          const hasHistoricalReference =
            finding.temporal_basis === "current_and_historical" ||
            finding.temporal_basis === "historical_reference_only";
          return (
            <div className="risk-finding" key={finding.risk_category}>
              <div className="risk-labels">
                {finding.risk_labels.map((label) => (
                  <StatusBadge key={label} tone="warning">{label}</StatusBadge>
                ))}
                {finding.evidence_qualification === "user_generated_auxiliary_only" && (
                  <StatusBadge>仅辅助线索</StatusBadge>
                )}
                {hasHistoricalReference && (
                  <StatusBadge>含历史筛查参考</StatusBadge>
                )}
              </div>
              <p>{finding.possible_risk_summary}</p>
              {historicalReferenceMessage(finding) && (
                <p className="context-note">{historicalReferenceMessage(finding)}</p>
              )}
              {finding.substance_follow_ups.map((substance) => (
                <SubstanceCard key={substance.substance_id} substance={substance} />
              ))}
            </div>
          );
        })
      )}
      {(hasKnowledgeGap || (inspection.riskFindings.length > 0 && !hasSubstances)) && (
        <div className="knowledge-gap">
          <BookOpenCheck size={17} />
          <p>{KNOWLEDGE_GAP_MESSAGE}</p>
        </div>
      )}
      {inspection.disclaimer && (
        <p className="recommendation-disclaimer">{inspection.disclaimer}</p>
      )}
    </section>
  );
}
