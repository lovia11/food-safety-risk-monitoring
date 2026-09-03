"""SQLite business index for task, product snapshot, evidence and review data.

The run directory remains the source of truth for large/raw collector artifacts.
This module stores only queryable business fields and relative artifact paths.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

from src.runtime import iso_now, read_json


REVIEW_STATUSES = {"pending", "recommend_follow_up", "no_further_action"}
TARGET_TYPES = {"food_medicine", "health_food"}
QUERY_TYPES = {"base", "product_form"}
QUERY_SOURCES = {
    "standard_name",
    "official_alias",
    "observed_product_form",
    "manual",
}
QUERY_VALIDATION_STATUSES = {"unvalidated", "search_validated"}
DATASET_STATUSES = {"development_seed", "reference_pending", "verified_reference"}
DEFAULT_MONITOR_CONFIG_PATHS = (
    Path("config/monitor_targets.development.json"),
    Path("config/monitor_targets.reference.json"),
)
SCHEMA_VERSION = 4

_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_DATASET_FIELDS = (
    "dataset_id",
    "dataset_version",
    "dataset_status",
    "source_name",
    "source_reference",
    "source_date",
    "collected_at",
    "verified_at",
    "targets",
)


class DataStoreError(RuntimeError):
    """Base error for the local business data index."""


class SnapshotNotFoundError(DataStoreError):
    """The requested product snapshot does not exist."""


class ReviewValidationError(DataStoreError):
    """A review update contains an unsupported value."""


class MonitorConfigValidationError(DataStoreError):
    """A MonitorTarget dataset is incomplete or internally inconsistent."""


def _json_text(value: Any, default: Any) -> str:
    return json.dumps(value if value is not None else default, ensure_ascii=False)


def _json_value(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


def make_snapshot_id(task_id: str, product_id: str) -> str:
    """Return a stable, URL-safe identifier for one task/product observation."""

    digest = hashlib.sha256(f"{task_id}\0{product_id}".encode("utf-8")).hexdigest()
    return f"ps_{digest[:24]}"


def _read_optional_json(path: Path, default: Any) -> Any:
    try:
        return read_json(path) if path.is_file() else default
    except (OSError, ValueError, TypeError):
        return default


def _required_text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise MonitorConfigValidationError(f"{field}不能为空")
    return text


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _identifier(value: Any, field: str) -> str:
    text = _required_text(value, field)
    if not _IDENTIFIER_PATTERN.fullmatch(text):
        raise MonitorConfigValidationError(
            f"{field}只能包含字母、数字、点、下划线、冒号和连字符"
        )
    return text


def _optional_iso_date(value: Any, field: str) -> str | None:
    text = _optional_text(value)
    if text is None:
        return None
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise MonitorConfigValidationError(f"{field}必须使用YYYY-MM-DD格式")
    try:
        date.fromisoformat(text)
    except ValueError as error:
        raise MonitorConfigValidationError(f"{field}不是有效日期：{text}") from error
    return text


def _optional_iso_datetime(value: Any, field: str) -> str | None:
    text = _optional_text(value)
    if text is None:
        return None
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise MonitorConfigValidationError(f"{field}不是有效ISO时间：{text}") from error
    return text


def _boolean(value: Any, field: str, *, default: bool = True) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise MonitorConfigValidationError(f"{field}必须是布尔值")
    return value


def _official_name_parts(standard_name: str) -> tuple[str, set[str]]:
    """Return the official primary name and literal parenthesized name parts."""

    match = re.fullmatch(r"\s*([^（）]+?)\s*（([^（）]+)）\s*", standard_name)
    if not match:
        return standard_name, set()
    primary = match.group(1).strip()
    aliases = {
        item.strip()
        for item in re.split(r"[、，,]", match.group(2))
        if item.strip()
    }
    return primary, aliases


def validate_monitor_config(payload: Any) -> dict[str, Any]:
    """Validate and normalize one development or reference MonitorTarget dataset."""

    if not isinstance(payload, dict):
        raise MonitorConfigValidationError("监测数据集根节点必须是JSON对象")
    missing = [field for field in _DATASET_FIELDS if field not in payload]
    if missing:
        raise MonitorConfigValidationError(
            f"监测数据集缺少字段：{', '.join(missing)}"
        )
    schema_version = payload.get("schema_version")
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version < 1
    ):
        raise MonitorConfigValidationError("schema_version必须是正整数")

    dataset_id = _identifier(payload.get("dataset_id"), "dataset_id")
    dataset_version = _required_text(payload.get("dataset_version"), "dataset_version")
    dataset_status = _required_text(payload.get("dataset_status"), "dataset_status")
    if dataset_status not in DATASET_STATUSES:
        raise MonitorConfigValidationError(
            f"不支持的dataset_status：{dataset_status}"
        )
    dataset_source_name = _optional_text(payload.get("source_name"))
    dataset_source_reference = _optional_text(payload.get("source_reference"))
    dataset_source_date = _optional_iso_date(payload.get("source_date"), "source_date")
    collected_at = _optional_iso_datetime(payload.get("collected_at"), "collected_at")
    verified_at = _optional_iso_datetime(payload.get("verified_at"), "verified_at")

    if dataset_status in {"development_seed", "verified_reference"}:
        if not dataset_source_name:
            raise MonitorConfigValidationError(
                f"{dataset_status}数据集必须包含source_name"
            )
        if not dataset_source_reference:
            raise MonitorConfigValidationError(
                f"{dataset_status}数据集必须包含source_reference"
            )
    if dataset_status == "verified_reference" and not verified_at:
        raise MonitorConfigValidationError(
            "verified_reference数据集必须包含verified_at"
        )

    raw_targets = payload.get("targets")
    if not isinstance(raw_targets, list):
        raise MonitorConfigValidationError("targets必须是数组")
    if dataset_status == "reference_pending" and raw_targets:
        raise MonitorConfigValidationError(
            "reference_pending数据集不能包含未经核验的MonitorTarget"
        )
    if dataset_status == "verified_reference" and not raw_targets:
        raise MonitorConfigValidationError(
            "verified_reference数据集必须至少包含一个已核验MonitorTarget"
        )

    normalized_targets: list[dict[str, Any]] = []
    target_ids: set[str] = set()
    query_ids: set[str] = set()
    for target_position, target in enumerate(raw_targets, start=1):
        if not isinstance(target, dict):
            raise MonitorConfigValidationError(
                f"targets[{target_position}]必须是JSON对象"
            )
        target_id = _identifier(
            target.get("target_id"), f"targets[{target_position}].target_id"
        )
        if target_id in target_ids:
            raise MonitorConfigValidationError(f"target_id重复：{target_id}")
        target_ids.add(target_id)
        standard_name = _required_text(
            target.get("standard_name"),
            f"MonitorTarget {target_id} 的standard_name",
        )
        target_type = _required_text(
            target.get("target_type"), f"MonitorTarget {target_id} 的target_type"
        )
        if target_type not in TARGET_TYPES:
            raise MonitorConfigValidationError(f"不支持的target_type：{target_type}")

        target_dataset_id = _identifier(
            target.get("dataset_id"), f"MonitorTarget {target_id} 的dataset_id"
        )
        if target_dataset_id != dataset_id:
            raise MonitorConfigValidationError(
                f"MonitorTarget {target_id} 的dataset_id必须等于所属数据集 {dataset_id}"
            )
        target_enabled = _boolean(
            target.get("enabled"), f"MonitorTarget {target_id} 的enabled"
        )

        target_source_name = _optional_text(target.get("source_name"))
        target_source_reference = _optional_text(target.get("source_reference"))
        source_name = target_source_name or dataset_source_name
        source_reference = target_source_reference or dataset_source_reference
        raw_source_date = target.get("source_date")
        source_date = _optional_iso_date(
            raw_source_date if raw_source_date is not None else dataset_source_date,
            f"MonitorTarget {target_id} 的source_date",
        )
        if not source_name or not source_reference:
            raise MonitorConfigValidationError(
                f"MonitorTarget {target_id} 必须具有可追踪的来源名称和引用"
            )
        if dataset_status == "verified_reference" and (
            not target_source_name
            or not target_source_reference
            or raw_source_date is None
        ):
            raise MonitorConfigValidationError(
                f"verified_reference中的MonitorTarget {target_id} 必须独立记录"
                "source_name、source_reference和source_date"
            )

        raw_queries = target.get("queries")
        if not isinstance(raw_queries, list):
            raise MonitorConfigValidationError(
                f"MonitorTarget {target_id} 的queries必须是数组"
            )
        if not raw_queries and not (
            dataset_status == "verified_reference" and not target_enabled
        ):
            raise MonitorConfigValidationError(
                f"MonitorTarget {target_id} 必须至少包含一个SearchQuery；"
                "只有停用的verified_reference目标可以暂不配置Query"
            )
        normalized_queries: list[dict[str, Any]] = []
        query_orders: set[int] = set()
        for query_position, query in enumerate(raw_queries, start=1):
            if not isinstance(query, dict):
                raise MonitorConfigValidationError(
                    f"MonitorTarget {target_id} 的queries[{query_position}]必须是JSON对象"
                )
            query_target_id = _optional_text(query.get("target_id"))
            if query_target_id is not None and query_target_id != target_id:
                raise MonitorConfigValidationError(
                    f"SearchQuery的target_id不存在或与所属MonitorTarget不一致：{query_target_id}"
                )
            query_id = _identifier(
                query.get("query_id"),
                f"MonitorTarget {target_id} 的query_id",
            )
            if query_id in query_ids:
                raise MonitorConfigValidationError(f"query_id重复：{query_id}")
            query_ids.add(query_id)
            query_text = _required_text(
                query.get("query_text"), f"SearchQuery {query_id} 的query_text"
            )
            query_type = _required_text(
                query.get("query_type"), f"SearchQuery {query_id} 的query_type"
            )
            if query_type not in QUERY_TYPES:
                raise MonitorConfigValidationError(
                    f"不支持的query_type：{query_type}"
                )
            query_source = _required_text(
                query.get("query_source"),
                f"SearchQuery {query_id} 的query_source",
            )
            if query_source not in QUERY_SOURCES:
                raise MonitorConfigValidationError(
                    f"不支持的query_source：{query_source}"
                )
            validation_status = _required_text(
                query.get("validation_status"),
                f"SearchQuery {query_id} 的validation_status",
            )
            if validation_status not in QUERY_VALIDATION_STATUSES:
                raise MonitorConfigValidationError(
                    f"不支持的validation_status：{validation_status}"
                )
            query_note = _optional_text(query.get("query_note"))
            primary_name, official_aliases = _official_name_parts(standard_name)
            if query_source == "standard_name" and query_text not in {
                standard_name,
                primary_name,
            }:
                raise MonitorConfigValidationError(
                    f"SearchQuery {query_id} 标记为standard_name时必须使用官方标准名称"
                )
            if query_source == "official_alias" and query_text not in official_aliases:
                raise MonitorConfigValidationError(
                    f"SearchQuery {query_id} 的official_alias未出现在官方名称括号中"
                )
            if query_source in {"standard_name", "official_alias"} and query_type != "base":
                raise MonitorConfigValidationError(
                    f"SearchQuery {query_id} 的{query_source}必须使用base类型"
                )
            if query_source == "observed_product_form" and query_type != "product_form":
                raise MonitorConfigValidationError(
                    f"SearchQuery {query_id} 的observed_product_form必须使用product_form类型"
                )
            if query_source in {"observed_product_form", "manual"} and not query_note:
                raise MonitorConfigValidationError(
                    f"SearchQuery {query_id} 的{query_source}必须记录query_note"
                )
            query_order = query.get("order")
            if (
                not isinstance(query_order, int)
                or isinstance(query_order, bool)
                or query_order < 1
            ):
                raise MonitorConfigValidationError(
                    f"SearchQuery {query_id} 的order必须是正整数"
                )
            if query_order in query_orders:
                raise MonitorConfigValidationError(
                    f"MonitorTarget {target_id} 的SearchQuery order重复：{query_order}"
                )
            query_orders.add(query_order)
            query_enabled = _boolean(
                query.get("enabled"), f"SearchQuery {query_id} 的enabled"
            )
            if query_enabled and validation_status != "search_validated":
                raise MonitorConfigValidationError(
                    f"SearchQuery {query_id} 未经search_validated不能启用"
                )
            normalized_queries.append(
                {
                    "query_id": query_id,
                    "target_id": target_id,
                    "query_text": query_text,
                    "query_type": query_type,
                    "query_source": query_source,
                    "validation_status": validation_status,
                    "query_note": query_note,
                    "order": query_order,
                    "enabled": query_enabled,
                }
            )

        if target_enabled and not any(
            query["enabled"]
            and query["validation_status"] == "search_validated"
            for query in normalized_queries
        ):
            raise MonitorConfigValidationError(
                f"启用的MonitorTarget {target_id} 必须至少有一个已验证且启用的SearchQuery"
            )

        normalized_targets.append(
            {
                "target_id": target_id,
                "dataset_id": target_dataset_id,
                "standard_name": standard_name,
                "target_type": target_type,
                "source_name": source_name,
                "source_reference": source_reference,
                "source_date": source_date,
                "enabled": target_enabled,
                "queries": normalized_queries,
            }
        )

    return {
        "schema_version": schema_version,
        "dataset_id": dataset_id,
        "dataset_version": dataset_version,
        "dataset_status": dataset_status,
        "source_name": dataset_source_name,
        "source_reference": dataset_source_reference,
        "source_date": dataset_source_date,
        "collected_at": collected_at,
        "verified_at": verified_at,
        "description": str(payload.get("description") or "").strip(),
        "targets": normalized_targets,
    }


class DataStore:
    """Small sqlite3 repository; connections are opened per operation/thread."""

    def __init__(self, database_path: Path, output_root: Path) -> None:
        self.database_path = database_path.resolve()
        self.output_root = output_root.resolve()

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    keyword TEXT NOT NULL DEFAULT '',
                    candidate_limit INTEGER,
                    detail_limit INTEGER,
                    stage TEXT NOT NULL DEFAULT '',
                    created_at TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    run_path TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS products (
                    taobao_product_id TEXT PRIMARY KEY,
                    first_seen_at TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS product_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    product_id TEXT NOT NULL REFERENCES products(taobao_product_id),
                    task_id TEXT NOT NULL REFERENCES tasks(task_id),
                    rank INTEGER,
                    product_name TEXT NOT NULL DEFAULT '',
                    shop_name TEXT NOT NULL DEFAULT '',
                    region TEXT NOT NULL DEFAULT '',
                    product_url TEXT NOT NULL DEFAULT '',
                    collected_at TEXT,
                    status TEXT NOT NULL DEFAULT '',
                    detected_effects_json TEXT NOT NULL DEFAULT '[]',
                    review_required INTEGER,
                    analysis_summary TEXT NOT NULL DEFAULT '',
                    product_path TEXT NOT NULL,
                    meta_path TEXT,
                    analysis_path TEXT,
                    original_image_count INTEGER NOT NULL DEFAULT 0,
                    ocr_image_count INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    UNIQUE(task_id, product_id)
                );

                CREATE TABLE IF NOT EXISTS evidence (
                    evidence_id TEXT PRIMARY KEY,
                    snapshot_id TEXT NOT NULL REFERENCES product_snapshots(snapshot_id)
                        ON DELETE CASCADE,
                    ordinal INTEGER NOT NULL,
                    effect TEXT NOT NULL DEFAULT '',
                    text TEXT NOT NULL DEFAULT '',
                    matched_keywords_json TEXT NOT NULL DEFAULT '[]',
                    source_type TEXT NOT NULL DEFAULT '',
                    source_label TEXT NOT NULL DEFAULT '',
                    content_origin TEXT NOT NULL DEFAULT '',
                    source_path TEXT NOT NULL DEFAULT '',
                    line_number INTEGER,
                    UNIQUE(snapshot_id, ordinal)
                );

                CREATE TABLE IF NOT EXISTS reviews (
                    snapshot_id TEXT PRIMARY KEY REFERENCES product_snapshots(snapshot_id)
                        ON DELETE CASCADE,
                    review_status TEXT NOT NULL DEFAULT 'pending'
                        CHECK(review_status IN ('pending', 'recommend_follow_up', 'no_further_action')),
                    review_note TEXT NOT NULL DEFAULT '',
                    reviewed_at TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_snapshots_task
                    ON product_snapshots(task_id, rank);
                CREATE INDEX IF NOT EXISTS idx_snapshots_product
                    ON product_snapshots(product_id, collected_at DESC);
                CREATE INDEX IF NOT EXISTS idx_evidence_snapshot
                    ON evidence(snapshot_id, ordinal);
                CREATE INDEX IF NOT EXISTS idx_reviews_status
                    ON reviews(review_status);

                CREATE TABLE IF NOT EXISTS monitor_datasets (
                    dataset_id TEXT PRIMARY KEY,
                    dataset_version TEXT NOT NULL,
                    dataset_status TEXT NOT NULL
                        CHECK(dataset_status IN (
                            'development_seed', 'reference_pending', 'verified_reference'
                        )),
                    source_name TEXT,
                    source_reference TEXT,
                    source_date TEXT,
                    collected_at TEXT,
                    verified_at TEXT,
                    description TEXT NOT NULL DEFAULT '',
                    imported_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS monitor_targets (
                    target_id TEXT PRIMARY KEY,
                    dataset_id TEXT REFERENCES monitor_datasets(dataset_id),
                    standard_name TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    source_reference TEXT NOT NULL,
                    source_date TEXT,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS search_queries (
                    query_id TEXT PRIMARY KEY,
                    target_id TEXT NOT NULL REFERENCES monitor_targets(target_id)
                        ON DELETE CASCADE,
                    query_text TEXT NOT NULL,
                    query_type TEXT NOT NULL,
                    query_source TEXT NOT NULL DEFAULT 'manual',
                    validation_status TEXT NOT NULL DEFAULT 'unvalidated',
                    query_note TEXT NOT NULL DEFAULT '',
                    query_order INTEGER NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL,
                    UNIQUE(target_id, query_text)
                );

                CREATE TABLE IF NOT EXISTS candidate_hits (
                    hit_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
                    product_id TEXT NOT NULL REFERENCES products(taobao_product_id),
                    query_id TEXT NOT NULL REFERENCES search_queries(query_id),
                    query_text TEXT NOT NULL,
                    rank INTEGER,
                    discovered_at TEXT NOT NULL,
                    UNIQUE(task_id, product_id, query_id)
                );

                CREATE INDEX IF NOT EXISTS idx_queries_target
                    ON search_queries(target_id, query_order);
                CREATE INDEX IF NOT EXISTS idx_hits_task
                    ON candidate_hits(task_id, query_id, rank);
                CREATE INDEX IF NOT EXISTS idx_hits_product
                    ON candidate_hits(product_id, discovered_at);
                """
            )
            self._ensure_column(connection, "tasks", "task_type", "TEXT NOT NULL DEFAULT 'quick'")
            self._ensure_column(connection, "tasks", "target_id", "TEXT")
            self._ensure_column(connection, "tasks", "per_query_candidate_limit", "INTEGER")
            self._ensure_column(
                connection,
                "monitor_targets",
                "dataset_id",
                "TEXT REFERENCES monitor_datasets(dataset_id)",
            )
            self._ensure_column(
                connection,
                "search_queries",
                "query_source",
                "TEXT NOT NULL DEFAULT 'manual'",
            )
            self._ensure_column(
                connection,
                "search_queries",
                "validation_status",
                "TEXT NOT NULL DEFAULT 'unvalidated'",
            )
            self._ensure_column(
                connection,
                "search_queries",
                "query_note",
                "TEXT NOT NULL DEFAULT ''",
            )
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    @staticmethod
    def _ensure_column(
        connection: sqlite3.Connection, table: str, column: str, definition: str
    ) -> None:
        columns = {
            str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")
        }
        if column not in columns:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def import_monitor_config(self, config_path: Path) -> dict[str, int]:
        payload = validate_monitor_config(read_json(config_path))
        targets = payload["targets"]
        target_count = 0
        query_count = 0
        now = iso_now()
        with self._connect() as connection:
            existing_dataset = connection.execute(
                "SELECT dataset_status FROM monitor_datasets WHERE dataset_id = ?",
                (payload["dataset_id"],),
            ).fetchone()
            if existing_dataset is not None:
                previous_status = str(existing_dataset["dataset_status"])
                next_status = str(payload["dataset_status"])
                allowed_transition = (
                    previous_status == next_status
                    or (
                        previous_status == "reference_pending"
                        and next_status == "verified_reference"
                    )
                )
                if not allowed_transition:
                    raise MonitorConfigValidationError(
                        f"数据集 {payload['dataset_id']} 不能从"
                        f" {previous_status} 自动变更为 {next_status}"
                    )
            connection.execute(
                """
                INSERT INTO monitor_datasets (
                    dataset_id, dataset_version, dataset_status, source_name,
                    source_reference, source_date, collected_at, verified_at,
                    description, imported_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(dataset_id) DO UPDATE SET
                    dataset_version=excluded.dataset_version,
                    dataset_status=excluded.dataset_status,
                    source_name=excluded.source_name,
                    source_reference=excluded.source_reference,
                    source_date=excluded.source_date,
                    collected_at=excluded.collected_at,
                    verified_at=excluded.verified_at,
                    description=excluded.description,
                    updated_at=excluded.updated_at
                """,
                (
                    payload["dataset_id"],
                    payload["dataset_version"],
                    payload["dataset_status"],
                    payload["source_name"],
                    payload["source_reference"],
                    payload["source_date"],
                    payload["collected_at"],
                    payload["verified_at"],
                    payload["description"],
                    now,
                    now,
                ),
            )
            for target in targets:
                target_id = str(target.get("target_id") or "").strip()
                target_type = str(target.get("target_type") or "").strip()
                existing_target = connection.execute(
                    "SELECT dataset_id FROM monitor_targets WHERE target_id = ?",
                    (target_id,),
                ).fetchone()
                if (
                    existing_target is not None
                    and existing_target["dataset_id"] is not None
                    and existing_target["dataset_id"] != payload["dataset_id"]
                ):
                    raise MonitorConfigValidationError(
                        f"target_id {target_id} 已属于数据集"
                        f" {existing_target['dataset_id']}，不能自动转入"
                        f" {payload['dataset_id']}"
                    )
                connection.execute(
                    """
                    INSERT INTO monitor_targets (
                        target_id, dataset_id, standard_name, target_type,
                        source_name, source_reference, source_date, enabled, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(target_id) DO UPDATE SET
                        dataset_id=excluded.dataset_id,
                        standard_name=excluded.standard_name,
                        target_type=excluded.target_type,
                        source_name=excluded.source_name,
                        source_reference=excluded.source_reference,
                        source_date=excluded.source_date,
                        enabled=excluded.enabled,
                        updated_at=excluded.updated_at
                    """,
                    (
                        target_id,
                        payload["dataset_id"],
                        str(target.get("standard_name") or "").strip(),
                        target_type,
                        str(target.get("source_name") or ""),
                        str(target.get("source_reference") or ""),
                        target.get("source_date"),
                        1 if target.get("enabled", True) else 0,
                        now,
                    ),
                )
                target_count += 1
                for query in target["queries"]:
                    query_id = str(query.get("query_id") or "").strip()
                    query_text = str(query.get("query_text") or "").strip()
                    query_type = str(query.get("query_type") or "").strip()
                    existing_query = connection.execute(
                        "SELECT target_id FROM search_queries WHERE query_id = ?",
                        (query_id,),
                    ).fetchone()
                    if (
                        existing_query is not None
                        and existing_query["target_id"] != target_id
                    ):
                        raise MonitorConfigValidationError(
                            f"query_id {query_id} 已属于MonitorTarget"
                            f" {existing_query['target_id']}，不能改绑到 {target_id}"
                        )
                    connection.execute(
                        """
                        INSERT INTO search_queries (
                            query_id, target_id, query_text, query_type,
                            query_source, validation_status, query_note,
                            query_order, enabled, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(query_id) DO UPDATE SET
                            target_id=excluded.target_id,
                            query_text=excluded.query_text,
                            query_type=excluded.query_type,
                            query_source=excluded.query_source,
                            validation_status=excluded.validation_status,
                            query_note=excluded.query_note,
                            query_order=excluded.query_order,
                            enabled=excluded.enabled,
                            updated_at=excluded.updated_at
                        """,
                        (
                            query_id,
                            target_id,
                            query_text,
                            query_type,
                            query["query_source"],
                            query["validation_status"],
                            query.get("query_note") or "",
                            query["order"],
                            1 if query.get("enabled", True) else 0,
                            now,
                        ),
                    )
                    query_count += 1
        return {"datasets": 1, "targets": target_count, "queries": query_count}

    def list_monitor_targets(self, *, enabled_only: bool = False) -> list[dict[str, Any]]:
        where = " WHERE t.enabled = 1" if enabled_only else ""
        with self._connect() as connection:
            targets = connection.execute(
                """
                SELECT t.*, d.dataset_version, d.dataset_status,
                       d.source_name AS dataset_source_name,
                       d.source_reference AS dataset_source_reference,
                       d.source_date AS dataset_source_date,
                       d.collected_at AS dataset_collected_at,
                       d.verified_at AS dataset_verified_at,
                       d.description AS dataset_description
                FROM monitor_targets t
                LEFT JOIN monitor_datasets d ON d.dataset_id = t.dataset_id
                """
                + where
                + " ORDER BY t.standard_name, t.target_id"
            ).fetchall()
            query_rows = connection.execute(
                "SELECT * FROM search_queries ORDER BY target_id, query_order, query_id"
            ).fetchall()
        by_target: dict[str, list[dict[str, Any]]] = {}
        for row in query_rows:
            by_target.setdefault(str(row["target_id"]), []).append(
                {
                    "query_id": row["query_id"],
                    "target_id": row["target_id"],
                    "query_text": row["query_text"],
                    "query_type": row["query_type"],
                    "query_source": row["query_source"],
                    "validation_status": row["validation_status"],
                    "query_note": row["query_note"],
                    "order": row["query_order"],
                    "enabled": bool(row["enabled"]),
                }
            )
        return [
            {
                "target_id": row["target_id"],
                "dataset_id": row["dataset_id"],
                "dataset_version": row["dataset_version"],
                "dataset_status": row["dataset_status"],
                "standard_name": row["standard_name"],
                "target_type": row["target_type"],
                "source_name": row["source_name"],
                "source_reference": row["source_reference"],
                "source_date": row["source_date"],
                "enabled": bool(row["enabled"]),
                "dataset": {
                    "dataset_id": row["dataset_id"],
                    "dataset_version": row["dataset_version"],
                    "dataset_status": row["dataset_status"],
                    "source_name": row["dataset_source_name"],
                    "source_reference": row["dataset_source_reference"],
                    "source_date": row["dataset_source_date"],
                    "collected_at": row["dataset_collected_at"],
                    "verified_at": row["dataset_verified_at"],
                    "description": row["dataset_description"],
                },
                "queries": by_target.get(str(row["target_id"]), []),
            }
            for row in targets
        ]

    def get_monitor_target(self, target_id: str) -> dict[str, Any] | None:
        return next(
            (
                item
                for item in self.list_monitor_targets()
                if item["target_id"] == target_id
            ),
            None,
        )

    def import_all_runs(self) -> dict[str, int]:
        result = {"discovered": 0, "imported": 0, "skipped": 0}
        if not self.output_root.is_dir():
            return result
        for run_root in sorted(self.output_root.iterdir()):
            if not run_root.is_dir() or not (run_root / "web_snapshot.json").is_file():
                continue
            result["discovered"] += 1
            try:
                self.import_run(run_root)
            except (OSError, ValueError, TypeError, sqlite3.Error):
                result["skipped"] += 1
            else:
                result["imported"] += 1
        return result

    def import_run(self, run_root: Path) -> dict[str, int]:
        """Upsert one run without replacing an existing human review."""

        run_root = run_root.resolve()
        if run_root.parent != self.output_root:
            raise ValueError("run directory must be a direct child of output root")
        snapshot = read_json(run_root / "web_snapshot.json")
        if not isinstance(snapshot, dict):
            raise ValueError("web_snapshot.json must contain an object")
        task = snapshot.get("task") or {}
        task_id = str(task.get("id") or run_root.name)
        if task_id != run_root.name:
            raise ValueError("snapshot task id does not match run directory")
        request = _read_optional_json(run_root / "task_request.json", {})
        config = _read_optional_json(run_root / "run_config.json", {})
        generated_at = str(snapshot.get("generatedAt") or iso_now())
        stage = str(task.get("stage") or "")
        terminal = bool(task.get("terminal"))
        created_at = request.get("created_at") or config.get("generated_at")
        candidate_limit = (
            request.get("candidate_limit")
            or config.get("resolved_candidate_limit")
            or config.get("candidate_limit")
            or config.get("limit")
        )
        detail_limit = (
            request.get("detail_limit")
            or config.get("resolved_detail_limit")
            or config.get("detail_limit")
        )
        task_type = str(request.get("task_type") or config.get("task_type") or "quick")
        target_id = request.get("target_id") or config.get("target_id")
        per_query_candidate_limit = (
            request.get("per_query_candidate_limit")
            or config.get("per_query_candidate_limit")
            or config.get("resolved_per_query_candidate_limit")
        )
        products = [
            item for item in (snapshot.get("products") or []) if isinstance(item, dict)
        ]
        imported_evidence = 0
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO tasks (
                    task_id, keyword, candidate_limit, detail_limit, stage,
                    created_at, started_at, completed_at, run_path, updated_at,
                    task_type, target_id, per_query_candidate_limit
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    keyword=excluded.keyword,
                    candidate_limit=COALESCE(excluded.candidate_limit, tasks.candidate_limit),
                    detail_limit=COALESCE(excluded.detail_limit, tasks.detail_limit),
                    stage=excluded.stage,
                    created_at=COALESCE(tasks.created_at, excluded.created_at),
                    started_at=COALESCE(tasks.started_at, excluded.started_at),
                    completed_at=excluded.completed_at,
                    run_path=excluded.run_path,
                    updated_at=excluded.updated_at,
                    task_type=excluded.task_type,
                    target_id=excluded.target_id,
                    per_query_candidate_limit=COALESCE(
                        excluded.per_query_candidate_limit,
                        tasks.per_query_candidate_limit
                    )
                """,
                (
                    task_id,
                    str(task.get("keyword") or ""),
                    int(candidate_limit) if candidate_limit is not None else None,
                    int(detail_limit) if detail_limit is not None else None,
                    stage,
                    created_at,
                    created_at,
                    generated_at if terminal else None,
                    run_root.name,
                    generated_at,
                    task_type,
                    target_id,
                    int(per_query_candidate_limit)
                    if per_query_candidate_limit is not None
                    else None,
                ),
            )
            for product in products:
                product_id = str(product.get("id") or "").strip()
                if not product_id:
                    continue
                collected_at = product.get("collectedAt")
                connection.execute(
                    """
                    INSERT INTO products (taobao_product_id, first_seen_at, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(taobao_product_id) DO UPDATE SET
                        first_seen_at=COALESCE(products.first_seen_at, excluded.first_seen_at),
                        updated_at=excluded.updated_at
                    """,
                    (product_id, collected_at or generated_at, generated_at),
                )
                snapshot_id = make_snapshot_id(task_id, product_id)
                risk = product.get("risk") or {}
                assets = product.get("assets") or {}
                status = product.get("status") or {}
                review_required = risk.get("reviewRequired")
                if review_required is not None:
                    review_required = 1 if review_required else 0
                connection.execute(
                    """
                    INSERT INTO product_snapshots (
                        snapshot_id, product_id, task_id, rank, product_name,
                        shop_name, region, product_url, collected_at, status,
                        detected_effects_json, review_required, analysis_summary,
                        product_path, meta_path, analysis_path,
                        original_image_count, ocr_image_count, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(snapshot_id) DO UPDATE SET
                        rank=excluded.rank,
                        product_name=excluded.product_name,
                        shop_name=excluded.shop_name,
                        region=excluded.region,
                        product_url=excluded.product_url,
                        collected_at=excluded.collected_at,
                        status=excluded.status,
                        detected_effects_json=excluded.detected_effects_json,
                        review_required=excluded.review_required,
                        analysis_summary=excluded.analysis_summary,
                        product_path=excluded.product_path,
                        meta_path=excluded.meta_path,
                        analysis_path=excluded.analysis_path,
                        original_image_count=excluded.original_image_count,
                        ocr_image_count=excluded.ocr_image_count,
                        updated_at=excluded.updated_at
                    """,
                    (
                        snapshot_id,
                        product_id,
                        task_id,
                        product.get("rank"),
                        str(product.get("name") or ""),
                        str(product.get("shopName") or ""),
                        str(product.get("region") or ""),
                        str(product.get("productUrl") or ""),
                        collected_at,
                        str(status.get("code") or ""),
                        _json_text(risk.get("detectedEffects"), []),
                        review_required,
                        str(risk.get("reason") or ""),
                        f"products/{product_id}",
                        assets.get("metaPath"),
                        assets.get("analysisPath"),
                        int((product.get("counts") or {}).get("originalImages") or 0),
                        int((product.get("counts") or {}).get("ocrImages") or 0),
                        generated_at,
                    ),
                )
                connection.execute(
                    "INSERT OR IGNORE INTO reviews (snapshot_id) VALUES (?)",
                    (snapshot_id,),
                )
                connection.execute(
                    "DELETE FROM evidence WHERE snapshot_id = ?", (snapshot_id,)
                )
                evidence_items = [
                    item
                    for item in (risk.get("evidenceDetails") or [])
                    if isinstance(item, dict)
                ]
                for ordinal, item in enumerate(evidence_items, start=1):
                    evidence_id = f"{snapshot_id}_e{ordinal:04d}"
                    connection.execute(
                        """
                        INSERT INTO evidence (
                            evidence_id, snapshot_id, ordinal, effect, text,
                            matched_keywords_json, source_type, source_label,
                            content_origin, source_path, line_number
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            evidence_id,
                            snapshot_id,
                            ordinal,
                            str(item.get("effect") or ""),
                            str(item.get("text") or ""),
                            _json_text(
                                item.get("matched_keywords")
                                or item.get("matchedKeywords"),
                                [],
                            ),
                            str(item.get("source_type") or item.get("sourceType") or ""),
                            str(item.get("source_label") or item.get("sourceLabel") or ""),
                            str(item.get("content_origin") or item.get("contentOrigin") or ""),
                            str(item.get("source_path") or item.get("sourcePath") or ""),
                            item.get("line_number") or item.get("lineNumber"),
                        ),
                    )
                imported_evidence += len(evidence_items)
            discovery = _read_optional_json(
                run_root / "search" / "discovery_summary.json", {}
            )
            if not isinstance(discovery, dict):
                discovery = {}
            for item in discovery.get("candidate_hits") or []:
                if not isinstance(item, dict):
                    continue
                product_id = str(item.get("product_id") or "").strip()
                query_id = str(item.get("query_id") or "").strip()
                if not product_id or not query_id:
                    continue
                connection.execute(
                    """
                    INSERT OR IGNORE INTO products (
                        taobao_product_id, first_seen_at, updated_at
                    ) VALUES (?, ?, ?)
                    """,
                    (
                        product_id,
                        item.get("discovered_at") or generated_at,
                        generated_at,
                    ),
                )
                hit_id = hashlib.sha256(
                    f"{task_id}\0{product_id}\0{query_id}".encode("utf-8")
                ).hexdigest()[:24]
                connection.execute(
                    """
                    INSERT INTO candidate_hits (
                        hit_id, task_id, product_id, query_id, query_text,
                        rank, discovered_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(task_id, product_id, query_id) DO UPDATE SET
                        query_text=excluded.query_text,
                        rank=excluded.rank,
                        discovered_at=excluded.discovered_at
                    """,
                    (
                        f"hit_{hit_id}",
                        task_id,
                        product_id,
                        query_id,
                        str(item.get("query_text") or ""),
                        item.get("rank"),
                        str(item.get("discovered_at") or generated_at),
                    ),
                )
        return {
            "tasks": 1,
            "products": len(products),
            "evidence": imported_evidence,
            "candidate_hits": len(
                (discovery.get("candidate_hits") or []) if isinstance(discovery, dict) else []
            ),
        }

    @staticmethod
    def _snapshot_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "snapshotId": row["snapshot_id"],
            "productId": row["product_id"],
            "taskId": row["task_id"],
            "targetId": row["target_id"],
            "targetName": row["target_name"],
            "rank": row["rank"],
            "productName": row["product_name"],
            "shopName": row["shop_name"],
            "region": row["region"],
            "productUrl": row["product_url"],
            "collectedAt": row["collected_at"],
            "status": row["status"],
            "detectedEffects": _json_value(row["detected_effects_json"], []),
            "reviewRequired": (
                None if row["review_required"] is None else bool(row["review_required"])
            ),
            "analysisSummary": row["analysis_summary"],
            "paths": {
                "run": row["run_path"],
                "product": row["product_path"],
                "meta": row["meta_path"],
                "analysis": row["analysis_path"],
            },
            "counts": {
                "originalImages": row["original_image_count"],
                "ocrImages": row["ocr_image_count"],
            },
            "review": {
                "status": row["review_status"],
                "note": row["review_note"],
                "reviewedAt": row["reviewed_at"],
            },
        }

    def _base_snapshot_query(self) -> str:
        return """
            SELECT s.*, t.run_path, t.target_id,
                   mt.standard_name AS target_name,
                   r.review_status, r.review_note, r.reviewed_at
        """ + self._base_snapshot_from()

    @staticmethod
    def _base_snapshot_from() -> str:
        return """
            FROM product_snapshots s
            JOIN tasks t ON t.task_id = s.task_id
            JOIN reviews r ON r.snapshot_id = s.snapshot_id
            LEFT JOIN monitor_targets mt ON mt.target_id = t.target_id
        """

    def _product_filter(
        self,
        *,
        query: str = "",
        review_status: str = "",
        effect: str = "",
        task_id: str = "",
        target_id: str = "",
    ) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        values: list[Any] = []
        if query:
            clauses.append(
                "(s.product_name LIKE ? OR s.shop_name LIKE ? OR s.product_id LIKE ?)"
            )
            needle = f"%{query}%"
            values.extend([needle, needle, needle])
        if review_status:
            if review_status not in REVIEW_STATUSES:
                raise ReviewValidationError("人工复核状态不合法")
            clauses.append("r.review_status = ?")
            values.append(review_status)
        if effect:
            clauses.append("s.detected_effects_json LIKE ?")
            values.append(f'%"{effect}"%')
        if task_id:
            clauses.append("s.task_id = ?")
            values.append(task_id)
        if target_id:
            clauses.append("t.target_id = ?")
            values.append(target_id)
        if not task_id:
            target_scope = ""
            if target_id:
                target_scope = " AND newer_task.target_id = ?"
            clauses.append(
                """
                NOT EXISTS (
                    SELECT 1
                    FROM product_snapshots newer
                    JOIN tasks newer_task ON newer_task.task_id = newer.task_id
                    WHERE newer.product_id = s.product_id
                """
                + target_scope
                + """
                      AND (COALESCE(newer.collected_at, '') > COALESCE(s.collected_at, '')
                           OR (COALESCE(newer.collected_at, '') = COALESCE(s.collected_at, '')
                               AND newer.task_id > s.task_id))
                )
                """
            )
            if target_id:
                values.append(target_id)
        return " WHERE " + " AND ".join(clauses), values

    def list_products(
        self,
        *,
        query: str = "",
        review_status: str = "",
        effect: str = "",
        task_id: str = "",
        target_id: str = "",
        page: int = 1,
        page_size: int = 20,
    ) -> list[dict[str, Any]]:
        where, values = self._product_filter(
            query=query,
            review_status=review_status,
            effect=effect,
            task_id=task_id,
            target_id=target_id,
        )
        if task_id:
            order = " ORDER BY s.rank, s.product_id"
        else:
            order = " ORDER BY COALESCE(s.collected_at, '') DESC, s.product_id"
        sql = self._base_snapshot_query() + where + order + " LIMIT ? OFFSET ?"
        values.extend([page_size, (page - 1) * page_size])
        with self._connect() as connection:
            rows = connection.execute(sql, values).fetchall()
        return [self._snapshot_dict(row) for row in rows]

    def count_products(
        self,
        *,
        query: str = "",
        review_status: str = "",
        effect: str = "",
        task_id: str = "",
        target_id: str = "",
    ) -> int:
        where, values = self._product_filter(
            query=query,
            review_status=review_status,
            effect=effect,
            task_id=task_id,
            target_id=target_id,
        )
        sql = "SELECT COUNT(*)" + self._base_snapshot_from() + where
        with self._connect() as connection:
            return int(connection.execute(sql, values).fetchone()[0])

    def list_product_snapshots(self, product_id: str) -> list[dict[str, Any]]:
        sql = (
            self._base_snapshot_query()
            + " WHERE s.product_id = ? ORDER BY COALESCE(s.collected_at, '') DESC, s.task_id DESC"
        )
        with self._connect() as connection:
            rows = connection.execute(sql, (product_id,)).fetchall()
        return [self._snapshot_dict(row) for row in rows]

    def get_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        sql = self._base_snapshot_query() + " WHERE s.snapshot_id = ?"
        with self._connect() as connection:
            row = connection.execute(sql, (snapshot_id,)).fetchone()
            if row is None:
                raise SnapshotNotFoundError("商品快照不存在")
            evidence_rows = connection.execute(
                "SELECT * FROM evidence WHERE snapshot_id = ? ORDER BY ordinal",
                (snapshot_id,),
            ).fetchall()
        result = self._snapshot_dict(row)
        result["evidence"] = [
            {
                "evidenceId": item["evidence_id"],
                "effect": item["effect"],
                "text": item["text"],
                "matchedKeywords": _json_value(item["matched_keywords_json"], []),
                "sourceType": item["source_type"],
                "sourceLabel": item["source_label"],
                "contentOrigin": item["content_origin"],
                "sourcePath": item["source_path"],
                "lineNumber": item["line_number"],
            }
            for item in evidence_rows
        ]
        return result

    def update_review(
        self, snapshot_id: str, review_status: str, review_note: str = ""
    ) -> dict[str, Any]:
        if review_status not in REVIEW_STATUSES:
            raise ReviewValidationError("人工复核状态不合法")
        note = str(review_note or "").strip()
        if len(note) > 2000:
            raise ReviewValidationError("复核备注不能超过2000个字符")
        reviewed_at = None if review_status == "pending" else iso_now()
        with self._connect() as connection:
            exists = connection.execute(
                "SELECT 1 FROM product_snapshots WHERE snapshot_id = ?", (snapshot_id,)
            ).fetchone()
            if exists is None:
                raise SnapshotNotFoundError("商品快照不存在")
            connection.execute(
                """
                INSERT INTO reviews (snapshot_id, review_status, review_note, reviewed_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(snapshot_id) DO UPDATE SET
                    review_status=excluded.review_status,
                    review_note=excluded.review_note,
                    reviewed_at=excluded.reviewed_at
                """,
                (snapshot_id, review_status, note, reviewed_at),
            )
        return self.get_snapshot(snapshot_id)["review"]

    def list_candidate_hits(self, task_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT h.*, q.query_type, q.query_order
                FROM candidate_hits h
                JOIN search_queries q ON q.query_id = h.query_id
                WHERE h.task_id = ?
                ORDER BY q.query_order, COALESCE(h.rank, 1000000000), h.product_id
                """,
                (task_id,),
            ).fetchall()
        return [
            {
                "hitId": row["hit_id"],
                "taskId": row["task_id"],
                "productId": row["product_id"],
                "queryId": row["query_id"],
                "queryText": row["query_text"],
                "queryType": row["query_type"],
                "queryOrder": row["query_order"],
                "rank": row["rank"],
                "discoveredAt": row["discovered_at"],
            }
            for row in rows
        ]

    def table_counts(self) -> dict[str, int]:
        with self._connect() as connection:
            return {
                table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                for table in (
                    "tasks",
                    "products",
                    "product_snapshots",
                    "evidence",
                    "reviews",
                    "monitor_datasets",
                    "monitor_targets",
                    "search_queries",
                    "candidate_hits",
                )
            }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="索引已有运行结果到本地SQLite")
    parser.add_argument("--output-root", type=Path, default=Path("output"))
    parser.add_argument("--database", type=Path, default=Path("data/app.db"))
    parser.add_argument(
        "--monitor-config",
        type=Path,
        action="append",
        dest="monitor_configs",
        help="可重复指定；默认导入development与reference数据集",
    )
    parser.add_argument("--run-id")
    args = parser.parse_args(argv)
    store = DataStore(args.database, args.output_root)
    store.initialize()
    monitor_configs = args.monitor_configs or list(DEFAULT_MONITOR_CONFIG_PATHS)
    monitor_imports = []
    for monitor_config in monitor_configs:
        if not monitor_config.is_file():
            if args.monitor_configs:
                raise FileNotFoundError(f"监测数据集不存在：{monitor_config}")
            continue
        monitor_imports.append(store.import_monitor_config(monitor_config))
    result = (
        store.import_run((args.output_root / args.run_id).resolve())
        if args.run_id
        else store.import_all_runs()
    )
    print(
        json.dumps(
            {
                "monitor_imports": monitor_imports,
                "result": result,
                "counts": store.table_counts(),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
