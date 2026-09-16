import { Eye } from "lucide-react";

import type {
  KnowledgeHealthFunction,
  KnowledgeInspectionMethod,
  KnowledgeMonitorTarget,
  KnowledgeRegulatoryDocument,
  KnowledgeRiskMapping,
  KnowledgeSubstance,
} from "../../api/contracts";
import { StatusBadge } from "../../components/StatusBadge";
import {
  METHOD_KNOWLEDGE_DEPTH_LABELS,
  knowledgeAvailabilityPresentation,
  knowledgeDepthTone,
  knowledgeLifecyclePresentation,
  type KnowledgeTabId,
} from "../../domain/knowledge";
import type { KnowledgeRecord } from "./types";

type KnowledgeTableProps = {
  tab: KnowledgeTabId;
  records: KnowledgeRecord[];
  selectedId?: string;
  onSelect: (record: KnowledgeRecord) => void;
};

function ViewButton({ label }: { label: string }) {
  return (
    <span className="knowledge-view-label">
      <Eye size={14} aria-hidden="true" /> 查看详情
      <span className="sr-only">：{label}</span>
    </span>
  );
}

function MonitorRows({
  records,
  selectedId,
  onSelect,
}: Omit<KnowledgeTableProps, "tab">) {
  return (
    <>
      <thead><tr><th>标准名称</th><th>当前可排查状态</th><th>Validated Query</th><th>来源版本</th><th>操作</th></tr></thead>
      <tbody>
        {(records as KnowledgeMonitorTarget[]).map((item) => {
          const status = knowledgeAvailabilityPresentation(item.availability);
          return (
            <tr key={item.targetId} data-selected={selectedId === item.targetId}>
              <td><strong>{item.standardName}</strong><small>{item.targetId}</small></td>
              <td><StatusBadge tone={status.tone}>{status.label}</StatusBadge></td>
              <td>{item.hasValidatedSearchQuery ? <StatusBadge tone="success">已有 {item.validatedSearchQueryCount} 条已验证策略</StatusBadge> : <span className="knowledge-muted">尚无已验证搜索策略</span>}</td>
              <td><span>{item.source.datasetVersion}</span><small>{item.source.sourceName || item.source.datasetId}</small></td>
              <td><button type="button" className="knowledge-row-button" onClick={() => onSelect(item)} aria-label={`查看${item.standardName}详情`}><ViewButton label={item.standardName} /></button></td>
            </tr>
          );
        })}
      </tbody>
    </>
  );
}

function HealthFunctionRows({
  records,
  selectedId,
  onSelect,
}: Omit<KnowledgeTableProps, "tab">) {
  return (
    <>
      <thead><tr><th>官方功能名称</th><th>Framework</th><th>序号</th><th>状态</th><th>操作</th></tr></thead>
      <tbody>
        {(records as KnowledgeHealthFunction[]).map((item) => {
          const status = knowledgeLifecyclePresentation(item.status);
          return (
            <tr key={item.functionId} data-selected={selectedId === item.functionId}>
              <td><strong>{item.officialName}</strong><small>{item.functionId}</small></td>
              <td><span>{item.frameworkName}</span><small>{item.frameworkType === "nutrient_supplement" ? "营养素补充剂框架" : "非营养素功能框架"}</small></td>
              <td>{item.ordinal}</td>
              <td><StatusBadge tone={status.tone}>{status.label}</StatusBadge></td>
              <td><button type="button" className="knowledge-row-button" onClick={() => onSelect(item)} aria-label={`查看${item.officialName}详情`}><ViewButton label={item.officialName} /></button></td>
            </tr>
          );
        })}
      </tbody>
    </>
  );
}

function SubstanceRows({
  records,
  selectedId,
  onSelect,
}: Omit<KnowledgeTableProps, "tab">) {
  return (
    <>
      <thead><tr><th>物质名称</th><th>CAS</th><th>检验方法覆盖</th><th>监管语境</th><th>操作</th></tr></thead>
      <tbody>
        {(records as KnowledgeSubstance[]).map((item) => (
          <tr key={item.substanceId} data-selected={selectedId === item.substanceId}>
            <td><strong>{item.canonicalName}</strong><small>{item.englishName || item.substanceId}</small></td>
            <td>{item.casNo || <span className="knowledge-muted">尚未记录</span>}</td>
            <td><span>已关联 {item.methodCoverageCount} 个检验方法</span><small>其中 {item.recommendationReadyMethodCount} 个达到推荐准入深度</small></td>
            <td>{item.regulatoryContext.availability === "recorded" ? <StatusBadge tone="info">已记录 {item.regulatoryContext.count} 条</StatusBadge> : <StatusBadge tone="neutral">尚未记录监管语境</StatusBadge>}</td>
            <td><button type="button" className="knowledge-row-button" onClick={() => onSelect(item)} aria-label={`查看${item.canonicalName}详情`}><ViewButton label={item.canonicalName} /></button></td>
          </tr>
        ))}
      </tbody>
    </>
  );
}

