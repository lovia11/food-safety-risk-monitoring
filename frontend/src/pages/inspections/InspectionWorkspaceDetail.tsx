import { AlertCircle, ExternalLink, Info } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import type { SnapshotWorkspace } from "../../api/contracts";
import { getSnapshotWorkspace, updateInspectionContext } from "../../api/products";
import { EmptyState } from "../../components/EmptyState";
import { ClaimAnalysisSection } from "../../components/ClaimAnalysisSection";
import { ClaimConsistencySection } from "../../components/ClaimConsistencySection";
import { DeclaredOriginFact } from "../../components/DeclaredOriginFact";
import { EvidenceReviewSection } from "../../components/EvidenceReviewSection";
import { LoadingState } from "../../components/LoadingState";
import { HealthFoodIdentitySection } from "../../components/HealthFoodIdentitySection";
import { ProductContextForm } from "../../components/ProductContextForm";
import { ProductSnapshotSummary } from "../../components/ProductSnapshotSummary";
import { RecommendationPanel } from "../../components/RecommendationPanel";
import { ReviewActions } from "../../components/ReviewActions";
import { useToast } from "../../components/ToastProvider";
import { analysisStatePresentation } from "../../domain/analysis";
import { groupEvidence, partitionEvidenceGroups } from "../../domain/evidence";
import { formatDateTime, safeHttpUrl } from "../../domain/product";
import { needsProductContext } from "../../domain/recommendation";
import {
  healthFoodIdentityAnchorId,
  healthFoodOfficialSourceControlId,
} from "../../domain/healthFoodIdentity";

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

  const evidencePartitions = useMemo(() => {
    return partitionEvidenceGroups(groupEvidence(workspace?.evidence || []));
  }, [workspace]);
  const analysis = useMemo(() => workspace ? analysisStatePresentation({
    readiness: workspace.snapshot.readiness,
    evidence: workspace.evidence,
    inspection: workspace.inspection,
  }) : null, [workspace]);

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
  if (!analysis) return null;
  const productUrl = safeHttpUrl(workspace.snapshot.productUrl);

  return (
    <article className="workspace-detail">
      <header className="workspace-detail-header">
        <p>商品研判详情</p>
        <h2>{workspace.snapshot.productName || workspace.snapshot.productId}</h2>
        <span>{workspace.snapshot.shopName || "店铺未记录"}</span>
      </header>
      <ProductSnapshotSummary
        workspace={workspace}
        analysis={analysis}
        partitions={evidencePartitions}
      />
      <section className="detail-section product-facts">
        <h3><Info size={17} />商品信息</h3>
        <dl>
          <div><dt>商品 ID</dt><dd>{workspace.snapshot.productId}</dd></div>
          <div><dt>所属排查</dt><dd>{workspace.snapshot.taskDisplayName}</dd></div>
          <div><dt>Snapshot 采集时间</dt><dd>{formatDateTime(workspace.snapshot.collectedAt)}</dd></div>
          <div><dt>搜索页地区</dt><dd>{workspace.snapshot.region || "—"}</dd></div>
          <div>
            <dt>商品标称产地</dt>
            <dd>
              <DeclaredOriginFact
                origin={workspace.declaredOrigin}
                assets={workspace.assets}
                runId={workspace.snapshot.taskId}
                productId={workspace.snapshot.productId}
              />
            </dd>
          </div>
        </dl>
        {productUrl && <a className="text-link" href={productUrl} target="_blank" rel="noreferrer">打开保存的商品链接 <ExternalLink size={14} /></a>}
      </section>
      <HealthFoodIdentitySection
        identity={workspace.healthFoodIdentity}
        assets={workspace.assets}
        runId={workspace.snapshot.taskId}
        productId={workspace.snapshot.productId}
        snapshotId={workspace.snapshot.snapshotId}
      />
      <EvidenceReviewSection
        evidence={workspace.evidence}
        assets={workspace.assets}
        runId={workspace.snapshot.taskId}
      />
      <ClaimAnalysisSection
        status={workspace.claimAnalysisStatus}
        signals={workspace.claimSignals}
        mentions={workspace.claimMentions}
        evidence={workspace.evidence}
      />
      <ClaimConsistencySection
        status={workspace.claimConsistencyStatus}
        assessment={workspace.claimConsistency}
        claimSignals={workspace.claimSignals}
        claimMentions={workspace.claimMentions}
        evidence={workspace.evidence}
        identityAnchorId={healthFoodIdentityAnchorId(workspace.snapshot.snapshotId)}
        officialSourceControlId={healthFoodOfficialSourceControlId(workspace.snapshot.snapshotId)}
        officialSourceAvailable={Boolean(
          workspace.healthFoodIdentity.registryRecord?.sourceReference
          || workspace.healthFoodIdentity.registryRecord?.rawArtifactPath,
        )}
      />
      <RecommendationPanel inspection={workspace.inspection} analysis={analysis} />
      {needsProductContext(workspace.inspection) && <ProductContextForm context={workspace.inspection.context} saving={savingContext} onSave={saveContext} />}
      {workspace.snapshot.readiness.reviewEligible ? (
        <ReviewActions
          snapshotId={snapshotId}
          productId={workspace.snapshot.productId}
          review={workspace.review}
          sampling={workspace.sampling}
          addedFrom="inspection_workspace"
          weakEvidence={evidencePartitions.seller.length === 0 && evidencePartitions.ugc.length > 0}
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
