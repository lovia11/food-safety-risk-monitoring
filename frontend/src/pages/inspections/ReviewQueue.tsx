import { CheckCircle2, FileText, ListChecks, MessageSquareText } from "lucide-react";

import type { SnapshotSummary } from "../../api/contracts";
import { StatusBadge } from "../../components/StatusBadge";
import { queueFilters, queueMatches, type QueueFilter } from "../../domain/reviewQueue";

export type { QueueFilter } from "../../domain/reviewQueue";

const queuePresentation = {
  pending: { label: "待复核", tone: "warning" },
  current: { label: "已纳入当前清单", tone: "success" },
  reviewed_follow_up: { label: "已复核 / 当前未在清单", tone: "info" },
  no_further_action: { label: "暂不纳入", tone: "neutral" },
} as const;

type ReviewQueueProps = {
  products: SnapshotSummary[];
  selectedSnapshotId: string;
  filter: QueueFilter;
  onFilterChange: (filter: QueueFilter) => void;
  onSelect: (snapshotId: string) => void;
  pendingCompleted: boolean;
};

export function ReviewQueue({
  products,
  selectedSnapshotId,
  filter,
  onFilterChange,
  onSelect,
  pendingCompleted,
}: ReviewQueueProps) {
  const filtered = products.filter((item) => queueMatches(item, filter));
  return (
    <aside className="review-queue" aria-label="商品复核队列">
      <div className="queue-header">
        <div>
          <p>商品队列</p>
          <strong>{products.length} 件商品快照</strong>
        </div>
        <ListChecks size={18} />
      </div>
      <label className="queue-filter">
        <span>队列筛选</span>
        <select value={filter} onChange={(event) => onFilterChange(event.target.value as QueueFilter)}>
          {queueFilters.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
        </select>
      </label>
      {pendingCompleted && (
        <div className="queue-complete" role="status">
          <CheckCircle2 size={17} /> 本批次待复核已完成
        </div>
      )}
      <div className="queue-list">
        {filtered.length ? filtered.map((item) => {
          const state = queuePresentation[item.sampling.decisionStatus];
          const evidence = item.representativeEvidence;
          return (
            <button
              type="button"
              className="queue-card"
              key={item.snapshotId}
              data-selected={item.snapshotId === selectedSnapshotId}
              onClick={() => onSelect(item.snapshotId)}
            >
              <span className="queue-card-heading">
                <strong title={item.productName}>{item.productName || item.productId}</strong>
                <StatusBadge tone={state.tone}>{state.label}</StatusBadge>
              </span>
              <span className="queue-effects">
                {item.detectedEffects.length ? item.detectedEffects.slice(0, 3).join("、") : "暂无页面功效线索"}
              </span>
              <span className="queue-evidence">
                <MessageSquareText size={14} />
                {evidence?.text || "暂无可展示的代表性证据原文"}
              </span>
              <span className="queue-source-counts">
                <FileText size={13} /> 商家内容 {item.counts.sellerManagedEvidence} · 用户内容 {item.counts.ugcEvidence}
              </span>
            </button>
          );
        }) : (
          <div className="queue-empty">该筛选下没有商品。</div>
        )}
      </div>
    </aside>
  );
}
