import { ArrowRight, History } from "lucide-react";

import type { SnapshotSummary } from "../../api/contracts";
import { ProductThumbnail } from "../../components/ProductThumbnail";
import { StatusBadge } from "../../components/StatusBadge";
import { claimPresentation, claimSignalLabels } from "../../domain/claims";
import {
  formatDateTime,
  isProductRowActivationKey,
  productAnalysisPresentation,
} from "../../domain/product";
import { pageRegionClueValues } from "../../domain/productFacts";
import { reviewPresentation } from "../../domain/presentation";

type ProductTableProps = {
  products: SnapshotSummary[];
  selectedProductId?: string;
  onSelect: (productId: string) => void;
};

function SamplingCell({ product }: { product: SnapshotSummary }) {
  const { sampling } = product;
  const tone = sampling.inCurrentList
    ? "success"
    : sampling.decisionStatus === "reviewed_follow_up"
      ? "info"
      : "neutral";
  return (
    <div className="sampling-cell">
      <StatusBadge tone={tone}>
        {sampling.inCurrentList
          ? "当前清单中"
          : sampling.decisionStatus === "reviewed_follow_up"
            ? "已复核 / 当前未在"
            : sampling.decisionStatus === "no_further_action"
              ? "暂不纳入"
              : sampling.historicalCount > 0
                ? "曾纳入 / 当前未在"
                : "从未纳入"}
      </StatusBadge>
      {sampling.historicalCount > 0 && (
        <small>曾纳入 {sampling.historicalCount} 次</small>
      )}
    </div>
  );
}

export function ProductTable({
  products,
  selectedProductId,
  onSelect,
}: ProductTableProps) {
  return (
    <div className="product-table-scroll">
      <table className="product-table">
        <thead>
          <tr>
            <th>商品</th>
            <th>地区信息</th>
            <th>页面宣传线索</th>
            <th>人工复核</th>
            <th>抽检清单</th>
            <th>最近采集</th>
            <th>历史记录</th>
            <th><span className="sr-only">操作</span></th>
          </tr>
        </thead>
        <tbody>
          {products.map((product) => {
            const review = !product.readiness.reviewEligible && product.review.status === "pending"
              ? { label: "尚不可复核", tone: "neutral" as const }
              : reviewPresentation[product.review.status];
            const analysis = productAnalysisPresentation(product.status);
            const claims = claimPresentation(
              product.claimAnalysisStatus,
              product.claimSignalSummaries,
            );
            const claimLabels = claimSignalLabels(product.claimSignalSummaries);
            const selected = selectedProductId === product.productId;
            const pageRegionClues = pageRegionClueValues(
              [],
              product.productName,
              product.targetName || "",
            );
            const productRegionText = pageRegionClues.length > 0
              ? pageRegionClues.join("、")
              : "—";
            return (
              <tr
                key={product.productId}
                data-selected={selected}
                role="link"
                tabIndex={0}
                aria-label={`查看 ${product.productName || product.productId} 的详情`}
                onClick={(event) => {
                  const target = event.target as HTMLElement;
                  if (target.closest("a,button,input,select,textarea,[data-row-interactive]")) return;
                  onSelect(product.productId);
                }}
                onKeyDown={(event) => {
                  if (event.target !== event.currentTarget || !isProductRowActivationKey(event.key)) return;
                  event.preventDefault();
                  onSelect(product.productId);
                }}
              >
                <td className="product-name-cell">
                  <div className="product-identity">
                    <ProductThumbnail
                      src={product.thumbnailUrl}
                      alt={product.productName || `商品 ${product.productId}`}
                    />
                    <div>
                      <strong title={product.productName}>{product.productName || "未命名商品"}</strong>
                      <span>{product.shopName || "店铺未记录"}</span>
                      <small>ID {product.productId}</small>
                      <StatusBadge tone={analysis.tone}>{analysis.label}</StatusBadge>
                    </div>
                  </div>
                </td>
                <td>
                  <div className="region-cell">
                    <span><small>搜索页地区</small><strong>{product.region || "—"}</strong></span>
                    <span title={pageRegionClues.length > 0 ? "来自商品标题的页面地区线索，详情页可查看完整说明" : undefined}>
                      <small>产地/地区线索</small>
                      <strong>{productRegionText}</strong>
                    </span>
                  </div>
                </td>
                <td>
                  <div className="claim-summary-cell">
                    {claims.code === "with_claims" ? (
                      claimLabels.labels.map((label) => (
                        <StatusBadge key={label} tone="info">{label}</StatusBadge>
                      ))
                    ) : claims.code === "error" ? (
                      <StatusBadge tone="danger">{claims.label}</StatusBadge>
                    ) : (
                      <span className="muted-cell" data-state={claims.code}>
                        {claims.label}
                      </span>
                    )}
                    {claimLabels.remaining > 0 && (
                      <small>另有 {claimLabels.remaining} 类</small>
                    )}
                  </div>
                </td>
                <td><StatusBadge tone={review.tone}>{review.label}</StatusBadge></td>
                <td><SamplingCell product={product} /></td>
                <td><span className="cell-primary">{formatDateTime(product.collectedAt)}</span></td>
                <td>
                  <span className="history-count"><History size={14} />{product.snapshotCount} 次</span>
                </td>
                <td>
                  <span className="row-action" aria-hidden="true"><ArrowRight size={17} /></span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
