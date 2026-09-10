"""Repository for current Membership and frozen-list metadata/index rows.

This module deliberately has no Review, evidence, recommendation, or UI rules.
Frozen JSON/XLSX content is owned by the application export service.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ADDED_FROM_VALUES = {"product_overview", "inspection_workspace"}


def _membership_now() -> str:
    """Use sub-second identity so a remove/restore cannot mimic a frozen row."""

    return datetime.now(timezone.utc).astimezone().isoformat(timespec="microseconds")


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


def _history_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "listId": row["list_id"],
        "status": row["status"],
        "exportedAt": row["exported_at"],
        "itemCount": int(row["item_count"] or 0),
        "snapshotPath": row["snapshot_path"],
        "workbookPath": row["workbook_path"],
        "snapshotSha256": row["snapshot_sha256"],
        "workbookSha256": row["workbook_sha256"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


class SamplingStore:
    """Mutate Sampling rows without reading or changing Review facts."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path.resolve()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    @staticmethod
    def validate_added_from(added_from: str) -> str:
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

        origin = self.validate_added_from(added_from)
        existing = connection.execute(
            "SELECT * FROM sampling_list_memberships WHERE product_id = ?",
            (product_id,),
        ).fetchone()
        if existing is not None:
            return _membership_dict(existing)
        now = _membership_now()
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
            return self.list_current_in_transaction(connection)

    def list_current_in_transaction(
        self, connection: sqlite3.Connection
    ) -> list[dict[str, Any]]:
        rows = connection.execute(
            """
            SELECT sm.*, s.product_name, s.shop_name, s.collected_at,
                   r.review_status, r.review_note, r.reviewed_at
            FROM sampling_list_memberships sm
            JOIN product_snapshots s ON s.snapshot_id = sm.source_snapshot_id
            JOIN reviews r ON r.snapshot_id = sm.source_snapshot_id
            ORDER BY sm.added_at, sm.product_id
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

    def create_preparing(
        self,
        connection: sqlite3.Connection,
        *,
        list_id: str,
        snapshot_path: str,
        workbook_path: str,
        created_at: str,
    ) -> dict[str, Any]:
        connection.execute(
            """
            INSERT INTO sampling_lists (
                list_id, status, exported_at, item_count,
                snapshot_path, workbook_path,
                snapshot_sha256, workbook_sha256,
                created_at, updated_at
            ) VALUES (?, 'preparing', NULL, 0, ?, ?, '', '', ?, ?)
            """,
            (list_id, snapshot_path, workbook_path, created_at, created_at),
        )
        row = connection.execute(
            "SELECT * FROM sampling_lists WHERE list_id = ?", (list_id,)
        ).fetchone()
        return _history_dict(row)

    def finalize_export(
        self,
        connection: sqlite3.Connection,
        *,
        list_id: str,
        exported_at: str,
        item_count: int,
        snapshot_sha256: str,
        workbook_sha256: str,
        items: list[dict[str, Any]],
        frozen_memberships: list[dict[str, Any]],
    ) -> dict[str, Any]:
        updated = connection.execute(
            """
            UPDATE sampling_lists
            SET status = 'exported', exported_at = ?, item_count = ?,
                snapshot_sha256 = ?, workbook_sha256 = ?, updated_at = ?
            WHERE list_id = ?
            """,
            (
                exported_at,
                item_count,
                snapshot_sha256,
                workbook_sha256,
                exported_at,
                list_id,
            ),
        )
        if updated.rowcount != 1:
            raise SamplingStoreError("历史抽检清单元数据不存在")
        connection.execute(
            "DELETE FROM sampling_list_item_index WHERE list_id = ?", (list_id,)
        )
        for item in items:
            connection.execute(
                """
                INSERT INTO sampling_list_item_index (
                    list_id, ordinal, product_id,
                    source_snapshot_id, source_task_id
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    list_id,
                    int(item["ordinal"]),
                    str(item["productId"]),
                    str(item["sourceSnapshotId"]),
                    str(item["sourceTaskId"]),
                ),
            )
        for membership in frozen_memberships:
            connection.execute(
                """
                DELETE FROM sampling_list_memberships
                WHERE product_id = ? AND source_snapshot_id = ?
                  AND source_task_id = ? AND added_from = ?
                  AND added_at = ? AND updated_at = ?
                """,
                (
                    membership["productId"],
                    membership["sourceSnapshotId"],
                    membership["sourceTaskId"],
                    membership["addedFrom"],
                    membership["addedAt"],
                    membership["updatedAt"],
                ),
            )
        row = connection.execute(
            "SELECT * FROM sampling_lists WHERE list_id = ?", (list_id,)
        ).fetchone()
        return _history_dict(row)

    def rebuild_exported(
        self,
        *,
        list_id: str,
        exported_at: str,
        item_count: int,
        snapshot_path: str,
        workbook_path: str,
        snapshot_sha256: str,
        workbook_sha256: str,
        created_at: str,
        items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Idempotently rebuild history metadata/index from a frozen JSON fact."""

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO sampling_lists (
                    list_id, status, exported_at, item_count,
                    snapshot_path, workbook_path,
                    snapshot_sha256, workbook_sha256,
                    created_at, updated_at
                ) VALUES (?, 'exported', ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(list_id) DO UPDATE SET
                    status = 'exported',
                    exported_at = excluded.exported_at,
                    item_count = excluded.item_count,
                    snapshot_path = excluded.snapshot_path,
                    workbook_path = excluded.workbook_path,
                    snapshot_sha256 = excluded.snapshot_sha256,
                    workbook_sha256 = excluded.workbook_sha256,
                    updated_at = excluded.updated_at
                """,
                (
                    list_id,
                    exported_at,
                    item_count,
                    snapshot_path,
                    workbook_path,
                    snapshot_sha256,
                    workbook_sha256,
                    created_at,
                    exported_at,
                ),
            )
            connection.execute(
                "DELETE FROM sampling_list_item_index WHERE list_id = ?", (list_id,)
            )
            for item in items:
                connection.execute(
                    """
                    INSERT INTO sampling_list_item_index (
                        list_id, ordinal, product_id,
                        source_snapshot_id, source_task_id
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        list_id,
                        int(item["ordinal"]),
                        str(item["productId"]),
                        str(item["sourceSnapshotId"]),
                        str(item["sourceTaskId"]),
                    ),
                )
            row = connection.execute(
                "SELECT * FROM sampling_lists WHERE list_id = ?", (list_id,)
            ).fetchone()
            return _history_dict(row)

    def list_history(self, *, status: str = "exported") -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM sampling_lists
                WHERE status = ?
                ORDER BY COALESCE(exported_at, created_at) DESC, list_id DESC
                """,
                (status,),
            ).fetchall()
        return [_history_dict(row) for row in rows]

    def get_history_metadata(self, list_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM sampling_lists WHERE list_id = ?", (list_id,)
            ).fetchone()
        return _history_dict(row) if row is not None else None

    def delete_history(self, list_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM sampling_lists WHERE list_id = ?", (list_id,)
            )
