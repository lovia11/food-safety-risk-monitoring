"""Deterministic, offline audit of governed inspection knowledge.

This tool reports what the committed knowledge contracts actually contain.  It
does not fetch sources, add knowledge, expand substance groups, infer Risk from
method analytes, or change Recommendation behavior.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.effect_risk_bridge import validate_effect_risk_bridge_config
from src.inspection_method_candidates import validate_inspection_candidate_manifest
from src.inspection_reference import validate_inspection_config
from src.risk_substance_reference import validate_risk_substance_config
from src.runtime import read_json


AUDIT_CONTRACT_VERSION = "v2.7b1-1"
DEFAULT_INSPECTION_CONFIG = PROJECT_ROOT / "config" / "inspection_reference.json"
DEFAULT_RISK_CONFIG = PROJECT_ROOT / "config" / "risk_substance_reference.json"
DEFAULT_BRIDGE_CONFIG = PROJECT_ROOT / "config" / "effect_risk_bridge.json"
DEFAULT_CANDIDATE_CONFIG = (
    PROJECT_ROOT / "config" / "inspection_method_candidates_v2.json"
)

_METHOD_STATUSES = ("current", "superseded", "revoked", "verification_pending")
_METHOD_TYPES = ("supplementary_bjs", "rapid_kj", "national_standard_gbt")


class InspectionKnowledgeAuditError(ValueError):
    """Governed inputs cannot produce a safe coverage report."""


def _official_source_reference(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and (
        host == "samr.gov.cn"
        or host.endswith(".samr.gov.cn")
        or host == "nhc.gov.cn"
        or host.endswith(".nhc.gov.cn")
        or host.endswith(".gov.cn")
    )


def _ratio(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "ratio": None if denominator == 0 else round(numerator / denominator, 6),
    }


def _method_audit(
    method: Mapping[str, Any],
    relations: list[Mapping[str, Any]],
    applicabilities: list[Mapping[str, Any]],
) -> dict[str, Any]:
    reference_complete = all(
        method.get(field)
        for field in (
            "method_id",
            "method_no",
            "method_name",
            "method_type",
            "method_status",
            "publisher",
            "source_name",
            "source_reference",
            "regulatory_document_id",
        )
    ) and _official_source_reference(method.get("source_reference"))
    analyte_verified = bool(relations) and all(
        relation.get("source_label")
        and relation.get("determination_role")
        and relation.get("substance_id")
        for relation in relations
    )
    method_level_applicabilities = [
        item for item in applicabilities if item.get("substance_id") is None
    ]
    applicability_verified = bool(method_level_applicabilities) and all(
        item.get("source_scope_text") for item in applicabilities
    )

    status = method.get("method_status")
    lifecycle_complete = status in _METHOD_STATUSES
    if status == "superseded":
        lifecycle_complete = lifecycle_complete and bool(
            method.get("replaced_by_method_no")
        )
    recommendation_ready = bool(
        reference_complete
        and analyte_verified
        and applicability_verified
        and lifecycle_complete
        and status == "current"
        and method.get("source_date")
    )
    if not reference_complete:
        depth = "reference_incomplete"
    elif not analyte_verified:
        depth = "reference_only"
    elif not applicability_verified:
        depth = "analyte_verified"
    elif recommendation_ready:
        depth = "recommendation_ready"
    else:
        depth = "applicability_verified"

    return {
        "method_id": method["method_id"],
        "method_no": method["method_no"],
        "method_name": method["method_name"],
        "method_type": method["method_type"],
        "method_status": status,
        "declared_knowledge_depth": method["knowledge_depth"],
        "regulatory_document_id": method["regulatory_document_id"],
        "publisher": method["publisher"],
        "published_date": method["published_date"],
        "effective_date": method["effective_date"],
        "replaces_method_no": method["replaces_method_no"],
        "replaced_by_method_no": method["replaced_by_method_no"],
        "source_name": method["source_name"],
        "source_reference": method["source_reference"],
        "source_date": method["source_date"],
        "reference_complete": reference_complete,
        "official_source_reference": _official_source_reference(
            method["source_reference"]
        ),
        "analyte_relation_count": len(relations),
        "analyte_verified": analyte_verified,
        "applicability_count": len(applicabilities),
        "method_level_applicability_count": len(method_level_applicabilities),
        "substance_scoped_applicability_count": (
            len(applicabilities) - len(method_level_applicabilities)
        ),
        "applicability_verified": applicability_verified,
        "lifecycle_complete": lifecycle_complete,
        "knowledge_depth": depth,
        "depth_contract_matches": method["knowledge_depth"] == depth,
        "recommendation_ready": recommendation_ready,
        "note": method["note"],
    }


def build_audit(
    inspection: Mapping[str, Any],
    risk: Mapping[str, Any],
    bridge: Mapping[str, Any],
    candidates: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic report from already-normalized governed inputs."""

    methods = list(inspection["methods"])
    substances = list(inspection["substances"])
    method_substances = list(inspection["method_substances"])
    applicabilities = list(inspection["method_applicabilities"])
    regulatory_contexts = list(inspection["substance_regulatory_contexts"])
    regulatory_documents = list(inspection["regulatory_documents"])
    group_memberships = list(inspection["substance_group_memberships"])
    risk_mappings = list(risk["mappings"])
    bridge_mappings = list(bridge["mappings"])
    candidate_methods = list((candidates or {}).get("candidates", []))

    method_ids = {item["method_id"] for item in methods}
    substance_ids = {item["substance_id"] for item in substances}
    dangling_method_relations = sorted(
        {
            item["method_id"]
            for item in method_substances
            if item["method_id"] not in method_ids
        }
    )
    dangling_substance_relations = sorted(
        {
            item["substance_id"]
            for item in method_substances
            if item["substance_id"] not in substance_ids
        }
    )
    dangling_applicability_methods = sorted(
        {
            item["method_id"]
            for item in applicabilities
            if item["method_id"] not in method_ids
        }
    )
    dangling_applicability_substances = sorted(
        {
            item["substance_id"]
            for item in applicabilities
            if item["substance_id"] is not None
            and item["substance_id"] not in substance_ids
        }
    )
    dangling_risk_substances = sorted(
        {
            item["substance_id"]
            for item in risk_mappings
            if item["target_type"] == "substance"
            and item["substance_id"] not in substance_ids
        }
    )
    dangling_bridge_references = sorted(
        {
            item["reference_mapping_id"]
            for item in bridge_mappings
            if item["reference_mapping_id"]
            not in {mapping["mapping_id"] for mapping in risk_mappings}
        }
    )
    document_ids = {item["document_id"] for item in regulatory_documents}
    dangling_method_documents = sorted(
        {
            item["regulatory_document_id"]
            for item in methods
            if item["regulatory_document_id"] not in document_ids
        }
    )
    dangling_group_substances = sorted(
        {
            item["substance_id"]
            for item in group_memberships
            if item["substance_id"] not in substance_ids
        }
    )
    dangling = {
        "method_substance_method_ids": dangling_method_relations,
        "method_substance_substance_ids": dangling_substance_relations,
        "applicability_method_ids": dangling_applicability_methods,
        "applicability_substance_ids": dangling_applicability_substances,
        "risk_substance_ids": dangling_risk_substances,
        "bridge_reference_mapping_ids": dangling_bridge_references,
        "method_regulatory_document_ids": dangling_method_documents,
        "group_membership_substance_ids": dangling_group_substances,
    }
    if any(dangling.values()):
        raise InspectionKnowledgeAuditError(
            "Governed inspection knowledge contains dangling identities: "
            + json.dumps(dangling, ensure_ascii=False, sort_keys=True)
        )

    relations_by_method: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    methods_by_substance: dict[str, list[str]] = defaultdict(list)
    for relation in method_substances:
        relations_by_method[relation["method_id"]].append(relation)
        methods_by_substance[relation["substance_id"]].append(
            relation["method_id"]
        )
    applicabilities_by_method: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for applicability in applicabilities:
        applicabilities_by_method[applicability["method_id"]].append(applicability)

    method_matrix = [
        _method_audit(
            method,
            sorted(
                relations_by_method[method["method_id"]],
                key=lambda item: (
                    item.get("ordinal") is None,
                    item.get("ordinal") or 0,
                    item["substance_id"],
                ),
            ),
            sorted(
                applicabilities_by_method[method["method_id"]],
                key=lambda item: item["applicability_id"],
            ),
        )
        for method in sorted(methods, key=lambda item: item["method_id"])
    ]
    method_audit_by_id = {item["method_id"]: item for item in method_matrix}
    governed_method_numbers = {item["method_no"] for item in methods}
    candidate_collisions = sorted(
        item["method_no"]
        for item in candidate_methods
        if item["method_no"] in governed_method_numbers
    )
    if candidate_collisions:
        raise InspectionKnowledgeAuditError(
            "Candidate manifest overlaps the governed index: "
            + ", ".join(candidate_collisions)
        )

    relation_paths_with_applicability = 0
    missing_applicability_paths: list[dict[str, str]] = []
    for relation in method_substances:
        method_id = relation["method_id"]
        substance_id = relation["substance_id"]
        relevant = [
            item
            for item in applicabilities_by_method[method_id]
            if item["substance_id"] is None or item["substance_id"] == substance_id
        ]
        if relevant:
            relation_paths_with_applicability += 1
        else:
            missing_applicability_paths.append(
                {"method_id": method_id, "substance_id": substance_id}
            )

    bridge_risk_categories = {
        item["risk_category"] for item in bridge_mappings
    }
    bridge_reference_ids = {
        item["reference_mapping_id"] for item in bridge_mappings
    }
    reachability: list[dict[str, Any]] = []
    for mapping in sorted(risk_mappings, key=lambda item: item["mapping_id"]):
        target_type = mapping["target_type"]
        substance_id = mapping["substance_id"]
        candidate_method_ids = (
            sorted(set(methods_by_substance[substance_id]))
            if target_type == "substance"
            else []
        )
        methods_with_applicability: list[str] = []
        ready_method_ids: list[str] = []
        for method_id in candidate_method_ids:
            relevant_apps = [
                item
                for item in applicabilities_by_method[method_id]
                if item["substance_id"] is None
                or item["substance_id"] == substance_id
            ]
            if relevant_apps:
                methods_with_applicability.append(method_id)
            if relevant_apps and method_audit_by_id[method_id]["recommendation_ready"]:
                ready_method_ids.append(method_id)

        structurally_ready = target_type == "substance" and bool(ready_method_ids)
        bridged_category = mapping["risk_category"] in bridge_risk_categories
        end_to_end_reachable = structurally_ready and bridged_category
        if target_type == "substance_group":
            gap_reason = "group_not_expanded"
        elif not candidate_method_ids:
            gap_reason = "no_method_relation"
        elif not methods_with_applicability:
            gap_reason = "missing_applicability"
        elif not ready_method_ids:
            gap_reason = "no_current_deep_verified_method"
        elif not bridged_category:
            gap_reason = "no_evidence_to_risk_bridge"
        else:
            gap_reason = None
        reachability.append(
            {
                "mapping_id": mapping["mapping_id"],
                "risk_category": mapping["risk_category"],
                "target_type": target_type,
                "target": substance_id or mapping["target_group_label"],
                "has_explicit_substance": target_type == "substance",
                "method_ids": candidate_method_ids,
                "methods_with_applicability": methods_with_applicability,
                "recommendation_ready_method_ids": ready_method_ids,
                "structurally_recommendation_ready": structurally_ready,
                "bridge_referenced_directly": mapping["mapping_id"]
                in bridge_reference_ids,
                "evidence_to_risk_category_available": bridged_category,
                "end_to_end_reachable": end_to_end_reachable,
                "gap_reason": gap_reason,
            }
        )

    categories: list[dict[str, Any]] = []
    for category in sorted({item["risk_category"] for item in risk_mappings}):
        rows = [item for item in reachability if item["risk_category"] == category]
        categories.append(
            {
                "risk_category": category,
                "mapping_count": len(rows),
                "explicit_substance_mapping_count": sum(
                    item["has_explicit_substance"] for item in rows
                ),
                "group_mapping_count": sum(
                    item["target_type"] == "substance_group" for item in rows
                ),
                "structurally_recommendation_ready": any(
                    item["structurally_recommendation_ready"] for item in rows
                ),
                "evidence_to_risk_bridge_count": sum(
                    item["risk_category"] == category for item in bridge_mappings
                ),
                "end_to_end_reachable": any(
                    item["end_to_end_reachable"] for item in rows
                ),
            }
        )

    explicit_rows = [
        item for item in reachability if item["target_type"] == "substance"
    ]
    group_rows = [
        item for item in reachability if item["target_type"] == "substance_group"
    ]
    bridged_categories = {
        item["risk_category"] for item in categories if item["end_to_end_reachable"]
    }
    all_categories = {item["risk_category"] for item in categories}
    substances_with_methods = set(methods_by_substance)
    deep_methods = {
        item["method_id"]
        for item in method_matrix
        if item["knowledge_depth"] == "recommendation_ready"
    }
    depth_counts = {
        depth: sum(item["knowledge_depth"] == depth for item in method_matrix)
        for depth in (
            "reference_only",
            "analyte_verified",
            "applicability_verified",
            "recommendation_ready",
        )
    }
    document_numbers = {
        item["document_no"]
        for item in regulatory_documents
        if item["document_no"]
    }
    method_numbers = {item["method_no"] for item in methods}
    unresolved_lifecycle_edges = []
    for method in methods:
        for field, direction in (
            ("replaces_method_no", "replaces"),
            ("replaced_by_method_no", "replaced_by"),
        ):
            target = method[field]
            if target and target not in method_numbers and target not in document_numbers:
                unresolved_lifecycle_edges.append(
                    {
                        "method_id": method["method_id"],
                        "direction": direction,
                        "target_method_no": target,
                    }
                )

    used_risk_rows = [
        item
        for item in risk_mappings
        if item["risk_category"] in bridge_risk_categories
    ]
    used_substance_ids = {
        item["substance_id"]
        for item in used_risk_rows
        if item["target_type"] == "substance"
    }
    used_method_ids: set[str] = set()
    used_applicability_ids: set[str] = set()
    for substance_id in used_substance_ids:
        for method_id in methods_by_substance[substance_id]:
            if method_id not in deep_methods:
                continue
            used_method_ids.add(method_id)
            for item in applicabilities_by_method[method_id]:
                if item["substance_id"] is None or item["substance_id"] == substance_id:
                    used_applicability_ids.add(item["applicability_id"])

    metrics = {
        "method_reference_coverage": {
            **_ratio(
                sum(item["reference_complete"] for item in method_matrix),
                len(method_matrix),
            ),
            "denominator_definition": "methods in the committed Inspection Reference Index",
        },
        "method_deep_verification_coverage": {
            **_ratio(len(deep_methods), len(method_matrix)),
            "denominator_definition": "methods in the committed Inspection Reference Index",
        },
        "substance_to_method_coverage": {
            **_ratio(len(substances_with_methods), len(substances)),
            "denominator_definition": "substances in the committed Inspection Reference dataset",
        },
        "applicability_coverage": {
            **_ratio(relation_paths_with_applicability, len(method_substances)),
            "denominator_definition": "committed Method-to-Substance relation paths",
        },
        "risk_to_explicit_substance_coverage": {
            **_ratio(len(explicit_rows), len(reachability)),
            "denominator_definition": "current governed Risk target mappings, including group targets",
        },
        "group_resolution_coverage": {
            **_ratio(0, len(group_rows)),
            "denominator_definition": "current governed Risk-to-SubstanceGroup mappings",
        },
        "recommendation_structural_reachability": {
            **_ratio(
                sum(item["structurally_recommendation_ready"] for item in explicit_rows),
                len(explicit_rows),
            ),
            "denominator_definition": "current explicit governed Risk-to-Substance mappings",
        },
        "recommendation_end_to_end_reachability": {
            **_ratio(
                sum(item["end_to_end_reachable"] for item in explicit_rows),
                len(explicit_rows),
            ),
            "denominator_definition": (
                "current explicit governed Risk-to-Substance mappings; requires an existing "
                "Evidence-to-Risk category bridge and a structurally ready method path"
            ),
        },
        "risk_category_end_to_end_reachability": {
            **_ratio(len(bridged_categories), len(all_categories)),
            "denominator_definition": "risk categories present in the current governed Risk mapping dataset",
        },
    }

    source_scope_counts = Counter(
        {
            "explicit_applicable": sum(
                item["scope_type"] == "include" for item in applicabilities
            ),
            "requires_context": sum(
                item["scope_type"] == "conditional" for item in applicabilities
            ),
            "explicitly_not_applicable": sum(
                item["scope_type"] == "exclude" for item in applicabilities
            ),
            "unknown_relation_paths": len(missing_applicability_paths),
        }
    )

    return {
        "audit_contract_version": AUDIT_CONTRACT_VERSION,
        "dataset_versions": {
            "inspection": inspection["dataset_version"],
            "risk_substance": risk["dataset_version"],
            "effect_risk_bridge": bridge["bridge_version"],
        },
        "inventory": {
            "inspection_datasets": 1,
            "risk_mapping_datasets": 1,
            "effect_risk_bridges": 1,
            "governed_dataset_count": 3,
            "methods": len(methods),
            "indexed_methods": len(methods),
            "candidate_methods": len(candidate_methods),
            "candidate_method_ids": sorted(
                item["candidate_id"] for item in candidate_methods
            ),
            "knowledge_depth_counts": depth_counts,
            "method_type_counts": {
                key: sum(item["method_type"] == key for item in methods)
                for key in _METHOD_TYPES
            },
            "method_status_counts": {
                key: sum(item["method_status"] == key for item in methods)
                for key in _METHOD_STATUSES
            },
            "deprecated_methods": 0,
            "deprecated_status_supported": False,
            "substances": len(substances),
            "substances_with_group_label": sum(
                bool(item["substance_group"]) for item in substances
            ),
            "method_substance_relations": len(method_substances),
            "method_applicabilities": len(applicabilities),
            "applicability_scope_counts": dict(sorted(source_scope_counts.items())),
            "substance_regulatory_contexts": len(regulatory_contexts),
            "regulatory_documents": len(regulatory_documents),
            "method_regulatory_document_links": sum(
                bool(item["regulatory_document_id"]) for item in methods
            ),
            "unresolved_lifecycle_document_edges": len(
                unresolved_lifecycle_edges
            ),
            "risk_substance_mappings": len(explicit_rows),
            "risk_substance_group_mappings": len(group_rows),
            "risk_mappings_total": len(risk_mappings),
            "risk_categories": len(all_categories),
            "risk_group_labels": len(
                {
                    item["target_group_label"]
                    for item in risk_mappings
                    if item["target_type"] == "substance_group"
                }
            ),
            "group_membership_relations": len(group_memberships),
            "evidence_risk_bridge_mappings": len(bridge_mappings),
            "runtime_recommendation_usage": {
                "risk_categories": len(bridge_risk_categories),
                "risk_mapping_rows": len(used_risk_rows),
                "explicit_substances": len(used_substance_ids),
                "methods": len(used_method_ids),
                "applicability_records": len(used_applicability_ids),
                "risk_category_ids": sorted(bridge_risk_categories),
                "substance_ids": sorted(used_substance_ids),
                "method_ids": sorted(used_method_ids),
                "applicability_ids": sorted(used_applicability_ids),
            },
        },
        "method_matrix": method_matrix,
        "candidate_manifest": {
            "manifest_id": (candidates or {}).get("manifest_id"),
            "manifest_version": (candidates or {}).get("manifest_version"),
            "runtime_consumed": (candidates or {}).get("runtime_consumed"),
            "candidate_ids": sorted(
                item["candidate_id"] for item in candidate_methods
            ),
            "excluded_from_coverage_denominator": True,
        },
        "regulatory_documents": {
            "count": len(regulatory_documents),
            "method_link_count": sum(
                bool(item["regulatory_document_id"]) for item in methods
            ),
            "unresolved_lifecycle_edges": sorted(
                unresolved_lifecycle_edges,
                key=lambda item: (
                    item["method_id"],
                    item["direction"],
                    item["target_method_no"],
                ),
            ),
        },
        "risk_reachability": reachability,
        "risk_category_reachability": categories,
        "applicability_quality": {
            "record_classification": dict(sorted(source_scope_counts.items())),
            "missing_relation_paths": sorted(
                missing_applicability_paths,
                key=lambda item: (item["method_id"], item["substance_id"]),
            ),
            "interpretation": (
                "Record classes describe source scope facts. Product-level applicability "
                "still requires explicit Product Context; missing is unknown, not not-applicable."
            ),
        },
        "integrity": {
            "dangling_identities": dangling,
            "groups_expanded": False,
            "risk_mappings_derived_from_methods": False,
            "candidate_manifest_runtime_consumed": False,
            "depth_declarations_match_static_gate": all(
                item["depth_contract_matches"] for item in method_matrix
            ),
        },
        "metrics": metrics,
    }


