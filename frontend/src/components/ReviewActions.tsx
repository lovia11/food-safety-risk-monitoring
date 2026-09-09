import { Check, ListPlus, RotateCcw, Save, Trash2, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";

import type { Review, SamplingStatus } from "../api/contracts";
import {
  addSamplingItem,
  removeSamplingItem,
  saveReviewDecision,
} from "../api/products";
import { useAppState } from "../app/AppState";
import { reviewPresentation } from "../domain/presentation";
import { StatusBadge } from "./StatusBadge";
import { useToast } from "./ToastProvider";

type ReviewActionsProps = {
  snapshotId: string;
  productId: string;
  review: Review;
  sampling: SamplingStatus;
  addedFrom: "product_overview" | "inspection_workspace";
  weakEvidence: boolean;
  onChanged: (change?: {
    type: "decision" | "membership_removed" | "membership_restored";
    decision?: "recommend_follow_up" | "no_further_action";
  }) => Promise<void>;
};

export function ReviewActions({
  snapshotId,
  productId,
  review,
  sampling,
  addedFrom,
  weakEvidence,
  onChanged,
}: ReviewActionsProps) {
  const [note, setNote] = useState(review.note);
  const [saving, setSaving] = useState(false);
  const [confirmWeakEvidence, setConfirmWeakEvidence] = useState(false);
  const { refreshSamplingCount } = useAppState();
  const { pushToast } = useToast();

  useEffect(() => {
    setNote(review.note);
    setConfirmWeakEvidence(false);
  }, [review, snapshotId]);

  const refresh = async (change?: Parameters<ReviewActionsProps["onChanged"]>[0]) => {
    await Promise.all([refreshSamplingCount(), onChanged(change)]);
  };

  const decide = async (
    decision: "recommend_follow_up" | "no_further_action",
  ) => {
    if (decision === "recommend_follow_up" && weakEvidence && !confirmWeakEvidence) {
      setConfirmWeakEvidence(true);
      return;
    }
    setSaving(true);
    try {
      await saveReviewDecision(snapshotId, decision, addedFrom, note);
      await refresh({ type: "decision", decision });
      pushToast(
        decision === "recommend_follow_up"
          ? "已完成复核并加入当前抽检清单"
          : "已记录暂不纳入",
        "success",
      );
    } catch (reason) {
      pushToast(reason instanceof Error ? reason.message : "人工决策保存失败", "danger");
    } finally {
      setSaving(false);
      setConfirmWeakEvidence(false);
    }
  };

  const remove = async () => {
    setSaving(true);
    try {
      const removed = await removeSamplingItem(productId);
      await refresh({ type: "membership_removed" });
      pushToast("已移出当前抽检清单，人工复核结论仍为建议跟进", "info", {
        label: "撤销",
        run: async () => {
          try {
            await addSamplingItem(removed.productId, removed.sourceSnapshotId, removed.addedFrom);
            await refresh({ type: "membership_restored" });
            pushToast("已恢复到当前抽检清单", "success");
          } catch (reason) {
            pushToast(reason instanceof Error ? reason.message : "恢复失败", "danger");
          }
        },
      });
    } catch (reason) {
      pushToast(reason instanceof Error ? reason.message : "移出清单失败", "danger");
    } finally {
      setSaving(false);
    }
  };

  const presentation = reviewPresentation[review.status];
  return (
    <section className="detail-section review-section">
      <div className="review-heading">
        <h3>人工复核与抽检清单</h3>
        <StatusBadge tone={sampling.inCurrentList ? "success" : presentation.tone}>
          {sampling.inCurrentList
            ? "已纳入当前清单"
            : sampling.decisionStatus === "reviewed_follow_up"
              ? "已复核 / 建议跟进"
              : presentation.label}
        </StatusBadge>
      </div>

      {sampling.decisionStatus === "reviewed_follow_up" && (
        <div className="inline-message">
          <Check size={17} /> 已完成复核并建议跟进，当前未在抽检清单中。
        </div>
      )}
      <label className="review-note-field">
        人工备注（可选）
        <textarea
          value={note}
          onChange={(event) => setNote(event.target.value)}
          maxLength={2000}
          rows={3}
          placeholder="记录页面语境、判断依据或后续处理说明"
        />
        <small>{note.length}/2000</small>
      </label>

      {confirmWeakEvidence && (
        <div className="weak-evidence-confirm" role="alert">
          <TriangleAlert size={18} />
          <div>
            <strong>当前仅有用户生成内容辅助线索</strong>
            <p>这不会自动形成正式检测建议。确认后仍可基于人工判断加入清单。</p>
          </div>
          <button type="button" onClick={() => void decide("recommend_follow_up")}>
            确认加入
          </button>
          <button type="button" onClick={() => setConfirmWeakEvidence(false)}>
            取消
          </button>
        </div>
      )}

      <div className="review-decision-actions">
        {sampling.inCurrentList ? (
          <>
            <span className="current-membership-label"><Check size={16} />已在当前抽检清单</span>
            <button type="button" className="danger-button" disabled={saving} onClick={() => void remove()}>
              <Trash2 size={15} /> 移出当前清单
            </button>
          </>
        ) : (
          <>
            <button
              type="button"
              className="secondary-button"
              disabled={saving}
              onClick={() => void decide("no_further_action")}
            >
              <Save size={15} /> 暂不纳入
            </button>
            <button
              type="button"
              className="primary-button"
              disabled={saving}
              onClick={() => void decide("recommend_follow_up")}
            >
              {sampling.decisionStatus === "reviewed_follow_up" ? <RotateCcw size={15} /> : <ListPlus size={15} />}
              {sampling.decisionStatus === "reviewed_follow_up" ? "重新加入抽检清单" : "加入抽检清单"}
            </button>
          </>
        )}
      </div>
    </section>
  );
}
