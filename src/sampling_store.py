"""Repository for the current Sampling Membership relationship.

This module deliberately has no Review, evidence, recommendation, or UI rules.
Historical frozen-list export remains a later-phase concern.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from src.runtime import iso_now


ADDED_FROM_VALUES = {"product_overview", "inspection_workspace"}


class SamplingStoreError(RuntimeError):
    """Base error for current-list repository operations."""


class SamplingValidationError(SamplingStoreError):
    """The caller supplied an invalid relationship value."""


class SamplingSnapshotNotFoundError(SamplingStoreError):
    """The membership source Snapshot does not exist."""


class SamplingMembershipNotFoundError(SamplingStoreError):
    """The requested current membership does not exist."""


def _membership_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "productId": row["product_id"],
        "sourceSnapshotId": row["source_snapshot_id"],
        "sourceTaskId": row["source_task_id"],
        "addedFrom": row["added_from"],
        "addedAt": row["added_at"],
        "updatedAt": row["updated_at"],
        **(
            {
                "productName": row["product_name"],
                "shopName": row["shop_name"],
                "collectedAt": row["collected_at"],
                "review": {
                    "status": row["review_status"],
                    "note": row["review_note"],
                    "reviewedAt": row["reviewed_at"],
                },
            }
            if "product_name" in row.keys()
            else {}
        ),
    }


class SamplingStore:
    """Read and mutate only current Sampling Membership rows."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path.resolve()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    @staticmethod
    def _validate_added_from(added_from: str) -> str:
        value = str(added_from or "").strip()
        if value not in ADDED_FROM_VALUES:
            raise SamplingValidationError("added_from不合法")
        return value

    @staticmethod
    def snapshot_identity(
        connection: sqlite3.Connection, snapshot_id: str
    ) -> tuple[str, str]:
        row = connection.execute(
            "SELECT product_id, task_id FROM product_snapshots WHERE snapshot_id = ?",
            (snapshot_id,),
        ).fetchone()
        if row is None:
            raise SamplingSnapshotNotFoundError("商品快照不存在")
        return str(row["product_id"]), str(row["task_id"])

    def ensure_membership(
        self,
        connection: sqlite3.Connection,
        *,
        product_id: str,
        source_snapshot_id: str,
        source_task_id: str,
        added_from: str,
    ) -> dict[str, Any]:
        """Idempotently create one membership without replacing its source."""

        origin = self._validate_added_from(added_from)
        existing = connection.execute(
            "SELECT * FROM sampling_list_memberships WHERE product_id = ?",
            (product_id,),
        ).fetchone()
        if existing is not None:
            return _membership_dict(existing)
        now = iso_now()
        connection.execute(
            """
            INSERT INTO sampling_list_memberships (
                product_id, source_snapshot_id, source_task_id,
                added_from, added_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                product_id,
                source_snapshot_id,
                source_task_id,
                origin,
                now,
                now,
            ),
        )
        row = connection.execute(
            "SELECT * FROM sampling_list_memberships WHERE product_id = ?",
            (product_id,),
        ).fetchone()
        return _membership_dict(row)

    def remove_membership(
        self, connection: sqlite3.Connection, product_id: str
    ) -> dict[str, Any] | None:
        row = connection.execute(
            "SELECT * FROM sampling_list_memberships WHERE product_id = ?",
            (product_id,),
        ).fetchone()
        if row is None:
            return None
        result = _membership_dict(row)
        connection.execute(
            "DELETE FROM sampling_list_memberships WHERE product_id = ?",
            (product_id,),
        )
        return result

    def add_from_snapshot(self, snapshot_id: str, added_from: str) -> dict[str, Any]:
        with self._connect() as connection:
            product_id, task_id = self.snapshot_identity(connection, snapshot_id)
            return self.ensure_membership(
                connection,
                product_id=product_id,
                source_snapshot_id=snapshot_id,
                source_task_id=task_id,
                added_from=added_from,
            )

    def add(
        self, product_id: str, source_snapshot_id: str, added_from: str
    ) -> dict[str, Any]:
        """Restore a membership while verifying the frozen Product/Snapshot relation."""

        normalized_product = str(product_id or "").strip()
        if not normalized_product:
            raise SamplingValidationError("product_id不能为空")
        with self._connect() as connection:
            actual_product, task_id = self.snapshot_identity(
                connection, str(source_snapshot_id or "").strip()
            )
            if normalized_product != actual_product:
                raise SamplingValidationError("product_id与source_snapshot_id不匹配")
            return self.ensure_membership(
                connection,
                product_id=actual_product,
                source_snapshot_id=source_snapshot_id,
                source_task_id=task_id,
                added_from=added_from,
            )

    def remove(self, product_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            result = self.remove_membership(connection, product_id)
            if result is None:
                raise SamplingMembershipNotFoundError("商品不在当前抽检清单中")
            return result

    def get(self, product_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM sampling_list_memberships WHERE product_id = ?",
                (product_id,),
            ).fetchone()
        return _membership_dict(row) if row is not None else None

    def list_current(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT sm.*, s.product_name, s.shop_name, s.collected_at,
                       r.review_status, r.review_note, r.reviewed_at
                FROM sampling_list_memberships sm
                JOIN product_snapshots s ON s.snapshot_id = sm.source_snapshot_id
                JOIN reviews r ON r.snapshot_id = sm.source_snapshot_id
                ORDER BY sm.added_at DESC, sm.product_id
                """
            ).fetchall()
        return [_membership_dict(row) for row in rows]

    def count_current(self) -> int:
        with self._connect() as connection:
            return int(
                connection.execute(
                    "SELECT COUNT(*) FROM sampling_list_memberships"
                ).fetchone()[0]
            )
