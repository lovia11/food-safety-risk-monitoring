"""Deterministic V2 Claim-to-official-HealthFunction topic comparison.

This module consumes only persisted HealthFoodIdentity/Registry facts, the V2
Claim sidecar, and governed configuration.  It does not create RiskSignals,
recommendations, Review decisions, Sampling state, or legality conclusions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.claim_analysis import (
    CLAIM_ANALYSIS_ERROR_FILE,
    CLAIM_ANALYSIS_FILE,
    DEFAULT_CLAIM_TAXONOMY_PATH,
    load_claim_analysis,
    load_claim_taxonomy,
)
from src.health_food_identity import HEALTH_FOOD_IDENTITY_FILE, load_health_food_identity
from src.runtime import iso_now, read_json, write_json


CLAIM_CONSISTENCY_SCHEMA_VERSION = 1
CLAIM_CONSISTENCY_ASSESSMENT_VERSION = "claim-consistency-v2.0"
CLAIM_CONSISTENCY_FILE = "claim_consistency.json"
CLAIM_CONSISTENCY_ERROR_FILE = "claim_consistency_error.json"
DEFAULT_HEALTH_FUNCTIONS_PATH = (
    Path(__file__).resolve().parents[1] / "config" / "health_functions_v2.json"
)
DEFAULT_CLAIM_HEALTH_FUNCTION_MAPPING_PATH = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "claim_health_function_mapping_v2.json"
)

ASSESSMENT_STATES = frozenset(
    {
        "identity_not_verified",
        "claim_not_generated",
        "claim_analysis_error",
        "framework_unresolved",
        "official_function_unresolved",
        "no_page_claims",
        "assessed",
    }
)
CLAIM_RELATIONS = frozenset(
    {
        "function_topic_recorded",
        "function_topic_not_recorded",
        "no_governed_function_mapping",
        "mapping_unresolved",
    }
)
RESOLUTION_SOURCES = frozenset(
    {
        "current_official_name",
        "official_transition_alias",
        "explicit_governed_mapping",
    }
)
ATTENTION_GAP = "claim_expression_attention_dataset_pending_manual_governance"


class ClaimConsistencyConfigError(ValueError):
    """Governed HealthFunction or topic-mapping configuration is invalid."""


class ClaimConsistencyValidationError(ValueError):
    """A persisted ClaimConsistency artifact violates the domain contract."""


def _require_text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ClaimConsistencyConfigError(f"Claim consistency {field} is required")
    return text


def _require_artifact_text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ClaimConsistencyValidationError(
            f"Claim consistency artifact {field} is required"
        )
    return text


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = read_json(path.resolve())
    except (OSError, ValueError, TypeError) as exc:
        raise ClaimConsistencyConfigError(
            f"Cannot load {label} {path}: {type(exc).__name__}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise ClaimConsistencyConfigError(f"{label} must be a JSON object")
    return payload


def validate_health_function_dataset(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ClaimConsistencyConfigError(
            "HealthFunction dataset must be a JSON object"
        )
    _require_text(payload.get("dataset_version"), "health function dataset_version")
    frameworks = payload.get("frameworks")
    functions = payload.get("functions")
    aliases = payload.get("aliases")
    sources = payload.get("sources")
    if not all(isinstance(value, list) for value in (frameworks, functions, aliases, sources)):
        raise ClaimConsistencyConfigError(
            "HealthFunction frameworks, functions, aliases and sources must be arrays"
        )

    source_ids: set[str] = set()
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            raise ClaimConsistencyConfigError(f"sources[{index}] must be an object")
        source_id = _require_text(source.get("source_id"), f"sources[{index}].source_id")
        _require_text(source.get("source_name"), f"sources[{index}].source_name")
        _require_text(source.get("source_reference"), f"sources[{index}].source_reference")
        if source_id in source_ids:
            raise ClaimConsistencyConfigError(f"Duplicate HealthFunction source id: {source_id}")
        source_ids.add(source_id)

    framework_ids: set[str] = set()
    for index, framework in enumerate(frameworks):
        if not isinstance(framework, dict):
            raise ClaimConsistencyConfigError(f"frameworks[{index}] must be an object")
        framework_id = _require_text(
            framework.get("framework_id"), f"frameworks[{index}].framework_id"
        )
        _require_text(framework.get("official_name"), f"frameworks[{index}].official_name")
        referenced_sources = framework.get("source_ids")
        if not isinstance(referenced_sources, list) or not referenced_sources:
            raise ClaimConsistencyConfigError(
                f"frameworks[{index}].source_ids must be a non-empty array"
            )
        if any(str(source_id) not in source_ids for source_id in referenced_sources):
            raise ClaimConsistencyConfigError(
                f"frameworks[{index}] references an unknown provenance source"
            )
        if framework_id in framework_ids:
            raise ClaimConsistencyConfigError(f"Duplicate framework id: {framework_id}")
        framework_ids.add(framework_id)

    function_ids: set[str] = set()
    official_names: set[str] = set()
    for index, function in enumerate(functions):
        if not isinstance(function, dict):
            raise ClaimConsistencyConfigError(f"functions[{index}] must be an object")
        function_id = _require_text(
            function.get("function_id"), f"functions[{index}].function_id"
        )
        framework_id = _require_text(
            function.get("framework_id"), f"functions[{index}].framework_id"
        )
        official_name = _require_text(
            function.get("official_name"), f"functions[{index}].official_name"
        )
        _require_text(function.get("source_name"), f"functions[{index}].source_name")
        _require_text(
            function.get("source_reference"), f"functions[{index}].source_reference"
        )
        if framework_id not in framework_ids:
            raise ClaimConsistencyConfigError(
                f"Function {function_id} references unknown framework {framework_id}"
            )
        if function_id in function_ids:
            raise ClaimConsistencyConfigError(f"Duplicate function id: {function_id}")
        if official_name in official_names:
            raise ClaimConsistencyConfigError(
                f"Duplicate current official function name: {official_name}"
            )
        function_ids.add(function_id)
        official_names.add(official_name)

    alias_ids: set[str] = set()
    alias_texts: set[str] = set()
    for index, alias in enumerate(aliases):
        if not isinstance(alias, dict):
            raise ClaimConsistencyConfigError(f"aliases[{index}] must be an object")
        alias_id = _require_text(alias.get("alias_id"), f"aliases[{index}].alias_id")
        alias_text = _require_text(alias.get("alias_text"), f"aliases[{index}].alias_text")
        function_id = _require_text(
            alias.get("function_id"), f"aliases[{index}].function_id"
        )
        _require_text(alias.get("source_name"), f"aliases[{index}].source_name")
        _require_text(
            alias.get("source_reference"), f"aliases[{index}].source_reference"
        )
        if function_id not in function_ids:
            raise ClaimConsistencyConfigError(
                f"Alias {alias_id} references unknown function {function_id}"
            )
        if alias_id in alias_ids:
            raise ClaimConsistencyConfigError(f"Duplicate alias id: {alias_id}")
        if alias_text in alias_texts or alias_text in official_names:
            raise ClaimConsistencyConfigError(
                f"Ambiguous exact official function alias: {alias_text}"
            )
        alias_ids.add(alias_id)
        alias_texts.add(alias_text)

    metadata = payload.get("metadata")
    policy = metadata.get("normalization_policy") if isinstance(metadata, dict) else None
    allowed = policy.get("allowed_resolution_sources") if isinstance(policy, dict) else None
    if not isinstance(allowed, list) or set(map(str, allowed)) != RESOLUTION_SOURCES:
        raise ClaimConsistencyConfigError(
            "HealthFunction normalization sources do not match the governed contract"
        )
    if policy.get("raw_registry_function_must_be_preserved") is not True:
        raise ClaimConsistencyConfigError(
            "HealthFunction policy must preserve raw Registry strings"
        )
    return payload


def load_health_function_dataset(
    path: Path = DEFAULT_HEALTH_FUNCTIONS_PATH,
) -> dict[str, Any]:
    return validate_health_function_dataset(_load_json_object(path, "HealthFunction dataset"))


def validate_claim_health_function_mapping(
    payload: Any,
    *,
    health_functions: dict[str, Any],
    claim_taxonomy: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ClaimConsistencyConfigError("Claim/HealthFunction mapping must be an object")
    _require_text(payload.get("dataset_version"), "mapping dataset_version")
    if payload.get("claim_taxonomy_version") != claim_taxonomy.get("version"):
        raise ClaimConsistencyConfigError("Mapping Claim taxonomy version does not match")
    if payload.get("health_function_dataset_version") != health_functions.get(
        "dataset_version"
    ):
        raise ClaimConsistencyConfigError("Mapping HealthFunction dataset version does not match")
    if payload.get("allowed_relations") != ["topic_related"]:
        raise ClaimConsistencyConfigError("Mapping allows relations other than topic_related")
    mappings = payload.get("mappings")
    if not isinstance(mappings, list):
        raise ClaimConsistencyConfigError("Mapping records must be an array")
    claim_types = {
        str(item.get("id"))
        for item in claim_taxonomy.get("claim_types", [])
        if isinstance(item, dict)
    }
    functions = {
        str(item.get("function_id")): item
        for item in health_functions.get("functions", [])
        if isinstance(item, dict)
    }
    mapping_ids: set[str] = set()
    mapped_claim_types: set[str] = set()
    for index, mapping in enumerate(mappings):
        if not isinstance(mapping, dict):
            raise ClaimConsistencyConfigError(f"mappings[{index}] must be an object")
        mapping_id = _require_text(
            mapping.get("mapping_id"), f"mappings[{index}].mapping_id"
        )
        claim_type = _require_text(
            mapping.get("claim_type"), f"mappings[{index}].claim_type"
        )
        function_id = _require_text(
            mapping.get("health_function_id"),
            f"mappings[{index}].health_function_id",
        )
        if mapping.get("relation") != "topic_related":
            raise ClaimConsistencyConfigError(
                f"Mapping {mapping_id} relation must be topic_related"
            )
        if claim_type not in claim_types:
            raise ClaimConsistencyConfigError(
                f"Mapping {mapping_id} references unknown Claim type {claim_type}"
            )
        if function_id not in functions:
            raise ClaimConsistencyConfigError(
                f"Mapping {mapping_id} references unknown HealthFunction {function_id}"
            )
        references = mapping.get("source_references")
        if not isinstance(references, list) or not references:
            raise ClaimConsistencyConfigError(
                f"Mapping {mapping_id} must retain provenance references"
            )
        for reference in references:
            if not isinstance(reference, dict):
                raise ClaimConsistencyConfigError(
                    f"Mapping {mapping_id} provenance must be objects"
                )
            _require_text(reference.get("name"), f"mapping {mapping_id} source name")
            _require_text(
                reference.get("reference"), f"mapping {mapping_id} source reference"
            )
        forbidden = {
            "risk_mapping",
            "substance",
            "substance_id",
            "method",
            "method_id",
            "legal_status",
            "compliance_status",
        }
        if forbidden.intersection(map(str, mapping)):
            raise ClaimConsistencyConfigError(
                f"Mapping {mapping_id} contains a forbidden cross-domain field"
            )
        if mapping_id in mapping_ids:
            raise ClaimConsistencyConfigError(f"Duplicate mapping id: {mapping_id}")
        if claim_type in mapped_claim_types:
            raise ClaimConsistencyConfigError(
                f"Claim type has ambiguous governed mappings: {claim_type}"
            )
        mapping_ids.add(mapping_id)
        mapped_claim_types.add(claim_type)
    return payload


def load_claim_health_function_mapping(
    path: Path = DEFAULT_CLAIM_HEALTH_FUNCTION_MAPPING_PATH,
    *,
    health_functions: dict[str, Any] | None = None,
    claim_taxonomy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    health_functions = health_functions or load_health_function_dataset()
    claim_taxonomy = claim_taxonomy or load_claim_taxonomy()
    return validate_claim_health_function_mapping(
        _load_json_object(path, "Claim/HealthFunction mapping"),
        health_functions=health_functions,
        claim_taxonomy=claim_taxonomy,
    )


def resolve_official_function(
    raw_text: Any,
    *,
    health_functions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve a Registry string by exact governed identity only."""

    dataset = health_functions or load_health_function_dataset()
    raw = str(raw_text) if raw_text is not None else ""
    functions = {
        str(item["function_id"]): item for item in dataset["functions"]
    }
    for function in dataset["functions"]:
        if raw == function["official_name"]:
            return {
                "rawOfficialFunction": raw,
                "resolutionStatus": "resolved",
                "resolutionSource": "current_official_name",
                "frameworkId": function["framework_id"],
                "healthFunctionId": function["function_id"],
                "healthFunctionOfficialName": function["official_name"],
            }
    for alias in dataset["aliases"]:
        if raw == alias["alias_text"]:
            function = functions[str(alias["function_id"])]
            return {
                "rawOfficialFunction": raw,
                "resolutionStatus": "resolved",
                "resolutionSource": "official_transition_alias",
                "frameworkId": function["framework_id"],
                "healthFunctionId": function["function_id"],
                "healthFunctionOfficialName": function["official_name"],
            }
    return {
        "rawOfficialFunction": raw,
        "resolutionStatus": "unresolved",
        "resolutionSource": None,
        "frameworkId": None,
        "healthFunctionId": None,
        "healthFunctionOfficialName": None,
    }


