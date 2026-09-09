import { AlertCircle, BookOpenCheck, ExternalLink, FlaskConical } from "lucide-react";

import type {
  FollowUpMethod,
  InspectionView,
  SubstanceFollowUp,
} from "../api/contracts";
import { KNOWLEDGE_GAP_MESSAGE } from "../domain/recommendation";
import { safeHttpUrl } from "../domain/product";
import { StatusBadge } from "./StatusBadge";

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
          {substance.follow_up_status === "suggest_testing"
            ? "建议重点关注"
            : substance.follow_up_status === "needs_context_review"
              ? "需要补充信息"
              : "需人工判断"}
        </StatusBadge>
      </div>
      <p className="substance-reason">{substance.reason}</p>
      <MethodGroup title="相关已核验方法" methods={substance.suggested_methods} />
      <MethodGroup
        title="需补充商品信息后判断"
        methods={substance.methods_needing_context}
        secondary
      />
      {substance.other_known_methods.length > 0 && (
        <details className="other-methods">
          <summary>其他已知方法（{substance.other_known_methods.length}）</summary>
          <MethodGroup
            title=""
            methods={substance.other_known_methods}
            secondary
          />
        </details>
      )}
      {substance.regulatory_context_note && (
        <p className="context-note">{substance.regulatory_context_note}</p>
      )}
    </article>
  );
}

export function RecommendationPanel({ inspection }: { inspection: InspectionView }) {
  if (inspection.recommendationStatus === "error") {
    return (
      <section className="detail-section">
        <h3><FlaskConical size={17} />抽检辅助建议</h3>
        <div className="inline-message" data-tone="danger">
          <AlertCircle size={17} />
          <span>{inspection.error?.message || "该次快照的抽检辅助建议暂时无法读取。"}</span>
        </div>
      </section>
    );
  }
  if (!inspection.available) {
    return (
      <section className="detail-section">
        <h3><FlaskConical size={17} />抽检辅助建议</h3>
        <div className="inline-message">
          <BookOpenCheck size={17} />
          <span>该次快照尚无可用的抽检辅助建议文件，页面证据与人工复核仍可查看。</span>
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
      {inspection.riskFindings.length === 0 ? (
        <div className="inline-message">
          <BookOpenCheck size={17} />
          <span>当前快照没有可桥接至已核验知识的风险方向，页面证据仍可供人工复核。</span>
        </div>
      ) : (
        inspection.riskFindings.map((finding) => (
          <div className="risk-finding" key={finding.risk_category}>
            <div className="risk-labels">
              {finding.risk_labels.map((label) => (
                <StatusBadge key={label} tone="warning">{label}</StatusBadge>
              ))}
              {finding.evidence_qualification === "user_generated_auxiliary_only" && (
                <StatusBadge>仅辅助线索</StatusBadge>
              )}
            </div>
            <p>{finding.possible_risk_summary}</p>
            {finding.substance_follow_ups.map((substance) => (
              <SubstanceCard key={substance.substance_id} substance={substance} />
            ))}
          </div>
        ))
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