function RiskMappingRows({
  records,
  selectedId,
  onSelect,
}: Omit<KnowledgeTableProps, "tab">) {
  return (
    <>
      <thead><tr><th>风险方向</th><th>Target</th><th>Target Type</th><th>Evidence / Basis</th><th>时态</th><th>操作</th></tr></thead>
      <tbody>
        {(records as KnowledgeRiskMapping[]).map((item) => {
          const temporal = knowledgeLifecyclePresentation(item.temporalStatus);
          return (
            <tr key={item.mappingId} data-selected={selectedId === item.mappingId}>
              <td><strong>{item.riskLabel}</strong><small>{item.riskCategory}</small></td>
              <td><span>{item.target.label}</span><small>{item.target.casNo || item.mappingId}</small></td>
              <td><StatusBadge tone={item.targetType === "substance_group" ? "warning" : "info"}>{item.targetType === "substance_group" ? "组级映射" : "单一物质"}</StatusBadge></td>
              <td><span>证据等级 {item.evidenceGrade}</span><small>{item.basisType === "current_official_guidance" ? "现行官方指导" : item.basisType}</small></td>
              <td><StatusBadge tone={temporal.tone}>{temporal.label}</StatusBadge></td>
              <td><button type="button" className="knowledge-row-button" onClick={() => onSelect(item)} aria-label={`查看${item.riskLabel}详情`}><ViewButton label={item.riskLabel} /></button></td>
            </tr>
          );
        })}
      </tbody>
    </>
  );
}

function MethodRows({
  records,
  selectedId,
  onSelect,
}: Omit<KnowledgeTableProps, "tab">) {
  return (
    <>
      <thead><tr><th>方法编号 / 名称</th><th>官方生命周期</th><th>知识深度</th><th>Publisher</th><th>Analyte</th><th>Applicability</th><th>操作</th></tr></thead>
      <tbody>
        {(records as KnowledgeInspectionMethod[]).map((item) => {
          const lifecycle = knowledgeLifecyclePresentation(item.methodStatus);
          return (
            <tr key={item.methodId} data-selected={selectedId === item.methodId}>
              <td><strong>{item.methodNo}</strong><small className="knowledge-title-clamp" title={item.methodName}>{item.methodName}</small></td>
              <td><StatusBadge tone={lifecycle.tone}>{lifecycle.label}</StatusBadge></td>
              <td><StatusBadge tone={knowledgeDepthTone(item.knowledgeDepth)}>{METHOD_KNOWLEDGE_DEPTH_LABELS[item.knowledgeDepth]}</StatusBadge></td>
              <td>{item.publisher}</td>
              <td>{item.analyteCount}</td>
              <td>{item.applicability.availability === "recorded" ? item.applicability.count : <span className="knowledge-muted">尚未记录</span>}</td>
              <td><button type="button" className="knowledge-row-button" onClick={() => onSelect(item)} aria-label={`查看${item.methodNo}详情`}><ViewButton label={item.methodNo} /></button></td>
            </tr>
          );
        })}
      </tbody>
    </>
  );
}

function DocumentRows({
  records,
  selectedId,
  onSelect,
}: Omit<KnowledgeTableProps, "tab">) {
  return (
    <>
      <thead><tr><th>文号 / 标题</th><th>类型</th><th>Publisher</th><th>Lifecycle</th><th>发布日期 / 生效日期</th><th>操作</th></tr></thead>
      <tbody>
        {(records as KnowledgeRegulatoryDocument[]).map((item) => {
          const lifecycle = knowledgeLifecyclePresentation(item.status);
          return (
            <tr key={item.documentId} data-selected={selectedId === item.documentId}>
              <td><strong>{item.documentNo || "文号尚未记录"}</strong><small className="knowledge-title-clamp" title={item.title}>{item.title}</small></td>
              <td>{item.documentType === "official_method_page" ? "官方方法页面" : item.documentType === "official_announcement" ? "官方公告" : "国家标准记录"}</td>
              <td>{item.publisher}</td>
              <td><StatusBadge tone={lifecycle.tone}>{lifecycle.label}</StatusBadge></td>
              <td><span>{item.publishedDate || "发布日期尚未记录"}</span><small>{item.effectiveDate ? `生效 ${item.effectiveDate}` : "生效日期尚未记录"}</small></td>
              <td><button type="button" className="knowledge-row-button" onClick={() => onSelect(item)} aria-label={`查看${item.title}详情`}><ViewButton label={item.title} /></button></td>
            </tr>
          );
        })}
      </tbody>
    </>
  );
}

export function KnowledgeTable(props: KnowledgeTableProps) {
  const content = (() => {
    switch (props.tab) {
      case "monitor-targets": return <MonitorRows {...props} />;
      case "health-functions": return <HealthFunctionRows {...props} />;
      case "substances": return <SubstanceRows {...props} />;
      case "risk-mappings": return <RiskMappingRows {...props} />;
      case "inspection-methods": return <MethodRows {...props} />;
      case "regulatory-documents": return <DocumentRows {...props} />;
    }
  })();

  return (
    <div className="knowledge-table-scroll">
      <table className="knowledge-table">
        <caption className="sr-only">当前知识域治理记录</caption>
        {content}
      </table>
    </div>
  );
}
