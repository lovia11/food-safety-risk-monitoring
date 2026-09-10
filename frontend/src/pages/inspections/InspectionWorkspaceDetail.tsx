import { AlertCircle, ExternalLink, Info, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import type { SnapshotWorkspace } from "../../api/contracts";
import { getSnapshotWorkspace, updateInspectionContext } from "../../api/products";
import { EmptyState } from "../../components/EmptyState";
import { EvidenceCard } from "../../components/EvidenceCard";
import { LoadingState } from "../../components/LoadingState";
import { ProductContextForm } from "../../components/ProductContextForm";
import { RecommendationPanel } from "../../components/RecommendationPanel";
import { ReviewActions } from "../../components/ReviewActions";
import { StatusBadge } from "../../components/StatusBadge";
import { useToast } from "../../components/ToastProvider";
import { formatDateTime, safeHttpUrl } from "../../domain/product";
import { needsProductContext } from "../../domain/recommendation";

type ReviewChange = {
  type: "decision" | "membership_removed" | "membership_restored";
  decision?: "recommend_follow_up" | "no_further_action";
};

type Props = {
  snapshotId: string;
  onChanged: (change?: ReviewChange) => Promise<void>;
};

export function InspectionWorkspaceDetail({ snapshotId, onChanged }: Props) {
  const [workspace, setWorkspace] = useState<SnapshotWorkspace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [savingContext, setSavingContext] = useState(false);
  const { pushToast } = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setWorkspace(await getSnapshotWorkspace(snapshotId));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "商品研判详情加载失败");
    } finally {
      setLoading(false);
    }
  }, [snapshotId]);

  useEffect(() => { void load(); }, [load]);

  const evidenceGroups = useMemo(() => {
    const seller = workspace?.evidence.filter((item) => item.contentOrigin === "seller_managed") || [];
    const ugc = workspace?.evidence.filter((item) => item.contentOrigin !== "seller_managed") || [];
    return { seller, ugc };
  }, [workspace]);

  const saveContext = async (context: {
    product_category: string | null;
    product_form: string | null;
    confirmed_ingredient_contexts: string[];
  }) => {
    if (!workspace) return;
    setSavingContext(true);
    try {
      await updateInspectionContext(workspace.snapshot.taskId, workspace.snapshot.productId, context);
      await load();
      pushToast("商品信息已保存，抽检辅助建议已重新评估", "success");
    } catch (reason) {
      pushToast(reason instanceof Error ? reason.message : "商品信息保存失败", "danger");
    } finally {
      setSavingContext(false);
    }
  };

  if (loading) return <div className="workspace-detail-state"><LoadingState label="正在读取商品研判详情" /></div>;
  if (error) return <div className="workspace-detail-state"><EmptyState icon={AlertCircle} title="商品详情加载失败" description={error} action={<button className="primary-button" type="button" onClick={() => void load()}>重试</button>} /></div>;
  if (!workspace) return null;
  const productUrl = safeHttpUrl(workspace.snapshot.productUrl);

  return (
    <article className="workspace-detail">
      <header className="workspace-detail-header">
        <p>商品研判详情</p>
        <h2>{workspace.snapshot.productName || workspace.snapshot.productId}</h2>
        <span>{workspace.snapshot.shopName || "店铺未记录"}</span>
      </header>
      <section className="detail-section product-facts">
        <h3><Info size={17} />商品信息</h3>
        <dl>
          <div><dt>商品 ID</dt><dd>{workspace.snapshot.productId}</dd></div>
          <div><dt>所属排查</dt><dd>{workspace.snapshot.taskDisplayName}</dd></div>
          <div><dt>Snapshot 采集时间</dt><dd>{formatDateTime(workspace.snapshot.collectedAt)}</dd></div>
          <div><dt>搜索页地区</dt><dd>{workspace.snapshot.region || "未记录"}</dd></div>
        </dl>
        {productUrl && <a className="text-link" href={productUrl} target="_blank" rel="noreferrer">打开保存的商品链接 <ExternalLink size={14} /></a>}
      </section>
      <section className="detail-section risk-direction-section">
        <h3><ShieldCheck size={17} />页面功效线索 / 可能风险方向</h3>
        {workspace.snapshot.detectedEffects.length > 0 && (
          <div className="risk-labels page-effect-labels">
            {workspace.snapshot.detectedEffects.map((effect) => <StatusBadge key={effect} tone="info">{effect}</StatusBadge>)}
          </div>
        )}
        {workspace.inspection.riskFindings.length ? workspace.inspection.riskFindings.map((finding) => (
          <div className="risk-summary" key={finding.risk_category}>
            <div className="risk-labels">{finding.risk_labels.map((label) => <StatusBadge key={label} tone="warning">{label}</StatusBadge>)}</div>
            <p>{finding.possible_risk_summary}</p>
          </div>
        )) : <p className="section-description">该次快照暂无可展示的已桥接风险方向。</p>}
      </section>
      <section className="detail-section evidence-section">
        <h3>页面证据</h3>
        {!workspace.evidence.length ? <div className="inline-message">该次快照没有保存结构化 Evidence。</div> : (
          <>
            <details open>
              <summary>商家管理内容 · 主要证据（{evidenceGroups.seller.length}）</summary>
              <div className="evidence-list">{evidenceGroups.seller.length ? evidenceGroups.seller.map((evidence) => <EvidenceCard key={evidence.evidenceId} evidence={evidence} assets={workspace.assets} runId={workspace.snapshot.taskId} />) : <p className="section-description">没有商家管理内容证据。</p>}</div>
            </details>
            {evidenceGroups.ugc.length > 0 && <details><summary>用户生成内容 · 辅助线索（{evidenceGroups.ugc.length}）</summary><div className="evidence-list">{evidenceGroups.ugc.map((evidence) => <EvidenceCard key={evidence.evidenceId} evidence={evidence} assets={workspace.assets} runId={workspace.snapshot.taskId} />)}</div></details>}
          </>
        )}
      </section>
      <RecommendationPanel inspection={workspace.inspection} />
      {needsProductContext(workspace.inspection) && <ProductContextForm context={workspace.inspection.context} saving={savingContext} onSave={saveContext} />}
      {workspace.snapshot.readiness.reviewEligible ? (
        <ReviewActions
          snapshotId={snapshotId}
          productId={workspace.snapshot.productId}
          review={workspace.review}
          sampling={workspace.sampling}
          addedFrom="inspection_workspace"
          weakEvidence={evidenceGroups.seller.length === 0 && evidenceGroups.ugc.length > 0}
          onChanged={async (change) => { await load(); await onChanged(change); }}
        />
      ) : (
        <section className="detail-section review-section">
          <h3>人工复核</h3>
          <div className="inline-message">该页面快照尚未完成线索分析，暂不可进行人工复核。</div>
        </section>
      )}
    </article>
  );
}
