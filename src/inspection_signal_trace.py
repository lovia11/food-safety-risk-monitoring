"""Compose Phase 3 evidence, D2 RiskSignals, and D1 KnowledgeTraces.

This runtime composition layer delegates evidence matching to D2 and knowledge
resolution to D1.  It does not infer risk categories, expand groups, evaluate
product applicability, rank methods, or create inspection recommendations.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import asdict, dataclass
from typing import Any, TypedDict

from src.data_store import DataStore
from src.effect_risk_bridge import (
    TriggerEvidence,
    UnmappedEvidence,
    bridge_analysis_evidence,
    load_effect_risk_bridge_config,
)
from src.inspection_knowledge import InspectionKnowledgeResolver


class RiskKnowledgeSignal(TypedDict):
    risk_category: str
    bridge_mapping_ids: list[str]
    reference_mapping_ids: list[str]
    trigger_evidence: list[TriggerEvidence]
    knowledge_trace: dict[str, Any]


class CompositionGap(TypedDict):
    type: str
    risk_category: str
    bridge_mapping_ids: list[str]
    reference_mapping_id: str
    message: str


@dataclass(frozen=True)
class InspectionSignalTraceResult(Mapping[str, Any]):
    """Stable JSON-compatible Evidence-to-Inspection knowledge trace."""

    bridge_id: str
    bridge_version: str
    risk_knowledge_signals: list[RiskKnowledgeSignal]
    unmapped_evidence: list[UnmappedEvidence]
    composition_gaps: list[CompositionGap]

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


def _resolved_mapping_ids(knowledge_trace: Mapping[str, Any]) -> set[str]:
    mapping_ids: set[str] = set()
    for target_field in ("group_targets", "substance_targets"):
        for target in knowledge_trace[target_field]:
            mapping_ids.update(
                evidence["mapping_id"] for evidence in target["mapping_evidence"]
            )
    return mapping_ids


class InspectionSignalTraceResolver:
    """Compose the frozen D2 and D1 contracts without adding inference."""

    def __init__(self, data_store: DataStore) -> None:
        self.knowledge_resolver = InspectionKnowledgeResolver(data_store)

    def resolve_analysis(
        self,
        analysis: Mapping[str, Any],
        *,
        include_historical: bool = False,
    ) -> InspectionSignalTraceResult:
        """Resolve D2 risk signals into D1 knowledge traces."""

        if not isinstance(include_historical, bool):
            raise TypeError("include_historical must be a boolean")

        bridge_result = bridge_analysis_evidence(analysis)
        bridge_config = load_effect_risk_bridge_config()
        reference_id_by_bridge_id = {
            mapping["bridge_mapping_id"]: mapping["reference_mapping_id"]
            for mapping in bridge_config["mappings"]
        }

        risk_knowledge_signals: list[RiskKnowledgeSignal] = []
        composition_gaps: list[CompositionGap] = []
        for risk_signal in bridge_result.risk_signals:
            risk_category = risk_signal["risk_category"]
            bridge_mapping_ids = risk_signal["bridge_mapping_ids"]
            reference_to_bridge_ids: dict[str, list[str]] = {}
            for bridge_mapping_id in bridge_mapping_ids:
                reference_mapping_id = reference_id_by_bridge_id[bridge_mapping_id]
                reference_to_bridge_ids.setdefault(reference_mapping_id, []).append(
                    bridge_mapping_id
                )
            reference_mapping_ids = sorted(reference_to_bridge_ids)

            knowledge_trace = self.knowledge_resolver.resolve(
                risk_category,
                include_historical=include_historical,
            ).to_dict()
            resolved_mapping_ids = _resolved_mapping_ids(knowledge_trace)
            for reference_mapping_id in reference_mapping_ids:
                if reference_mapping_id in resolved_mapping_ids:
                    continue
                composition_gaps.append(
                    {
                        "type": "bridge_reference_not_in_knowledge_trace",
                        "risk_category": risk_category,
                        "bridge_mapping_ids": sorted(
                            reference_to_bridge_ids[reference_mapping_id]
                        ),
                        "reference_mapping_id": reference_mapping_id,
                        "message": (
                            "The verified Bridge reference mapping is not present "
                            "in the current SQLite KnowledgeTrace."
                        ),
                    }
                )

            risk_knowledge_signals.append(
                {
                    "risk_category": risk_category,
                    "bridge_mapping_ids": bridge_mapping_ids,
                    "reference_mapping_ids": reference_mapping_ids,
                    "trigger_evidence": risk_signal["trigger_evidence"],
                    "knowledge_trace": knowledge_trace,
                }
            )

        composition_gaps.sort(
            key=lambda gap: (
                gap["risk_category"],
                gap["reference_mapping_id"],
            )
        )
        return InspectionSignalTraceResult(
            bridge_id=bridge_result.bridge_id,
            bridge_version=bridge_result.bridge_version,
            risk_knowledge_signals=risk_knowledge_signals,
            unmapped_evidence=bridge_result.unmapped_evidence,
            composition_gaps=composition_gaps,
        )
