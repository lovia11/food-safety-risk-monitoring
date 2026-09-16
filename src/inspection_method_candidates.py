"""Validation for the non-runtime Inspection Method candidate trace manifest.

Records may advance from discovery through verification to promotion, but the
manifest itself deliberately has no DataStore importer or Recommendation path.
Promoted Methods enter runtime only through the governed Inspection Reference.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from src.inspection_reference import KNOWLEDGE_DEPTHS


_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_CANDIDATE_STATUSES = {"candidate", "verification", "promoted"}


class InspectionCandidateValidationError(ValueError):
    """The candidate manifest is malformed or overstates candidate status."""


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InspectionCandidateValidationError(f"{field}不能为空")
    return value.strip()


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise InspectionCandidateValidationError(f"{field}必须是字符串或null")
    return value.strip() or None


def _identifier(value: Any, field: str) -> str:
    text = _required_text(value, field)
    if not _IDENTIFIER_PATTERN.fullmatch(text):
        raise InspectionCandidateValidationError(f"{field}不是有效标识符")
    return text


def _iso_datetime(value: Any, field: str) -> str:
    text = _required_text(value, field)
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise InspectionCandidateValidationError(
            f"{field}不是有效ISO时间：{text}"
        ) from error
    return text


def _verification_sources(value: Any, field: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise InspectionCandidateValidationError(f"{field}必须是数组")
    sources: list[dict[str, Any]] = []
    references: set[str] = set()
    for position, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise InspectionCandidateValidationError(
                f"{field}[{position}]必须是JSON对象"
            )
        reference = _required_text(
            item.get("source_reference"), f"{field}[{position}].source_reference"
        )
        if reference in references:
            raise InspectionCandidateValidationError(
                f"{field} source_reference重复：{reference}"
            )
        references.add(reference)
        facts = item.get("verified_facts")
        if not isinstance(facts, list) or not facts:
            raise InspectionCandidateValidationError(
                f"{field}[{position}].verified_facts必须是非空数组"
            )
        sources.append(
            {
                "source_name": _required_text(
                    item.get("source_name"), f"{field}[{position}].source_name"
                ),
                "source_reference": reference,
                "verified_facts": [
                    _required_text(fact, f"{field}[{position}].verified_facts")
                    for fact in facts
                ],
            }
        )
    return sources


def validate_inspection_candidate_manifest(payload: Any) -> dict[str, Any]:
    """Validate discovery/promotion trace without importing it into runtime."""

    if not isinstance(payload, dict):
        raise InspectionCandidateValidationError("candidate manifest必须是JSON对象")
    if payload.get("schema_version") != 1 or isinstance(
        payload.get("schema_version"), bool
    ):
        raise InspectionCandidateValidationError("schema_version必须为1")
    manifest_id = _identifier(payload.get("manifest_id"), "manifest_id")
    manifest_version = _required_text(
        payload.get("manifest_version"), "manifest_version"
    )
    if payload.get("status") != "non_runtime_candidate_manifest":
        raise InspectionCandidateValidationError(
            "status必须为non_runtime_candidate_manifest"
        )
    if payload.get("runtime_consumed") is not False:
        raise InspectionCandidateValidationError("runtime_consumed必须显式为false")
    values = payload.get("candidates")
    if not isinstance(values, list):
        raise InspectionCandidateValidationError("candidates必须是数组")

    candidates: list[dict[str, Any]] = []
    candidate_ids: set[str] = set()
    method_numbers: set[str] = set()
    for position, value in enumerate(values, start=1):
        if not isinstance(value, dict):
            raise InspectionCandidateValidationError(
                f"candidates[{position}]必须是JSON对象"
            )
        candidate_id = _identifier(
            value.get("candidate_id"), f"candidates[{position}].candidate_id"
        )
        if candidate_id in candidate_ids:
            raise InspectionCandidateValidationError(
                f"candidate_id重复：{candidate_id}"
            )
        candidate_ids.add(candidate_id)
        method_no = _required_text(
            value.get("method_no"), f"Candidate {candidate_id} 的method_no"
        )
        if method_no in method_numbers:
            raise InspectionCandidateValidationError(f"method_no重复：{method_no}")
        method_numbers.add(method_no)
        status = _required_text(value.get("status"), f"Candidate {candidate_id} 的status")
        if status not in _CANDIDATE_STATUSES:
            raise InspectionCandidateValidationError(
                f"Candidate {candidate_id} 的status不受支持：{status}"
            )
        expected_depth = _required_text(
            value.get("expected_depth"),
            f"Candidate {candidate_id} 的expected_depth",
        )
        if expected_depth not in KNOWLEDGE_DEPTHS:
            raise InspectionCandidateValidationError(
                f"Candidate {candidate_id} 的expected_depth不受支持：{expected_depth}"
            )
        verification_sources = _verification_sources(
            value.get("verification_sources", []),
            f"Candidate {candidate_id} 的verification_sources",
        )
        verified_at = value.get("verified_at")
        promoted_method_id = value.get("promoted_method_id")
        promoted_dataset_version = value.get("promoted_dataset_version")
        if status == "candidate":
            if verification_sources or any(
                item is not None
                for item in (verified_at, promoted_method_id, promoted_dataset_version)
            ):
                raise InspectionCandidateValidationError(
                    f"Candidate {candidate_id} 尚未核验，不能记录promotion字段"
                )
            normalized_verified_at = None
            normalized_promoted_method_id = None
            normalized_promoted_dataset_version = None
        else:
            if not verification_sources:
                raise InspectionCandidateValidationError(
                    f"Candidate {candidate_id} 的{status}状态必须包含verification_sources"
                )
            normalized_verified_at = _iso_datetime(
                verified_at, f"Candidate {candidate_id} 的verified_at"
            )
            if status == "verification":
                if promoted_method_id is not None or promoted_dataset_version is not None:
                    raise InspectionCandidateValidationError(
                        f"Candidate {candidate_id} 尚未promoted，不能记录promotion目标"
                    )
                normalized_promoted_method_id = None
                normalized_promoted_dataset_version = None
            else:
                normalized_promoted_method_id = _identifier(
                    promoted_method_id,
                    f"Candidate {candidate_id} 的promoted_method_id",
                )
                normalized_promoted_dataset_version = _required_text(
                    promoted_dataset_version,
                    f"Candidate {candidate_id} 的promoted_dataset_version",
                )
        candidates.append(
            {
                "candidate_id": candidate_id,
                "method_no": method_no,
                "title": _optional_text(
                    value.get("title"), f"Candidate {candidate_id} 的title"
                ),
                "status": status,
                "expected_depth": expected_depth,
                "discovery_source_name": _required_text(
                    value.get("discovery_source_name"),
                    f"Candidate {candidate_id} 的discovery_source_name",
                ),
                "discovery_source_reference": _required_text(
                    value.get("discovery_source_reference"),
                    f"Candidate {candidate_id} 的discovery_source_reference",
                ),
                "discovery_source_date": _optional_text(
                    value.get("discovery_source_date"),
                    f"Candidate {candidate_id} 的discovery_source_date",
                ),
                "discovery_source_record_id": _required_text(
                    value.get("discovery_source_record_id"),
                    f"Candidate {candidate_id} 的discovery_source_record_id",
                ),
                "reason": _required_text(
                    value.get("reason"), f"Candidate {candidate_id} 的reason"
                ),
                "correction_note": _optional_text(
                    value.get("correction_note"),
                    f"Candidate {candidate_id} 的correction_note",
                ),
                "verification_sources": verification_sources,
                "verified_at": normalized_verified_at,
                "promoted_method_id": normalized_promoted_method_id,
                "promoted_dataset_version": normalized_promoted_dataset_version,
            }
        )

    return {
        "schema_version": 1,
        "manifest_id": manifest_id,
        "manifest_version": manifest_version,
        "status": "non_runtime_candidate_manifest",
        "runtime_consumed": False,
        "description": _required_text(payload.get("description"), "description"),
        "candidates": candidates,
    }
