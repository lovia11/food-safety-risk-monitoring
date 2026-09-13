"""Governed query-validation planning and tracked-ledger checks."""

from __future__ import annotations

import copy
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
REVIEW_LABELS = {
    "relevant_food",
    "raw_medicinal_or_nonfood_scope",
    "non_food",
    "ambiguous",
    "duplicate",
}
REVIEW_LABEL_ZH = {
    "relevant_food": "食品相关",
    "raw_medicinal_or_nonfood_scope": "药材/非食品监管范围",
    "non_food": "非食品",
    "ambiguous": "信息不足，无法判断",
    "duplicate": "重复结果",
}
REVIEW_LABEL_ALIASES = {value: key for key, value in REVIEW_LABEL_ZH.items()}
DECISION_ZH = {
    "promote": "通过验证，可启用",
    "hold": "暂缓启用",
    "reject": "不采用",
}
DECISION_ALIASES = {value: key for key, value in DECISION_ZH.items()}


def normalize_review_label(value: Any) -> str:
    label = str(value or "").strip()
    normalized = REVIEW_LABEL_ALIASES.get(label, label)
    if normalized not in REVIEW_LABELS:
        raise ValueError(f"人工标签不合法：{label}")
    return normalized


def review_label_zh(value: Any) -> str:
    return REVIEW_LABEL_ZH[normalize_review_label(value)]


def normalize_validation_decision(value: Any) -> str:
    decision = str(value or "").strip()
    normalized = DECISION_ALIASES.get(decision, decision)
    if normalized not in FINAL_DECISIONS:
        raise ValueError(f"验证决策不合法：{decision}")
    return normalized


def validation_decision_zh(value: Any) -> str:
    return DECISION_ZH[normalize_validation_decision(value)]


def calculate_review_metrics(
    results: list[dict[str, Any]],
    *,
    sample_size: int = 10,
) -> dict[str, Any]:
    """Calculate the fixed first-N assessable sample without inferring labels."""

    if sample_size < 1:
        raise ValueError("sample_size必须大于0")
    ranks = [int(item.get("rank") or 0) for item in results]
    if any(rank < 1 for rank in ranks) or ranks != sorted(ranks) or len(set(ranks)) != len(ranks):
        raise ValueError("人工复核结果必须保持唯一、递增的原始rank")
    evaluation_ranks: list[int] = []
    relevant_count = 0
    raw_scope_count = 0
    non_food_count = 0
    ambiguous_skipped = 0
    duplicate_skipped = 0
    for item in results:
        if len(evaluation_ranks) >= sample_size:
            break
        value = item.get("reviewedLabel")
        if value in {None, ""}:
            raise ValueError(
                f"Rank {item.get('rank')}尚未人工标注，无法得到前{sample_size}个可评估结果"
            )
        label = normalize_review_label(value)
        if label == "ambiguous":
            ambiguous_skipped += 1
            continue
        if label == "duplicate":
            duplicate_skipped += 1
            continue
        evaluation_ranks.append(int(item["rank"]))
        if label == "relevant_food":
            relevant_count += 1
        elif label == "raw_medicinal_or_nonfood_scope":
            raw_scope_count += 1
        elif label == "non_food":
            non_food_count += 1
    assessable_count = len(evaluation_ranks)
    if assessable_count < sample_size:
        raise ValueError(
            f"只有{assessable_count}个可评估结果，未达到固定样本量{sample_size}"
        )
    relevance_rate = round(relevant_count / assessable_count, 4)
    return {
        "sampleSize": sample_size,
        "assessableCount": assessable_count,
        "relevantCount": relevant_count,
        "rawMedicinalOrNonfoodScopeCount": raw_scope_count,
        "nonFoodCount": non_food_count,
        "ambiguousSkipped": ambiguous_skipped,
        "duplicateSkipped": duplicate_skipped,
        "relevanceRate": relevance_rate,
        "evaluationRanks": evaluation_ranks,
    }


