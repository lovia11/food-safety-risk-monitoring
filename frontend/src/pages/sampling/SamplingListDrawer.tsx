import { ExternalLink, FileCheck2, FlaskConical, Info, Quote, ShieldCheck } from "lucide-react";

import type { SamplingItem, SamplingMethodSummary } from "../../api/contracts";
import { Drawer } from "../../components/Drawer";
import { StatusBadge } from "../../components/StatusBadge";
import { formatDateTime, safeHttpUrl } from "../../domain/product";
import { KNOWLEDGE_GAP_MESSAGE } from "../../domain/recommendation";
import {
  evidenceQualificationLabel,
  frozenAssetLabel,
  samplingMethodLabel,
  samplingMethodGroups,
} from "../../domain/sampling";

type SamplingListDrawerProps = {
  item: SamplingItem;
  historical?: boolean;
  onClose: () => void;
};

function MethodCards({ methods }: { methods: SamplingMethodSummary[] }) {
  return methods.length ? methods.map((method) => (
    <article key={method.methodId || samplingMethodLabel(method)}>
      <strong>{samplingMethodLabel(method)}</strong>
      <StatusBadge tone={method.applicabilityStatus === "applicable" ? "success" : "neutral"}>
        {method.applicabilityStatus || "适用性未记录"}
      </StatusBadge>
      {method.methodStatus && <small>方法状态：{method.methodStatus}</small>}
      {method.applicabilityReason && <p>{method.applicabilityReason}</p>}
    </article>
  )) : <p className="table-empty">暂无记录。</p>;
}

