"""Read-only Risk-to-Inspection knowledge trace composition.

The resolver deliberately stops at persisted reference facts.  It does not
expand groups, rank methods, evaluate product applicability, or derive legal
conclusions.  Runtime data comes from SQLite through the public DataStore read
API; the Reference JSON files are import inputs, not a resolver data source.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterator, Mapping, TypedDict

from src.data_store import DataStore


class MappingEvidence(TypedDict):
    mapping_id: str
    evidence_grade: str
    basis_type: str
    temporal_status: str
    product_scope: str
    source_name: str
    source_reference: str
    source_date: str | None
    source_basis_text: str
    note: str


class GroupTarget(TypedDict):
    target_group_label: str
    resolution_status: str
    mapping_evidence: MappingEvidence


class UnresolvedGroup(TypedDict):
    mapping_id: str
    target_group_label: str
    resolution_status: str


class ApplicabilityTrace(TypedDict):
    applicability_id: str
    method_id: str
    substance_id: str | None
    scope_type: str
    product_category: str
    product_form: str
    ingredient_context: str
    source_scope_text: str
    note: str


class InspectionMethodTrace(TypedDict):
    method_id: str
    method_no: str
    method_name: str
    method_type: str
    method_status: str
    publisher: str
    published_date: str | None
    effective_date: str | None
    determination_role: str
    source_label: str
    source_cas_no: str
    normalization_note: str
    source_name: str
    source_reference: str
    source_date: str | None
    note: str
    method_level_applicabilities: list[ApplicabilityTrace]
    substance_scoped_applicabilities: list[ApplicabilityTrace]


class RegulatoryContextTrace(TypedDict):
    context_id: str
    context_status: str
    product_scope: str
    jurisdiction: str
    valid_from: str | None
    valid_to: str | None
    source_label: str
    source_name: str
    source_reference: str
    source_date: str | None
    note: str


class SubstanceTarget(TypedDict):
    substance_id: str
    canonical_name: str
    english_name: str
    cas_no: str
    mapping_evidence: MappingEvidence
    inspection_methods: list[InspectionMethodTrace]
    regulatory_contexts: list[RegulatoryContextTrace]


class KnowledgeGap(TypedDict, total=False):
    type: str
    mapping_id: str
    target_group_label: str
    substance_id: str
    message: str


@dataclass(frozen=True)
class KnowledgeTrace(Mapping[str, Any]):
    """Stable, JSON-compatible result of resolving one risk category."""

    risk_category: str
    risk_labels: list[str]
    group_targets: list[GroupTarget]
    substance_targets: list[SubstanceTarget]
    unresolved_groups: list[UnresolvedGroup]
    knowledge_gaps: list[KnowledgeGap]

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


class InspectionKnowledgeResolver:
    """Compose deterministic knowledge traces from persisted Reference rows."""

    def __init__(self, data_store: DataStore) -> None:
        self.data_store = data_store

    @staticmethod
    def _mapping_evidence(mapping: dict[str, Any]) -> MappingEvidence:
        return {
            "mapping_id": mapping["mapping_id"],
            "evidence_grade": mapping["evidence_grade"],
            "basis_type": mapping["basis_type"],
            "temporal_status": mapping["temporal_status"],
            "product_scope": mapping["product_scope"],
            "source_name": mapping["source_name"],
            "source_reference": mapping["source_reference"],
            "source_date": mapping["source_date"],
            "source_basis_text": mapping["source_basis_text"],
            "note": mapping["note"],
        }

    def _inspection_methods(
        self, substance_id: str
    ) -> list[InspectionMethodTrace]:
        methods: list[InspectionMethodTrace] = []
        for method_row in self.data_store.list_substance_methods(substance_id):
            applicability_rows = self.data_store.list_method_applicabilities(
                str(method_row["method_id"]), substance_id
            )
            method_level = [
                row for row in applicability_rows if row["substance_id"] is None
            ]
            substance_scoped = [
                row for row in applicability_rows if row["substance_id"] == substance_id
            ]
            methods.append(
                {
                    **method_row,
                    "method_level_applicabilities": method_level,
                    "substance_scoped_applicabilities": substance_scoped,
                }
            )
        return methods

    def resolve(
        self, risk_category: str, *, include_historical: bool = False
    ) -> KnowledgeTrace:
        """Resolve one risk category without product-level inference."""

        if not isinstance(risk_category, str):
            raise TypeError("risk_category must be a string")
        if not isinstance(include_historical, bool):
            raise TypeError("include_historical must be a boolean")

        category = risk_category.strip()
        mappings = self.data_store.list_risk_mappings(
            category, include_historical=include_historical
        )
        risk_labels = sorted({str(row["risk_label"]) for row in mappings})
        group_targets: list[GroupTarget] = []
        substance_targets: list[SubstanceTarget] = []
        unresolved_groups: list[UnresolvedGroup] = []
        knowledge_gaps: list[KnowledgeGap] = []

        for mapping in mappings:
            evidence = self._mapping_evidence(mapping)
            if mapping["target_type"] == "substance_group":
                group_label = str(mapping["target_group_label"])
                group_target: GroupTarget = {
                    "target_group_label": group_label,
                    "resolution_status": "partial",
                    "mapping_evidence": evidence,
                }
                group_targets.append(group_target)
                unresolved_groups.append(
                    {
                        "mapping_id": str(mapping["mapping_id"]),
                        "target_group_label": group_label,
                        "resolution_status": "partial",
                    }
                )
                knowledge_gaps.append(
                    {
                        "type": "unresolved_group",
                        "mapping_id": str(mapping["mapping_id"]),
                        "target_group_label": group_label,
                        "message": "Group membership is not expanded in D1.",
                    }
                )
                continue

            substance_id = str(mapping["substance_id"])
            substance = self.data_store.get_inspection_substance(substance_id)
            if substance is None:
                knowledge_gaps.append(
                    {
                        "type": "unresolved_substance",
                        "mapping_id": str(mapping["mapping_id"]),
                        "substance_id": substance_id,
                        "message": "The mapped Inspection Substance is unavailable.",
                    }
                )
                continue

            methods = self._inspection_methods(substance_id)
            contexts = self.data_store.list_substance_regulatory_contexts(substance_id)
            substance_targets.append(
                {
                    **substance,
                    "mapping_evidence": evidence,
                    "inspection_methods": methods,
                    "regulatory_contexts": contexts,
                }
            )
            if not methods:
                knowledge_gaps.append(
                    {
                        "type": "no_verified_method",
                        "substance_id": substance_id,
                        "message": "No persisted MethodSubstance relation was found.",
                    }
                )

        if mappings and not substance_targets:
            knowledge_gaps.append(
                {
                    "type": "no_concrete_substance",
                    "message": "This risk has no resolvable concrete Substance mapping.",
                }
            )

        return KnowledgeTrace(
            risk_category=category,
            risk_labels=risk_labels,
            group_targets=group_targets,
            substance_targets=substance_targets,
            unresolved_groups=unresolved_groups,
            knowledge_gaps=knowledge_gaps,
        )
