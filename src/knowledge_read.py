"""Read-only V2 Knowledge Base projections over governed runtime authorities.

This module creates no new knowledge relation and performs no write.  Monitor,
Inspection, Risk and RegulatoryDocument records come from the same schema-13
SQLite projection used by runtime code.  HealthFunction records come from the
same validated governed JSON consumed by Claim Consistency.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.claim_consistency import (
    DEFAULT_HEALTH_FUNCTIONS_PATH,
    load_health_function_dataset,
)
from src.data_store import DataStore


DEFAULT_LIMIT = 50
MAX_LIMIT = 100


class KnowledgeQueryValidationError(ValueError):
    """Knowledge read filters or pagination are invalid."""


def _text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _matches(query: str, *values: Any) -> bool:
    if not query:
        return True
    needle = query.casefold()
    return any(needle in str(value or "").casefold() for value in values)


def _validate_choice(value: str, field: str, choices: set[str]) -> str:
    if value and value not in choices:
        raise KnowledgeQueryValidationError(
            f"{field} must be one of: {', '.join(sorted(choices))}"
        )
    return value


def _page(items: list[dict[str, Any]], *, limit: int, offset: int) -> dict[str, Any]:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_LIMIT:
        raise KnowledgeQueryValidationError(f"limit must be between 1 and {MAX_LIMIT}")
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise KnowledgeQueryValidationError("offset must be zero or greater")
    selected = items[offset : offset + limit]
    return {
        "items": selected,
        "count": len(selected),
        "total": len(items),
        "limit": limit,
        "offset": offset,
        "hasMore": offset + len(selected) < len(items),
    }


def _dataset_trace(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "datasetId": row["dataset_id"],
        "datasetVersion": row["dataset_version"],
        "datasetStatus": row["dataset_status"],
        "sourceName": row.get("dataset_source_name"),
        "sourceReference": row.get("dataset_source_reference"),
        "sourceDate": row.get("dataset_source_date"),
    }


class KnowledgeReadService:
    """Compose stable API DTOs without changing any source or business state."""

    def __init__(
        self,
        store: DataStore,
        health_functions_path: Path = DEFAULT_HEALTH_FUNCTIONS_PATH,
    ) -> None:
        self.store = store
        self.health_functions_path = health_functions_path

    def _health_dataset(self) -> dict[str, Any]:
        return load_health_function_dataset(self.health_functions_path)

    def summary(self) -> dict[str, Any]:
        targets = self.store.list_monitor_targets(scope="reference")
        health = self._health_dataset()
        methods = self.store.list_knowledge_inspection_methods()
        substances = self.store.list_knowledge_substances()
        mappings = self.store.list_knowledge_risk_mappings()
        documents = self.store.list_knowledge_regulatory_documents()
        monitor_datasets = {
            (item["dataset_id"], item["dataset_version"]): item["dataset"]
            for item in targets
        }
        return {
            "counts": {
                "referenceMonitorTargets": len(targets),
                "operationalMonitorTargets": sum(
                    item["availability"] == "operational" for item in targets
                ),
                "queryPendingMonitorTargets": sum(
                    item["availability"] == "query_pending" for item in targets
                ),
                "pausedMonitorTargets": sum(
                    item["availability"] == "paused" for item in targets
                ),
                "healthFunctions": len(health["functions"]),
                "inspectionMethods": len(methods),
                "recommendationReadyMethods": sum(
                    item["knowledge_depth"] == "recommendation_ready"
                    for item in methods
                ),
                "referenceOnlyMethods": sum(
                    item["knowledge_depth"] == "reference_only" for item in methods
                ),
                "substances": len(substances),
                "riskMappings": len(mappings),
                "groupMappings": sum(
                    item["target_type"] == "substance_group" for item in mappings
                ),
                "regulatoryDocuments": len(documents),
            },
            "authorities": {
                "monitorReferences": [
                    {
                        "datasetId": dataset["dataset_id"],
                        "datasetVersion": dataset["dataset_version"],
                        "datasetStatus": dataset["dataset_status"],
                        "sourceName": dataset["source_name"],
                        "sourceReference": dataset["source_reference"],
                        "sourceDate": dataset["source_date"],
                    }
                    for dataset in monitor_datasets.values()
                ],
                "healthFunctions": {
                    "datasetId": health["dataset_id"],
                    "datasetVersion": health["dataset_version"],
                    "datasetStatus": health["dataset_status"],
                },
                "inspection": _dataset_trace(methods[0]) if methods else None,
                "riskMappings": _dataset_trace(mappings[0]) if mappings else None,
            },
            "metricBoundary": (
                "Counts use separate governed denominators and are not a blended "
                "knowledge completeness score."
            ),
        }

    def monitor_targets(
        self,
        *,
        query: str = "",
        availability: str = "",
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> dict[str, Any]:
        availability = _validate_choice(
            availability,
            "availability",
            {"operational", "query_pending", "paused"},
        )
        items: list[dict[str, Any]] = []
        for row in self.store.list_monitor_targets(scope="reference"):
            if availability and row["availability"] != availability:
                continue
            if not _matches(
                query,
                row["target_id"],
                row["standard_name"],
                *(item["query_text"] for item in row["queries"]),
            ):
                continue
            gaps = []
            if row["availability"] == "query_pending":
                gaps.append("validated_search_query_not_available")
            elif row["availability"] == "paused":
                gaps.append("operational_search_paused")
            items.append(
                {
                    "targetId": row["target_id"],
                    "standardName": row["standard_name"],
                    "targetType": row["target_type"],
                    "availability": row["availability"],
                    "availabilityReason": row["availability_reason"],
                    "validatedSearchQueryCount": row["validated_query_count"],
                    "hasValidatedSearchQuery": row["validated_query_count"] > 0,
                    "searchQueries": row["queries"],
                    "source": {
                        "datasetId": row["dataset_id"],
                        "datasetVersion": row["dataset_version"],
                        "datasetStatus": row["dataset_status"],
                        "sourceName": row["source_name"],
                        "sourceReference": row["source_reference"],
                        "sourceDate": row["source_date"],
                    },
                    "knowledgeGaps": gaps,
                    "interpretation": (
                        "Reference membership does not imply Operational Search readiness."
                    ),
                }
            )
        return _page(items, limit=limit, offset=offset)

    def health_functions(
        self,
        *,
        query: str = "",
        framework: str = "",
        status: str = "",
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> dict[str, Any]:
        payload = self._health_dataset()
        frameworks = {item["framework_id"]: item for item in payload["frameworks"]}
        if framework and framework not in frameworks:
            raise KnowledgeQueryValidationError("framework is not governed")
        governed_statuses = {item["status"] for item in payload["functions"]}
        status = _validate_choice(status, "status", governed_statuses)
        aliases_by_function: dict[str, list[dict[str, Any]]] = {}
        for alias in payload["aliases"]:
            aliases_by_function.setdefault(alias["function_id"], []).append(alias)
        items = []
        for row in payload["functions"]:
            if framework and row["framework_id"] != framework:
                continue
            if status and row["status"] != status:
                continue
            current_framework = frameworks[row["framework_id"]]
            aliases = aliases_by_function.get(row["function_id"], [])
            if not _matches(
                query,
                row["function_id"],
                row["official_name"],
                *(item["alias_text"] for item in aliases),
            ):
                continue
            coverage_status = current_framework["coverage_status"]
            gaps = (
                []
                if coverage_status == "current_catalog_and_official_transition_complete"
                else ["framework_catalog_detail_not_governed"]
            )
            items.append(
                {
                    "functionId": row["function_id"],
                    "frameworkId": row["framework_id"],
                    "frameworkType": current_framework["framework_type"],
                    "frameworkName": current_framework["official_name"],
                    "frameworkCoverageStatus": coverage_status,
                    "officialName": row["official_name"],
                    "ordinal": row["ordinal"],
                    "status": row["status"],
                    "jurisdiction": row["jurisdiction"],
                    "frameworkVersion": row["framework_version"],
                    "effectiveDate": row.get("effective_date"),
                    "transitionAliases": [
                        {
                            "aliasId": item["alias_id"],
                            "aliasText": item["alias_text"],
                            "aliasType": item["alias_type"],
                            "status": item["status"],
                            "sourceName": item["source_name"],
                            "sourceReference": item["source_reference"],
                            "sourceDate": item["source_date"],
                        }
                        for item in aliases
                    ],
                    "source": {
                        "datasetId": payload["dataset_id"],
                        "datasetVersion": payload["dataset_version"],
                        "datasetStatus": payload["dataset_status"],
                        "sourceName": row["source_name"],
                        "sourceReference": row["source_reference"],
                        "sourceDate": row["source_date"],
                    },
                    "knowledgeGaps": gaps,
                    "interpretation": "HealthFunction is not a page ClaimSignal.",
                }
            )
        items.sort(key=lambda item: (item["frameworkId"], item["ordinal"]))
        return _page(items, limit=limit, offset=offset)

    def substances(
        self,
        *,
        query: str = "",
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> dict[str, Any]:
        items = []
        for row in self.store.list_knowledge_substances():
            if not _matches(
                query,
                row["substance_id"],
                row["canonical_name"],
                row["english_name"],
                row["cas_no"],
            ):
                continue
            contexts = [
                {
                    "contextId": item["context_id"],
                    "status": item["context_status"],
                    "productScope": item["product_scope"],
                    "jurisdiction": item["jurisdiction"],
                    "validFrom": item["valid_from"],
                    "validTo": item["valid_to"],
                    "sourceName": item["source_name"],
                    "sourceReference": item["source_reference"],
                    "sourceDate": item["source_date"],
                    "note": item["note"],
                }
                for item in row["regulatory_contexts"]
            ]
            memberships = [
                {
                    "membershipId": item["membership_id"],
                    "groupIdentity": item["group_identity"],
                    "groupLabel": item["group_label"],
                    "membershipScope": item["membership_scope"],
                    "completenessContext": item["completeness_context"],
                    "sourceBasis": item["source_basis"],
                    "sourceReference": item["source_reference"],
                    "status": item["status"],
                    "datasetId": item["dataset_id"],
                    "datasetVersion": item["dataset_version"],
                }
                for item in row["group_memberships"]
            ]
            items.append(
                {
                    "substanceId": row["substance_id"],
                    "canonicalName": row["canonical_name"],
                    "englishName": _text(row["english_name"]),
                    "casNo": _text(row["cas_no"]),
                    "groupMetadata": {
                        "state": "recorded" if memberships else "not_recorded",
                        "memberships": memberships,
                    },
                    "regulatoryContext": {
                        "availability": "recorded" if contexts else "not_recorded",
                        "count": len(contexts),
                        "contexts": contexts,
                    },
                    "methodCoverageCount": row["method_coverage_count"],
                    "recommendationReadyMethodCount": row[
                        "recommendation_ready_method_count"
                    ],
                    "note": row["note"],
                    "source": _dataset_trace(row),
                    "knowledgeGaps": (
                        [] if contexts else ["regulatory_context_not_recorded"]
                    ),
                    "interpretation": (
                        "Method coverage does not mean that a product contains this substance."
                    ),
                }
            )
        return _page(items, limit=limit, offset=offset)

    def risk_mappings(
        self,
        *,
        query: str = "",
        target_type: str = "",
        status: str = "",
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> dict[str, Any]:
        target_type = _validate_choice(
            target_type, "target_type", {"substance", "substance_group"}
        )
        status = _validate_choice(status, "status", {"current", "historical"})
        items = []
        for row in self.store.list_knowledge_risk_mappings():
            if target_type and row["target_type"] != target_type:
                continue
            if status and row["temporal_status"] != status:
                continue
            target_label = row["substance_name"] or row["target_group_label"]
            if not _matches(
                query,
                row["mapping_id"],
                row["risk_category"],
                row["risk_label"],
                target_label,
            ):
                continue
            memberships = row["group_memberships"]
            group_resolution = None
            gaps = []
            if row["target_type"] == "substance_group":
                if not memberships:
                    resolution_status = "unresolved"
                    gaps.append("substance_group_membership_unresolved")
                elif any(
                    item["completeness_context"] == "complete"
                    for item in memberships
                ):
                    resolution_status = "complete"
                else:
                    resolution_status = "partial"
                    gaps.append("substance_group_membership_partial")
                group_resolution = {
                    "status": resolution_status,
                    "memberCount": len(memberships),
                }
            items.append(
                {
                    "mappingId": row["mapping_id"],
                    "riskCategory": row["risk_category"],
                    "riskLabel": row["risk_label"],
                    "targetType": row["target_type"],
                    "target": {
                        "substanceId": row["substance_id"],
                        "label": target_label,
                        "casNo": _text(row["substance_cas_no"]),
                        "groupLabel": row["target_group_label"],
                    },
                    "evidenceGrade": row["evidence_grade"],
                    "basisType": row["basis_type"],
                    "productScope": row["product_scope"],
                    "temporalStatus": row["temporal_status"],
                    "sourceBasisText": row["source_basis_text"],
                    "note": row["note"],
                    "groupResolution": group_resolution,
                    "source": {
                        **_dataset_trace(row),
                        "sourceName": row["source_name"],
                        "sourceReference": row["source_reference"],
                        "sourceDate": row["source_date"],
                    },
                    "knowledgeGaps": gaps,
                    "interpretation": (
                        "A Risk mapping is an inspection direction, not evidence that "
                        "the target exists in a product. Group mappings do not expand "
                        "without governed memberships."
                    ),
                }
            )
        return _page(items, limit=limit, offset=offset)

    def inspection_methods(
        self,
        *,
        query: str = "",
        status: str = "",
        knowledge_depth: str = "",
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> dict[str, Any]:
        status = _validate_choice(
            status,
            "status",
            {"current", "superseded", "revoked", "verification_pending"},
        )
        knowledge_depth = _validate_choice(
            knowledge_depth,
            "knowledge_depth",
            {
                "reference_only",
                "analyte_verified",
                "applicability_verified",
                "recommendation_ready",
            },
        )
        items = []
        for row in self.store.list_knowledge_inspection_methods():
            if status and row["method_status"] != status:
                continue
            if knowledge_depth and row["knowledge_depth"] != knowledge_depth:
                continue
            if not _matches(
                query, row["method_id"], row["method_no"], row["method_name"]
            ):
                continue
            gaps = []
            if row["knowledge_depth"] == "reference_only":
                gaps.extend(
                    ["analyte_depth_not_verified", "applicability_not_verified"]
                )
            elif row["applicability_count"] == 0:
                gaps.append("applicability_not_recorded")
            document = None
            if row["regulatory_document_id"]:
                document = {
                    "documentId": row["regulatory_document_id"],
                    "documentType": row["document_type"],
                    "documentNo": row["document_no"],
                    "title": row["document_title"],
                    "publisher": row["document_publisher"],
                    "publishedDate": row["document_published_date"],
                    "effectiveDate": row["document_effective_date"],
                    "status": row["document_status"],
                    "sourceReference": row["document_source_reference"],
                    "jurisdiction": row["document_jurisdiction"],
                    "supersedes": json.loads(row["supersedes_json"] or "[]"),
                    "supersededBy": json.loads(
                        row["superseded_by_json"] or "[]"
                    ),
                }
            else:
                gaps.append("regulatory_document_not_linked")
            items.append(
                {
                    "methodId": row["method_id"],
                    "methodNo": row["method_no"],
                    "methodName": row["method_name"],
                    "methodType": row["method_type"],
                    "methodStatus": row["method_status"],
                    "knowledgeDepth": row["knowledge_depth"],
                    "publisher": row["publisher"],
                    "publishedDate": row["published_date"],
                    "effectiveDate": row["effective_date"],
                    "replacesMethodNo": row["replaces_method_no"],
                    "replacedByMethodNo": row["replaced_by_method_no"],
                    "analyteCount": row["analyte_count"],
                    "applicability": {
                        "availability": (
                            "recorded"
                            if row["applicability_count"]
                            else "not_recorded"
                        ),
                        "count": row["applicability_count"],
                        "includeCount": row["include_count"],
                        "conditionalCount": row["conditional_count"],
                        "excludeCount": row["exclude_count"],
                    },
                    "regulatoryDocument": document,
                    "note": row["note"],
                    "source": {
                        **_dataset_trace(row),
                        "sourceName": row["source_name"],
                        "sourceReference": row["source_reference"],
                        "sourceDate": row["source_date"],
                    },
                    "knowledgeGaps": gaps,
                    "interpretation": (
                        "Method lifecycle and project knowledge depth are independent."
                    ),
                }
            )
        return _page(items, limit=limit, offset=offset)

    def regulatory_documents(
        self,
        *,
        query: str = "",
        status: str = "",
        document_type: str = "",
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> dict[str, Any]:
        status = _validate_choice(
            status,
            "status",
            {"current", "superseded", "revoked", "verification_pending"},
        )
        document_type = _validate_choice(
            document_type,
            "document_type",
            {
                "official_method_page",
                "official_announcement",
                "national_standard_record",
            },
        )
        items = []
        for row in self.store.list_knowledge_regulatory_documents():
            if status and row["status"] != status:
                continue
            if document_type and row["document_type"] != document_type:
                continue
            if not _matches(
                query, row["document_id"], row["document_no"], row["title"]
            ):
                continue
            supersedes = json.loads(row["supersedes_json"] or "[]")
            superseded_by = json.loads(row["superseded_by_json"] or "[]")
            gaps = []
            if not row["effective_date"]:
                gaps.append("effective_date_not_recorded")
            items.append(
                {
                    "documentId": row["document_id"],
                    "documentType": row["document_type"],
                    "documentNo": row["document_no"],
                    "title": row["title"],
                    "publisher": row["publisher"],
                    "publishedDate": row["published_date"],
                    "effectiveDate": row["effective_date"],
                    "status": row["status"],
                    "jurisdiction": row["jurisdiction"],
                    "sourceReference": row["source_reference"],
                    "supersedes": supersedes,
                    "supersededBy": superseded_by,
                    "linkedMethodCount": row["linked_method_count"],
                    "source": _dataset_trace(row),
                    "knowledgeGaps": gaps,
                }
            )
        return _page(items, limit=limit, offset=offset)