export function SamplingListDrawer({
  item,
  historical = false,
  onClose,
}: SamplingListDrawerProps) {
  const productUrl = safeHttpUrl(item.productUrl);
  const methods = samplingMethodGroups(item);

  return (
    <Drawer
      title={item.productName || item.productId}
      subtitle={`${item.shopName || "店铺未记录"} · ID ${item.productId}`}
      kicker={historical ? "历史冻结条目" : "当前清单条目"}
      closeLabel="关闭抽检清单详情"
      onClose={onClose}
    >
      {historical && (
        <div className="readonly-banner">
          <FileCheck2 size={17} aria-hidden="true" />
          <div>
            <strong>已冻结，只读</strong>
            <p>以导出时保存的内容为准，不会换成当前商品数据。</p>
          </div>
        </div>
      )}

      <section className="detail-section sampling-detail-facts">
        <h3><ShieldCheck size={16} />条目追溯</h3>
        <dl>
          <div><dt>来源排查</dt><dd>{item.sourceTaskDisplayName || item.sourceTaskId}</dd></div>
          <div><dt>页面采集时间</dt><dd>{formatDateTime(item.collectedAt)}</dd></div>
          <div><dt>加入时间</dt><dd>{formatDateTime(item.addedAt)}</dd></div>
          <div><dt>加入入口</dt><dd>{item.addedFrom === "product_overview" ? "商品总览" : "排查工作区"}</dd></div>
          <div><dt>采集记录 ID</dt><dd>{item.sourceSnapshotId}</dd></div>
          <div><dt>导出前历史纳入</dt><dd>{item.historicalCountBeforeExport} 次</dd></div>
        </dl>
        <div className="detail-inline-actions">
          {productUrl && <a className="text-link" href={productUrl} target="_blank" rel="noreferrer">打开保存的商品链接 <ExternalLink size={13} /></a>}
          {!historical && <a className="text-link" href={`#/products/${encodeURIComponent(item.productId)}`}>查看商品采集记录</a>}
        </div>
      </section>

      <section className="detail-section">
        <h3><FlaskConical size={16} />抽检辅助建议</h3>
        <div className="sampling-summary-grid">
          <div><span>页面功效线索</span><strong>{item.summary.pageEffectClues.join("、") || "暂无页面功效线索"}</strong></div>
          <div><span>可能风险方向</span><strong>{item.summary.riskDirections.join("、") || "暂无已核验映射"}</strong></div>
          <div><span>建议关注/检测成分</span><strong>{item.summary.substances.join("、") || "暂无已核验成分建议"}</strong></div>
        </div>
        <div className="sampling-method-list">
          <h4>建议参考方法/标准</h4>
          <MethodCards methods={methods.suggested} />
        </div>
        {methods.needsContext.length > 0 && (
          <div className="sampling-method-list needs-context-methods">
            <h4>需补充商品信息后判断</h4>
            <MethodCards methods={methods.needsContext} />
          </div>
        )}
        {methods.otherKnown.length > 0 && (
          <details className="sampling-method-disclosure">
            <summary>其他已知方法（非直接建议）</summary>
            <div className="sampling-method-list"><MethodCards methods={methods.otherKnown} /></div>
          </details>
        )}
        {methods.legacyUnclassified.length > 0 && (
          <details className="sampling-method-disclosure">
            <summary>旧版记录中未分类的方法</summary>
            <p>旧版冻结记录未保存方法分层，本页不将其作为建议方法展示。</p>
            <div className="sampling-method-list"><MethodCards methods={methods.legacyUnclassified} /></div>
          </details>
        )}
        {(item.summary.pageEffectClues.length > 0 && item.summary.riskDirections.length === 0) && (
          <div className="knowledge-gap"><Info size={16} /><p>{KNOWLEDGE_GAP_MESSAGE}</p></div>
        )}
      </section>

      {(item.productContext.product_category ||
        item.productContext.product_form ||
        item.productContext.confirmed_ingredient_contexts.length > 0) && (
        <section className="detail-section sampling-detail-facts">
          <h3><Info size={16} />商品补充信息</h3>
          <dl>
            <div><dt>商品类别</dt><dd>{item.productContext.product_category || "未填写"}</dd></div>
            <div><dt>商品剂型</dt><dd>{item.productContext.product_form || "未填写"}</dd></div>
            <div><dt>已确认配料背景</dt><dd>{item.productContext.confirmed_ingredient_contexts.join("、") || "未填写"}</dd></div>
          </dl>
        </section>
      )}

      <section className="detail-section">
        <h3><Quote size={16} />页面证据</h3>
        <div className="sampling-evidence-list">
          {item.evidence.length ? item.evidence.map((evidence) => (
            <article key={evidence.evidenceId}>
              <div>
                <StatusBadge tone={evidence.contentOrigin === "seller_managed" ? "warning" : "neutral"}>
                  {evidence.contentOrigin === "seller_managed" ? "商家管理内容" : "用户生成内容"}
                </StatusBadge>
                <small>{evidence.sourceLabel || evidence.sourceType}</small>
              </div>
              <blockquote>{evidence.text}</blockquote>
            </article>
          )) : <p className="table-empty">导出时未保存可展示的页面证据。</p>}
        </div>
        <p className="qualification-note">
          页面证据性质：{evidenceQualificationLabel(item.summary.pageEvidenceQualification)}
        </p>
        {item.summary.riskEvidenceQualifications.length > 0 && (
          <p className="qualification-note">
            风险映射证据性质：{item.summary.riskEvidenceQualifications.map(evidenceQualificationLabel).join("、")}
          </p>
        )}
        {historical && item.frozenAssets.length > 0 && (
          <div className="frozen-asset-links">
            {item.frozenAssets.filter((asset) => asset.url).map((asset) => (
              <a key={asset.frozenPath} href={asset.url || undefined} target="_blank" rel="noreferrer">
                {frozenAssetLabel(asset.kind)} <ExternalLink size={12} />
              </a>
            ))}
          </div>
        )}
      </section>

      <section className="detail-section sampling-review-note">
        <h3>人工复核</h3>
        <StatusBadge tone="success">已复核 / 建议跟进</StatusBadge>
        <p>{item.review.note || "未填写人工备注"}</p>
        <small>{formatDateTime(item.review.reviewedAt)}</small>
      </section>

      <p className="sampling-disclaimer">{item.disclaimer}</p>
    </Drawer>
  );
}
