import {
  BookOpenCheck,
  ExternalLink,
  FileText,
  Info,
  Layers3,
} from "lucide-react";

import type {
  KnowledgeHealthFunction,
  KnowledgeInspectionMethod,
  KnowledgeMonitorTarget,
  KnowledgeRegulatoryDocument,
  KnowledgeRiskMapping,
  KnowledgeSourceTrace,
  KnowledgeSubstance,
} from "../../api/contracts";
import { Drawer } from "../../components/Drawer";
import { StatusBadge } from "../../components/StatusBadge";
import {
  METHOD_KNOWLEDGE_DEPTH_LABELS,
  knowledgeAvailabilityPresentation,
  knowledgeDepthTone,
  knowledgeGapLabel,
  knowledgeGapTone,
  knowledgeLifecyclePresentation,
  mapKnowledgeSource,
  safeKnowledgeSourceUrl,
  type KnowledgeTabId,
} from "../../domain/knowledge";
import type { KnowledgeRecord } from "./types";
import { knowledgeRecordId, knowledgeRecordTitle } from "./types";

type KnowledgeDetailDrawerProps = {
  tab: KnowledgeTabId;
  record: KnowledgeRecord;
  onClose: () => void;
};

function SourceLink({ url, label }: { url: string | null | undefined; label: string }) {
  const safeUrl = safeKnowledgeSourceUrl(url);
  return safeUrl ? (
    <a
      className="knowledge-source-link"
      href={safeUrl}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`${label}（在新标签页打开）`}
    >
      {label} <ExternalLink size={13} aria-hidden="true" />
    </a>
  ) : (
    <span className="knowledge-muted">官方来源尚未记录</span>
  );
}

function SourceTrace({ source }: { source: KnowledgeSourceTrace }) {
  const view = mapKnowledgeSource(source);
  return (
    <section className="detail-section knowledge-source-trace">
      <h3><BookOpenCheck size={16} />来源与版本</h3>
      <dl className="knowledge-detail-grid">
        <div><dt>来源</dt><dd>{view.authority}</dd></div>
        <div><dt>数据集版本</dt><dd>{view.version}</dd></div>
        <div><dt>数据集状态</dt><dd>{view.status}</dd></div>
        <div><dt>来源日期</dt><dd>{view.date || "尚未记录"}</dd></div>
      </dl>
      <SourceLink url={view.reference} label="查看官方来源" />
    </section>
  );
}

function KnowledgeGaps({ gaps }: { gaps: string[] }) {
  if (!gaps.length) return null;
  return (
    <section className="detail-section knowledge-gap-section">
      <h3><Info size={16} />知识缺口</h3>
      <ul>
        {gaps.map((gap) => (
          <li key={gap} data-tone={knowledgeGapTone(gap)}>
            <span>{knowledgeGapLabel(gap)}</span>
            <small>{gap}</small>
          </li>
        ))}
      </ul>
    </section>
  );
}

function MonitorDetail({ item }: { item: KnowledgeMonitorTarget }) {
  const availability = knowledgeAvailabilityPresentation(item.availability);
  return (
    <>
      <section className="detail-section">
        <h3><Layers3 size={16} />目录对象</h3>
        <dl className="knowledge-detail-grid">
          <div><dt>Target ID</dt><dd>{item.targetId}</dd></div>
          <div><dt>Target Type</dt><dd>{item.targetType}</dd></div>
          <div><dt>当前可排查状态</dt><dd><StatusBadge tone={availability.tone}>{availability.label}</StatusBadge></dd></div>
          <div><dt>已验证搜索策略</dt><dd>{item.validatedSearchQueryCount} 条</dd></div>
        </dl>
        <p className="knowledge-boundary-note">Reference membership 不代表 Operational Search readiness。</p>
        {item.availabilityReason && <p className="knowledge-record-note">{item.availabilityReason}</p>}
      </section>
      <section className="detail-section">
        <h3>Governed SearchQueries</h3>
        {item.searchQueries.length ? (
          <div className="knowledge-stack-list">
            {item.searchQueries.map((query) => (
              <article key={query.query_id}>
                <strong>{query.query_text}</strong>
                <span>{query.validation_status} · {query.query_source}</span>
                {query.query_note && <p>{query.query_note}</p>}
              </article>
            ))}
          </div>
        ) : <p className="knowledge-not-recorded">尚无已验证搜索策略。</p>}
      </section>
      <KnowledgeGaps gaps={item.knowledgeGaps} />
      <SourceTrace source={item.source} />
    </>
  );
}

