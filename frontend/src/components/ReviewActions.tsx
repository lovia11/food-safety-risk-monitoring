import { Save } from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";

import type { Review, ReviewStatus } from "../api/contracts";
import { reviewPresentation } from "../domain/presentation";
import { StatusBadge } from "./StatusBadge";

type ReviewActionsProps = {
  review: Review;
  saving: boolean;
  onSave: (status: ReviewStatus, note: string) => Promise<void>;
};

export function ReviewActions({ review, saving, onSave }: ReviewActionsProps) {
  const [status, setStatus] = useState(review.status);
  const [note, setNote] = useState(review.note);

  useEffect(() => {
    setStatus(review.status);
    setNote(review.note);
  }, [review]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    await onSave(status, note);
  };

  return (
    <section className="detail-section review-section">
      <div className="review-heading">
        <h3>人工复核</h3>
        <StatusBadge tone={reviewPresentation[review.status].tone}>
          {reviewPresentation[review.status].label}
        </StatusBadge>
      </div>
      <p className="section-description">
        Phase 1 仅保存既有 Review；加入抽检清单等完整人工决策将在 Phase 2 实现。
      </p>
      <form className="review-form" onSubmit={submit}>
        <label>
          复核结论
          <select
            value={status}
            onChange={(event) => setStatus(event.target.value as ReviewStatus)}
          >
            {Object.entries(reviewPresentation).map(([value, item]) => (
              <option key={value} value={value}>{item.label}</option>
            ))}
          </select>
        </label>
        <label>
          人工备注
          <textarea
            value={note}
            onChange={(event) => setNote(event.target.value)}
            maxLength={2000}
            rows={3}
            placeholder="记录需要复核的页面语境或后续处理说明"
          />
        </label>
        <div className="form-footer">
          <span>{note.length}/2000</span>
          <button type="submit" className="primary-button" disabled={saving}>
            <Save size={15} /> {saving ? "正在保存" : "保存复核"}
          </button>
        </div>
      </form>
    </section>
  );
}