def _explicit_registry_framework(
    identity: dict[str, Any],
) -> tuple[str | None, str | None, bool]:
    lookup = identity.get("officialLookup")
    lookup = lookup if isinstance(lookup, dict) else {}
    record = lookup.get("record")
    record = record if isinstance(record, dict) else {}
    assessment = identity.get("identityAssessment")
    assessment = assessment if isinstance(assessment, dict) else {}
    locations = (
        (record, "frameworkId"),
        (record, "healthFunctionFrameworkId"),
        (lookup, "frameworkId"),
        (assessment, "healthFunctionFrameworkId"),
    )
    explicitly_recorded = any(key in container for container, key in locations)
    candidates = tuple(container.get(key) for container, key in locations)
    values = list(dict.fromkeys(str(value) for value in candidates if value))
    if len(values) == 1:
        return values[0], "explicit_registry_framework", True
    return None, None, explicitly_recorded


def resolve_registry_framework(
    identity: dict[str, Any],
    resolved_functions: list[dict[str, Any]],
    *,
    health_functions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    dataset = health_functions or load_health_function_dataset()
    known = {str(item["framework_id"]) for item in dataset["frameworks"]}
    explicit, source, explicitly_recorded = _explicit_registry_framework(identity)
    if explicit is not None:
        if explicit not in known:
            return {"frameworkId": None, "resolutionSource": None}
        resolved_frameworks = {
            str(item["frameworkId"])
            for item in resolved_functions
            if item.get("frameworkId")
        }
        if resolved_frameworks and resolved_frameworks != {explicit}:
            return {"frameworkId": None, "resolutionSource": None}
        return {"frameworkId": explicit, "resolutionSource": source}
    if explicitly_recorded:
        return {"frameworkId": None, "resolutionSource": None}
    resolved_frameworks = {
        str(item["frameworkId"])
        for item in resolved_functions
        if item.get("frameworkId")
    }
    if len(resolved_frameworks) == 1:
        return {
            "frameworkId": next(iter(resolved_frameworks)),
            "resolutionSource": "resolved_official_functions",
        }
    return {"frameworkId": None, "resolutionSource": None}


def _append_gap(gaps: list[str], value: str) -> None:
    if value not in gaps:
        gaps.append(value)


def derive_claim_consistency(
    snapshot_id: str,
    identity: dict[str, Any],
    claim_analysis_status: str,
    claim_analysis: dict[str, Any] | None,
    *,
    health_functions: dict[str, Any] | None = None,
    mapping_dataset: dict[str, Any] | None = None,
    claim_taxonomy: dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build one Snapshot-scoped, non-adjudicative assessment."""

    if claim_analysis_status not in {"not_generated", "complete", "error"}:
        raise ClaimConsistencyValidationError("Unknown Claim analysis status")
    health_functions = health_functions or load_health_function_dataset()
    claim_taxonomy = claim_taxonomy or load_claim_taxonomy()
    mapping_dataset = mapping_dataset or load_claim_health_function_mapping(
        health_functions=health_functions, claim_taxonomy=claim_taxonomy
    )
    if claim_analysis_status == "complete" and not isinstance(claim_analysis, dict):
        raise ClaimConsistencyValidationError(
            "Complete Claim analysis requires a valid Claim artifact"
        )

    assessment = identity.get("identityAssessment")
    assessment = assessment if isinstance(assessment, dict) else {}
    lookup = identity.get("officialLookup")
    lookup = lookup if isinstance(lookup, dict) else {}
    record = lookup.get("record")
    record = record if isinstance(record, dict) else {}
    raw_official_functions = record.get("officialHealthFunctions")
    raw_official_functions = (
        [str(value) for value in raw_official_functions]
        if isinstance(raw_official_functions, list)
        else []
    )
    all_resolutions = [
        resolve_official_function(value, health_functions=health_functions)
        for value in raw_official_functions
    ]
    resolved = [
        item for item in all_resolutions if item["resolutionStatus"] == "resolved"
    ]
    unresolved = [
        item for item in all_resolutions if item["resolutionStatus"] == "unresolved"
    ]
    framework = resolve_registry_framework(
        identity, resolved, health_functions=health_functions
    )
    claim_signals = (
        claim_analysis.get("claimSignals", [])
        if isinstance(claim_analysis, dict)
        else []
    )
    claim_mentions = (
        claim_analysis.get("claimMentions", [])
        if isinstance(claim_analysis, dict)
        else []
    )
    if not isinstance(claim_signals, list) or not isinstance(claim_mentions, list):
        raise ClaimConsistencyValidationError("Claim artifact arrays are invalid")

    state: str
    gaps: list[str] = []
    if assessment.get("state") != "verified_match":
        state = "identity_not_verified"
        _append_gap(gaps, "health_food_identity_not_verified")
    elif claim_analysis_status == "not_generated":
        state = "claim_not_generated"
        _append_gap(gaps, "claim_analysis_not_generated")
    elif claim_analysis_status == "error":
        state = "claim_analysis_error"
        _append_gap(gaps, "claim_analysis_error")
    elif framework["frameworkId"] is None:
        state = "framework_unresolved"
        _append_gap(gaps, "registry_health_function_framework_unresolved")
    elif unresolved:
        state = "official_function_unresolved"
        _append_gap(gaps, "official_function_exact_resolution_incomplete")
    elif not claim_signals:
        state = "no_page_claims"
        _append_gap(gaps, "no_governed_page_claims_detected")
    else:
        state = "assessed"

    functions_by_id = {
        str(item["function_id"]): item for item in health_functions["functions"]
    }
    mappings_by_claim = {
        str(item["claim_type"]): item for item in mapping_dataset["mappings"]
    }
    resolved_ids = {str(item["healthFunctionId"]) for item in resolved}
    per_claim: list[dict[str, Any]] = []
    comparison_allowed = state in {"no_page_claims", "assessed"} or (
        state == "official_function_unresolved" and bool(resolved)
    )
    if comparison_allowed:
        for signal in claim_signals:
            if not isinstance(signal, dict):
                raise ClaimConsistencyValidationError(
                    "ClaimSignal records must be objects"
                )
            claim_type = str(signal.get("claimType") or "")
            signal_id = str(signal.get("claimSignalId") or "")
            mapping = mappings_by_claim.get(claim_type)
            relation: str
            per_gaps: list[str] = []
            mapped_function: dict[str, Any] | None = None
            if mapping is None:
                relation = "no_governed_function_mapping"
                per_gaps.append("no_governed_health_function_mapping")
            else:
                mapped_function = functions_by_id.get(str(mapping["health_function_id"]))
                if mapped_function is None:
                    relation = "mapping_unresolved"
                    per_gaps.append("governed_mapping_target_unresolved")
                elif mapped_function["framework_id"] != framework["frameworkId"]:
                    relation = "no_governed_function_mapping"
                    per_gaps.append("no_mapping_for_resolved_registry_framework")
                elif mapped_function["function_id"] in resolved_ids:
                    relation = "function_topic_recorded"
                elif unresolved:
                    relation = "mapping_unresolved"
                    per_gaps.append("unresolved_official_function_may_affect_comparison")
                else:
                    relation = "function_topic_not_recorded"
            mention_ids = [str(value) for value in signal.get("mentionIds", [])]
            evidence_ids = [str(value) for value in signal.get("evidenceIds", [])]
            per_claim.append(
                {
                    "claimSignalId": signal_id,
                    "claimType": claim_type,
                    "claimMentionIds": mention_ids,
                    "evidenceIds": evidence_ids,
                    "relation": relation,
                    "mappingId": mapping.get("mapping_id") if mapping else None,
                    "healthFunctionId": (
                        mapped_function.get("function_id") if mapped_function else None
                    ),
                    "healthFunctionOfficialName": (
                        mapped_function.get("official_name") if mapped_function else None
                    ),
                    "frameworkId": (
                        mapped_function.get("framework_id") if mapped_function else None
                    ),
                    "supportingResolvedOfficialFunctions": [
                        item
                        for item in resolved
                        if mapped_function
                        and item.get("healthFunctionId")
                        == mapped_function.get("function_id")
                    ],
                    "gaps": per_gaps,
                }
            )
    _append_gap(gaps, ATTENTION_GAP)
    relation_counts = {
        relation: sum(item["relation"] == relation for item in per_claim)
        for relation in CLAIM_RELATIONS
    }
    payload = {
        "schemaVersion": CLAIM_CONSISTENCY_SCHEMA_VERSION,
        "assessmentVersion": CLAIM_CONSISTENCY_ASSESSMENT_VERSION,
        "snapshotId": snapshot_id,
        "state": state,
        "claimTaxonomyVersion": claim_taxonomy["version"],
        "healthFunctionDatasetVersion": health_functions["dataset_version"],
        "claimHealthFunctionMappingVersion": mapping_dataset["dataset_version"],
        "healthFoodRegistryIdentifier": record.get("identifier"),
        "healthFoodRegistryRecordReferenceOrHash": (
            record.get("rawArtifactHash")
            or lookup.get("rawArtifactSha256")
            or record.get("sourceReference")
        ),
        "healthFoodRegistryRetrievedAt": record.get("retrievedAt"),
        "healthFoodRegistrySourceName": record.get("sourceName"),
        "healthFoodRegistrySourceReference": record.get("sourceReference"),
        "healthFoodRegistryRawArtifactPath": (
            record.get("rawArtifactPath") or lookup.get("rawArtifactPath")
        ),
        "registryFrameworkId": framework["frameworkId"],
        "registryFrameworkResolutionSource": framework["resolutionSource"],
        "rawOfficialFunctions": raw_official_functions,
        "resolvedHealthFunctions": resolved,
        "unresolvedOfficialFunctions": unresolved,
        "claimSignalIds": [
            str(item.get("claimSignalId") or "")
            for item in claim_signals
            if isinstance(item, dict)
        ],
        "claimMentionIds": [
            str(item.get("claimMentionId") or "")
            for item in claim_mentions
            if isinstance(item, dict)
        ],
        "perClaimAssessments": per_claim,
        "mentionAttentions": [],
        "summary": {
            "claimSignalCount": len(claim_signals),
            "functionTopicRecordedCount": relation_counts[
                "function_topic_recorded"
            ],
            "functionTopicNotRecordedCount": relation_counts[
                "function_topic_not_recorded"
            ],
            "noMappingCount": relation_counts["no_governed_function_mapping"],
            "mappingUnresolvedCount": relation_counts["mapping_unresolved"],
            "unresolvedOfficialFunctionCount": len(unresolved),
            "attentionMentionCount": 0,
        },
        "gaps": gaps,
        "generatedAt": generated_at or iso_now(),
    }
    return validate_claim_consistency(
        payload,
        expected_snapshot_id=snapshot_id,
        health_functions=health_functions,
        mapping_dataset=mapping_dataset,
        claim_taxonomy=claim_taxonomy,
    )


def validate_claim_consistency(
    payload: Any,
    *,
    expected_snapshot_id: str | None = None,
    health_functions: dict[str, Any] | None = None,
    mapping_dataset: dict[str, Any] | None = None,
    claim_taxonomy: dict[str, Any] | None = None,
    expected_claim_signal_ids: list[str] | None = None,
    expected_claim_mention_ids: list[str] | None = None,
    expected_claim_signals: list[dict[str, Any]] | None = None,
    expected_identity_state: str | None = None,
    expected_claim_analysis_status: str | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ClaimConsistencyValidationError("Claim consistency artifact must be an object")
    if payload.get("schemaVersion") != CLAIM_CONSISTENCY_SCHEMA_VERSION:
        raise ClaimConsistencyValidationError("Unsupported Claim consistency schemaVersion")
    if payload.get("assessmentVersion") != CLAIM_CONSISTENCY_ASSESSMENT_VERSION:
        raise ClaimConsistencyValidationError("Unsupported Claim consistency assessmentVersion")
    snapshot_id = _require_artifact_text(payload.get("snapshotId"), "snapshotId")
    if expected_snapshot_id and snapshot_id != expected_snapshot_id:
        raise ClaimConsistencyValidationError("Claim consistency snapshotId mismatch")
    if payload.get("state") not in ASSESSMENT_STATES:
        raise ClaimConsistencyValidationError("Unknown Claim consistency state")
    health_functions = health_functions or load_health_function_dataset()
    claim_taxonomy = claim_taxonomy or load_claim_taxonomy()
    mapping_dataset = mapping_dataset or load_claim_health_function_mapping(
        health_functions=health_functions, claim_taxonomy=claim_taxonomy
    )
    expected_versions = {
        "claimTaxonomyVersion": claim_taxonomy["version"],
        "healthFunctionDatasetVersion": health_functions["dataset_version"],
        "claimHealthFunctionMappingVersion": mapping_dataset["dataset_version"],
    }
    for field, expected in expected_versions.items():
        if payload.get(field) != expected:
            raise ClaimConsistencyValidationError(
                f"Claim consistency {field} does not match governed config"
            )
    arrays = (
        "rawOfficialFunctions",
        "resolvedHealthFunctions",
        "unresolvedOfficialFunctions",
        "claimSignalIds",
        "claimMentionIds",
        "perClaimAssessments",
        "mentionAttentions",
        "gaps",
    )
    if any(not isinstance(payload.get(field), list) for field in arrays):
        raise ClaimConsistencyValidationError("Claim consistency array field is invalid")
    if expected_claim_signal_ids is not None and payload["claimSignalIds"] != expected_claim_signal_ids:
        raise ClaimConsistencyValidationError(
            "Claim consistency ClaimSignal trace differs from the Claim artifact"
        )
    if expected_claim_mention_ids is not None and payload["claimMentionIds"] != expected_claim_mention_ids:
        raise ClaimConsistencyValidationError(
            "Claim consistency ClaimMention trace differs from the Claim artifact"
        )
    if payload["mentionAttentions"] != []:
        raise ClaimConsistencyValidationError(
            "Claim expression attention entries are not governed in V2-6B1"
        )
    if ATTENTION_GAP not in payload["gaps"]:
        raise ClaimConsistencyValidationError(
            "Claim expression attention governance gap must be explicit"
        )
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise ClaimConsistencyValidationError("Claim consistency summary is invalid")
    for key in (
        "claimSignalCount",
        "functionTopicRecordedCount",
        "functionTopicNotRecordedCount",
        "noMappingCount",
        "mappingUnresolvedCount",
        "unresolvedOfficialFunctionCount",
        "attentionMentionCount",
    ):
        value = summary.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ClaimConsistencyValidationError(
                f"Claim consistency summary {key} is invalid"
            )
    if summary["claimSignalCount"] != len(payload["claimSignalIds"]):
        raise ClaimConsistencyValidationError(
            "Claim consistency ClaimSignal summary count is inconsistent"
        )
    if summary["unresolvedOfficialFunctionCount"] != len(
        payload["unresolvedOfficialFunctions"]
    ):
        raise ClaimConsistencyValidationError(
            "Claim consistency unresolved-function count is inconsistent"
        )
    if summary["attentionMentionCount"] != len(payload["mentionAttentions"]):
        raise ClaimConsistencyValidationError(
            "Claim consistency attention count is inconsistent"
        )
    raw = payload["rawOfficialFunctions"]
    resolutions = payload["resolvedHealthFunctions"] + payload["unresolvedOfficialFunctions"]
    if [item.get("rawOfficialFunction") for item in resolutions if isinstance(item, dict)] != raw:
        # Resolved/unresolved are separate arrays, so compare as a stable multiset below.
        expected_counts: dict[str, int] = {}
        actual_counts: dict[str, int] = {}
        for value in raw:
            expected_counts[str(value)] = expected_counts.get(str(value), 0) + 1
        for item in resolutions:
            if not isinstance(item, dict):
                raise ClaimConsistencyValidationError("Official function resolution is invalid")
            value = str(item.get("rawOfficialFunction"))
            actual_counts[value] = actual_counts.get(value, 0) + 1
        if actual_counts != expected_counts:
            raise ClaimConsistencyValidationError(
                "Official function projection does not preserve every raw value"
            )
    function_ids = {
        str(item["function_id"]): item for item in health_functions["functions"]
    }
    for item in payload["resolvedHealthFunctions"]:
        if not isinstance(item, dict) or item.get("resolutionStatus") != "resolved":
            raise ClaimConsistencyValidationError("Resolved HealthFunction row is invalid")
        function = function_ids.get(str(item.get("healthFunctionId")))
        if function is None or item.get("frameworkId") != function["framework_id"]:
            raise ClaimConsistencyValidationError("Resolved HealthFunction identity is invalid")
        if item.get("resolutionSource") not in RESOLUTION_SOURCES:
            raise ClaimConsistencyValidationError("Official resolution source is invalid")
    expected_resolutions = [
        resolve_official_function(value, health_functions=health_functions)
        for value in raw
    ]
    if payload["resolvedHealthFunctions"] != [
        item for item in expected_resolutions if item["resolutionStatus"] == "resolved"
    ] or payload["unresolvedOfficialFunctions"] != [
        item for item in expected_resolutions if item["resolutionStatus"] == "unresolved"
    ]:
        raise ClaimConsistencyValidationError(
            "Official function resolutions are not the exact governed projection"
        )
    state = str(payload["state"])
    framework_id = payload.get("registryFrameworkId")
    if state == "framework_unresolved" and framework_id is not None:
        raise ClaimConsistencyValidationError(
            "framework_unresolved artifact cannot contain a resolved framework"
        )
    if state in {
        "official_function_unresolved",
        "no_page_claims",
        "assessed",
    } and not framework_id:
        raise ClaimConsistencyValidationError(
            "Comparable Claim consistency state requires a resolved framework"
        )
    if state == "official_function_unresolved" and not payload[
        "unresolvedOfficialFunctions"
    ]:
        raise ClaimConsistencyValidationError(
            "official_function_unresolved requires an unresolved Registry string"
        )
    if state in {"no_page_claims", "assessed"} and payload[
        "unresolvedOfficialFunctions"
    ]:
        raise ClaimConsistencyValidationError(
            "Fully resolved Claim consistency state retains unresolved functions"
        )
    if state == "no_page_claims" and payload["claimSignalIds"]:
        raise ClaimConsistencyValidationError(
            "no_page_claims cannot contain formal ClaimSignals"
        )
    if state == "assessed" and not payload["claimSignalIds"]:
        raise ClaimConsistencyValidationError(
            "assessed requires at least one formal ClaimSignal"
        )
    if expected_identity_state is not None:
        expected_state = None
        if expected_identity_state != "verified_match":
            expected_state = "identity_not_verified"
        elif expected_claim_analysis_status == "not_generated":
            expected_state = "claim_not_generated"
        elif expected_claim_analysis_status == "error":
            expected_state = "claim_analysis_error"
        elif framework_id is None:
            expected_state = "framework_unresolved"
        elif payload["unresolvedOfficialFunctions"]:
            expected_state = "official_function_unresolved"
        elif not payload["claimSignalIds"]:
            expected_state = "no_page_claims"
        else:
            expected_state = "assessed"
        if state != expected_state:
            raise ClaimConsistencyValidationError(
                "Claim consistency state conflicts with persisted upstream facts"
            )
    claim_signal_ids = set(map(str, payload["claimSignalIds"]))
    for item in payload["perClaimAssessments"]:
        if not isinstance(item, dict):
            raise ClaimConsistencyValidationError("Per-Claim assessment must be an object")
        if str(item.get("claimSignalId")) not in claim_signal_ids:
            raise ClaimConsistencyValidationError("Per-Claim assessment references unknown signal")
        if item.get("relation") not in CLAIM_RELATIONS:
            raise ClaimConsistencyValidationError("Per-Claim relation is invalid")
        if not isinstance(item.get("claimMentionIds"), list) or not isinstance(
            item.get("evidenceIds"), list
        ) or not isinstance(item.get("gaps"), list):
            raise ClaimConsistencyValidationError("Per-Claim trace fields are invalid")
    relation_summary_keys = {
        "function_topic_recorded": "functionTopicRecordedCount",
        "function_topic_not_recorded": "functionTopicNotRecordedCount",
        "no_governed_function_mapping": "noMappingCount",
        "mapping_unresolved": "mappingUnresolvedCount",
    }
    for relation, key in relation_summary_keys.items():
        if summary[key] != sum(
            item.get("relation") == relation
            for item in payload["perClaimAssessments"]
            if isinstance(item, dict)
        ):
            raise ClaimConsistencyValidationError(
                f"Claim consistency relation count {key} is inconsistent"
            )
    if expected_claim_signals is not None:
        expected_by_id = {
            str(item.get("claimSignalId")): item
            for item in expected_claim_signals
            if isinstance(item, dict)
        }
        for item in payload["perClaimAssessments"]:
            signal = expected_by_id.get(str(item["claimSignalId"]))
            if signal is None or item["claimType"] != signal.get("claimType"):
                raise ClaimConsistencyValidationError(
                    "Per-Claim assessment conflicts with its ClaimSignal"
                )
            if item["claimMentionIds"] != signal.get("mentionIds") or item[
                "evidenceIds"
            ] != signal.get("evidenceIds"):
                raise ClaimConsistencyValidationError(
                    "Per-Claim assessment trace conflicts with its ClaimSignal"
                )
    _require_artifact_text(payload.get("generatedAt"), "generatedAt")
    forbidden = {
        "riskLevel",
        "legalStatus",
        "complianceStatus",
        "approvedWording",
        "allowedClaim",
        "officialAliasMatchedForClaim",
        "totalRiskScore",
        "consistencyScore",
        "passRate",
        "complianceRate",
    }
    stack: list[Any] = [payload]
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            if forbidden.intersection(value):
                raise ClaimConsistencyValidationError(
                    "Claim consistency artifact contains a forbidden adjudicative field"
                )
            stack.extend(value.values())
        elif isinstance(value, list):
            stack.extend(value)
    return payload


def load_claim_consistency(
    artifact_path: Path,
    *,
    expected_snapshot_id: str | None = None,
    health_functions: dict[str, Any] | None = None,
    mapping_dataset: dict[str, Any] | None = None,
    claim_taxonomy: dict[str, Any] | None = None,
    expected_claim_signal_ids: list[str] | None = None,
    expected_claim_mention_ids: list[str] | None = None,
    expected_claim_signals: list[dict[str, Any]] | None = None,
    expected_identity_state: str | None = None,
    expected_claim_analysis_status: str | None = None,
) -> dict[str, Any] | None:
    if not artifact_path.is_file():
        return None
    try:
        payload = read_json(artifact_path)
    except (OSError, ValueError, TypeError) as exc:
        raise ClaimConsistencyValidationError(
            f"Cannot load Claim consistency artifact: {type(exc).__name__}: {exc}"
        ) from exc
    return validate_claim_consistency(
        payload,
        expected_snapshot_id=expected_snapshot_id,
        health_functions=health_functions,
        mapping_dataset=mapping_dataset,
        claim_taxonomy=claim_taxonomy,
        expected_claim_signal_ids=expected_claim_signal_ids,
        expected_claim_mention_ids=expected_claim_mention_ids,
        expected_claim_signals=expected_claim_signals,
        expected_identity_state=expected_identity_state,
        expected_claim_analysis_status=expected_claim_analysis_status,
    )


def write_claim_consistency_from_artifacts(
    product_root: Path,
    snapshot_id: str,
    *,
    health_functions_path: Path = DEFAULT_HEALTH_FUNCTIONS_PATH,
    mapping_path: Path = DEFAULT_CLAIM_HEALTH_FUNCTION_MAPPING_PATH,
    claim_taxonomy_path: Path = DEFAULT_CLAIM_TAXONOMY_PATH,
) -> dict[str, Any]:
    health_functions = load_health_function_dataset(health_functions_path)
    claim_taxonomy = load_claim_taxonomy(claim_taxonomy_path)
    mapping_dataset = load_claim_health_function_mapping(
        mapping_path,
        health_functions=health_functions,
        claim_taxonomy=claim_taxonomy,
    )
    identity = load_health_food_identity(
        product_root / HEALTH_FOOD_IDENTITY_FILE,
        expected_snapshot_id=snapshot_id,
    )
    if identity is None:
        raise ClaimConsistencyValidationError(
            "A valid HealthFoodIdentity artifact is required"
        )
    claim_path = product_root / CLAIM_ANALYSIS_FILE
    claim_analysis = load_claim_analysis(
        claim_path,
        expected_snapshot_id=snapshot_id,
        taxonomy=claim_taxonomy,
    )
    if claim_analysis is not None:
        claim_status = "complete"
    elif (product_root / CLAIM_ANALYSIS_ERROR_FILE).is_file():
        claim_status = "error"
    else:
        claim_status = "not_generated"
    payload = derive_claim_consistency(
        snapshot_id,
        identity,
        claim_status,
        claim_analysis,
        health_functions=health_functions,
        mapping_dataset=mapping_dataset,
        claim_taxonomy=claim_taxonomy,
    )
    write_json(product_root / CLAIM_CONSISTENCY_FILE, payload)
    (product_root / CLAIM_CONSISTENCY_ERROR_FILE).unlink(missing_ok=True)
    return payload


def record_claim_consistency_failure(
    product_root: Path,
    snapshot_id: str,
    error: Exception,
) -> dict[str, Any]:
    product_root = product_root.resolve()
    (product_root / CLAIM_CONSISTENCY_FILE).unlink(missing_ok=True)
    payload = {
        "schemaVersion": CLAIM_CONSISTENCY_SCHEMA_VERSION,
        "assessmentVersion": CLAIM_CONSISTENCY_ASSESSMENT_VERSION,
        "status": "error",
        "snapshotId": snapshot_id,
        "errorType": type(error).__name__,
        "message": str(error),
        "failedAt": iso_now(),
    }
    write_json(product_root / CLAIM_CONSISTENCY_ERROR_FILE, payload)
    return payload
