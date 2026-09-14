"""Deterministic, Evidence-backed V2 ClaimMention/ClaimSignal derivation.

This sidecar records only marketing expressions observed in current-product,
seller-managed Evidence.  It deliberately does not create health-function,
risk, legality, substance, method, Review, or Sampling conclusions.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Iterable

from src.runtime import iso_now, read_json, write_json


CLAIM_ANALYSIS_SCHEMA_VERSION = 1
CLAIM_ANALYSIS_FILE = "claim_analysis.json"
CLAIM_ANALYSIS_ERROR_FILE = "claim_analysis_error.json"
CLAIM_EXTRACTION_METHOD = "exact_literal_occurrence"
DEFAULT_CLAIM_TAXONOMY_PATH = (
    Path(__file__).resolve().parents[1] / "config" / "claim_taxonomy_v2.json"
)
SUPPORTED_MATCH_MODES = frozenset({"exact"})

_FORBIDDEN_MAPPING_KEYS = frozenset(
    {
        "risk_mapping",
        "risk_mappings",
        "health_function_mapping",
        "health_function_mappings",
        "healthfunction_mapping",
        "healthfunction_mappings",
        "substance_mapping",
        "substance_mappings",
        "method_mapping",
        "method_mappings",
        "legal_status",
        "legality",
        "compliance_status",
    }
)


class ClaimTaxonomyValidationError(ValueError):
    """The governed Claim taxonomy cannot safely drive extraction."""


class ClaimAnalysisValidationError(ValueError):
    """A persisted Claim analysis artifact violates its domain contract."""


def normalize_claim_text(value: Any) -> str:
    """Apply formatting-only normalization while preserving the raw text."""

    text = unicodedata.normalize("NFKC", str(value or ""))
    return re.sub(r"\s+", " ", text).strip()


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{digest}"


def _require_nonempty(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ClaimTaxonomyValidationError(f"Claim taxonomy {field} is required")
    return text


def _validate_forbidden_keys(value: Any, path: str = "taxonomy") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = str(key).strip().lower()
            if normalized_key in _FORBIDDEN_MAPPING_KEYS:
                raise ClaimTaxonomyValidationError(
                    f"Claim taxonomy contains forbidden cross-domain field: {path}.{key}"
                )
            _validate_forbidden_keys(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _validate_forbidden_keys(item, f"{path}[{index}]")


def validate_claim_taxonomy(payload: Any) -> dict[str, Any]:
    """Strictly validate the sole governed Claim taxonomy runtime input."""

    if not isinstance(payload, dict):
        raise ClaimTaxonomyValidationError("Claim taxonomy must be a JSON object")
    _validate_forbidden_keys(payload)
    _require_nonempty(payload.get("version"), "version")
    claim_types = payload.get("claim_types")
    expressions = payload.get("expressions")
    if not isinstance(claim_types, list) or not isinstance(expressions, list):
        raise ClaimTaxonomyValidationError(
            "Claim taxonomy claim_types and expressions must be arrays"
        )

    type_ids: set[str] = set()
    for index, item in enumerate(claim_types):
        if not isinstance(item, dict):
            raise ClaimTaxonomyValidationError(
                f"Claim taxonomy claim_types[{index}] must be an object"
            )
        claim_type = _require_nonempty(item.get("id"), f"claim_types[{index}].id")
        _require_nonempty(item.get("label_zh"), f"claim_types[{index}].label_zh")
        _require_nonempty(item.get("status"), f"claim_types[{index}].status")
        if claim_type in type_ids:
            raise ClaimTaxonomyValidationError(
                f"Duplicate Claim type id: {claim_type}"
            )
        type_ids.add(claim_type)

    expression_ids: set[str] = set()
    for index, item in enumerate(expressions):
        if not isinstance(item, dict):
            raise ClaimTaxonomyValidationError(
                f"Claim taxonomy expressions[{index}] must be an object"
            )
        expression_id = _require_nonempty(
            item.get("expression_id"), f"expressions[{index}].expression_id"
        )
        _require_nonempty(item.get("text"), f"expressions[{index}].text")
        claim_type = _require_nonempty(
            item.get("claim_type"), f"expressions[{index}].claim_type"
        )
        match_mode = _require_nonempty(
            item.get("match_mode"), f"expressions[{index}].match_mode"
        )
        _require_nonempty(item.get("status"), f"expressions[{index}].status")
        if expression_id in expression_ids:
            raise ClaimTaxonomyValidationError(
                f"Duplicate Claim expression id: {expression_id}"
            )
        if claim_type not in type_ids:
            raise ClaimTaxonomyValidationError(
                f"Unknown Claim type reference: {claim_type}"
            )
        if match_mode not in SUPPORTED_MATCH_MODES:
            raise ClaimTaxonomyValidationError(
                f"Unsupported Claim match mode: {match_mode}"
            )
        if str(item.get("status") or "") == "active":
            _require_nonempty(item.get("source"), f"expressions[{index}].source")
        expression_ids.add(expression_id)

    metadata = payload.get("metadata")
    policy = metadata.get("formal_claim_source_policy") if isinstance(metadata, dict) else None
    eligible = policy.get("eligible_content_origins") if isinstance(policy, dict) else None
    if eligible != ["seller_managed"]:
        raise ClaimTaxonomyValidationError(
            "Claim taxonomy formal source policy must allow only seller_managed"
        )
    return payload


def load_claim_taxonomy(path: Path = DEFAULT_CLAIM_TAXONOMY_PATH) -> dict[str, Any]:
    try:
        payload = read_json(path.resolve())
    except (OSError, ValueError, TypeError) as exc:
        raise ClaimTaxonomyValidationError(
            f"Cannot load Claim taxonomy {path}: {type(exc).__name__}: {exc}"
        ) from exc
    return validate_claim_taxonomy(payload)


def _field(item: dict[str, Any], camel: str, snake: str) -> Any:
    return item.get(camel) if camel in item else item.get(snake)


def _literal_occurrences(text: str, expression: str) -> list[int]:
    """Return every literal occurrence, retaining overlaps deterministically."""

    positions: list[int] = []
    start = 0
    while expression and start <= len(text) - len(expression):
        position = text.find(expression, start)
        if position < 0:
            break
        positions.append(position)
        start = position + 1
    return positions


def derive_claim_analysis(
    snapshot_id: str,
    evidence_records: Iterable[dict[str, Any]],
    taxonomy: dict[str, Any],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Derive formal Claim records from canonical Snapshot Evidence only."""

    taxonomy = validate_claim_taxonomy(taxonomy)
    snapshot_id = str(snapshot_id or "").strip()
    if not snapshot_id:
        raise ClaimAnalysisValidationError("snapshot_id is required")
    created_at = generated_at or iso_now()
    taxonomy_version = str(taxonomy["version"])
    types = {
        str(item["id"]): item
        for item in taxonomy["claim_types"]
        if str(item.get("status") or "") == "active"
    }
    expressions = [
        item
        for item in taxonomy["expressions"]
        if str(item.get("status") or "") == "active"
        and str(item.get("claim_type") or "") in types
    ]

    evidence = list(evidence_records)
    seen_evidence_ids: set[str] = set()
    formal_evidence_count = 0
    mentions: list[dict[str, Any]] = []
    for evidence_ordinal, item in enumerate(evidence, start=1):
        if not isinstance(item, dict):
            raise ClaimAnalysisValidationError(
                f"Evidence record {evidence_ordinal} must be an object"
            )
        evidence_id = str(_field(item, "evidenceId", "evidence_id") or "").strip()
        if not evidence_id:
            raise ClaimAnalysisValidationError(
                f"Evidence record {evidence_ordinal} has no evidence_id"
            )
        if evidence_id in seen_evidence_ids:
            raise ClaimAnalysisValidationError(f"Duplicate Evidence id: {evidence_id}")
        seen_evidence_ids.add(evidence_id)
        evidence_snapshot_id = str(
            _field(item, "snapshotId", "snapshot_id") or snapshot_id
        )
        if evidence_snapshot_id != snapshot_id:
            raise ClaimAnalysisValidationError(
                f"Evidence {evidence_id} belongs to another Snapshot"
            )
        source_scope = str(
            _field(item, "contentOrigin", "content_origin") or ""
        ).strip()
        if source_scope != "seller_managed":
            continue
        formal_evidence_count += 1
        raw_text = str(item.get("text") or "")
        normalized_text = normalize_claim_text(raw_text)
        if not normalized_text:
            continue
        source_asset_type = str(
            _field(item, "sourceType", "source_type") or ""
        ).strip()
        source_path = str(
            _field(item, "sourcePath", "source_path") or ""
        ).strip()
        line_number = _field(item, "lineNumber", "line_number")
        for expression in expressions:
            governed_text = str(expression["text"])
            normalized_expression = normalize_claim_text(governed_text)
            positions = _literal_occurrences(normalized_text, normalized_expression)
            for occurrence_ordinal, _position in enumerate(positions, start=1):
                expression_id = str(expression["expression_id"])
                claim_type = str(expression["claim_type"])
                mention_id = _stable_id(
                    "cm",
                    snapshot_id,
                    evidence_id,
                    expression_id,
                    str(occurrence_ordinal),
                )
                mentions.append(
                    {
                        "claimMentionId": mention_id,
                        "snapshotId": snapshot_id,
                        "claimType": claim_type,
                        "expressionId": expression_id,
                        "rawText": raw_text,
                        "normalizedText": normalized_text,
                        "matchedExpression": governed_text,
                        "evidenceId": evidence_id,
                        "sourceScope": "seller_managed",
                        "sourceAssetType": source_asset_type,
                        "sourceLocator": {
                            "sourcePath": source_path,
                            "lineNumber": line_number,
                        },
                        "extractionMethod": CLAIM_EXTRACTION_METHOD,
                        "taxonomyVersion": taxonomy_version,
                        "createdAt": created_at,
                    }
                )

    signals: list[dict[str, Any]] = []
    for claim_type, type_item in types.items():
        selected = [item for item in mentions if item["claimType"] == claim_type]
        if not selected:
            continue
        mention_ids = [str(item["claimMentionId"]) for item in selected]
        evidence_ids = list(dict.fromkeys(str(item["evidenceId"]) for item in selected))
        signals.append(
            {
                "claimSignalId": _stable_id(
                    "cs", snapshot_id, claim_type, taxonomy_version
                ),
                "snapshotId": snapshot_id,
                "claimType": claim_type,
                "displayLabel": str(type_item["label_zh"]),
                "mentionIds": mention_ids,
                "evidenceIds": evidence_ids,
                "taxonomyVersion": taxonomy_version,
                "status": "normalized",
                "createdAt": created_at,
            }
        )

    return {
        "schemaVersion": CLAIM_ANALYSIS_SCHEMA_VERSION,
        "status": "complete",
        "taxonomyVersion": taxonomy_version,
        "snapshotId": snapshot_id,
        "generatedAt": created_at,
        "claimMentions": mentions,
        "claimSignals": signals,
        "sourcePolicy": {
            "formalClaimSourceScope": "seller_managed",
            "userGenerated": "auxiliary_only_not_included",
            "excludedOtherProduct": "forbidden_not_included",
        },
        "summary": {
            "inputEvidenceCount": len(evidence),
            "formalEvidenceCount": formal_evidence_count,
            "claimMentionCount": len(mentions),
            "claimSignalCount": len(signals),
        },
    }


