"""SQLite business index for task, product snapshot, evidence and review data.

The run directory remains the source of truth for large/raw collector artifacts.
This module stores only queryable business fields and relative artifact paths.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from src.runtime import iso_now, read_json


REVIEW_STATUSES = {"pending", "recommend_follow_up", "no_further_action"}
TARGET_TYPES = {"food_medicine", "health_food"}
QUERY_TYPES = {"base", "product_form"}
SCHEMA_VERSION = 2


class DataStoreError(RuntimeError):
    """Base error for the local business data index."""


class SnapshotNotFoundError(DataStoreError):
    """The requested product snapshot does not exist."""


class ReviewValidationError(DataStoreError):
    """A review update contains an unsupported value."""


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

                CREATE TABLE IF NOT EXISTS monitor_targets (
                    target_id TEXT PRIMARY KEY,
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
        payload = read_json(config_path)
        targets = [
            item for item in (payload.get("targets") or []) if isinstance(item, dict)
        ]
        target_count = 0
        query_count = 0
        now = iso_now()
        with self._connect() as connection:
            for target in targets:
                target_id = str(target.get("target_id") or "").strip()
                target_type = str(target.get("target_type") or "").strip()
                if not target_id or not str(target.get("standard_name") or "").strip():
                    raise ValueError("MonitorTarget必须包含target_id和standard_name")
                if target_type not in TARGET_TYPES:
                    raise ValueError(f"不支持的target_type：{target_type}")
                connection.execute(
                    """
                    INSERT INTO monitor_targets (
                        target_id, standard_name, target_type, source_name,
                        source_reference, source_date, enabled, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(target_id) DO UPDATE SET
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
                for position, query in enumerate(target.get("queries") or [], start=1):
                    if not isinstance(query, dict):
                        continue
                    query_id = str(query.get("query_id") or "").strip()
                    query_text = str(query.get("query_text") or "").strip()
                    query_type = str(query.get("query_type") or "base").strip()
                    if not query_id or not query_text:
                        raise ValueError("SearchQuery必须包含query_id和query_text")
                    if query_type not in QUERY_TYPES:
                        raise ValueError(f"不支持的query_type：{query_type}")
                    connection.execute(
                        """
                        INSERT INTO search_queries (
                            query_id, target_id, query_text, query_type,
                            query_order, enabled, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(query_id) DO UPDATE SET
                            target_id=excluded.target_id,
                            query_text=excluded.query_text,
                            query_type=excluded.query_type,
                            query_order=excluded.query_order,
                            enabled=excluded.enabled,
                            updated_at=excluded.updated_at
                        """,
                        (
                            query_id,
                            target_id,
                            query_text,
                            query_type,
                            int(query.get("order") or position),
                            1 if query.get("enabled", True) else 0,
                            now,
                        ),
                    )
                    query_count += 1
        return {"targets": target_count, "queries": query_count}

    def list_monitor_targets(self, *, enabled_only: bool = False) -> list[dict[str, Any]]:
        where = " WHERE t.enabled = 1" if enabled_only else ""
        with self._connect() as connection:
            targets = connection.execute(
                "SELECT t.* FROM monitor_targets t" + where + " ORDER BY t.standard_name, t.target_id"
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
                    "order": row["query_order"],
                    "enabled": bool(row["enabled"]),
                }
            )
        return [
            {
                "target_id": row["target_id"],
                "standard_name": row["standard_name"],
                "target_type": row["target_type"],
                "source_name": row["source_name"],
                "source_reference": row["source_reference"],
                "source_date": row["source_date"],
                "enabled": bool(row["enabled"]),
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
            SELECT s.*, t.run_path, r.review_status, r.review_note, r.reviewed_at
            FROM product_snapshots s
            JOIN tasks t ON t.task_id = s.task_id
            JOIN reviews r ON r.snapshot_id = s.snapshot_id
        """

    def list_products(
        self,
        *,
        query: str = "",
        review_status: str = "",
        effect: str = "",
        task_id: str = "",
    ) -> list[dict[str, Any]]:
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
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        # One product row per task when task_id is supplied; otherwise expose the
        # newest observation for each stable Taobao product identity.
        if task_id:
            sql = self._base_snapshot_query() + where + " ORDER BY s.rank, s.product_id"
        else:
            latest = """
                AND NOT EXISTS (
                    SELECT 1 FROM product_snapshots newer
                    WHERE newer.product_id = s.product_id
                      AND (COALESCE(newer.collected_at, '') > COALESCE(s.collected_at, '')
                           OR (COALESCE(newer.collected_at, '') = COALESCE(s.collected_at, '')
                               AND newer.task_id > s.task_id))
                )
            """
            sql = self._base_snapshot_query() + where
            sql += latest if where else " WHERE 1=1" + latest
            sql += " ORDER BY COALESCE(s.collected_at, '') DESC, s.product_id"
        with self._connect() as connection:
            rows = connection.execute(sql, values).fetchall()
        return [self._snapshot_dict(row) for row in rows]

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
        default=Path("config/monitor_targets.development.json"),
    )
    parser.add_argument("--run-id")
    args = parser.parse_args(argv)
    store = DataStore(args.database, args.output_root)
    store.initialize()
    if args.monitor_config.is_file():
        store.import_monitor_config(args.monitor_config)
    result = (
        store.import_run((args.output_root / args.run_id).resolve())
        if args.run_id
        else store.import_all_runs()
    )
    print(json.dumps({"result": result, "counts": store.table_counts()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
