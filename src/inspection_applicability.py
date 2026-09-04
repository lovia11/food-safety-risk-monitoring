"""Exact Product Context evaluation for D3 inspection knowledge traces.

This module consumes an existing D3 result and caller-confirmed structured
product context.  It does not extract context, rerun earlier stages, rank
methods, interpret regulatory status, or generate inspection recommendations.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import asdict, dataclass
from typing import Any, Literal, TypedDict

from src.inspection_signal_trace import InspectionSignalTraceResult


ApplicabilityStatus = Literal[
    "applicable",
    "conditional",
    "not_applicable",
    "insufficient_context",
]


class MethodApplicabilityAssessment(TypedDict):
    risk_category: str
    substance_id: str
    canonical_name: str
    method_id: str
    method_no: str
    method_name: str
    method_status: str
    determination_role: str
    applicability_status: ApplicabilityStatus
    matched_applicability_ids: list[str]
    conditional_applicability_ids: list[str]
    blocking_applicability_ids: list[str]
    unresolved_applicability_ids: list[str]
    reason: str


@dataclass(frozen=True)
class ProductInspectionContext(Mapping[str, Any]):
    """Caller-confirmed product context; no values are inferred or normalized."""

    product_category: str | None
    product_form: str | None
    confirmed_ingredient_contexts: list[str]
    context_evidence: list[dict[str, Any]]

    def __post_init__(self) -> None:
        for field_name in ("product_category", "product_form"):
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, str):
                raise TypeError(f"{field_name} must be a string or None")
            if value == "":
                raise ValueError(f"{field_name} must use None when unknown")
        if not isinstance(self.confirmed_ingredient_contexts, list):
            raise TypeError("confirmed_ingredient_contexts must be a list")
        if any(
            not isinstance(value, str) or not value
            for value in self.confirmed_ingredient_contexts
        ):
            raise ValueError(
                "confirmed_ingredient_contexts must contain non-empty strings"
            )
        if not isinstance(self.context_evidence, list):
            raise TypeError("context_evidence must be a list")
        if any(not isinstance(item, dict) for item in self.context_evidence):
            raise TypeError("context_evidence must contain JSON objects")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def __getitem__(self, key: str) -> Any:
        if key not in self.__dataclass_fields__:
            raise KeyError(key)
        return getattr(self, key)

    def __iter__(self) -> Iterator[str]:
        return iter(self.__dataclass_fields__)

    def __len__(self) -> int:
        return len(self.__dataclass_fields__)


@dataclass(frozen=True)
class ProductApplicabilityResult(Mapping[str, Any]):
    """Stable JSON-compatible product/method applicability output."""

    product_context: dict[str, Any]
    method_assessments: list[MethodApplicabilityAssessment]
    composition_gaps: list[dict[str, Any]]
    knowledge_gaps: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def __getitem__(self, key: str) -> Any:
        if key not in self.__dataclass_fields__:
            raise KeyError(key)
        return getattr(self, key)

    def __iter__(self) -> Iterator[str]:
        return iter(self.__dataclass_fields__)

    def __len__(self) -> int:
        return len(self.__dataclass_fields__)


def _row_match_state(
    applicability: Mapping[str, Any],
    product_context: ProductInspectionContext,
) -> Literal["matched", "unresolved", "not_matched"]:
    unresolved = False
    for field_name in ("product_category", "product_form"):
        required_value = applicability[field_name]
        if not required_value:
            continue
        context_value = getattr(product_context, field_name)
        if context_value is None:
            unresolved = True
        elif context_value != required_value:
            return "not_matched"

    required_ingredient_context = applicability["ingredient_context"]
    if (
        required_ingredient_context
        and required_ingredient_context
        not in product_context.confirmed_ingredient_contexts
    ):
        unresolved = True

    return "unresolved" if unresolved else "matched"


def _assessment_reason(
    status: ApplicabilityStatus,
    *,
    blocked: bool,
) -> str:
    if blocked:
        return (
            "A confirmed Reference exclude scope blocks this substance-method "
            "context. This does not establish that the method is scientifically "
            "unusable in every context."
        )
    if status == "not_applicable":
        return (
            "The confirmed context is not covered by a matching Reference include "
            "or conditional scope. This does not establish that the method is "
            "scientifically unusable."
        )
    if status == "applicable":
        return (
            "A Reference include scope exactly matches and no unresolved exclude "
            "or conditional scope could change the result."
        )
    if status == "conditional":
        return (
            "A Reference conditional scope exactly matches; its source constraints "
            "remain applicable."
        )
    return (
        "Potentially relevant Reference applicability cannot be resolved because "
        "required product context has not been explicitly confirmed."
    )


def _evaluate_method(
    *,
    risk_category: str,
    substance: Mapping[str, Any],
    method: Mapping[str, Any],
    product_context: ProductInspectionContext,
) -> MethodApplicabilityAssessment:
    substance_id = str(substance["substance_id"])
    applicability_rows = [
        row
        for row in method["method_level_applicabilities"]
        if row["substance_id"] is None
    ]
    applicability_rows.extend(
        row
        for row in method["substance_scoped_applicabilities"]
        if row["substance_id"] == substance_id
    )

    matched_ids: list[str] = []
    conditional_ids: list[str] = []
    blocking_ids: list[str] = []
    unresolved_ids: list[str] = []
    unresolved_special = False
    for applicability in applicability_rows:
        scope_type = applicability["scope_type"]
        if scope_type not in {"include", "conditional", "exclude"}:
            raise ValueError(f"Unsupported applicability scope_type: {scope_type}")
        match_state = _row_match_state(applicability, product_context)
        applicability_id = str(applicability["applicability_id"])
        if match_state == "unresolved":
            unresolved_ids.append(applicability_id)
            if scope_type in {"conditional", "exclude"}:
                unresolved_special = True
        elif match_state == "matched":
            if scope_type == "include":
                matched_ids.append(applicability_id)
            elif scope_type == "conditional":
                conditional_ids.append(applicability_id)
            else:
                blocking_ids.append(applicability_id)

    if blocking_ids:
        status: ApplicabilityStatus = "not_applicable"
    elif matched_ids and not unresolved_special:
        status = "applicable"
    elif conditional_ids:
        status = "conditional"
    elif unresolved_ids:
        status = "insufficient_context"
    else:
        status = "not_applicable"

    return {
        "risk_category": risk_category,
        "substance_id": substance_id,
        "canonical_name": str(substance["canonical_name"]),
        "method_id": str(method["method_id"]),
        "method_no": str(method["method_no"]),
        "method_name": str(method["method_name"]),
        "method_status": str(method["method_status"]),
        "determination_role": str(method["determination_role"]),
        "applicability_status": status,
        "matched_applicability_ids": sorted(matched_ids),
        "conditional_applicability_ids": sorted(conditional_ids),
        "blocking_applicability_ids": sorted(blocking_ids),
        "unresolved_applicability_ids": sorted(unresolved_ids),
        "reason": _assessment_reason(status, blocked=bool(blocking_ids)),
    }


def evaluate_signal_trace(
    signal_trace: InspectionSignalTraceResult | Mapping[str, Any],
    product_context: ProductInspectionContext,
) -> ProductApplicabilityResult:
    """Evaluate each D3 substance-method relation against explicit context."""

    if not isinstance(signal_trace, Mapping):
        raise TypeError("signal_trace must be an InspectionSignalTraceResult or mapping")
    if not isinstance(product_context, ProductInspectionContext):
        raise TypeError("product_context must be a ProductInspectionContext")

    assessments_by_identity: dict[
        tuple[str, str, str], MethodApplicabilityAssessment
    ] = {}
    knowledge_gaps: list[dict[str, Any]] = []
    for signal in signal_trace["risk_knowledge_signals"]:
        risk_category = str(signal["risk_category"])
        knowledge_trace = signal["knowledge_trace"]
        knowledge_gaps.extend(
            {"risk_category": risk_category, **gap}
            for gap in knowledge_trace["knowledge_gaps"]
        )
        for substance in knowledge_trace["substance_targets"]:
            for method in substance["inspection_methods"]:
                identity = (
                    risk_category,
                    str(substance["substance_id"]),
                    str(method["method_id"]),
                )
                assessments_by_identity.setdefault(
                    identity,
                    _evaluate_method(
                        risk_category=risk_category,
                        substance=substance,
                        method=method,
                        product_context=product_context,
                    ),
                )

    method_assessments = [
        assessments_by_identity[identity]
        for identity in sorted(assessments_by_identity)
    ]
    return ProductApplicabilityResult(
        product_context=product_context.to_dict(),
        method_assessments=method_assessments,
        composition_gaps=signal_trace["composition_gaps"],
        knowledge_gaps=knowledge_gaps,
    )
