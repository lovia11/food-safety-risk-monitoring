import { Clock3 } from "lucide-react";

import type { SnapshotSummary } from "../../api/contracts";
import { formatDateTime, snapshotTimelineMode } from "../../domain/product";

type SnapshotTimelineProps = {
  snapshots: SnapshotSummary[];
  selectedSnapshotId: string;
  onSelect: (snapshotId: string) => void;
};

export function SnapshotTimeline({
  snapshots,
  selectedSnapshotId,
  onSelect,
}: SnapshotTimelineProps) {
  if (snapshotTimelineMode(snapshots.length) === "compact") {
    const snapshot = snapshots[0];
    return (
      <section className="snapshot-timeline snapshot-timeline-compact" aria-label="商品快照信息">
        <div className="section-label"><Clock3 size={15} />快照</div>
        <strong>{formatDateTime(snapshot?.collectedAt || null)}</strong>
        <span>共 1 次记录</span>
        {snapshot?.taskDisplayName && <small>{snapshot.taskDisplayName}</small>}
      </section>
    );
  }
  return (
    <section className="snapshot-timeline" aria-label="商品快照时间线">
      <div className="section-label"><Clock3 size={15} />Product Snapshot 时间线</div>
      <div className="timeline-list">
        {snapshots.map((snapshot, index) => (
          <button
            type="button"
            key={snapshot.snapshotId}
            data-active={snapshot.snapshotId === selectedSnapshotId}
            onClick={() => onSelect(snapshot.snapshotId)}
          >
            <span>{index === 0 ? "最新" : `历史 ${index}`}</span>
            <strong>{formatDateTime(snapshot.collectedAt)}</strong>
            <small>{snapshot.taskDisplayName}</small>
          </button>
        ))}
      </div>
    </section>
  );
}