def _required_string(item: dict[str, Any], field: str, context: str) -> str:
    value = str(item.get(field) or "").strip()
    if not value:
        raise ClaimAnalysisValidationError(f"{context}.{field} is required")
    return value


def validate_claim_analysis(
    payload: Any,
    *,
    expected_snapshot_id: str | None = None,
    expected_evidence_ids: set[str] | None = None,
    expected_evidence_records: dict[str, dict[str, Any]] | None = None,
    taxonomy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate an artifact before treating it as rebuild authority."""

    if not isinstance(payload, dict):
        raise ClaimAnalysisValidationError("Claim analysis must be a JSON object")
    if payload.get("schemaVersion") != CLAIM_ANALYSIS_SCHEMA_VERSION:
        raise ClaimAnalysisValidationError("Unsupported Claim analysis schemaVersion")
    if payload.get("status") != "complete":
        raise ClaimAnalysisValidationError("Claim analysis status must be complete")
    snapshot_id = _required_string(payload, "snapshotId", "claimAnalysis")
    taxonomy_version = _required_string(payload, "taxonomyVersion", "claimAnalysis")
    _required_string(payload, "generatedAt", "claimAnalysis")
    if expected_snapshot_id and snapshot_id != expected_snapshot_id:
        raise ClaimAnalysisValidationError("Claim analysis belongs to another Snapshot")
    mentions = payload.get("claimMentions")
    signals = payload.get("claimSignals")
    if not isinstance(mentions, list) or not isinstance(signals, list):
        raise ClaimAnalysisValidationError(
            "claimMentions and claimSignals must be arrays"
        )

    taxonomy_types: dict[str, dict[str, Any]] | None = None
    taxonomy_expressions: dict[str, dict[str, Any]] | None = None
    if taxonomy is not None:
        taxonomy = validate_claim_taxonomy(taxonomy)
        if str(taxonomy["version"]) != taxonomy_version:
            raise ClaimAnalysisValidationError(
                "Claim analysis taxonomy version differs from the governed taxonomy"
            )
        taxonomy_types = {
            str(item["id"]): item
            for item in taxonomy["claim_types"]
            if str(item.get("status") or "") == "active"
        }
        taxonomy_expressions = {
            str(item["expression_id"]): item
            for item in taxonomy["expressions"]
            if str(item.get("status") or "") == "active"
        }

    mention_by_id: dict[str, dict[str, Any]] = {}
    occurrence_counts: dict[tuple[str, str], int] = {}
    for index, item in enumerate(mentions):
        if not isinstance(item, dict):
            raise ClaimAnalysisValidationError(f"claimMentions[{index}] must be an object")
        context = f"claimMentions[{index}]"
        mention_id = _required_string(item, "claimMentionId", context)
        if mention_id in mention_by_id:
            raise ClaimAnalysisValidationError(f"Duplicate ClaimMention id: {mention_id}")
        if _required_string(item, "snapshotId", context) != snapshot_id:
            raise ClaimAnalysisValidationError(f"{context} belongs to another Snapshot")
        if _required_string(item, "sourceScope", context) != "seller_managed":
            raise ClaimAnalysisValidationError(f"{context} is not seller-managed")
        if _required_string(item, "taxonomyVersion", context) != taxonomy_version:
            raise ClaimAnalysisValidationError(f"{context} taxonomy version differs")
        for field in (
            "claimType",
            "expressionId",
            "rawText",
            "normalizedText",
            "matchedExpression",
            "evidenceId",
            "sourceAssetType",
            "extractionMethod",
            "createdAt",
        ):
            _required_string(item, field, context)
        expression_id = str(item["expressionId"])
        claim_type = str(item["claimType"])
        if taxonomy_expressions is not None:
            expression = taxonomy_expressions.get(expression_id)
            if expression is None:
                raise ClaimAnalysisValidationError(
                    f"{context} references an unknown active Claim expression"
                )
            if (
                str(expression["claim_type"]) != claim_type
                or str(expression["text"]) != str(item["matchedExpression"])
            ):
                raise ClaimAnalysisValidationError(
                    f"{context} conflicts with the governed Claim expression"
                )
        if not isinstance(item.get("sourceLocator"), dict):
            raise ClaimAnalysisValidationError(f"{context}.sourceLocator must be an object")
        evidence_id = str(item["evidenceId"])
        if expected_evidence_ids is not None and evidence_id not in expected_evidence_ids:
            raise ClaimAnalysisValidationError(
                f"{context} references unknown Evidence: {evidence_id}"
            )
        if expected_evidence_records is not None:
            evidence_record = expected_evidence_records.get(evidence_id)
            if evidence_record is None:
                raise ClaimAnalysisValidationError(
                    f"{context} references unknown Evidence: {evidence_id}"
                )
            expected_locator = {
                "sourcePath": str(
                    _field(evidence_record, "sourcePath", "source_path") or ""
                ).strip(),
                "lineNumber": _field(
                    evidence_record, "lineNumber", "line_number"
                ),
            }
            if (
                str(item["rawText"]) != str(evidence_record.get("text") or "")
                or str(item["normalizedText"])
                != normalize_claim_text(evidence_record.get("text"))
                or str(item["sourceScope"])
                != str(
                    _field(evidence_record, "contentOrigin", "content_origin") or ""
                )
                or str(item["sourceAssetType"])
                != str(_field(evidence_record, "sourceType", "source_type") or "")
                or item["sourceLocator"] != expected_locator
            ):
                raise ClaimAnalysisValidationError(
                    f"{context} does not reproduce its Evidence source trace"
                )
        occurrence_key = (evidence_id, expression_id)
        occurrence_counts[occurrence_key] = occurrence_counts.get(occurrence_key, 0) + 1
        expected_mention_id = _stable_id(
            "cm",
            snapshot_id,
            evidence_id,
            expression_id,
            str(occurrence_counts[occurrence_key]),
        )
        if mention_id != expected_mention_id:
            raise ClaimAnalysisValidationError(
                f"{context}.claimMentionId is not deterministic"
            )
        mention_by_id[mention_id] = item

    signal_ids: set[str] = set()
    signal_claim_types: set[str] = set()
    linked_mention_counts: dict[str, int] = {}
    for index, item in enumerate(signals):
        if not isinstance(item, dict):
            raise ClaimAnalysisValidationError(f"claimSignals[{index}] must be an object")
        context = f"claimSignals[{index}]"
        signal_id = _required_string(item, "claimSignalId", context)
        if signal_id in signal_ids:
            raise ClaimAnalysisValidationError(f"Duplicate ClaimSignal id: {signal_id}")
        signal_ids.add(signal_id)
        if _required_string(item, "snapshotId", context) != snapshot_id:
            raise ClaimAnalysisValidationError(f"{context} belongs to another Snapshot")
        claim_type = _required_string(item, "claimType", context)
        if claim_type in signal_claim_types:
            raise ClaimAnalysisValidationError(
                f"Duplicate ClaimSignal claim type: {claim_type}"
            )
        signal_claim_types.add(claim_type)
        if taxonomy_types is not None:
            type_item = taxonomy_types.get(claim_type)
            if type_item is None:
                raise ClaimAnalysisValidationError(
                    f"{context} references an unknown active Claim type"
                )
            if str(type_item["label_zh"]) != str(item.get("displayLabel") or ""):
                raise ClaimAnalysisValidationError(
                    f"{context}.displayLabel conflicts with the governed taxonomy"
                )
        if _required_string(item, "taxonomyVersion", context) != taxonomy_version:
            raise ClaimAnalysisValidationError(f"{context} taxonomy version differs")
        if _required_string(item, "status", context) != "normalized":
            raise ClaimAnalysisValidationError(f"{context}.status must be normalized")
        _required_string(item, "displayLabel", context)
        _required_string(item, "createdAt", context)
        if signal_id != _stable_id("cs", snapshot_id, claim_type, taxonomy_version):
            raise ClaimAnalysisValidationError(
                f"{context}.claimSignalId is not deterministic"
            )
        mention_ids = item.get("mentionIds")
        evidence_ids = item.get("evidenceIds")
        if not isinstance(mention_ids, list) or not mention_ids:
            raise ClaimAnalysisValidationError(f"{context}.mentionIds must be non-empty")
        if len({str(value) for value in mention_ids}) != len(mention_ids):
            raise ClaimAnalysisValidationError(f"{context}.mentionIds contains duplicates")
        selected: list[dict[str, Any]] = []
        for mention_id in mention_ids:
            mention = mention_by_id.get(str(mention_id))
            if mention is None:
                raise ClaimAnalysisValidationError(
                    f"{context} references unknown ClaimMention: {mention_id}"
                )
            if mention["claimType"] != claim_type:
                raise ClaimAnalysisValidationError(
                    f"{context} mixes ClaimMention claim types"
                )
            selected.append(mention)
            linked_mention_counts[str(mention_id)] = (
                linked_mention_counts.get(str(mention_id), 0) + 1
            )
        expected_signal_evidence = list(
            dict.fromkeys(str(mention["evidenceId"]) for mention in selected)
        )
        if evidence_ids != expected_signal_evidence:
            raise ClaimAnalysisValidationError(
                f"{context}.evidenceIds is not the complete deterministic Evidence set"
            )
    if set(linked_mention_counts) != set(mention_by_id) or any(
        count != 1 for count in linked_mention_counts.values()
    ):
        raise ClaimAnalysisValidationError(
            "Every ClaimMention must belong to exactly one ClaimSignal"
        )
    return payload


def load_claim_analysis(
    artifact_path: Path,
    *,
    expected_snapshot_id: str | None = None,
    expected_evidence_ids: set[str] | None = None,
    expected_evidence_records: dict[str, dict[str, Any]] | None = None,
    taxonomy: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not artifact_path.is_file():
        return None
    try:
        payload = read_json(artifact_path)
    except (OSError, ValueError, TypeError) as exc:
        raise ClaimAnalysisValidationError(
            f"Cannot read Claim analysis: {type(exc).__name__}: {exc}"
        ) from exc
    return validate_claim_analysis(
        payload,
        expected_snapshot_id=expected_snapshot_id,
        expected_evidence_ids=expected_evidence_ids,
        expected_evidence_records=expected_evidence_records,
        taxonomy=taxonomy,
    )


def write_claim_analysis(
    product_root: Path,
    snapshot_id: str,
    evidence_records: Iterable[dict[str, Any]],
    *,
    taxonomy_path: Path = DEFAULT_CLAIM_TAXONOMY_PATH,
    generated_at: str | None = None,
) -> dict[str, Any]:
    taxonomy = load_claim_taxonomy(taxonomy_path)
    payload = derive_claim_analysis(
        snapshot_id,
        evidence_records,
        taxonomy,
        generated_at=generated_at,
    )
    product_root = product_root.resolve()
    write_json(product_root / CLAIM_ANALYSIS_FILE, payload)
    (product_root / CLAIM_ANALYSIS_ERROR_FILE).unlink(missing_ok=True)
    return payload


def record_claim_analysis_failure(
    product_root: Path,
    snapshot_id: str,
    error: Exception,
    *,
    taxonomy_path: Path = DEFAULT_CLAIM_TAXONOMY_PATH,
) -> Path:
    """Persist a degradable sidecar error without changing pipeline readiness."""

    product_root = product_root.resolve()
    (product_root / CLAIM_ANALYSIS_FILE).unlink(missing_ok=True)
    path = product_root / CLAIM_ANALYSIS_ERROR_FILE
    write_json(
        path,
        {
            "schemaVersion": CLAIM_ANALYSIS_SCHEMA_VERSION,
            "status": "error",
            "snapshotId": snapshot_id,
            "taxonomyPath": taxonomy_path.as_posix(),
            "errorType": type(error).__name__,
            "message": str(error),
            "failedAt": iso_now(),
        },
    )
    return path