function HealthFunctionDetail({ item }: { item: KnowledgeHealthFunction }) {
  const status = knowledgeLifecyclePresentation(item.status);
  return (
    <>
      <section className="detail-section">
        <h3><Layers3 size={16} />官方功能记录</h3>
        <dl className="knowledge-detail-grid">
          <div><dt>Function ID</dt><dd>{item.functionId}</dd></div>
          <div><dt>官方名称</dt><dd>{item.officialName}</dd></div>
          <div><dt>Framework</dt><dd>{item.frameworkName}</dd></div>
          <div><dt>Framework Type</dt><dd>{item.frameworkType === "nutrient_supplement" ? "营养素补充剂框架" : "非营养素功能框架"}</dd></div>
          <div><dt>Framework Version</dt><dd>{item.frameworkVersion}</dd></div>
          <div><dt>序号</dt><dd>{item.ordinal}</dd></div>
          <div><dt>状态</dt><dd><StatusBadge tone={status.tone}>{status.label}</StatusBadge></dd></div>
          <div><dt>生效日期</dt><dd>{item.effectiveDate || "尚未记录"}</dd></div>
        </dl>
        <p className="knowledge-boundary-note">保健功能 ≠ 页面宣传线索；本页不建立 HealthFunction 与 ClaimSignal 的关系。</p>
      </section>
      <section className="detail-section">
        <h3>官方 transition aliases</h3>
        {item.transitionAliases.length ? (
          <div className="knowledge-stack-list">
            {item.transitionAliases.map((alias) => (
              <article key={alias.aliasId}>
                <strong>{alias.aliasText}</strong>
                <span>{alias.sourceName} · {alias.sourceDate}</span>
                <SourceLink url={alias.sourceReference} label={`查看“${alias.aliasText}”的官方来源`} />
              </article>
            ))}
          </div>
        ) : <p className="knowledge-not-recorded">未记录官方新旧功能名称衔接。</p>}
      </section>
      <KnowledgeGaps gaps={item.knowledgeGaps} />
      <SourceTrace source={item.source} />
    </>
  );
}

function SubstanceDetail({ item }: { item: KnowledgeSubstance }) {
  return (
    <>
      <section className="detail-section">
        <h3><Layers3 size={16} />物质记录</h3>
        <dl className="knowledge-detail-grid">
          <div><dt>Substance ID</dt><dd>{item.substanceId}</dd></div>
          <div><dt>英文名</dt><dd>{item.englishName || "尚未记录"}</dd></div>
          <div><dt>CAS</dt><dd>{item.casNo || "尚未记录"}</dd></div>
          <div><dt>检验方法覆盖</dt><dd>已关联 {item.methodCoverageCount} 个检验方法</dd></div>
          <div><dt>推荐准入深度方法</dt><dd>{item.recommendationReadyMethodCount} 个</dd></div>
          <div><dt>物质组信息</dt><dd>{item.groupMetadata.state === "recorded" ? `已记录 ${item.groupMetadata.memberships.length} 条` : "尚未记录"}</dd></div>
        </dl>
        <p className="knowledge-boundary-note">方法覆盖只表示知识关联，不表示任何商品含有或检出该物质。</p>
        {item.note && <p className="knowledge-record-note">{item.note}</p>}
      </section>
      <section className="detail-section">
        <h3>Group metadata</h3>
        {item.groupMetadata.memberships.length ? (
          <div className="knowledge-stack-list">
            {item.groupMetadata.memberships.map((membership) => (
              <article key={membership.membershipId}>
                <strong>{membership.groupLabel}</strong>
                <span>{membership.membershipScope} · {membership.completenessContext === "complete" ? "完整记录" : "部分记录"}</span>
                <p>{membership.sourceBasis}</p>
              </article>
            ))}
          </div>
        ) : <p className="knowledge-not-recorded">尚未记录物质组成员信息。</p>}
      </section>
      <section className="detail-section">
        <h3>监管语境</h3>
        {item.regulatoryContext.contexts.length ? (
          <div className="knowledge-stack-list">
            {item.regulatoryContext.contexts.map((context) => (
              <article key={context.contextId}>
                <strong>{context.productScope}</strong>
                <span>{context.status} · {context.jurisdiction}</span>
                {context.note && <p>{context.note}</p>}
                <SourceLink url={context.sourceReference} label="查看监管语境来源" />
              </article>
            ))}
          </div>
        ) : <p className="knowledge-not-recorded">尚未记录监管语境。</p>}
      </section>
      <KnowledgeGaps gaps={item.knowledgeGaps} />
      <SourceTrace source={item.source} />
    </>
  );
}

