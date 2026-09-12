import { ClipboardCheck, FileSearch, Link2, ScanSearch } from "lucide-react";

import type { SnapshotWorkspace } from "../api/contracts";
import {
  productCluePresentation,
  type AnalysisStatePresentation,
} from "../domain/analysis";
import type { EvidencePartitions } from "../domain/evidence";
import { reviewPresentation } from "../domain/presentation";
import { formatDateTime } from "../domain/product";
import { ProductThumbnail } from "./ProductThumbnail";
import { StatusBadge } from "./StatusBadge";

type ProductSnapshotSummaryProps = {
  workspace: SnapshotWorkspace;
  analysis: AnalysisStatePresentation;
  partitions: EvidencePartitions;
};

export function ProductSnapshotSummary({
  workspace,
  analysis,
  partitions,
}: ProductSnapshotSummaryProps) {
  const sellerCount = partitions.seller.reduce((sum, group) => sum + group.recordCount, 0);
  const ugcCount = partitions.ugc.reduce((sum, group) => sum + group.recordCount, 0);
  const review = workspace.snapshot.readiness.reviewEligible
    ? reviewPresentation[workspace.review.status]
    : { label: "尚不可复核", tone: "neutral" as const };

  return (
    <section className="snapshot-summary">
      <div className="snapshot-summary-heading">
        <ProductThumbnail
          src={workspace.snapshot.thumbnailUrl}
          alt={workspace.snapshot.productName || "商品图片"}
          variant="summary"
        />
        <div className="snapshot-summary-identity">
          <h3>{workspace.snapshot.productName || "未命名商品"}</h3>
          <p>{workspace.snapshot.shopName || "店铺未记录"}</p>
          <small>本次快照采集于 {formatDateTime(workspace.snapshot.collectedAt)}</small>
        </div>
        <div className="snapshot-summary-statuses">
          <StatusBadge tone={analysis.tone}>{analysis.label}</StatusBadge>
          <StatusBadge tone={review.tone}>{review.label}</StatusBadge>
        </div>
      </div>
      <dl className="snapshot-summary-grid">
        <div>
          <dt><ScanSearch size={15} />页面线索</dt>
          <dd>{productCluePresentation(workspace.snapshot)}</dd>
        </div>
        <div>
          <dt><FileSearch size={15} />主要证据</dt>
          <dd>Seller {sellerCount} · UGC {ugcCount}</dd>
        </div>
        <div>
          <dt><Link2 size={15} />知识桥接</dt>
          <dd>{analysis.summary}</dd>
        </div>
        <div>
          <dt><ClipboardCheck size={15} />人工状态</dt>
          <dd>{review.label}</dd>
        </div>
      </dl>
    </section>
  );
}
