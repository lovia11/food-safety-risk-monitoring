"""Shared, read-only contracts for pipeline readiness and task flow projection.

The run directory remains the artifact source of truth.  The SQLite index stores
the fields required to project the same readiness semantics without adding a
second persistent state machine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


DETAIL_REACHED_STATUSES = {
    "detail_collected",
    "processing_ocr_analysis",
    "failed_processing",
    "success",
}
TERMINAL_TASK_STAGES = {
    "collection_completed",
    "completed",
    "completed_with_errors",
    "interrupted",
    "failed",
}
FLOW_STATES = {"future", "active", "done", "partial", "failed"}


@dataclass(frozen=True)
class PipelineReadiness:
    detail_collected: bool
    ocr_input_ready: bool
    ocr_ready: bool
    analysis_ready: bool
    review_eligible: bool
    reason: str

    def to_api(self) -> dict[str, Any]:
        return {
            "detailCollected": self.detail_collected,
            "ocrInputReady": self.ocr_input_ready,
            "ocrReady": self.ocr_ready,
            "analysisReady": self.analysis_ready,
            "reviewEligible": self.review_eligible,
            "reason": self.reason,
        }


def evaluate_pipeline_readiness(
    *,
    status: str,
    meta_path: str | None,
    analysis_path: str | None,
    original_image_count: int,
    ocr_image_count: int,
) -> PipelineReadiness:
    """Evaluate the sole backend readiness predicate from indexed artifacts."""

    normalized_status = str(status or "")
    detail_collected = (
        normalized_status in DETAIL_REACHED_STATUSES and bool(meta_path)
    )
    ocr_input_ready = detail_collected and int(original_image_count or 0) > 0
    ocr_ready = ocr_input_ready and int(ocr_image_count or 0) > 0
    analysis_ready = (
        normalized_status == "success" and ocr_ready and bool(analysis_path)
    )
    if analysis_ready:
        reason = "eligible"
    elif not detail_collected:
        reason = "detail_not_collected"
    elif not ocr_input_ready:
        reason = "ocr_input_missing"
    elif not ocr_ready:
        reason = "ocr_not_ready"
    else:
        reason = "analysis_not_ready"
    return PipelineReadiness(
        detail_collected=detail_collected,
        ocr_input_ready=ocr_input_ready,
        ocr_ready=ocr_ready,
        analysis_ready=analysis_ready,
        review_eligible=analysis_ready,
        reason=reason,
    )


def review_eligibility_sql(alias: str = "s") -> str:
    """Return the SQL equivalent of :func:`evaluate_pipeline_readiness`."""

    prefix = f"{alias}." if alias else ""
    return (
        f"({prefix}status = 'success' "
        f"AND NULLIF(TRIM({prefix}meta_path), '') IS NOT NULL "
        f"AND NULLIF(TRIM({prefix}analysis_path), '') IS NOT NULL "
        f"AND {prefix}original_image_count > 0 "
        f"AND {prefix}ocr_image_count > 0)"
    )


def project_task_flow(
    stage: str,
    active: bool,
    summary: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Project the four existing UI steps from real aggregate outcomes."""

    terminal = stage in TERMINAL_TASK_STAGES
    candidates = int(summary.get("searchCandidates") or 0)
    detail_completed = int(summary.get("detailCompleted") or 0)
    detail_target = int(summary.get("detailTarget") or 0)
    detail_failed = int(summary.get("detailFailed") or 0)
    analysis_completed = int(summary.get("analysisCompleted") or 0)
    analysis_target = int(summary.get("analysisTarget") or 0)
    analysis_failed = int(summary.get("analysisFailed") or 0)
    pending_review = int(summary.get("pendingReview") or 0)
    completed_review = int(summary.get("completedReview") or 0)

    if candidates > 0:
        search_state = "done"
    elif terminal:
        search_state = "failed"
    elif active or stage in {"initializing", "searching"}:
        search_state = "active"
    else:
        search_state = "future"

    if detail_target <= 0:
        detail_state = "future"
    elif detail_completed >= detail_target:
        detail_state = "done"
    elif active and stage in {
        "collecting_details",
        "manual_action_required",
        "waiting_for_manual_action",
    }:
        detail_state = "active"
    elif detail_failed > 0:
        detail_state = "partial" if detail_completed > 0 else "failed"
    elif detail_completed > 0:
        detail_state = "partial"
    else:
        detail_state = "future"

    if analysis_target <= 0:
        analysis_state = "future"
    elif analysis_completed >= analysis_target:
        analysis_state = "done"
    elif active and stage == "processing_ocr_analysis":
        analysis_state = "active"
    elif analysis_failed > 0:
        analysis_state = "partial" if analysis_completed > 0 else "failed"
    elif analysis_completed > 0:
        analysis_state = "partial"
    else:
        analysis_state = "future"

    review_total = pending_review + completed_review
    if review_total <= 0:
        review_state = "future"
    elif pending_review > 0:
        review_state = "active"
    else:
        review_state = "done"

    steps = [
        ("search", "搜索商品", search_state, candidates, candidates),
        (
            "detail",
            "采集详情",
            detail_state,
            detail_completed,
            detail_target,
        ),
        (
            "analysis",
            "线索识别",
            analysis_state,
            analysis_completed,
            analysis_target,
        ),
        (
            "review",
            "人工复核",
            review_state,
            completed_review,
            review_total,
        ),
    ]
    assert all(item[2] in FLOW_STATES for item in steps)
    return [
        {
            "key": key,
            "label": label,
            "state": state,
            "completed": completed,
            "target": target,
        }
        for key, label, state, completed, target in steps
    ]
