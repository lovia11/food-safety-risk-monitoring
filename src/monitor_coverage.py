"""Pure MonitorTarget/SearchQuery coverage and availability rules."""

from __future__ import annotations

from typing import Any, Iterable


SEARCH_VALIDATED = "search_validated"
CANDIDATE_UNVALIDATED = "candidate_unvalidated"
PAUSED_QUERY_STATUSES = {
    "rejected_low_relevance",
    "paused_scope_issue",
    "deprecated",
}


def normalized_validation_status(value: Any) -> str:
    """Map the pre-V2-4 legacy value at read boundaries without changing schema."""

    status = str(value or "").strip()
    return CANDIDATE_UNVALIDATED if status == "unvalidated" else status


def is_operational_query(query: dict[str, Any]) -> bool:
    return bool(query.get("enabled")) and normalized_validation_status(
        query.get("validation_status")
    ) == SEARCH_VALIDATED


def operational_queries(target: dict[str, Any]) -> list[dict[str, Any]]:
    if not bool(target.get("enabled")):
        return []
    queries = [
        query
        for query in (target.get("queries") or [])
        if isinstance(query, dict) and is_operational_query(query)
    ]
    return sorted(
        queries,
        key=lambda item: (int(item.get("order") or 0), str(item.get("query_id") or "")),
    )


def target_availability(target: dict[str, Any]) -> str:
    if operational_queries(target):
        return "operational"
    statuses = {
        normalized_validation_status(query.get("validation_status"))
        for query in (target.get("queries") or [])
        if isinstance(query, dict)
    }
    return "paused" if statuses & PAUSED_QUERY_STATUSES else "query_pending"


def availability_reason(target: dict[str, Any]) -> str | None:
    if target_availability(target) != "paused":
        return None
    for query in target.get("queries") or []:
        if not isinstance(query, dict):
            continue
        if (
            normalized_validation_status(query.get("validation_status"))
            in PAUSED_QUERY_STATUSES
        ):
            note = str(query.get("query_note") or "").strip()
            if note:
                return note
    return "现有搜索策略暂不满足运行条件。"


def present_monitor_target(target: dict[str, Any]) -> dict[str, Any]:
    queries = []
    for raw_query in target.get("queries") or []:
        if not isinstance(raw_query, dict):
            continue
        query = dict(raw_query)
        query["validation_status"] = normalized_validation_status(
            query.get("validation_status")
        )
        queries.append(query)
    projected = {**target, "queries": queries}
    validated = operational_queries(projected)
    candidate_count = sum(
        1
        for query in queries
        if query["validation_status"] == CANDIDATE_UNVALIDATED
    )
    projected.update(
        {
            "availability": target_availability(projected),
            "availability_reason": availability_reason(projected),
            "validated_query_count": len(validated),
            "candidate_query_count": candidate_count,
            "validated_queries": validated,
            # Additive API aliases preserve the original snake_case contract while
            # exposing the V2 Reference DTO names used by the frontend specification.
            "targetId": projected.get("target_id"),
            "standardName": projected.get("standard_name"),
            "targetType": projected.get("target_type"),
            "datasetId": projected.get("dataset_id"),
            "sourceName": projected.get("source_name"),
            "sourceReference": projected.get("source_reference"),
            "sourceDate": projected.get("source_date"),
            "availabilityReason": availability_reason(projected),
            "validatedQueryCount": len(validated),
            "candidateQueryCount": candidate_count,
            "validatedQueries": validated,
        }
    )
    return projected


def reference_coverage(targets: Iterable[dict[str, Any]]) -> dict[str, int]:
    formal = [
        target
        for target in targets
        if target.get("dataset_status") == "verified_reference"
    ]
    queries = [
        query
        for target in formal
        for query in (target.get("queries") or [])
        if isinstance(query, dict)
    ]
    return {
        "reference_target_count": len(formal),
        "targets_with_query_count": sum(bool(target.get("queries")) for target in formal),
        "operational_target_count": sum(
            target_availability(target) == "operational" for target in formal
        ),
        "enabled_query_count": sum(bool(query.get("enabled")) for query in queries),
        "validated_query_count": sum(
            normalized_validation_status(query.get("validation_status"))
            == SEARCH_VALIDATED
            for query in queries
        ),
        "disabled_query_count": sum(not bool(query.get("enabled")) for query in queries),
        "candidate_query_count": sum(
            normalized_validation_status(query.get("validation_status"))
            == CANDIDATE_UNVALIDATED
            for query in queries
        ),
        "paused_target_count": sum(
            target_availability(target) == "paused" for target in formal
        ),
    }
