"""Governed query-validation planning and tracked-ledger checks."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.monitor_coverage import normalized_validation_status


FINAL_DECISIONS = {"promote", "hold", "reject"}
LEDGER_REQUIRED_STATUSES = {
    "search_validated",
    "rejected_low_relevance",
    "paused_scope_issue",
    "deprecated",
}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def select_validation_queries(
    config: dict[str, Any],
    *,
    target_ids: set[str] | None = None,
    query_ids: set[str] | None = None,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    selected: list[tuple[dict[str, Any], dict[str, Any]]] = []
    known_targets = {target["target_id"] for target in config["targets"]}
    known_queries = {
        query["query_id"]
        for target in config["targets"]
        for query in target.get("queries") or []
    }
    if target_ids:
        missing = sorted(target_ids - known_targets)
        if missing:
            raise ValueError(f"配置中不存在MonitorTarget：{', '.join(missing)}")
    if query_ids:
        missing = sorted(query_ids - known_queries)
        if missing:
            raise ValueError(f"配置中不存在SearchQuery：{', '.join(missing)}")
    for target in config["targets"]:
        if target_ids and target["target_id"] not in target_ids:
            continue
        for query in target.get("queries") or []:
            if query_ids and query["query_id"] not in query_ids:
                continue
            if not query_ids and normalized_validation_status(
                query.get("validation_status")
            ) != "candidate_unvalidated":
                continue
            selected.append((target, query))
    selected.sort(
        key=lambda item: (
            str(item[0].get("target_id") or ""),
            int(item[1].get("order") or 0),
            str(item[1].get("query_id") or ""),
        )
    )
    if not selected:
        raise ValueError("没有符合条件的待验证SearchQuery")
    return selected


def validation_dry_run(
    *,
    batch_id: str,
    output_root: Path,
    max_results: int,
    selected: list[tuple[dict[str, Any], dict[str, Any]]],
) -> dict[str, Any]:
    if not batch_id.strip():
        raise ValueError("batch不能为空")
    if not 1 <= max_results <= 20:
        raise ValueError("max-results必须在1到20之间")
    return {
        "batchId": batch_id,
        "dryRun": True,
        "searchOnly": True,
        "collectionRawLimit": max_results,
        "evaluationSampleSize": 10,
        "plannedResultSampleSize": 10,
        "outputDestination": str((output_root / batch_id).resolve()),
        "queryCount": len(selected),
        "queries": [
            {
                "targetId": target["target_id"],
                "standardName": target["standard_name"],
                "queryId": query["query_id"],
                "queryText": query["query_text"],
                "validationStatus": query["validation_status"],
            }
            for target, query in selected
        ],
    }


def validate_validation_ledger(
    config: dict[str, Any], ledger: Any
) -> dict[str, Any]:
    if not isinstance(ledger, dict) or not isinstance(ledger.get("records"), list):
        raise ValueError("validation ledger必须包含records数组")
    records: dict[str, dict[str, Any]] = {}
    required_fields = {
        "query_id",
        "target_id",
        "batch_id",
        "validation_date",
        "sample_size",
        "relevant_count",
        "ambiguous_count",
        "relevance_rate",
        "decision",
        "validation_note",
        "artifact_manifest_sha256",
    }
    for record in ledger["records"]:
        if not isinstance(record, dict):
            raise ValueError("validation ledger record必须是JSON对象")
        missing = sorted(required_fields - record.keys())
        if missing:
            raise ValueError(f"ledger record缺少字段：{', '.join(missing)}")
        query_id = str(record["query_id"] or "")
        if not query_id or query_id in records:
            raise ValueError(f"ledger query_id为空或重复：{query_id}")
        if record["decision"] not in FINAL_DECISIONS:
            raise ValueError(f"ledger decision不合法：{record['decision']}")
        sha256 = str(record["artifact_manifest_sha256"] or "")
        if not SHA256_PATTERN.fullmatch(sha256):
            raise ValueError(f"ledger SHA256不合法：{query_id}")
        records[query_id] = record

    governed: dict[str, tuple[str, str]] = {}
    for target in config["targets"]:
        for query in target.get("queries") or []:
            status = normalized_validation_status(query.get("validation_status"))
            if status in LEDGER_REQUIRED_STATUSES:
                governed[query["query_id"]] = (target["target_id"], status)
    missing_records = sorted(set(governed) - set(records))
    if missing_records:
        raise ValueError(
            "validated/rejected Query缺少ledger记录：" + ", ".join(missing_records)
        )
    for query_id, (target_id, status) in governed.items():
        record = records[query_id]
        if record["target_id"] != target_id:
            raise ValueError(f"ledger target_id与Query不一致：{query_id}")
        expected = "promote" if status == "search_validated" else None
        if expected and record["decision"] != expected:
            raise ValueError(f"search_validated Query必须具有promote记录：{query_id}")
    return ledger
