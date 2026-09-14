import { ExternalLink, Eye, Trash2 } from "lucide-react";

import type { SamplingItem } from "../../api/contracts";
import { claimPresentation, claimSignalLabels } from "../../domain/claims";
import { formatDateTime, safeHttpUrl } from "../../domain/product";
import {
  samplingMethodLabel,
  suggestedSamplingMethods,
} from "../../domain/sampling";
import { StatusBadge } from "../../components/StatusBadge";

type SamplingListTableProps = {
  items: SamplingItem[];
  selectedProductId?: string;
  readOnly?: boolean;
  onSelect: (item: SamplingItem) => void;
  onRemove?: (productId: string) => void;
};

function textList(values: string[], empty: string) {
  return values.length ? values.join("、") : empty;
}

export function SamplingListTable({
  items,
  selectedProductId,
  readOnly = false,
  onSelect,
  onRemove,
}: SamplingListTableProps) {
  return (
    <div className="sampling-table-scroll">
      <table className="sampling-table">
        <caption className="sr-only">
          {readOnly ? "历史抽检辅助清单" : "当前抽检辅助清单"}
        </caption>
        <thead>
          <tr>
            <th scope="col">商品</th>
            <th scope="col">商品链接</th>
            <th scope="col">来源排查</th>
            <th scope="col">{readOnly ? "旧版冻结分析结果" : "页面宣传线索"}</th>
            <th scope="col">可能风险方向</th>
            <th scope="col">建议关注/检测成分</th>
            <th scope="col">建议参考方法/标准</th>
            <th scope="col">加入时间</th>
            <th scope="col">历史曾纳入</th>
            <th scope="col">操作</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const productUrl = safeHttpUrl(item.productUrl);
            const suggestedMethods = suggestedSamplingMethods(item);
            const claims = claimPresentation(
              item.claimAnalysisStatus || "not_generated",
              item.claimSignals || [],
            );
            const claimLabels = claimSignalLabels(item.claimSignals || []);
            const currentClaimText = claims.code === "with_claims"
              ? `${claimLabels.labels.join("、")}${claimLabels.remaining ? ` +${claimLabels.remaining}` : ""}`
              : claims.label;
            return (
              <tr
                key={`${item.ordinal}-${item.productId}`}
                data-selected={selectedProductId === item.productId}
              >
                <td>
                  <button
                    type="button"
                    className="sampling-product-button"
                    onClick={() => onSelect(item)}
                  >
                    <strong>{item.productName || item.productId}</strong>
                    <span>{item.shopName || "店铺未记录"}</span>
                    <small>ID {item.productId}</small>
                  </button>
                </td>
                <td>
                  {productUrl ? (
                    <a
                      className="table-link"
                      href={productUrl}
                      target="_blank"
                      rel="noreferrer"
                    >
                      打开保存链接 <ExternalLink size={13} />
                    </a>
                  ) : (
                    <span className="table-empty">无可用链接</span>
                  )}
                </td>
                <td>
                  <strong className="table-primary-text">
                    {item.sourceTaskDisplayName || item.sourceTaskId}
                  </strong>
                  <small className="table-secondary-text">
                    采集记录 ID {item.sourceSnapshotId}
                  </small>
                </td>
                <td>
                  {!readOnly && claims.code === "error" ? (
                    <StatusBadge tone="danger">{currentClaimText}</StatusBadge>
                  ) : (
                    <span className="clamped-cell" data-claim-state={readOnly ? "legacy" : claims.code}>
                      {readOnly
                        ? textList(item.summary.pageEffectClues, "未记录旧版分析结果")
                        : currentClaimText}
                    </span>
                  )}
                </td>
                <td>
                  <span className="clamped-cell">
                    {textList(item.summary.riskDirections, "暂无已核验映射")}
                  </span>
                </td>
                <td>
                  <span className="clamped-cell">
                    {textList(item.summary.substances, "暂无已核验成分建议")}
                  </span>
                </td>
                <td>
                  <span className="clamped-cell">
                    {suggestedMethods.length
                      ? suggestedMethods.map(samplingMethodLabel).join("、")
                      : "暂无建议参考方法"}
                  </span>
                </td>
                <td>{formatDateTime(item.addedAt)}</td>
                <td>
                  {item.historicalCountBeforeExport > 0 ? (
                    <StatusBadge tone="info">
                      是 · {item.historicalCountBeforeExport} 次
                    </StatusBadge>
                  ) : (
                    <StatusBadge>否</StatusBadge>
                  )}
                </td>
                <td>
                  <div className="sampling-row-actions">
                    <button
                      type="button"
                      className="row-action"
                      onClick={() => onSelect(item)}
                    >
                      <Eye size={14} />详情
                    </button>
                    {!readOnly && onRemove && (
                      <button
                        type="button"
                        className="danger-button compact-button"
                        onClick={() => onRemove(item.productId)}
                      >
                        <Trash2 size={14} />移出
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
