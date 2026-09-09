"""Application service coordinating one atomic human review decision."""

from __future__ import annotations

from typing import Any

from src.data_store import DataStore, SnapshotNotFoundError
from src.sampling_store import (
    ADDED_FROM_VALUES,
    SamplingSnapshotNotFoundError,
    SamplingStore,
    SamplingValidationError,
)


DECISIONS = {"recommend_follow_up", "no_further_action"}


class ReviewDecisionValidationError(ValueError):
    """The application decision payload is invalid."""


class ReviewDecisionService:
    """Coordinate Review and Membership repositories in one transaction."""

    def __init__(self, data_store: DataStore, sampling_store: SamplingStore) -> None:
        self.data_store = data_store
        self.sampling_store = sampling_store

    def decide(
        self,
        snapshot_id: str,
        decision: str,
        added_from: str,
        note: str = "",
    ) -> dict[str, Any]:
        decision = str(decision or "").strip()
        added_from = str(added_from or "").strip()
        if decision not in DECISIONS:
            raise ReviewDecisionValidationError("decision不合法")
        if added_from not in ADDED_FROM_VALUES:
            raise ReviewDecisionValidationError("added_from不合法")
        try:
            with self.data_store.transaction() as connection:
                product_id, task_id = self.sampling_store.snapshot_identity(
                    connection, snapshot_id
                )
                review = self.data_store.save_review(
                    connection, snapshot_id, decision, note
                )
                if decision == "recommend_follow_up":
                    membership = self.sampling_store.ensure_membership(
                        connection,
                        product_id=product_id,
                        source_snapshot_id=snapshot_id,
                        source_task_id=task_id,
                        added_from=added_from,
                    )
                else:
                    self.sampling_store.remove_membership(connection, product_id)
                    membership = None
        except SamplingSnapshotNotFoundError as exc:
            raise SnapshotNotFoundError(str(exc)) from exc
        except SamplingValidationError as exc:
            raise ReviewDecisionValidationError(str(exc)) from exc
        snapshot = self.data_store.get_snapshot(snapshot_id)
        return {
            "snapshotId": snapshot_id,
            "productId": product_id,
            "review": review,
            "membership": membership,
            "sampling": snapshot["sampling"],
        }
