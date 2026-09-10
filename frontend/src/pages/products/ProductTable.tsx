import { ArrowRight, History } from "lucide-react";

import type { SnapshotSummary } from "../../api/contracts";
import { StatusBadge } from "../../components/StatusBadge";
import { formatDateTime, productAnalysisPresentation } from "../../domain/product";
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
            <th>页面功效线索</th>
            <th>人工复核</th>
            <th>抽检清单</th>
            <th>最近采集</th>
            <th>历史记录</th>
            <th><span className="sr-only">操作</span></th>
          </tr>
        </thead>
        <tbody>
          {products.map((product) => {
            const review = reviewPresentation[product.review.status];
            const analysis = productAnalysisPresentation(product.status);
            const selected = selectedProductId === product.productId;
            return (
              <tr key={product.productId} data-selected={selected}>
                <td className="product-name-cell">
                  <button type="button" onClick={() => onSelect(product.productId)}>
                    <strong title={product.productName}>{product.productName || "未命名商品"}</strong>
                    <span>{product.shopName || "店铺未记录"}</span>
                    <small>ID {product.productId}</small>
                    <StatusBadge tone={analysis.tone}>{analysis.label}</StatusBadge>
                  </button>
                </td>
                <td>
                  <div className="region-cell">
                    <span><small>搜索页地区</small>{product.region || "未记录"}</span>
                    <span><small>商品产地</small><em>待采集</em></span>
                  </div>
                </td>
                <td>
                  <div className="effect-list">
                    {product.detectedEffects.length ? (
                      product.detectedEffects.slice(0, 2).map((effect) => (
                        <StatusBadge key={effect} tone="warning">{effect}</StatusBadge>
                      ))
                    ) : (
                      <span className="muted-cell">暂无明确方向</span>
                    )}
                    {product.detectedEffects.length > 2 && (
                      <small>另有 {product.detectedEffects.length - 2} 项</small>
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
                  <button
                    type="button"
                    className="row-action"
                    onClick={() => onSelect(product.productId)}
                    aria-label={`查看 ${product.productName || product.productId} 的详情`}
                    title="查看详情"
                  >
                    <ArrowRight size={17} />
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