def load_and_build_audit(
    inspection_path: Path = DEFAULT_INSPECTION_CONFIG,
    risk_path: Path = DEFAULT_RISK_CONFIG,
    bridge_path: Path = DEFAULT_BRIDGE_CONFIG,
    candidate_path: Path = DEFAULT_CANDIDATE_CONFIG,
) -> dict[str, Any]:
    """Validate governed files and build an offline audit."""

    inspection_raw = read_json(inspection_path)
    risk_raw = read_json(risk_path)
    bridge_raw = read_json(bridge_path)
    candidate_raw = read_json(candidate_path)
    inspection = validate_inspection_config(inspection_raw)
    risk = validate_risk_substance_config(risk_raw)
    bridge = validate_effect_risk_bridge_config(
        bridge_raw,
        risk_reference_config=risk_raw,
    )
    candidates = validate_inspection_candidate_manifest(candidate_raw)
    return build_audit(inspection, risk, bridge, candidates)


def render_markdown(report: Mapping[str, Any]) -> str:
    """Render a compact deterministic Markdown summary for human review."""

    inventory = report["inventory"]
    lines = [
        "# Inspection Knowledge Audit Summary",
        "",
        f"Contract: `{report['audit_contract_version']}`",
        "",
        "## Inventory",
        "",
        "| Fact | Count |",
        "|---|---:|",
        f"| Methods | {inventory['methods']} |",
        f"| Non-runtime candidates | {inventory['candidate_methods']} |",
        f"| Regulatory documents | {inventory['regulatory_documents']} |",
        f"| Substances | {inventory['substances']} |",
        f"| Method→Substance | {inventory['method_substance_relations']} |",
        f"| Applicabilities | {inventory['method_applicabilities']} |",
        f"| Regulatory contexts | {inventory['substance_regulatory_contexts']} |",
        f"| Risk→Substance | {inventory['risk_substance_mappings']} |",
        f"| Risk→Group | {inventory['risk_substance_group_mappings']} |",
        f"| Evidence→Risk bridge | {inventory['evidence_risk_bridge_mappings']} |",
        f"| Governed group memberships | {inventory['group_membership_relations']} |",
        "",
        "## Methods",
        "",
        "| Method | Lifecycle | Analytes | Applicability | Depth |",
        "|---|---|---:|---:|---|",
    ]
    for method in report["method_matrix"]:
        lines.append(
            f"| {method['method_no']} | {method['method_status']} | "
            f"{method['analyte_relation_count']} | {method['applicability_count']} | "
            f"{method['knowledge_depth']} |"
        )
    lines.extend(
        [
            "",
            "## Coverage",
            "",
            "| Metric | Numerator | Denominator | Ratio |",
            "|---|---:|---:|---:|",
        ]
    )
    for name, metric in report["metrics"].items():
        ratio = "n/a" if metric["ratio"] is None else f"{metric['ratio']:.1%}"
        lines.append(
            f"| `{name}` | {metric['numerator']} | {metric['denominator']} | {ratio} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspection", type=Path, default=DEFAULT_INSPECTION_CONFIG)
    parser.add_argument("--risk", type=Path, default=DEFAULT_RISK_CONFIG)
    parser.add_argument("--bridge", type=Path, default=DEFAULT_BRIDGE_CONFIG)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATE_CONFIG)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args(argv)

    report = load_and_build_audit(
        args.inspection,
        args.risk,
        args.bridge,
        args.candidates,
    )
    if args.format == "markdown":
        sys.stdout.write(render_markdown(report))
    else:
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
