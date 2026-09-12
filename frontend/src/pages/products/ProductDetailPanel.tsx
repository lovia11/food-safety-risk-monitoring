import {
  AlertCircle,
  ExternalLink,
  Info,
  PackageOpen,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import type {
  SnapshotSummary,
  SnapshotWorkspace,
} from "../../api/contracts";
import {
  getProductSnapshots,
  getSnapshotWorkspace,
  updateInspectionContext,
} from "../../api/products";
import { Drawer } from "../../components/Drawer";
import { DeclaredOriginFact } from "../../components/DeclaredOriginFact";
import { EmptyState } from "../../components/EmptyState";
import { EvidenceReviewSection } from "../../components/EvidenceReviewSection";
import { LoadingState } from "../../components/LoadingState";
import { ProductContextForm } from "../../components/ProductContextForm";
import { ProductSnapshotSummary } from "../../components/ProductSnapshotSummary";
import { RecommendationPanel } from "../../components/RecommendationPanel";
import { ReviewActions } from "../../components/ReviewActions";
import { StatusBadge } from "../../components/StatusBadge";
import { useToast } from "../../components/ToastProvider";
import { analysisStatePresentation } from "../../domain/analysis";
import { groupEvidence, partitionEvidenceGroups } from "../../domain/evidence";
import { formatDateTime, safeHttpUrl } from "../../domain/product";
import { needsProductContext } from "../../domain/recommendation";
import { SnapshotTimeline } from "./SnapshotTimeline";

type ProductDetailPanelProps = {
  productId: string;
  onClose: () => void;
  onProductChanged: () => void;
};

export function ProductDetailPanel({
  productId,
  onClose,
  onProductChanged,
}: ProductDetailPanelProps) {
  const [snapshots, setSnapshots] = useState<SnapshotSummary[]>([]);
  const [selectedSnapshotId, setSelectedSnapshotId] = useState("");
  const [workspace, setWorkspace] = useState<SnapshotWorkspace | null>(null);
  const [snapshotError, setSnapshotError] = useState("");
  const [workspaceError, setWorkspaceError] = useState("");
  const [loadingSnapshots, setLoadingSnapshots] = useState(true);
  const [loadingWorkspace, setLoadingWorkspace] = useState(false);
  const [savingContext, setSavingContext] = useState(false);
  const { pushToast } = useToast();

  useEffect(() => {
    const controller = new AbortController();
    setLoadingSnapshots(true);
    setSnapshotError("");
    setSnapshots([]);
    setWorkspace(null);
    getProductSnapshots(productId, controller.signal)
      .then((items) => {
        setSnapshots(items);
        setSelectedSnapshotId(items[0]?.snapshotId || "");
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setSnapshotError(reason instanceof Error ? reason.message : "快照加载失败");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingSnapshots(false);
      });
    return () => controller.abort();
  }, [productId]);

  const loadWorkspace = useCallback(async (snapshotId: string) => {
    setLoadingWorkspace(true);
    setWorkspaceError("");
    try {
      const result = await getSnapshotWorkspace(snapshotId);
      setWorkspace(result);
    } catch (reason) {
      setWorkspaceError(reason instanceof Error ? reason.message : "详情加载失败");
    } finally {
      setLoadingWorkspace(false);
    }
  }, []);

  useEffect(() => {
    if (!selectedSnapshotId) return;
    const controller = new AbortController();
    setLoadingWorkspace(true);
    setWorkspaceError("");
    getSnapshotWorkspace(selectedSnapshotId, controller.signal)
      .then(setWorkspace)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setWorkspaceError(reason instanceof Error ? reason.message : "详情加载失败");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingWorkspace(false);
      });
    return () => controller.abort();
  }, [selectedSnapshotId]);

  const evidencePartitions = useMemo(() => {
    return partitionEvidenceGroups(groupEvidence(workspace?.evidence || []));
  }, [workspace]);
  const analysis = useMemo(() => workspace ? analysisStatePresentation({
    readiness: workspace.snapshot.readiness,
    evidence: workspace.evidence,
    detectedEffects: workspace.snapshot.detectedEffects,
    inspection: workspace.inspection,
  }) : null, [workspace]);

  const handleContextSave = async (context: {
    product_category: string | null;
    product_form: string | null;
    confirmed_ingredient_contexts: string[];
  }) => {
    if (!workspace || !selectedSnapshotId) return;
    setSavingContext(true);
    try {
      await updateInspectionContext(
        workspace.snapshot.taskId,
        workspace.snapshot.productId,
        context,
      );
      await loadWorkspace(selectedSnapshotId);
      pushToast("商品信息已保存，抽检辅助建议已重新评估", "success");
    } catch (reason) {
      pushToast(
        reason instanceof Error ? reason.message : "商品信息保存失败",
        "danger",
      );
    } finally {
      setSavingContext(false);
    }
  };

  const selectedSummary = snapshots.find(
    (item) => item.snapshotId === selectedSnapshotId,
  );
  const title = workspace?.snapshot.productName || selectedSummary?.productName || productId;
  const productUrl = safeHttpUrl(workspace?.snapshot.productUrl);

  return (
    <Drawer
      title={title}
      subtitle={workspace ? `${workspace.snapshot.shopName || "店铺未记录"} · ${workspace.snapshot.snapshotCount} 次快照` : undefined}
      onClose={onClose}
    >
      {loadingSnapshots ? (
        <LoadingState label="正在加载商品快照" />
      ) : snapshotError ? (
        <div className="inline-message" data-tone="danger">
          <AlertCircle size={17} /> {snapshotError}
        </div>
      ) : snapshots.length === 0 ? (
        <EmptyState
          icon={PackageOpen}
          title="没有可用快照"
          description="该商品当前没有已索引的 Product Snapshot。"
        />
      ) : (
        <>
          {workspace && analysis && (
            <ProductSnapshotSummary
              workspace={workspace}
              analysis={analysis}
              partitions={evidencePartitions}
            />
          )}
          <SnapshotTimeline
            snapshots={snapshots}
            selectedSnapshotId={selectedSnapshotId}
            onSelect={setSelectedSnapshotId}
          />
          {loadingWorkspace ? (
            <LoadingState label="正在读取所选快照" />
          ) : workspaceError ? (
            <div className="inline-message" data-tone="danger">
              <AlertCircle size={17} />
              <span>{workspaceError}</span>
              <button type="button" onClick={() => loadWorkspace(selectedSnapshotId)}>
                重试
              </button>
            </div>
          ) : workspace ? (
            <>
              <section className="detail-section product-facts">
                <h3><Info size={17} />商品信息</h3>
                <dl>
                  <div><dt>商品 ID</dt><dd>{workspace.snapshot.productId}</dd></div>
                  <div><dt>所属排查</dt><dd>{workspace.snapshot.taskDisplayName}</dd></div>
                  <div><dt>采集时间</dt><dd>{formatDateTime(workspace.snapshot.collectedAt)}</dd></div>
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
                  <div>
                    <dt>抽检清单</dt>
                    <dd>
                      <StatusBadge tone={workspace.sampling.inCurrentList ? "success" : "neutral"}>
                        {workspace.sampling.inCurrentList ? "当前清单中" : "当前未纳入"}
                      </StatusBadge>
                      {workspace.sampling.historicalCount > 0 && ` · 曾纳入 ${workspace.sampling.historicalCount} 次`}
                    </dd>
                  </div>
                </dl>
                {productUrl && (
                  <a
                    className="text-link"
                    href={productUrl}
                    target="_blank"
                    rel="noreferrer"
                  >
                    打开保存的商品链接 <ExternalLink size={14} />
                  </a>
                )}
              </section>
              <EvidenceReviewSection
                evidence={workspace.evidence}
                assets={workspace.assets}
                runId={workspace.snapshot.taskId}
              />

              {analysis && <RecommendationPanel inspection={workspace.inspection} analysis={analysis} />}
              {needsProductContext(workspace.inspection) && (
                <ProductContextForm
                  context={workspace.inspection.context}
                  saving={savingContext}
                  onSave={handleContextSave}
                />
              )}
              {workspace.snapshot.readiness.reviewEligible ? (
                <ReviewActions
                  snapshotId={selectedSnapshotId}
                  productId={workspace.snapshot.productId}
                  review={workspace.review}
                  sampling={workspace.sampling}
                  addedFrom="product_overview"
                  weakEvidence={evidencePartitions.seller.length === 0 && evidencePartitions.ugc.length > 0}
                  onChanged={async () => {
                    await loadWorkspace(selectedSnapshotId);
                    onProductChanged();
                  }}
                />
              ) : (
                <section className="detail-section review-section">
                  <h3>人工复核</h3>
                  <div className="inline-message">该页面快照尚未完成线索分析，暂不可进行人工复核。</div>
                </section>
              )}
            </>
          ) : null}
        </>
      )}
    </Drawer>
  );
}
