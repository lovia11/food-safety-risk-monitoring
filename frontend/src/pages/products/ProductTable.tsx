import { ArrowRight, History } from "lucide-react";

import type { SnapshotSummary } from "../../api/contracts";
import { StatusBadge } from "../../components/StatusBadge";
import { formatDateTime } from "../../domain/product";
import { reviewPresentation } from "../../domain/presentation";

type ProductTableProps = {
  products: SnapshotSummary[];
  selectedProductId?: string;
  onSelect: (productId: string) => void;
};

function SamplingCell({ product }: { product: SnapshotSummary }) {
  const { sampling } = product;
  return (
    <div className="sampling-cell">
      <StatusBadge tone={sampling.inCurrentList ? "success" : "neutral"}>
        {sampling.inCurrentList
          ? "当前清单中"
          : sampling.historicalCount > 0
            ? "当前未纳入"
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
            <th>最近所属排查</th>
            <th>可能风险方向</th>
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
            const selected = selectedProductId === product.productId;
            return (
              <tr key={product.productId} data-selected={selected}>
                <td className="product-name-cell">
                  <button type="button" onClick={() => onSelect(product.productId)}>
                    <strong title={product.productName}>{product.productName || "未命名商品"}</strong>
                    <span>{product.shopName || "店铺未记录"}</span>
                    <small>ID {product.productId}</small>
                  </button>
                </td>
                <td>
                  <span className="cell-primary">{product.taskDisplayName}</span>
                  {product.targetName && <small>{product.targetName}</small>}
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
