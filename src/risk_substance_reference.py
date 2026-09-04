"""Validation for Risk-Substance Reference datasets.

This module only validates and normalizes explicitly supplied Risk-to-Substance
or Risk-to-Group reference data.  It does not infer mappings from effect
keywords, inspection method titles, pharmacology, or any other project data.

Evidence grades A/B/C describe source strength only.  They are not a risk
score, model confidence, probability that a product is illegal, or detection
probability, and must never be converted into a numeric score.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any


DATASET_STATUSES = {
    "development_seed",
    "reference_pending",
    "verified_reference",
}
TARGET_TYPES = {"substance", "substance_group"}
EVIDENCE_GRADES = {"A", "B", "C"}
BASIS_TYPES = {
    "current_regulatory_source",
    "current_official_guidance",
    "historical_sampling_plan",
    "official_case",
    "research_evidence",
    "pharmacologic_inference",
}
TEMPORAL_STATUSES = {"current", "historical"}

_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_PLACEHOLDER_VALUES = {
    "待确认",
    "待核实",
    "未知",
    "unknown",
    "tbd",
    "todo",
    "pending",
    "待补充",
    "n/a",
    "na",
}
_TOP_LEVEL_FIELDS = (
    "schema_version",
    "dataset_id",
    "dataset_version",
    "dataset_status",
    "source_name",
    "source_reference",
    "source_date",
    "collected_at",
    "verified_at",
    "description",
    "mappings",
)
_MAPPING_FIELDS = (
    "mapping_id",
    "dataset_id",
    "risk_category",
    "risk_label",
    "target_type",
    "substance_id",
    "target_group_label",
    "evidence_grade",
    "basis_type",
    "temporal_status",
    "product_scope",
    "source_name",
    "source_reference",
    "source_date",
    "source_basis_text",
    "note",
)


class RiskSubstanceConfigValidationError(ValueError):
    """A Risk-Substance Reference payload is invalid or inconsistent."""


def _object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RiskSubstanceConfigValidationError(f"{field}必须是JSON对象")
    return value


def _array(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise RiskSubstanceConfigValidationError(f"{field}必须是数组")
    return value


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RiskSubstanceConfigValidationError(f"{field}不能为空")
    return value.strip()


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise RiskSubstanceConfigValidationError(f"{field}必须是字符串或null")
    return value.strip() or None


def _text_default(value: Any, field: str) -> str:
    return _optional_text(value, field) or ""


def _identifier(value: Any, field: str) -> str:
    text = _required_text(value, field)
    if not _IDENTIFIER_PATTERN.fullmatch(text):
        raise RiskSubstanceConfigValidationError(
            f"{field}只能包含字母、数字、点、下划线、冒号和连字符"
        )
    return text


def _choice(value: Any, field: str, allowed: set[str]) -> str:
    text = _required_text(value, field)
    if text not in allowed:
        raise RiskSubstanceConfigValidationError(f"不支持的{field}：{text}")
    return text


def _iso_date(value: Any, field: str) -> str | None:
    text = _optional_text(value, field)
    if text is None:
        return None
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise RiskSubstanceConfigValidationError(f"{field}必须使用YYYY-MM-DD格式")
    try:
        date.fromisoformat(text)
    except ValueError as error:
        raise RiskSubstanceConfigValidationError(
            f"{field}不是有效日期：{text}"
        ) from error
    return text


def _iso_datetime(value: Any, field: str) -> str | None:
    text = _optional_text(value, field)
    if text is None:
        return None
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise RiskSubstanceConfigValidationError(
            f"{field}不是有效ISO时间：{text}"
        ) from error
    return text


def _reject_duplicate(value: Any, seen: set[Any], field: str) -> None:
    if value in seen:
        raise RiskSubstanceConfigValidationError(f"{field}重复：{value}")
    seen.add(value)


def _reject_verified_placeholders(fields: dict[str, Any], label: str) -> None:
    for field, value in fields.items():
        if isinstance(value, str) and value.strip().lower() in _PLACEHOLDER_VALUES:
            raise RiskSubstanceConfigValidationError(
                f"verified_reference中的{label}.{field}不能使用占位值：{value}"
            )


def validate_risk_substance_config(payload: Any) -> dict[str, Any]:
    """Validate and normalize one Risk-Substance Reference JSON payload."""

    root = _object(payload, "Risk-Substance数据集根节点")
    missing = [field for field in _TOP_LEVEL_FIELDS if field not in root]
    if missing:
        raise RiskSubstanceConfigValidationError(
            f"Risk-Substance数据集缺少字段：{', '.join(missing)}"
        )
    if root.get("schema_version") != 1 or isinstance(
        root.get("schema_version"), bool
    ):
        raise RiskSubstanceConfigValidationError("schema_version必须为1")

    dataset_id = _identifier(root.get("dataset_id"), "dataset_id")
    dataset_version = _required_text(root.get("dataset_version"), "dataset_version")
    dataset_status = _choice(
        root.get("dataset_status"), "dataset_status", DATASET_STATUSES
    )
    source_name = _optional_text(root.get("source_name"), "source_name")
    source_reference = _optional_text(
        root.get("source_reference"), "source_reference"
    )
    source_date = _iso_date(root.get("source_date"), "source_date")
    collected_at = _iso_datetime(root.get("collected_at"), "collected_at")
    verified_at = _iso_datetime(root.get("verified_at"), "verified_at")
    description = _text_default(root.get("description"), "description")
    mappings_raw = _array(root.get("mappings"), "mappings")

    if dataset_status in {"development_seed", "verified_reference"}:
        if not source_name:
            raise RiskSubstanceConfigValidationError(
                f"{dataset_status}数据集必须包含source_name"
            )
        if not source_reference:
            raise RiskSubstanceConfigValidationError(
                f"{dataset_status}数据集必须包含source_reference"
            )
    if dataset_status == "reference_pending" and mappings_raw:
        raise RiskSubstanceConfigValidationError(
            "reference_pending数据集的mappings必须为空"
        )
    if dataset_status == "verified_reference":
        if not verified_at:
            raise RiskSubstanceConfigValidationError(
                "verified_reference数据集必须包含verified_at"
            )
        if not mappings_raw:
            raise RiskSubstanceConfigValidationError(
                "verified_reference数据集必须至少包含一条Mapping"
            )

    mappings: list[dict[str, Any]] = []
    mapping_ids: set[str] = set()
    for position, value in enumerate(mappings_raw, start=1):
        item = _object(value, f"mappings[{position}]")
        missing_mapping_fields = [
            field for field in _MAPPING_FIELDS if field not in item
        ]
        if missing_mapping_fields:
            raise RiskSubstanceConfigValidationError(
                f"mappings[{position}]缺少字段：{', '.join(missing_mapping_fields)}"
            )

        mapping_id = _identifier(
            item.get("mapping_id"), f"mappings[{position}].mapping_id"
        )
        _reject_duplicate(mapping_id, mapping_ids, "mapping_id")
        item_dataset_id = _identifier(
            item.get("dataset_id"), f"Mapping {mapping_id} 的dataset_id"
        )
        if item_dataset_id != dataset_id:
            raise RiskSubstanceConfigValidationError(
                f"Mapping {mapping_id} 的dataset_id必须等于所属数据集 {dataset_id}"
            )

        target_type = _choice(
            item.get("target_type"),
            f"Mapping {mapping_id} 的target_type",
            TARGET_TYPES,
        )
        raw_substance_id = item.get("substance_id")
        substance_id = (
            None
            if raw_substance_id is None
            else _identifier(
                raw_substance_id, f"Mapping {mapping_id} 的substance_id"
            )
        )
        target_group_label = _optional_text(
            item.get("target_group_label"),
            f"Mapping {mapping_id} 的target_group_label",
        )
        if target_type == "substance":
            if substance_id is None or target_group_label is not None:
                raise RiskSubstanceConfigValidationError(
                    f"Mapping {mapping_id} 的substance target必须仅包含substance_id"
                )
        elif substance_id is not None or target_group_label is None:
            raise RiskSubstanceConfigValidationError(
                f"Mapping {mapping_id} 的substance_group target必须仅包含"
                "target_group_label"
            )

        evidence_grade = _choice(
            item.get("evidence_grade"),
            f"Mapping {mapping_id} 的evidence_grade",
            EVIDENCE_GRADES,
        )
        basis_type = _choice(
            item.get("basis_type"),
            f"Mapping {mapping_id} 的basis_type",
            BASIS_TYPES,
        )
        temporal_status = _choice(
            item.get("temporal_status"),
            f"Mapping {mapping_id} 的temporal_status",
            TEMPORAL_STATUSES,
        )
        if evidence_grade == "A" and temporal_status != "current":
            raise RiskSubstanceConfigValidationError(
                f"Mapping {mapping_id} 的A级来源证据必须是current"
            )
        if basis_type == "historical_sampling_plan":
            if temporal_status != "historical":
                raise RiskSubstanceConfigValidationError(
                    f"Mapping {mapping_id} 的historical_sampling_plan必须是historical"
                )
            if evidence_grade == "A":
                raise RiskSubstanceConfigValidationError(
                    f"Mapping {mapping_id} 的historical_sampling_plan不能使用A级来源证据"
                )

        normalized = {
            "mapping_id": mapping_id,
            "dataset_id": item_dataset_id,
            "risk_category": _identifier(
                item.get("risk_category"),
                f"Mapping {mapping_id} 的risk_category",
            ),
            "risk_label": _required_text(
                item.get("risk_label"), f"Mapping {mapping_id} 的risk_label"
            ),
            "target_type": target_type,
            "substance_id": substance_id,
            "target_group_label": target_group_label,
            "evidence_grade": evidence_grade,
            "basis_type": basis_type,
            "temporal_status": temporal_status,
            "product_scope": _text_default(
                item.get("product_scope"), f"Mapping {mapping_id} 的product_scope"
            ),
            "source_name": _optional_text(
                item.get("source_name"), f"Mapping {mapping_id} 的source_name"
            ),
            "source_reference": _optional_text(
                item.get("source_reference"),
                f"Mapping {mapping_id} 的source_reference",
            ),
            "source_date": _iso_date(
                item.get("source_date"), f"Mapping {mapping_id} 的source_date"
            ),
            "source_basis_text": _text_default(
                item.get("source_basis_text"),
                f"Mapping {mapping_id} 的source_basis_text",
            ),
            "note": _text_default(
                item.get("note"), f"Mapping {mapping_id} 的note"
            ),
        }
        if dataset_status == "verified_reference":
            for field in (
                "source_name",
                "source_reference",
                "source_date",
                "source_basis_text",
            ):
                if not normalized[field]:
                    raise RiskSubstanceConfigValidationError(
                        f"verified_reference中的Mapping {mapping_id}必须包含{field}"
                    )
            _reject_verified_placeholders(normalized, f"Mapping {mapping_id}")
        mappings.append(normalized)

    normalized_root = {
        "schema_version": 1,
        "dataset_id": dataset_id,
        "dataset_version": dataset_version,
        "dataset_status": dataset_status,
        "source_name": source_name,
        "source_reference": source_reference,
        "source_date": source_date,
        "collected_at": collected_at,
        "verified_at": verified_at,
        "description": description,
        "mappings": mappings,
    }
    if dataset_status == "verified_reference":
        _reject_verified_placeholders(normalized_root, "数据集")
    return normalized_root
