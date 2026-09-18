"""Compose governed page signals with inspection knowledge traces.

V2 production recommendations use ClaimMention records as the page-promotion
entry point.  The legacy Phase 3 Effect bridge remains available only as a
compatibility path for historical artifacts that do not have Claim analysis.
Neither path infers new risk categories, expands groups, evaluates product
applicability, ranks methods, or creates inspection recommendations.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import asdict, dataclass
from typing import Any, TypedDict

from src.claim_inspection_bridge import (
    bridge_claim_analysis,
    load_claim_inspection_bridge_config,
)
from src.data_store import DataStore
from src.effect_risk_bridge import (
    bridge_analysis_evidence,
    load_effect_risk_bridge_config,
)
from src.inspection_knowledge import InspectionKnowledgeResolver


class RiskKnowledgeSignal(TypedDict):
    risk_category: str
    bridge_mapping_ids: list[str]
    reference_mapping_ids: list[str]
    historical_reference_mapping_ids: list[str]
    historical_reference_disclosure: str
    trigger_evidence: list[dict[str, Any]]
    knowledge_trace: dict[str, Any]


class CompositionGap(TypedDict):
    type: str
    risk_category: str
    bridge_mapping_ids: list[str]
    reference_mapping_id: str
    message: str


@dataclass(frozen=True)
class InspectionSignalTraceResult(Mapping[str, Any]):
    """Stable JSON-compatible page-signal-to-inspection knowledge trace."""

    bridge_id: str
    bridge_version: str
    risk_knowledge_signals: list[RiskKnowledgeSignal]
    unmapped_evidence: list[dict[str, Any]]
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
    """Compose governed page signals with the existing D1 knowledge trace."""

    def __init__(self, data_store: DataStore) -> None:
        self.knowledge_resolver = InspectionKnowledgeResolver(data_store)

    def _compose_bridge_result(
        self,
        bridge_result: Mapping[str, Any],
        bridge_config: Mapping[str, Any],
        *,
        include_historical: bool,
        selective_historical: bool,
    ) -> InspectionSignalTraceResult:
        mapping_by_bridge_id = {
            str(mapping["bridge_mapping_id"]): mapping
            for mapping in bridge_config["mappings"]
        }
        metadata = bridge_config.get("metadata")
        metadata = metadata if isinstance(metadata, Mapping) else {}
        historical_disclosure = str(
            metadata.get("historical_reference_disclosure") or ""
        )

        risk_knowledge_signals: list[RiskKnowledgeSignal] = []
        composition_gaps: list[CompositionGap] = []
        for risk_signal in bridge_result["risk_signals"]:
            risk_category = str(risk_signal["risk_category"])
            bridge_mapping_ids = [str(value) for value in risk_signal["bridge_mapping_ids"]]
            reference_to_bridge_ids: dict[str, list[str]] = {}
            historical_reference_mapping_ids: set[str] = set()
            for bridge_mapping_id in bridge_mapping_ids:
                mapping = mapping_by_bridge_id[bridge_mapping_id]
                reference_mapping_id = str(mapping["reference_mapping_id"])
                reference_to_bridge_ids.setdefault(reference_mapping_id, []).append(
                    bridge_mapping_id
                )
                if (
                    selective_historical
                    and str(mapping.get("temporal_policy") or "")
                    == "historical_reference_allowed"
                ):
                    authorized = mapping.get("authorized_historical_mapping_ids")
                    if not isinstance(authorized, list):
                        raise ValueError(
                            f"Bridge {bridge_mapping_id} missing authorized_historical_mapping_ids"
                        )
                    historical_reference_mapping_ids.update(
                        str(value) for value in authorized
                    )
            reference_mapping_ids = sorted(reference_to_bridge_ids)
            selected_historical_ids = sorted(historical_reference_mapping_ids)

            if selective_historical:
                knowledge_trace = self.knowledge_resolver.resolve(
                    risk_category,
                    allowed_historical_mapping_ids=set(selected_historical_ids),
                ).to_dict()
            else:
                knowledge_trace = self.knowledge_resolver.resolve(
                    risk_category,
                    include_historical=include_historical,
                ).to_dict()
            resolved_mapping_ids = _resolved_mapping_ids(knowledge_trace)
            required_mapping_ids = set(reference_mapping_ids)
            required_mapping_ids.update(selected_historical_ids)
            for reference_mapping_id in sorted(required_mapping_ids):
                if reference_mapping_id in resolved_mapping_ids:
                    continue
                bridge_ids = reference_to_bridge_ids.get(
                    reference_mapping_id, bridge_mapping_ids
                )
                composition_gaps.append(
                    {
                        "type": "bridge_reference_not_in_knowledge_trace",
                        "risk_category": risk_category,
                        "bridge_mapping_ids": sorted(bridge_ids),
                        "reference_mapping_id": reference_mapping_id,
                        "message": (
                            "The verified Bridge-authorized mapping is not present "
                            "in the current SQLite KnowledgeTrace."
                        ),
                    }
                )

            risk_knowledge_signals.append(
                {
                    "risk_category": risk_category,
                    "bridge_mapping_ids": bridge_mapping_ids,
                    "reference_mapping_ids": reference_mapping_ids,
                    "historical_reference_mapping_ids": selected_historical_ids,
                    "historical_reference_disclosure": (
                        historical_disclosure if selected_historical_ids else ""
                    ),
                    "trigger_evidence": list(risk_signal["trigger_evidence"]),
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
            bridge_id=str(bridge_result["bridge_id"]),
            bridge_version=str(bridge_result["bridge_version"]),
            risk_knowledge_signals=risk_knowledge_signals,
            unmapped_evidence=list(bridge_result["unmapped_evidence"]),
            composition_gaps=composition_gaps,
        )

    def resolve_claim_analysis(
        self,
        claim_analysis: Mapping[str, Any],
        *,
        include_historical: bool = False,
    ) -> InspectionSignalTraceResult:
        """Resolve V2 ClaimMention records into inspection knowledge traces.

        V2 production never accepts a category-wide historical switch.  Any
        historical mapping must be explicitly authorized by the exact Claim
        Bridge relation that references it.
        """

        if not isinstance(include_historical, bool):
            raise TypeError("include_historical must be a boolean")
        if include_historical:
            raise ValueError(
                "V2 Claim production forbids global include_historical; use governed Bridge temporal_policy"
            )
        bridge_result = bridge_claim_analysis(claim_analysis).to_dict()
        bridge_config = load_claim_inspection_bridge_config()
        return self._compose_bridge_result(
            bridge_result,
            bridge_config,
            include_historical=False,
            selective_historical=True,
        )

    def resolve_analysis(
        self,
        analysis: Mapping[str, Any],
        *,
        include_historical: bool = False,
    ) -> InspectionSignalTraceResult:
        """Resolve legacy Phase 3 Effect evidence for historical compatibility."""

        if not isinstance(include_historical, bool):
            raise TypeError("include_historical must be a boolean")
        bridge_result = bridge_analysis_evidence(analysis).to_dict()
        bridge_config = load_effect_risk_bridge_config()
        return self._compose_bridge_result(
            bridge_result,
            bridge_config,
            include_historical=include_historical,
            selective_historical=False,
        )
