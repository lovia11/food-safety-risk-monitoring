"""Deterministic, GET-only V2 Analytics projections.

Analytics reads the existing schema-13 business index and governed knowledge
audits.  It creates no fact, score, relation, cache table, or materialized
metric.  Every returned metric is defined by the governed metric dictionary.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from scripts.audit_inspection_knowledge import load_and_build_audit
from src.claim_analysis import DEFAULT_CLAIM_TAXONOMY_PATH, load_claim_taxonomy
from src.data_store import DataStore
from src.knowledge_read import KnowledgeReadService
from src.pipeline_contract import evaluate_pipeline_readiness
from src.product_facts import present_declared_origin
from src.runtime import read_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ANALYTICS_METRICS_PATH = PROJECT_ROOT / "config" / "analytics_metrics_v2.json"
ANALYTICS_SCOPE_NOTE = (
    "Metrics describe the current local index and governed datasets only; "
    "they are not representative market or national risk statistics."
)
_METRIC_TYPES = {"count", "ratio", "distribution", "coverage"}
_METRIC_DOMAINS = {"pipeline", "claims", "geography", "knowledge"}
_METRIC_STATUSES = {"available", "not_available", "future_metric"}
_REQUIRED_METRIC_FIELDS = {
    "metric_id",
    "title_zh",
    "domain",
    "metric_type",
    "grain",
    "unit",
    "numerator_definition",
    "denominator_definition",
    "time_basis",
    "dedup_rule",
    "missing_data_rule",
    "source_entities",
    "allowed_filters",
    "interpretation",
    "forbidden_interpretation",
    "version",
    "status",
}
_SNAPSHOT_STAGES = {
    "pending_detail_collection",
    "collecting_detail",
    "detail_collected",
    "processing_ocr_analysis",
    "success",
    "failed_collection",
    "failed_preparation",
    "failed_processing",
}
_DETAIL_ATTEMPTED_STAGES = _SNAPSHOT_STAGES - {"pending_detail_collection"}


class AnalyticsMetricDictionaryError(ValueError):
    """The governed metric dictionary is invalid."""


class AnalyticsQueryValidationError(ValueError):
    """Analytics filters are invalid or unsupported."""


def load_metric_dictionary(
    path: Path = DEFAULT_ANALYTICS_METRICS_PATH,
) -> dict[str, Any]:
    payload = read_json(path)
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise AnalyticsMetricDictionaryError(
            "Analytics metric dictionary must be a schema_version 1 object"
        )
    if payload.get("status") != "design_baseline":
        raise AnalyticsMetricDictionaryError(
            "Analytics metric dictionary status must be design_baseline"
        )
    if set(payload.get("metric_types") or []) != _METRIC_TYPES:
        raise AnalyticsMetricDictionaryError(
            "Analytics metric dictionary must govern count, ratio, distribution and coverage"
        )
    metrics = payload.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        raise AnalyticsMetricDictionaryError("Analytics metrics must be non-empty")
    identities: set[str] = set()
    for metric in metrics:
        if not isinstance(metric, dict) or not _REQUIRED_METRIC_FIELDS.issubset(metric):
            raise AnalyticsMetricDictionaryError(
                "Every Analytics metric must contain the complete definition contract"
            )
        metric_id = metric["metric_id"]
        if not isinstance(metric_id, str) or not metric_id or metric_id in identities:
            raise AnalyticsMetricDictionaryError(
                "Analytics metric_id must be unique and non-empty"
            )
        identities.add(metric_id)
        if metric["metric_type"] not in _METRIC_TYPES:
            raise AnalyticsMetricDictionaryError(
                f"Unsupported metric_type for {metric_id}"
            )
        if metric["domain"] not in _METRIC_DOMAINS:
            raise AnalyticsMetricDictionaryError(f"Unsupported domain for {metric_id}")
        if metric["status"] != "available":
            raise AnalyticsMetricDictionaryError(
                f"Implemented metric {metric_id} must have status=available"
            )
        if not isinstance(metric["source_entities"], list) or not metric[
            "source_entities"
        ]:
            raise AnalyticsMetricDictionaryError(
                f"Metric {metric_id} must name source_entities"
            )
        if not isinstance(metric["allowed_filters"], list):
            raise AnalyticsMetricDictionaryError(
                f"Metric {metric_id} allowed_filters must be an array"
            )
    unavailable = payload.get("unavailable_metrics")
    if not isinstance(unavailable, list):
        raise AnalyticsMetricDictionaryError(
            "Analytics unavailable_metrics must be an array"
        )
    for item in unavailable:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("metric_id"), str)
            or item.get("status") not in _METRIC_STATUSES - {"available"}
            or not isinstance(item.get("reason"), str)
            or not item["reason"].strip()
        ):
            raise AnalyticsMetricDictionaryError(
                "Unavailable metrics require metric_id, not_available/future_metric status and reason"
            )
        if item["metric_id"] in identities:
            raise AnalyticsMetricDictionaryError(
                f"Unavailable metric {item['metric_id']} duplicates an implemented metric"
            )
        identities.add(item["metric_id"])
    return payload


@dataclass(frozen=True)
class _TimeFilter:
    raw: str
    is_date: bool
    value: date | datetime


def _parse_time_filter(value: str, field: str) -> _TimeFilter | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    try:
        if len(normalized) == 10:
            return _TimeFilter(normalized, True, date.fromisoformat(normalized))
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AnalyticsQueryValidationError(
            f"{field} must be an ISO 8601 date or datetime"
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return _TimeFilter(normalized, False, parsed.astimezone(timezone.utc))


def _parse_row_time(value: Any) -> datetime | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _passes_time(
    value: Any,
    lower: _TimeFilter | None,
    upper: _TimeFilter | None,
) -> bool:
    if lower is None and upper is None:
        return True
    parsed = _parse_row_time(value)
    if parsed is None:
        return False
    if lower is not None:
        if lower.is_date:
            if parsed.date() < lower.value:
                return False
        elif parsed.astimezone(timezone.utc) < lower.value:
            return False
    if upper is not None:
        if upper.is_date:
            if parsed.date() > upper.value:
                return False
        elif parsed.astimezone(timezone.utc) > upper.value:
            return False
    return True


def _ratio(numerator: int, denominator: int) -> tuple[float | None, str | None]:
    if denominator == 0:
        return None, "zero_denominator"
    return numerator / denominator, None


class AnalyticsReadService:
    """Build reproducible metric DTOs without changing any source state."""

    def __init__(
        self,
        store: DataStore,
        *,
        dictionary_path: Path = DEFAULT_ANALYTICS_METRICS_PATH,
        claim_taxonomy_path: Path = DEFAULT_CLAIM_TAXONOMY_PATH,
        knowledge_read: KnowledgeReadService | None = None,
    ) -> None:
        self.store = store
        self.dictionary_path = dictionary_path
        self.dictionary = load_metric_dictionary(dictionary_path)
        self.metric_definitions = {
            item["metric_id"]: item for item in self.dictionary["metrics"]
        }
        taxonomy = load_claim_taxonomy(claim_taxonomy_path)
        self.claim_taxonomy_version = str(taxonomy["version"])
        self.claim_type_labels = {
            item["id"]: item["label_zh"] for item in taxonomy["claim_types"]
        }
        self.knowledge_read = knowledge_read or KnowledgeReadService(store)
        self._knowledge_audit: dict[str, Any] | None = None

    def metric_dictionary(self) -> dict[str, Any]:
        return json.loads(json.dumps(self.dictionary, ensure_ascii=False))

    @staticmethod
    def _filters(
        *,
        from_value: str = "",
        to_value: str = "",
        region: str = "",
        stage: str = "",
        claim_type: str = "",
    ) -> dict[str, str]:
        return {
            key: value
            for key, value in {
                "from": from_value,
                "to": to_value,
                "region": region,
                "stage": stage,
                "claimType": claim_type,
            }.items()
            if value
        }

    def _validate_filters(
        self,
        *,
        from_value: str = "",
        to_value: str = "",
        region: str = "",
        stage: str = "",
        claim_type: str = "",
    ) -> tuple[_TimeFilter | None, _TimeFilter | None]:
        lower = _parse_time_filter(from_value, "from")
        upper = _parse_time_filter(to_value, "to")
        if lower and upper:
            lower_day = lower.value if lower.is_date else lower.value.date()
            upper_day = upper.value if upper.is_date else upper.value.date()
            if lower_day > upper_day or (
                not lower.is_date
                and not upper.is_date
                and lower.value > upper.value
            ):
                raise AnalyticsQueryValidationError("from must not be after to")
        if stage and stage not in _SNAPSHOT_STAGES:
            raise AnalyticsQueryValidationError(
                "stage must be a governed ProductSnapshot status"
            )
        if claim_type and claim_type not in self.claim_type_labels:
            raise AnalyticsQueryValidationError(
                "claim_type must be a governed V2 Claim type"
            )
        if len(region) > 128:
            raise AnalyticsQueryValidationError("region must not exceed 128 characters")
        return lower, upper

    def _selected_snapshots(
        self,
        *,
        from_value: str = "",
        to_value: str = "",
        region: str = "",
        stage: str = "",
    ) -> list[dict[str, Any]]:
        lower, upper = self._validate_filters(
            from_value=from_value,
            to_value=to_value,
            region=region,
            stage=stage,
        )
        with self.store._connect() as connection:
            rows = connection.execute(
                """
                SELECT s.*, r.review_status, t.created_at AS task_created_at
                FROM product_snapshots s
                JOIN tasks t ON t.task_id = s.task_id
                LEFT JOIN reviews r ON r.snapshot_id = s.snapshot_id
                ORDER BY s.snapshot_id
                """
            ).fetchall()
        selected: list[dict[str, Any]] = []
        for raw in rows:
            row = dict(raw)
            if region and str(row["region"] or "") != region:
                continue
            if stage and str(row["status"] or "") != stage:
                continue
            if not _passes_time(row["task_created_at"], lower, upper):
                continue
            readiness = evaluate_pipeline_readiness(
                status=row["status"],
                meta_path=row["meta_path"],
                analysis_path=row["analysis_path"],
                original_image_count=row["original_image_count"],
                ocr_image_count=row["ocr_image_count"],
            )
            row["readiness"] = readiness
            selected.append(row)
        return selected

    def _base_metric(
        self,
        metric_id: str,
        *,
        value: int | float | None,
        filters: Mapping[str, str],
        dataset_version: str,
    ) -> dict[str, Any]:
        definition = self.metric_definitions[metric_id]
        return {
            "metricId": metric_id,
            "title": definition["title_zh"],
            "domain": definition["domain"],
            "metricType": definition["metric_type"],
            "value": value,
            "unit": definition["unit"],
            "grain": definition["grain"],
            "timeBasis": definition["time_basis"],
            "datasetVersion": dataset_version,
            "filters": dict(filters),
            "missingRule": definition["missing_data_rule"],
            "interpretation": definition["interpretation"],
            "forbiddenInterpretation": definition["forbidden_interpretation"],
        }

    def _count_metric(
        self,
        metric_id: str,
        count: int,
        filters: Mapping[str, str],
        dataset_version: str = "schema-13-live-index",
    ) -> dict[str, Any]:
        return self._base_metric(
            metric_id,
            value=count,
            filters=filters,
            dataset_version=dataset_version,
        )

    def _ratio_metric(
        self,
        metric_id: str,
        numerator: int,
        denominator: int,
        filters: Mapping[str, str],
        dataset_version: str = "schema-13-live-index",
    ) -> dict[str, Any]:
        rate, reason = _ratio(numerator, denominator)
        return {
            **self._base_metric(
                metric_id,
                value=rate,
                filters=filters,
                dataset_version=dataset_version,
            ),
            "numerator": numerator,
            "denominator": denominator,
            "rate": rate,
            "reason": reason,
        }

    def _distribution_metric(
        self,
        metric_id: str,
        counts: Mapping[str, int],
        denominator: int,
        filters: Mapping[str, str],
        *,
        labels: Mapping[str, str] | None = None,
        dataset_version: str = "schema-13-live-index",
    ) -> dict[str, Any]:
        buckets = []
        for key in sorted(counts):
            count = int(counts[key])
            rate, reason = _ratio(count, denominator)
            buckets.append(
                {
                    "key": key,
                    "label": (labels or {}).get(key, key),
                    "count": count,
                    "denominator": denominator,
                    "rate": rate,
                    "reason": reason,
                }
            )
        return {
            **self._base_metric(
                metric_id,
                value=sum(int(value) for value in counts.values()),
                filters=filters,
                dataset_version=dataset_version,
            ),
            "denominator": denominator,
            "buckets": buckets,
        }

    @staticmethod
    def _response(
        dictionary_version: str,
        filters: Mapping[str, str],
        metrics: Iterable[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "dictionaryVersion": dictionary_version,
            "filters": dict(filters),
            "scopeNote": ANALYTICS_SCOPE_NOTE,
            "metrics": list(metrics),
        }

    def pipeline(
        self,
        *,
        from_value: str = "",
        to_value: str = "",
        region: str = "",
        stage: str = "",
    ) -> dict[str, Any]:
        filters = self._filters(
            from_value=from_value, to_value=to_value, region=region, stage=stage
        )
        snapshots = self._selected_snapshots(
            from_value=from_value, to_value=to_value, region=region, stage=stage
        )
        candidate_count = len(snapshots)
        unique_products = len({row["product_id"] for row in snapshots})
        detail_attempted = sum(
            str(row["status"] or "") in _DETAIL_ATTEMPTED_STAGES
            for row in snapshots
        )
        detail_collected = sum(row["readiness"].detail_collected for row in snapshots)
        ocr_input_ready = sum(row["readiness"].ocr_input_ready for row in snapshots)
        ocr_ready = sum(row["readiness"].ocr_ready for row in snapshots)
        analysis_ready = sum(row["readiness"].analysis_ready for row in snapshots)
        eligible_reviews = [
            row for row in snapshots if row["readiness"].review_eligible
        ]
        review_counts = Counter(
            str(row["review_status"] or "pending") for row in eligible_reviews
        )
        for status in ("pending", "recommend_follow_up", "no_further_action"):
            review_counts.setdefault(status, 0)
        selected_snapshot_ids = {row["snapshot_id"] for row in snapshots}
        with self.store._connect() as connection:
            membership_rows = connection.execute(
                """
                SELECT product_id, source_snapshot_id
                FROM sampling_list_memberships
                ORDER BY product_id
                """
            ).fetchall()
        memberships = sum(
            row["source_snapshot_id"] in selected_snapshot_ids
            for row in membership_rows
        )
        metrics = [
            self._count_metric(
                "search_candidate_observation_count", candidate_count, filters
            ),
            self._count_metric("unique_product_count", unique_products, filters),
            self._count_metric(
                "detail_attempted_snapshot_count", detail_attempted, filters
            ),
            self._count_metric(
                "detail_collected_snapshot_count", detail_collected, filters
            ),
            self._ratio_metric(
                "detail_collection_success_rate",
                detail_collected,
                detail_attempted,
                filters,
            ),
            self._count_metric(
                "ocr_input_ready_snapshot_count", ocr_input_ready, filters
            ),
            self._count_metric("ocr_ready_snapshot_count", ocr_ready, filters),
            self._ratio_metric(
                "ocr_success_rate", ocr_ready, ocr_input_ready, filters
            ),
            self._count_metric(
                "analysis_ready_snapshot_count", analysis_ready, filters
            ),
            self._ratio_metric(
                "analysis_readiness_rate", analysis_ready, ocr_ready, filters
            ),
            self._distribution_metric(
                "review_status_distribution",
                review_counts,
                len(eligible_reviews),
                filters,
                labels={
                    "pending": "待复核",
                    "recommend_follow_up": "建议跟进",
                    "no_further_action": "暂不纳入",
                },
            ),
            self._count_metric(
                "current_sampling_membership_count", memberships, filters
            ),
        ]
        return self._response(self.dictionary["version"], filters, metrics)

    def claims(
        self,
        *,
        from_value: str = "",
        to_value: str = "",
        region: str = "",
        claim_type: str = "",
    ) -> dict[str, Any]:
        self._validate_filters(
            from_value=from_value,
            to_value=to_value,
            region=region,
            claim_type=claim_type,
        )
        filters = self._filters(
            from_value=from_value,
            to_value=to_value,
            region=region,
            claim_type=claim_type,
        )
        snapshots = self._selected_snapshots(
            from_value=from_value, to_value=to_value, region=region
        )
        ids = [str(row["snapshot_id"]) for row in snapshots]
        signals: list[dict[str, Any]] = []
        evidence: list[dict[str, Any]] = []
        if ids:
            placeholders = ", ".join("?" for _ in ids)
            with self.store._connect() as connection:
                signals = [
                    dict(row)
                    for row in connection.execute(
                        f"""
                        SELECT claim_signal_id, snapshot_id, claim_type,
                               taxonomy_version
                        FROM claim_signals
                        WHERE snapshot_id IN ({placeholders})
                        ORDER BY snapshot_id, claim_type
                        """,
                        ids,
                    ).fetchall()
                ]
                evidence = [
                    dict(row)
                    for row in connection.execute(
                        f"""
                        SELECT evidence_id, snapshot_id, content_origin
                        FROM evidence
                        WHERE snapshot_id IN ({placeholders})
                        ORDER BY snapshot_id, evidence_id
                        """,
                        ids,
                    ).fetchall()
                ]
        selected_signals = [
            item
            for item in signals
            if not claim_type or item["claim_type"] == claim_type
        ]
        signal_snapshot_ids = {str(item["snapshot_id"]) for item in signals}
        status_counts: Counter[str] = Counter()
        for row in snapshots:
            status = str(row["claim_analysis_status"] or "not_generated")
            if status == "complete":
                key = (
                    "complete_with_claims"
                    if row["snapshot_id"] in signal_snapshot_ids
                    else "complete_zero"
                )
            else:
                key = status if status in {"not_generated", "error"} else "error"
            status_counts[key] += 1
        for key in ("complete_with_claims", "complete_zero", "not_generated", "error"):
            status_counts.setdefault(key, 0)
        complete_snapshots = {
            str(row["snapshot_id"])
            for row in snapshots
            if row["claim_analysis_status"] == "complete"
        }
        type_snapshots: defaultdict[str, set[str]] = defaultdict(set)
        for item in selected_signals:
            type_snapshots[str(item["claim_type"])].add(str(item["snapshot_id"]))
        type_counts = {
            key: len(value) for key, value in sorted(type_snapshots.items())
        }
        if claim_type:
            type_counts.setdefault(claim_type, 0)
        evidence_counts = Counter(
            str(item["content_origin"] or "unknown") for item in evidence
        )
        for key in (
            "seller_managed",
            "user_generated",
            "excluded_other_product",
            "unknown",
        ):
            evidence_counts.setdefault(key, 0)
        metrics = [
            self._distribution_metric(
                "claim_analysis_status_distribution",
                status_counts,
                len(snapshots),
                {k: v for k, v in filters.items() if k != "claimType"},
                labels={
                    "complete_with_claims": "已生成且有页面宣传线索",
                    "complete_zero": "已生成但零页面宣传线索",
                    "not_generated": "尚未生成",
                    "error": "分析错误",
                },
                dataset_version=self.claim_taxonomy_version,
            ),
            self._count_metric(
                "formal_claim_signal_count",
                len(selected_signals),
                filters,
                dataset_version=self.claim_taxonomy_version,
            ),
            self._distribution_metric(
                "claim_type_snapshot_distribution",
                type_counts,
                len(complete_snapshots),
                filters,
                labels=self.claim_type_labels,
                dataset_version=self.claim_taxonomy_version,
            ),
            self._distribution_metric(
                "evidence_source_scope_distribution",
                evidence_counts,
                len(evidence),
                {k: v for k, v in filters.items() if k != "claimType"},
                labels={
                    "seller_managed": "商家管理内容",
                    "user_generated": "用户生成内容",
                    "excluded_other_product": "其他商品内容",
                    "unknown": "来源范围未记录",
                },
            ),
        ]
        return self._response(self.dictionary["version"], filters, metrics)

    def geography(
        self,
        *,
        from_value: str = "",
        to_value: str = "",
        region: str = "",
        claim_type: str = "",
    ) -> dict[str, Any]:
        self._validate_filters(
            from_value=from_value,
            to_value=to_value,
            region=region,
            claim_type=claim_type,
        )
        filters = self._filters(
            from_value=from_value,
            to_value=to_value,
            region=region,
            claim_type=claim_type,
        )
        snapshots = self._selected_snapshots(
            from_value=from_value, to_value=to_value, region=region
        )
        ids = [str(row["snapshot_id"]) for row in snapshots]
        search_regions = Counter(str(row["region"] or "unknown") for row in snapshots)
        claim_snapshot_ids: set[str] = set()
        facts_by_snapshot: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        if ids:
            placeholders = ", ".join("?" for _ in ids)
            with self.store._connect() as connection:
                claim_rows = connection.execute(
                    f"""
                    SELECT DISTINCT snapshot_id
                    FROM claim_signals
                    WHERE snapshot_id IN ({placeholders})
                    {"AND claim_type = ?" if claim_type else ""}
                    ORDER BY snapshot_id
                    """,
                    [*ids, claim_type] if claim_type else ids,
                ).fetchall()
                claim_snapshot_ids = {str(row["snapshot_id"]) for row in claim_rows}
                fact_rows = connection.execute(
                    f"""
                    SELECT * FROM product_facts
                    WHERE fact_type = 'declared_origin'
                      AND snapshot_id IN ({placeholders})
                    ORDER BY snapshot_id, fact_id
                    """,
                    ids,
                ).fetchall()
            for raw in fact_rows:
                row = dict(raw)
                facts_by_snapshot[str(row["snapshot_id"])].append(
                    {
                        "factType": row["fact_type"],
                        "normalizedValue": row["normalized_value"],
                    }
                )
        claim_regions = Counter(
            str(row["region"] or "unknown")
            for row in snapshots
            if row["snapshot_id"] in claim_snapshot_ids
        )
        origin_counts: Counter[str] = Counter()
        for row in snapshots:
            presentation = present_declared_origin(
                facts_by_snapshot.get(str(row["snapshot_id"]), [])
            )
            if presentation["state"] == "none":
                origin_counts["unknown"] += 1
            elif presentation["state"] == "conflict":
                origin_counts["conflict"] += 1
            else:
                origin_counts[str(presentation["values"][0])] += 1
        search_filters = {k: v for k, v in filters.items() if k != "claimType"}
        metrics = [
            self._distribution_metric(
                "collected_product_search_region_distribution",
                search_regions,
                len(snapshots),
                search_filters,
            ),
            self._distribution_metric(
                "claim_product_search_region_distribution",
                claim_regions,
                len(claim_snapshot_ids),
                filters,
                dataset_version=self.claim_taxonomy_version,
            ),
            self._distribution_metric(
                "declared_origin_distribution",
                origin_counts,
                len(snapshots),
                search_filters,
                labels={
                    "unknown": "标称产地未记录",
                    "conflict": "标称产地存在冲突",
                },
            ),
        ]
        return self._response(self.dictionary["version"], filters, metrics)

    def _audit(self) -> dict[str, Any]:
        if self._knowledge_audit is None:
            self._knowledge_audit = load_and_build_audit()
        return self._knowledge_audit

    def knowledge(self) -> dict[str, Any]:
        filters: dict[str, str] = {}
        summary = self.knowledge_read.summary()
        audit = self._audit()
        versions = audit["dataset_versions"]
        audit_version = ";".join(
            f"{key}={versions[key]}" for key in sorted(versions)
        )
        monitor_version = ";".join(
            sorted(
                f"{item['datasetId']}@{item['datasetVersion']}"
                for item in summary["authorities"]["monitorReferences"]
            )
        )
        inspection_version = str(versions["inspection"])

        def audit_metric(metric_id: str, audit_id: str) -> dict[str, Any]:
            source = audit["metrics"][audit_id]
            return self._ratio_metric(
                metric_id,
                int(source["numerator"]),
                int(source["denominator"]),
                filters,
                audit_version,
            )

        counts = summary["counts"]
        metrics = [
            self._count_metric(
                "reference_monitor_target_count",
                int(counts["referenceMonitorTargets"]),
                filters,
                monitor_version,
            ),
            self._ratio_metric(
                "operational_monitor_target_coverage",
                int(counts["operationalMonitorTargets"]),
                int(counts["referenceMonitorTargets"]),
                filters,
                monitor_version,
            ),
            self._count_metric(
                "inspection_indexed_method_count",
                int(audit["inventory"]["indexed_methods"]),
                filters,
                inspection_version,
            ),
            audit_metric(
                "inspection_method_reference_coverage",
                "method_reference_coverage",
            ),
            audit_metric(
                "inspection_method_deep_verification_coverage",
                "method_deep_verification_coverage",
            ),
            self._ratio_metric(
                "inspection_recommendation_ready_method_coverage",
                int(counts["recommendationReadyMethods"]),
                int(counts["inspectionMethods"]),
                filters,
                inspection_version,
            ),
            self._count_metric(
                "inspection_reference_only_method_count",
                int(counts["referenceOnlyMethods"]),
                filters,
                inspection_version,
            ),
            audit_metric(
                "risk_to_explicit_substance_coverage",
                "risk_to_explicit_substance_coverage",
            ),
            audit_metric("group_resolution_coverage", "group_resolution_coverage"),
            audit_metric(
                "recommendation_structural_reachability",
                "recommendation_structural_reachability",
            ),
            audit_metric(
                "recommendation_end_to_end_reachability",
                "recommendation_end_to_end_reachability",
            ),
            audit_metric(
                "risk_category_end_to_end_reachability",
                "risk_category_end_to_end_reachability",
            ),
            audit_metric(
                "context_corpus_recommendation_reachability",
                "context_corpus_recommendation_reachability",
            ),
        ]
        return self._response(self.dictionary["version"], filters, metrics)

    def summary(
        self,
        *,
        from_value: str = "",
        to_value: str = "",
        region: str = "",
    ) -> dict[str, Any]:
        pipeline = self.pipeline(
            from_value=from_value, to_value=to_value, region=region
        )
        claims = self.claims(
            from_value=from_value, to_value=to_value, region=region
        )
        selected = {
            "search_candidate_observation_count",
            "unique_product_count",
            "analysis_ready_snapshot_count",
            "review_status_distribution",
            "current_sampling_membership_count",
            "formal_claim_signal_count",
        }
        metrics = [
            item
            for item in [*pipeline["metrics"], *claims["metrics"]]
            if item["metricId"] in selected
        ]
        return self._response(
            self.dictionary["version"], pipeline["filters"], metrics
        )
