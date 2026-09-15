"""Validation for the non-runtime Inspection Method candidate manifest.

Candidates are discovery records only.  This module deliberately has no
DataStore importer and no Recommendation integration.
"""

from __future__ import annotations

import re
from typing import Any

from src.inspection_reference import KNOWLEDGE_DEPTHS


_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


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


def validate_inspection_candidate_manifest(payload: Any) -> dict[str, Any]:
    """Validate a manifest without promoting any candidate into runtime."""

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
        if value.get("status") != "candidate":
            raise InspectionCandidateValidationError(
                f"Candidate {candidate_id} 的status必须为candidate"
            )
        expected_depth = _required_text(
            value.get("expected_depth"),
            f"Candidate {candidate_id} 的expected_depth",
        )
        if expected_depth not in KNOWLEDGE_DEPTHS:
            raise InspectionCandidateValidationError(
                f"Candidate {candidate_id} 的expected_depth不受支持：{expected_depth}"
            )
        candidates.append(
            {
                "candidate_id": candidate_id,
                "method_no": method_no,
                "title": _optional_text(
                    value.get("title"), f"Candidate {candidate_id} 的title"
                ),
                "status": "candidate",
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