function RiskMappingDetail({ item }: { item: KnowledgeRiskMapping }) {
  const temporal = knowledgeLifecyclePresentation(item.temporalStatus);
  return (
    <>
      <section className="detail-section">
        <h3><Layers3 size={16} />映射事实</h3>
        <dl className="knowledge-detail-grid">
          <div><dt>Mapping ID</dt><dd>{item.mappingId}</dd></div>
          <div><dt>Risk Category</dt><dd>{item.riskCategory}</dd></div>
          <div><dt>Target</dt><dd>{item.target.label}</dd></div>
          <div><dt>Target Type</dt><dd><StatusBadge tone={item.targetType === "substance_group" ? "warning" : "info"}>{item.targetType === "substance_group" ? "组级映射" : "单一物质"}</StatusBadge></dd></div>
          <div><dt>Evidence Grade</dt><dd>{item.evidenceGrade}</dd></div>
          <div><dt>Basis</dt><dd>{item.basisType === "current_official_guidance" ? "现行官方指导" : item.basisType}</dd></div>
          <div><dt>Temporal Status</dt><dd><StatusBadge tone={temporal.tone}>{temporal.label}</StatusBadge></dd></div>
          <div><dt>Product Scope</dt><dd>{item.productScope}</dd></div>
        </dl>
        <p className="knowledge-boundary-note">风险映射不是商品含有目标物质的证据；检验方法分析物不会在浏览器中反向生成映射。</p>
      </section>
      <section className="detail-section">
        <h3>来源依据原文</h3>
        <p className="knowledge-long-copy">{item.sourceBasisText}</p>
        {item.note && <p className="knowledge-record-note">{item.note}</p>}
      </section>
      {item.targetType === "substance_group" && (
        <section className="detail-section">
          <h3>组级映射解析</h3>
          <p className="knowledge-not-recorded">
            {item.groupResolution?.status === "unresolved"
              ? "物质组成员尚未解析；本页不会自动展开组成员。"
              : item.groupResolution?.status === "partial"
                ? `仅部分解析，当前记录 ${item.groupResolution.memberCount} 个成员。`
                : `已记录 ${item.groupResolution?.memberCount || 0} 个治理成员。`}
          </p>
        </section>
      )}
      <KnowledgeGaps gaps={item.knowledgeGaps} />
      <SourceTrace source={item.source} />
    </>
  );
}

function MethodDetail({ item }: { item: KnowledgeInspectionMethod }) {
  const lifecycle = knowledgeLifecyclePresentation(item.methodStatus);
  return (
    <>
      <section className="detail-section">
        <h3><Layers3 size={16} />方法身份与状态</h3>
        <div className="knowledge-status-pair" aria-label="官方生命周期与知识深度">
          <div><span>官方生命周期</span><StatusBadge tone={lifecycle.tone}>{lifecycle.label}</StatusBadge></div>
          <div><span>知识深度</span><StatusBadge tone={knowledgeDepthTone(item.knowledgeDepth)}>{METHOD_KNOWLEDGE_DEPTH_LABELS[item.knowledgeDepth]}</StatusBadge></div>
        </div>
        <dl className="knowledge-detail-grid">
          <div><dt>Method ID</dt><dd>{item.methodId}</dd></div>
          <div><dt>Method Type</dt><dd>{item.methodType}</dd></div>
          <div><dt>Publisher</dt><dd>{item.publisher}</dd></div>
          <div><dt>发布日期</dt><dd>{item.publishedDate || "尚未记录"}</dd></div>
          <div><dt>生效日期</dt><dd>{item.effectiveDate || "尚未记录"}</dd></div>
          <div><dt>Analyte 数量</dt><dd>{item.analyteCount}</dd></div>
          <div><dt>替代方法</dt><dd>{item.replacesMethodNo || "尚未记录"}</dd></div>
          <div><dt>被替代为</dt><dd>{item.replacedByMethodNo || "尚未记录"}</dd></div>
        </dl>
        {item.knowledgeDepth === "reference_only" && (
          <p className="knowledge-boundary-note">仅索引官方身份/生命周期，不参与检验方法推荐。</p>
        )}
        {item.note && <p className="knowledge-record-note">{item.note}</p>}
      </section>
      <section className="detail-section">
        <h3>Applicability</h3>
        {item.applicability.availability === "recorded" ? (
          <dl className="knowledge-detail-grid">
            <div><dt>总数</dt><dd>{item.applicability.count}</dd></div>
            <div><dt>Include</dt><dd>{item.applicability.includeCount}</dd></div>
            <div><dt>Conditional</dt><dd>{item.applicability.conditionalCount}</dd></div>
            <div><dt>Exclude</dt><dd>{item.applicability.excludeCount}</dd></div>
          </dl>
        ) : <p className="knowledge-not-recorded">适用范围尚未记录。</p>}
      </section>
      <section className="detail-section">
        <h3><FileText size={16} />关联官方文件</h3>
        {item.regulatoryDocument ? (
          <div className="knowledge-document-card">
            <strong>{item.regulatoryDocument.documentNo || "文号尚未记录"}</strong>
            <p>{item.regulatoryDocument.title}</p>
            <span>{item.regulatoryDocument.publisher} · {item.regulatoryDocument.status}</span>
            <SourceLink url={item.regulatoryDocument.sourceReference} label="查看关联官方文件" />
          </div>
        ) : <p className="knowledge-not-recorded">尚未关联官方文件。</p>}
      </section>
      <KnowledgeGaps gaps={item.knowledgeGaps} />
      <SourceTrace source={item.source} />
    </>
  );
}

