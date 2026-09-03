"""Validation for Inspection Reference datasets.

This module deliberately contains no official inspection records and performs no
inference.  It only validates and normalizes explicitly supplied reference data
before the data reaches SQLite.
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
METHOD_TYPES = {
    "supplementary_bjs",
    "rapid_kj",
    "national_standard_gbt",
}
METHOD_STATUSES = {
    "current",
    "superseded",
    "revoked",
    "verification_pending",
}
DETERMINATION_ROLES = {
    "quantitative",
    "qualitative",
    "rapid_screen",
    "unspecified",
}
APPLICABILITY_SCOPE_TYPES = {"include", "exclude", "conditional"}
REGULATORY_CONTEXT_STATUSES = {
    "non_food_substance",
    "pharmaceutical_or_derivative",
    "legal_health_food_raw_material",
    "context_dependent",
    "verification_pending",
}

_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_COLLECTION_FIELDS = (
    "methods",
    "substances",
    "method_substances",
    "method_applicabilities",
    "substance_regulatory_contexts",
)
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
    *_COLLECTION_FIELDS,
)


class InspectionConfigValidationError(ValueError):
    """An Inspection Reference payload is invalid or internally inconsistent."""


def _object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InspectionConfigValidationError(f"{field}必须是JSON对象")
    return value


def _array(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise InspectionConfigValidationError(f"{field}必须是数组")
    return value


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InspectionConfigValidationError(f"{field}不能为空")
    return value.strip()


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise InspectionConfigValidationError(f"{field}必须是字符串或null")
    return value.strip() or None


def _text_default(value: Any, field: str) -> str:
    return _optional_text(value, field) or ""


def _identifier(value: Any, field: str) -> str:
    text = _required_text(value, field)
    if not _IDENTIFIER_PATTERN.fullmatch(text):
        raise InspectionConfigValidationError(
            f"{field}只能包含字母、数字、点、下划线、冒号和连字符"
        )
    return text


def _choice(value: Any, field: str, allowed: set[str]) -> str:
    text = _required_text(value, field)
    if text not in allowed:
        raise InspectionConfigValidationError(f"不支持的{field}：{text}")
    return text


def _iso_date(value: Any, field: str) -> str | None:
    text = _optional_text(value, field)
    if text is None:
        return None
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise InspectionConfigValidationError(f"{field}必须使用YYYY-MM-DD格式")
    try:
        date.fromisoformat(text)
    except ValueError as error:
        raise InspectionConfigValidationError(f"{field}不是有效日期：{text}") from error
    return text


def _iso_datetime(value: Any, field: str) -> str | None:
    text = _optional_text(value, field)
    if text is None:
        return None
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise InspectionConfigValidationError(f"{field}不是有效ISO时间：{text}") from error
    return text


def _positive_integer(value: Any, field: str) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise InspectionConfigValidationError(f"{field}必须是正整数或null")
    return value


def _reject_duplicate(value: Any, seen: set[Any], field: str) -> None:
    if value in seen:
        raise InspectionConfigValidationError(f"{field}重复：{value}")
    seen.add(value)


def validate_inspection_config(payload: Any) -> dict[str, Any]:
    """Validate and normalize one Inspection Reference JSON payload."""

    root = _object(payload, "Inspection数据集根节点")
    missing = [field for field in _TOP_LEVEL_FIELDS if field not in root]
    if missing:
        raise InspectionConfigValidationError(
            f"Inspection数据集缺少字段：{', '.join(missing)}"
        )
    if root.get("schema_version") != 1 or isinstance(
        root.get("schema_version"), bool
    ):
        raise InspectionConfigValidationError("schema_version必须为1")

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
    if dataset_status in {"development_seed", "verified_reference"}:
        if not source_name:
            raise InspectionConfigValidationError(
                f"{dataset_status}数据集必须包含source_name"
            )
        if not source_reference:
            raise InspectionConfigValidationError(
                f"{dataset_status}数据集必须包含source_reference"
            )

    collections = {
        field: _array(root.get(field), field) for field in _COLLECTION_FIELDS
    }
    if dataset_status == "reference_pending" and any(collections.values()):
        raise InspectionConfigValidationError(
            "reference_pending数据集的所有正式数据数组必须为空"
        )
    if dataset_status == "verified_reference" and not verified_at:
        raise InspectionConfigValidationError(
            "verified_reference数据集必须包含verified_at"
        )

    methods: list[dict[str, Any]] = []
    method_ids: set[str] = set()
    method_numbers: set[str] = set()
    for position, value in enumerate(collections["methods"], start=1):
        item = _object(value, f"methods[{position}]")
        method_id = _identifier(item.get("method_id"), f"methods[{position}].method_id")
        _reject_duplicate(method_id, method_ids, "method_id")
        item_dataset_id = _identifier(
            item.get("dataset_id"), f"Method {method_id} 的dataset_id"
        )
        if item_dataset_id != dataset_id:
            raise InspectionConfigValidationError(
                f"Method {method_id} 的dataset_id必须等于所属数据集 {dataset_id}"
            )
        method_no = _required_text(item.get("method_no"), f"Method {method_id} 的method_no")
        _reject_duplicate(method_no, method_numbers, "method_no")
        method_type = _choice(
            item.get("method_type"), f"Method {method_id} 的method_type", METHOD_TYPES
        )
        method_status = _choice(
            item.get("method_status"),
            f"Method {method_id} 的method_status",
            METHOD_STATUSES,
        )
        method_source_name = _required_text(
            item.get("source_name"), f"Method {method_id} 的source_name"
        )
        method_source_reference = _required_text(
            item.get("source_reference"), f"Method {method_id} 的source_reference"
        )
        method_source_date = _iso_date(
            item.get("source_date"), f"Method {method_id} 的source_date"
        )
        methods.append(
            {
                "method_id": method_id,
                "dataset_id": item_dataset_id,
                "method_no": method_no,
                "method_name": _required_text(
                    item.get("method_name"), f"Method {method_id} 的method_name"
                ),
                "method_type": method_type,
                "method_status": method_status,
                "publisher": _text_default(
                    item.get("publisher"), f"Method {method_id} 的publisher"
                ),
                "published_date": _iso_date(
                    item.get("published_date"), f"Method {method_id} 的published_date"
                ),
                "effective_date": _iso_date(
                    item.get("effective_date"), f"Method {method_id} 的effective_date"
                ),
                "replaces_method_no": _optional_text(
                    item.get("replaces_method_no"),
                    f"Method {method_id} 的replaces_method_no",
                ),
                "replaced_by_method_no": _optional_text(
                    item.get("replaced_by_method_no"),
                    f"Method {method_id} 的replaced_by_method_no",
                ),
                "source_name": method_source_name,
                "source_reference": method_source_reference,
                "source_date": method_source_date,
                "note": _text_default(item.get("note"), f"Method {method_id} 的note"),
            }
        )

    substances: list[dict[str, Any]] = []
    substance_ids: set[str] = set()
    canonical_names: set[str] = set()
    canonical_by_id: dict[str, str] = {}
    for position, value in enumerate(collections["substances"], start=1):
        item = _object(value, f"substances[{position}]")
        substance_id = _identifier(
            item.get("substance_id"), f"substances[{position}].substance_id"
        )
        _reject_duplicate(substance_id, substance_ids, "substance_id")
        item_dataset_id = _identifier(
            item.get("dataset_id"), f"Substance {substance_id} 的dataset_id"
        )
        if item_dataset_id != dataset_id:
            raise InspectionConfigValidationError(
                f"Substance {substance_id} 的dataset_id必须等于所属数据集 {dataset_id}"
            )
        canonical_name = _required_text(
            item.get("canonical_name"), f"Substance {substance_id} 的canonical_name"
        )
        _reject_duplicate(canonical_name, canonical_names, "canonical_name")
        canonical_by_id[substance_id] = canonical_name
        substances.append(
            {
                "substance_id": substance_id,
                "dataset_id": item_dataset_id,
                "canonical_name": canonical_name,
                "english_name": _text_default(
                    item.get("english_name"), f"Substance {substance_id} 的english_name"
                ),
                "cas_no": _text_default(
                    item.get("cas_no"), f"Substance {substance_id} 的cas_no"
                ),
                "substance_group": _text_default(
                    item.get("substance_group"),
                    f"Substance {substance_id} 的substance_group",
                ),
                "note": _text_default(item.get("note"), f"Substance {substance_id} 的note"),
            }
        )

    method_substances: list[dict[str, Any]] = []
    method_substance_keys: set[tuple[str, str]] = set()
    for position, value in enumerate(collections["method_substances"], start=1):
        item = _object(value, f"method_substances[{position}]")
        method_id = _identifier(
            item.get("method_id"), f"method_substances[{position}].method_id"
        )
        substance_id = _identifier(
            item.get("substance_id"), f"method_substances[{position}].substance_id"
        )
        if method_id not in method_ids:
            raise InspectionConfigValidationError(
                f"MethodSubstance引用的method_id不存在：{method_id}"
            )
        if substance_id not in substance_ids:
            raise InspectionConfigValidationError(
                f"MethodSubstance引用的substance_id不存在：{substance_id}"
            )
        key = (method_id, substance_id)
        _reject_duplicate(key, method_substance_keys, "MethodSubstance")
        source_label = _required_text(
            item.get("source_label"),
            f"MethodSubstance {method_id}/{substance_id} 的source_label",
        )
        normalization_note = _text_default(
            item.get("normalization_note"),
            f"MethodSubstance {method_id}/{substance_id} 的normalization_note",
        )
        if source_label != canonical_by_id[substance_id] and not normalization_note:
            raise InspectionConfigValidationError(
                f"MethodSubstance {method_id}/{substance_id} 的source_label与"
                "canonical_name不一致时必须包含normalization_note"
            )
        method_substances.append(
            {
                "method_id": method_id,
                "substance_id": substance_id,
                "source_label": source_label,
                "source_cas_no": _text_default(
                    item.get("source_cas_no"),
                    f"MethodSubstance {method_id}/{substance_id} 的source_cas_no",
                ),
                "determination_role": _choice(
                    item.get("determination_role"),
                    f"MethodSubstance {method_id}/{substance_id} 的determination_role",
                    DETERMINATION_ROLES,
                ),
                "normalization_note": normalization_note,
                "ordinal": _positive_integer(
                    item.get("ordinal"),
                    f"MethodSubstance {method_id}/{substance_id} 的ordinal",
                ),
            }
        )

    applicabilities: list[dict[str, Any]] = []
    applicability_ids: set[str] = set()
    for position, value in enumerate(collections["method_applicabilities"], start=1):
        item = _object(value, f"method_applicabilities[{position}]")
        applicability_id = _identifier(
            item.get("applicability_id"),
            f"method_applicabilities[{position}].applicability_id",
        )
        _reject_duplicate(applicability_id, applicability_ids, "applicability_id")
        method_id = _identifier(
            item.get("method_id"), f"Applicability {applicability_id} 的method_id"
        )
        if method_id not in method_ids:
            raise InspectionConfigValidationError(
                f"Applicability {applicability_id} 引用的method_id不存在：{method_id}"
            )
        applicabilities.append(
            {
                "applicability_id": applicability_id,
                "method_id": method_id,
                "scope_type": _choice(
                    item.get("scope_type"),
                    f"Applicability {applicability_id} 的scope_type",
                    APPLICABILITY_SCOPE_TYPES,
                ),
                "product_category": _text_default(
                    item.get("product_category"),
                    f"Applicability {applicability_id} 的product_category",
                ),
                "product_form": _text_default(
                    item.get("product_form"),
                    f"Applicability {applicability_id} 的product_form",
                ),
                "ingredient_context": _text_default(
                    item.get("ingredient_context"),
                    f"Applicability {applicability_id} 的ingredient_context",
                ),
                "source_scope_text": _text_default(
                    item.get("source_scope_text"),
                    f"Applicability {applicability_id} 的source_scope_text",
                ),
                "note": _text_default(
                    item.get("note"), f"Applicability {applicability_id} 的note"
                ),
            }
        )

    contexts: list[dict[str, Any]] = []
    context_ids: set[str] = set()
    for position, value in enumerate(
        collections["substance_regulatory_contexts"], start=1
    ):
        item = _object(value, f"substance_regulatory_contexts[{position}]")
        context_id = _identifier(
            item.get("context_id"),
            f"substance_regulatory_contexts[{position}].context_id",
        )
        _reject_duplicate(context_id, context_ids, "context_id")
        substance_id = _identifier(
            item.get("substance_id"), f"RegulatoryContext {context_id} 的substance_id"
        )
        if substance_id not in substance_ids:
            raise InspectionConfigValidationError(
                f"RegulatoryContext {context_id} 引用的substance_id不存在：{substance_id}"
            )
        valid_from = _iso_date(
            item.get("valid_from"), f"RegulatoryContext {context_id} 的valid_from"
        )
        valid_to = _iso_date(
            item.get("valid_to"), f"RegulatoryContext {context_id} 的valid_to"
        )
        if valid_from and valid_to and valid_from > valid_to:
            raise InspectionConfigValidationError(
                f"RegulatoryContext {context_id} 的valid_from不能晚于valid_to"
            )
        context_source_name = _required_text(
            item.get("source_name"), f"RegulatoryContext {context_id} 的source_name"
        )
        context_source_reference = _required_text(
            item.get("source_reference"),
            f"RegulatoryContext {context_id} 的source_reference",
        )
        context_source_date = _iso_date(
            item.get("source_date"), f"RegulatoryContext {context_id} 的source_date"
        )
        contexts.append(
            {
                "context_id": context_id,
                "substance_id": substance_id,
                "context_status": _choice(
                    item.get("context_status"),
                    f"RegulatoryContext {context_id} 的context_status",
                    REGULATORY_CONTEXT_STATUSES,
                ),
                "product_scope": _text_default(
                    item.get("product_scope"),
                    f"RegulatoryContext {context_id} 的product_scope",
                ),
                "jurisdiction": _text_default(
                    item.get("jurisdiction", "CN"),
                    f"RegulatoryContext {context_id} 的jurisdiction",
                )
                or "CN",
                "valid_from": valid_from,
                "valid_to": valid_to,
                "source_label": _text_default(
                    item.get("source_label"),
                    f"RegulatoryContext {context_id} 的source_label",
                ),
                "source_name": context_source_name,
                "source_reference": context_source_reference,
                "source_date": context_source_date,
                "note": _text_default(
                    item.get("note"), f"RegulatoryContext {context_id} 的note"
                ),
            }
        )

    if dataset_status == "verified_reference":
        if not methods or not substances:
            raise InspectionConfigValidationError(
                "verified_reference数据集必须至少包含一个Method和一个Substance"
            )
        for method in methods:
            method_id = method["method_id"]
            if method["method_status"] == "verification_pending":
                raise InspectionConfigValidationError(
                    f"verified_reference中的Method {method_id} 不能是verification_pending"
                )
            if not method["source_date"]:
                raise InspectionConfigValidationError(
                    f"verified_reference中的Method {method_id} 必须独立记录source_date"
                )
            if not any(item["method_id"] == method_id for item in method_substances):
                raise InspectionConfigValidationError(
                    f"verified_reference中的Method {method_id} 缺少MethodSubstance"
                )
            if not any(item["method_id"] == method_id for item in applicabilities):
                raise InspectionConfigValidationError(
                    f"verified_reference中的Method {method_id} 缺少MethodApplicability"
                )
        for substance in substances:
            substance_id = substance["substance_id"]
            if not any(
                item["substance_id"] == substance_id for item in method_substances
            ) and not any(item["substance_id"] == substance_id for item in contexts):
                raise InspectionConfigValidationError(
                    f"verified_reference中的Substance {substance_id} 是孤立实体"
                )
        for context in contexts:
            if not context["source_date"]:
                raise InspectionConfigValidationError(
                    f"verified_reference中的RegulatoryContext {context['context_id']} "
                    "必须独立记录source_date"
                )

    return {
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
        "methods": methods,
        "substances": substances,
        "method_substances": method_substances,
        "method_applicabilities": applicabilities,
        "substance_regulatory_contexts": contexts,
    }
