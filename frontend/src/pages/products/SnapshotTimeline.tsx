import { Clock3 } from "lucide-react";

import type { SnapshotSummary } from "../../api/contracts";
import { formatDateTime } from "../../domain/product";

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