function DocumentDetail({ item }: { item: KnowledgeRegulatoryDocument }) {
  const lifecycle = knowledgeLifecyclePresentation(item.status);
  return (
    <>
      <section className="detail-section">
        <h3><FileText size={16} />官方文件</h3>
        <dl className="knowledge-detail-grid">
          <div><dt>Document ID</dt><dd>{item.documentId}</dd></div>
          <div><dt>Document Type</dt><dd>{item.documentType}</dd></div>
          <div><dt>文号</dt><dd>{item.documentNo || "尚未记录"}</dd></div>
          <div><dt>Publisher</dt><dd>{item.publisher}</dd></div>
          <div><dt>Lifecycle</dt><dd><StatusBadge tone={lifecycle.tone}>{lifecycle.label}</StatusBadge></dd></div>
          <div><dt>Jurisdiction</dt><dd>{item.jurisdiction}</dd></div>
          <div><dt>发布日期</dt><dd>{item.publishedDate || "尚未记录"}</dd></div>
          <div><dt>生效日期</dt><dd>{item.effectiveDate || "尚未记录"}</dd></div>
          <div><dt>关联检验方法</dt><dd>{item.linkedMethodCount} 个</dd></div>
          <div><dt>Supersedes</dt><dd>{item.supersedes.join("、") || "尚未记录"}</dd></div>
          <div><dt>Superseded By</dt><dd>{item.supersededBy.join("、") || "尚未记录"}</dd></div>
        </dl>
        <SourceLink url={item.sourceReference} label="查看官方来源" />
      </section>
      <KnowledgeGaps gaps={item.knowledgeGaps} />
      <SourceTrace source={item.source} />
    </>
  );
}

export function KnowledgeDetailDrawer({
  tab,
  record,
  onClose,
}: KnowledgeDetailDrawerProps) {
  const content = (() => {
    switch (tab) {
      case "monitor-targets": return <MonitorDetail item={record as KnowledgeMonitorTarget} />;
      case "health-functions": return <HealthFunctionDetail item={record as KnowledgeHealthFunction} />;
      case "substances": return <SubstanceDetail item={record as KnowledgeSubstance} />;
      case "risk-mappings": return <RiskMappingDetail item={record as KnowledgeRiskMapping} />;
      case "inspection-methods": return <MethodDetail item={record as KnowledgeInspectionMethod} />;
      case "regulatory-documents": return <DocumentDetail item={record as KnowledgeRegulatoryDocument} />;
    }
  })();

  return (
    <div className="knowledge-drawer-overlay">
      <Drawer
        title={knowledgeRecordTitle(tab, record)}
        subtitle={`记录 ID ${knowledgeRecordId(tab, record)}`}
        kicker="治理知识详情 · 只读"
        closeLabel="关闭知识详情"
        onClose={onClose}
      >
        <div className="readonly-inline-note">
          <Info size={16} aria-hidden="true" />
          <span>本页读取当前治理知识，不提供新增、编辑或删除操作。</span>
        </div>
        {content}
      </Drawer>
    </div>
  );
}