def finalize_review_queue(
    queue: dict[str, Any],
    *,
    assignments: list[dict[str, Any]],
    decision: str,
    decision_note: str,
    systematic_scope_issue: bool,
    observed_product_forms: list[str] | None,
    reviewed_at: str,
    reviewed_by: str = "human_review",
) -> dict[str, Any]:
    reviewer = str(reviewed_by or "").strip()
    if not reviewer or reviewer.lower() in {"codex", "chatgpt"}:
        raise ValueError("reviewedBy必须标识真实人工复核，不能写Codex/ChatGPT")
    if not str(reviewed_at or "").strip():
        raise ValueError("reviewedAt不能为空")
    note = str(decision_note or "").strip()
    if not note:
        raise ValueError("decisionNote不能为空")
    normalized_decision = normalize_validation_decision(decision)
    finalized = copy.deepcopy(queue)
    results = finalized.get("results")
    if not isinstance(results, list):
        raise ValueError("review artifact必须包含results数组")
    by_rank = {int(item.get("rank") or 0): item for item in results}
    assigned_ranks: set[int] = set()
    for assignment in assignments:
        rank = int(assignment.get("rank") or 0)
        if rank in assigned_ranks:
            raise ValueError(f"人工复核输入rank重复：{rank}")
        if rank not in by_rank:
            raise ValueError(f"人工复核输入rank不存在：{rank}")
        assigned_ranks.add(rank)
        label = normalize_review_label(
            assignment.get("reviewedLabel", assignment.get("label"))
        )
        row = by_rank[rank]
        existing = row.get("reviewedLabel")
        if existing not in {None, ""} and normalize_review_label(existing) != label:
            raise ValueError(f"Rank {rank}已有不同人工标签，拒绝覆盖")
        row.update(
            {
                "reviewedLabel": label,
                "reviewedLabelZh": REVIEW_LABEL_ZH[label],
                "reviewNote": str(
                    assignment.get("reviewNote", assignment.get("note")) or ""
                ).strip()
                or None,
                "reviewedAt": reviewed_at,
                "reviewedBy": reviewer,
            }
        )
    metrics = calculate_review_metrics(results)
    numeric_gate_passed = (
        metrics["assessableCount"] >= 10
        and metrics["relevanceRate"] >= 0.70
        and metrics["relevantCount"] >= 5
    )
    if normalized_decision == "promote" and (
        not numeric_gate_passed or systematic_scope_issue
    ):
        raise ValueError("promote决策不满足固定数值Gate或仍存在系统性范围问题")
    finalized.update(
        {
            "reviewStatus": "reviewed",
            "reviewedAt": reviewed_at,
            "reviewedBy": reviewer,
            "metrics": metrics,
            "decision": normalized_decision,
            "decisionZh": DECISION_ZH[normalized_decision],
            "decisionNote": note,
            "systematicScopeIssue": bool(systematic_scope_issue),
            "numericGatePassed": numeric_gate_passed,
            "observedProductForms": list(observed_product_forms or []),
        }
    )
    return finalized


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
        if record.get("protocol_version"):
            reviewed_required = {
                "query_text",
                "reviewed_at",
                "assessable_count",
                "raw_medicinal_or_nonfood_scope_count",
                "non_food_count",
                "ambiguous_skipped",
                "duplicate_skipped",
                "decision_note",
                "systematic_scope_issue",
                "observed_product_forms",
                "artifact_ref",
                "review_artifact_ref",
            }
            missing_reviewed = sorted(reviewed_required - record.keys())
            if missing_reviewed:
                raise ValueError(
                    f"V2-4 ledger record缺少字段：{', '.join(missing_reviewed)}"
                )
            assessable = int(record["assessable_count"])
            relevant = int(record["relevant_count"])
            raw_scope = int(record["raw_medicinal_or_nonfood_scope_count"])
            non_food = int(record["non_food_count"])
            if assessable != int(record["sample_size"]):
                raise ValueError(f"ledger sample_size/assessable_count不一致：{query_id}")
            if relevant + raw_scope + non_food != assessable:
                raise ValueError(f"ledger可评估标签计数不守恒：{query_id}")
            expected_rate = round(relevant / assessable, 4) if assessable else 0.0
            if float(record["relevance_rate"]) != expected_rate:
                raise ValueError(f"ledger relevance_rate与标签计数不一致：{query_id}")
            if int(record["ambiguous_count"]) != int(record["ambiguous_skipped"]):
                raise ValueError(f"ledger ambiguous计数不一致：{query_id}")
            if not str(record["reviewed_at"] or "").strip():
                raise ValueError(f"ledger reviewed_at不能为空：{query_id}")
            if not str(record["decision_note"] or "").strip():
                raise ValueError(f"ledger decision_note不能为空：{query_id}")
            if not isinstance(record["observed_product_forms"], list):
                raise ValueError(f"ledger observed_product_forms必须是数组：{query_id}")
        records[query_id] = record

    governed: dict[str, tuple[str, str, str]] = {}
    for target in config["targets"]:
        for query in target.get("queries") or []:
            status = normalized_validation_status(query.get("validation_status"))
            if status in LEDGER_REQUIRED_STATUSES:
                governed[query["query_id"]] = (
                    target["target_id"],
                    status,
                    str(query.get("query_text") or ""),
                )
    missing_records = sorted(set(governed) - set(records))
    if missing_records:
        raise ValueError(
            "validated/rejected Query缺少ledger记录：" + ", ".join(missing_records)
        )
    for query_id, (target_id, status, query_text) in governed.items():
        record = records[query_id]
        if record["target_id"] != target_id:
            raise ValueError(f"ledger target_id与Query不一致：{query_id}")
        if record.get("query_text") is not None and record["query_text"] != query_text:
            raise ValueError(f"ledger query_text与Query不一致：{query_id}")
        expected = "promote" if status == "search_validated" else None
        if expected and record["decision"] != expected:
            raise ValueError(f"search_validated Query必须具有promote记录：{query_id}")
        if status in {"rejected_low_relevance", "paused_scope_issue", "deprecated"} and record[
            "decision"
        ] == "promote":
            raise ValueError(f"paused/rejected Query不能具有promote记录：{query_id}")
    return ledger
