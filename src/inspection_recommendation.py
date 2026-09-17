"""Product-level regulatory screening recommendations.

Current V2 products enter the inspection knowledge chain through governed Claim
records.  Legacy Phase 3 Effect analysis remains an explicit compatibility path
for historical artifacts without Claim analysis.  The builder does not infer
product context, create new mappings, select a best method, determine
illegality, or represent a laboratory detection result.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import asdict, dataclass
from typing import Any, Literal, TypedDict

from src.data_store import DataStore
from src.inspection_applicability import (
    ProductInspectionContext,
    evaluate_signal_trace,
)
from src.inspection_signal_trace import InspectionSignalTraceResolver


DISCLAIMER = (
    "基于页面宣传线索，建议重点关注/检测相关成分；"
    "以上结果仅用于监管抽检辅助筛查，不表示商品实际含有上述化合物，"
    "不构成违法认定或实验室检出结论。"
    "具体检验项目需结合产品身份、食品类别、剂型、配料/原料信息和样品情况，"
    "由检验人员及监管人员确认。"
)

REGULATORY_CONTEXT_NOTE = (
    "该物质存在需要结合具体产品解释的受治理监管语境；具体检验项目及风险解释"
    "需结合商品身份、食品类别、备案/注册情况、配料/原料信息及该监管语境人工确认。"
)

EvidenceQualification = Literal[
    "seller_managed_primary",
    "user_generated_auxiliary_only",
]

TemporalBasis = Literal[
    "current_only",
    "current_and_historical",
    "historical_reference_only",
]

FollowUpStatus = Literal[
    "suggest_testing",
    "needs_context_review",
    "regulatory_context_review",
    "auxiliary_evidence_only",
    "knowledge_integrity_gap",
    "no_applicable_verified_method",
]


class FollowUpMethod(TypedDict):
    method_id: str
    method_no: str
    method_name: str
    method_type: str
    method_status: str
    determination_role: str
    applicability_status: str
    matched_applicability_ids: list[str]
    conditional_applicability_ids: list[str]
    blocking_applicability_ids: list[str]
    unresolved_applicability_ids: list[str]
    applicability_reason: str
    source_name: str
    source_reference: str
    source_date: str | None


class SubstanceFollowUp(TypedDict):
    substance_id: str
    canonical_name: str
    english_name: str
    cas_no: str
    mapping_evidence: list[dict[str, Any]]
    regulatory_contexts: list[dict[str, Any]]
    regulatory_context_note: str
    follow_up_status: FollowUpStatus
    suggested_methods: list[FollowUpMethod]
    methods_needing_context: list[FollowUpMethod]
    other_known_methods: list[FollowUpMethod]
    reason: str


class RiskFinding(TypedDict):
    risk_category: str
    risk_labels: list[str]
    possible_risk_summary: str
    temporal_basis: TemporalBasis
    historical_reference_mapping_ids: list[str]
    historical_reference_note: str
    evidence_qualification: EvidenceQualification
    trigger_evidence: list[dict[str, Any]]
    group_targets: list[dict[str, Any]]
    substance_follow_ups: list[SubstanceFollowUp]


@dataclass(frozen=True)
class ProductInspectionRecommendationResult(Mapping[str, Any]):
    """Stable JSON-compatible product inspection screening result."""

    product_id: str
    product_name: str
    product_url: str
    product_context: dict[str, Any]
    risk_findings: list[RiskFinding]
    unmapped_evidence: list[dict[str, Any]]
    composition_gaps: list[dict[str, Any]]
    knowledge_gaps: list[dict[str, Any]]
    disclaimer: str

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


def _product_identity(analysis: Mapping[str, Any], field_name: str) -> str:
    value = analysis.get(field_name)
    return "" if value is None else str(value)


def _evidence_qualification(
    trigger_evidence: list[dict[str, Any]],
) -> EvidenceQualification:
    if any(
        evidence.get("content_origin") == "seller_managed"
        for evidence in trigger_evidence
    ):
        return "seller_managed_primary"
    return "user_generated_auxiliary_only"


def _knowledge_has_current_mapping(knowledge_trace: Mapping[str, Any]) -> bool:
    for target_field in ("group_targets", "substance_targets"):
        for target in knowledge_trace.get(target_field, []):
            for evidence in target.get("mapping_evidence", []):
                if evidence.get("temporal_status") == "current":
                    return True
    return False


def _temporal_basis(
    knowledge_trace: Mapping[str, Any],
    historical_reference_mapping_ids: list[str],
) -> TemporalBasis:
    if not historical_reference_mapping_ids:
        return "current_only"
    if _knowledge_has_current_mapping(knowledge_trace):
        return "current_and_historical"
    return "historical_reference_only"


def _possible_risk_summary(
    risk_category: str,
    risk_labels: list[str],
    temporal_basis: TemporalBasis,
) -> str:
    label = "、".join(risk_labels) if risk_labels else risk_category
    if temporal_basis == "historical_reference_only":
        return (
            f"页面中发现与“{label}”相关的宣传线索，"
            "该方向依据受治理的历史中央专项抽检/风险监测资料作为抽检筛查参考。"
        )
    if temporal_basis == "current_and_historical":
        return (
            f"页面中发现与“{label}”相关的宣传线索，"
            "当前受治理知识与历史中央专项抽检/风险监测资料共同提供抽检筛查参考。"
        )
    return (
        f"页面中发现与“{label}”相关的宣传线索，"
        "当前已治理知识将其作为监管抽检关注方向。"
    )


def _method_follow_up(
    method: Mapping[str, Any],
    assessment: Mapping[str, Any],
) -> FollowUpMethod:
    return {
        "method_id": str(method["method_id"]),
        "method_no": str(method["method_no"]),
        "method_name": str(method["method_name"]),
        "method_type": str(method["method_type"]),
        "method_status": str(assessment["method_status"]),
        "determination_role": str(assessment["determination_role"]),
        "applicability_status": str(assessment["applicability_status"]),
        "matched_applicability_ids": list(
            assessment["matched_applicability_ids"]
        ),
        "conditional_applicability_ids": list(
            assessment["conditional_applicability_ids"]
        ),
        "blocking_applicability_ids": list(
            assessment["blocking_applicability_ids"]
        ),
        "unresolved_applicability_ids": list(
            assessment["unresolved_applicability_ids"]
        ),
        "applicability_reason": str(assessment["reason"]),
        "source_name": str(method["source_name"]),
        "source_reference": str(method["source_reference"]),
        "source_date": method["source_date"],
    }


def _method_order(method: FollowUpMethod) -> tuple[str, str]:
    return (method["method_no"], method["method_id"])


def _follow_up_reason(
    status: FollowUpStatus,
    *,
    substance_name: str,
    suggested_methods: list[FollowUpMethod],
) -> str:
    if status == "knowledge_integrity_gap":
        return (
            "当前页面线索与知识库引用链存在不一致，暂不形成商品级检测"
            "建议；需先由人工核对知识完整性。"
        )
    if status == "auxiliary_evidence_only":
        return (
            "当前线索仅来自用户生成内容，不能等同于商家作出的功效宣传；"
            "该方向仅作为辅助筛查线索保留，建议人工复核页面。"
        )
    if status == "regulatory_context_review":
        return (
            f"“{substance_name}”存在需要结合具体产品解释的受治理监管语境；"
            "需先核对商品身份、食品类别、注册/备案及配料/原料信息，"
            "暂不依据页面宣传直接形成商品级检测建议。相关方法仅作为人工研判参考。"
        )
    if status == "suggest_testing":
        method_numbers = "、".join(
            method["method_no"] for method in suggested_methods
        )
        return (
            f"基于页面商家管理内容中的宣传线索，建议重点关注/检测“{substance_name}”；"
            f"当前知识库中已核验的相关检验方法包括{method_numbers}。"
            "以上为抽检辅助建议，不表示该商品实际含有上述化合物；具体检验项目"
            "需结合产品身份、食品类别、剂型、配料/原料信息和样品情况由检验人员确认。"
        )
    if status == "needs_context_review":
        return (
            "需要人工确认商品类别、剂型或相关配料/原料信息后，才能判断"
            "当前方法的适用范围是否覆盖该商品；暂不形成商品级检测建议。"
        )
    return (
        "当前已核验知识中没有同时满足现行状态和适用性条件的方法；"
        "这不表示相关方法在科学上绝对不可使用，需由检验人员人工判断。"
    )


class InspectionRecommendationBuilder:
    """Build deterministic product-level screening follow-ups."""

    def __init__(self, data_store: DataStore) -> None:
        self.signal_trace_resolver = InspectionSignalTraceResolver(data_store)

    def build(
        self,
        analysis: Mapping[str, Any],
        product_context: ProductInspectionContext,
        *,
        claim_analysis: Mapping[str, Any] | None = None,
        include_historical: bool = False,
    ) -> ProductInspectionRecommendationResult:
        """Compose governed page signals, knowledge and applicability.

        When ``claim_analysis`` is present it is the authoritative V2 page-signal
        input. ``include_historical`` is only a legacy-artifact compatibility
        switch; V2 Claim production admits historical references exclusively via
        each governed Bridge mapping's temporal policy.
        """

        if not isinstance(analysis, Mapping):
            raise TypeError("analysis must be a mapping")
        if claim_analysis is not None and not isinstance(claim_analysis, Mapping):
            raise TypeError("claim_analysis must be a mapping or None")
        if not isinstance(product_context, ProductInspectionContext):
            raise TypeError("product_context must be a ProductInspectionContext")

        if claim_analysis is not None:
            signal_trace = self.signal_trace_resolver.resolve_claim_analysis(
                claim_analysis,
                include_historical=include_historical,
            )
        else:
            signal_trace = self.signal_trace_resolver.resolve_analysis(
                analysis,
                include_historical=include_historical,
            )
        applicability_result = evaluate_signal_trace(signal_trace, product_context)
        assessments_by_identity = {
            (
                assessment["risk_category"],
                assessment["substance_id"],
                assessment["method_id"],
            ): assessment
            for assessment in applicability_result.method_assessments
        }
        gap_categories = {
            str(gap["risk_category"])
            for gap in applicability_result.composition_gaps
        }

        risk_findings: list[RiskFinding] = []
        for risk_signal in signal_trace.risk_knowledge_signals:
            risk_category = risk_signal["risk_category"]
            trigger_evidence = risk_signal["trigger_evidence"]
            evidence_qualification = _evidence_qualification(trigger_evidence)
            knowledge_trace = risk_signal["knowledge_trace"]
            historical_reference_mapping_ids = list(
                risk_signal.get("historical_reference_mapping_ids", [])
            )
            temporal_basis = _temporal_basis(
                knowledge_trace,
                historical_reference_mapping_ids,
            )
            historical_reference_note = str(
                risk_signal.get("historical_reference_disclosure") or ""
            )
            substance_follow_ups: list[SubstanceFollowUp] = []
            for substance in knowledge_trace["substance_targets"]:
                substance_id = substance["substance_id"]
                suggested_methods: list[FollowUpMethod] = []
                methods_needing_context: list[FollowUpMethod] = []
                other_known_methods: list[FollowUpMethod] = []
                for method in substance["inspection_methods"]:
                    assessment = assessments_by_identity[
                        (risk_category, substance_id, method["method_id"])
                    ]
                    method_follow_up = _method_follow_up(method, assessment)
                    if assessment["method_status"] != "current":
                        other_known_methods.append(method_follow_up)
                    elif assessment["applicability_status"] in {
                        "applicable",
                        "conditional",
                    }:
                        suggested_methods.append(method_follow_up)
                    elif assessment["applicability_status"] == "insufficient_context":
                        methods_needing_context.append(method_follow_up)
                    else:
                        other_known_methods.append(method_follow_up)

                regulatory_contexts = substance["regulatory_contexts"]
                if risk_category in gap_categories:
                    follow_up_status: FollowUpStatus = "knowledge_integrity_gap"
                    other_known_methods.extend(suggested_methods)
                    suggested_methods = []
                elif evidence_qualification == "user_generated_auxiliary_only":
                    follow_up_status = "auxiliary_evidence_only"
                    other_known_methods.extend(suggested_methods)
                    suggested_methods = []
                elif regulatory_contexts:
                    follow_up_status = "regulatory_context_review"
                    other_known_methods.extend(suggested_methods)
                    suggested_methods = []
                elif suggested_methods:
                    follow_up_status = "suggest_testing"
                elif methods_needing_context:
                    follow_up_status = "needs_context_review"
                else:
                    follow_up_status = "no_applicable_verified_method"

                suggested_methods.sort(key=_method_order)
                methods_needing_context.sort(key=_method_order)
                other_known_methods.sort(key=_method_order)
                substance_follow_ups.append(
                    {
                        "substance_id": substance_id,
                        "canonical_name": substance["canonical_name"],
                        "english_name": substance["english_name"],
                        "cas_no": substance["cas_no"],
                        "mapping_evidence": substance["mapping_evidence"],
                        "regulatory_contexts": regulatory_contexts,
                        "regulatory_context_note": (
                            REGULATORY_CONTEXT_NOTE if regulatory_contexts else ""
                        ),
                        "follow_up_status": follow_up_status,
                        "suggested_methods": suggested_methods,
                        "methods_needing_context": methods_needing_context,
                        "other_known_methods": other_known_methods,
                        "reason": _follow_up_reason(
                            follow_up_status,
                            substance_name=substance["canonical_name"],
                            suggested_methods=suggested_methods,
                        ),
                    }
                )

            substance_follow_ups.sort(key=lambda item: item["substance_id"])
            risk_labels = knowledge_trace["risk_labels"]
            risk_findings.append(
                {
                    "risk_category": risk_category,
                    "risk_labels": risk_labels,
                    "possible_risk_summary": _possible_risk_summary(
                        risk_category,
                        risk_labels,
                        temporal_basis,
                    ),
                    "temporal_basis": temporal_basis,
                    "historical_reference_mapping_ids": historical_reference_mapping_ids,
                    "historical_reference_note": historical_reference_note,
                    "evidence_qualification": evidence_qualification,
                    "trigger_evidence": trigger_evidence,
                    "group_targets": knowledge_trace["group_targets"],
                    "substance_follow_ups": substance_follow_ups,
                }
            )

        risk_findings.sort(key=lambda item: item["risk_category"])
        return ProductInspectionRecommendationResult(
            product_id=_product_identity(analysis, "product_id"),
            product_name=_product_identity(analysis, "product_name"),
            product_url=_product_identity(analysis, "product_url"),
            product_context=applicability_result.product_context,
            risk_findings=risk_findings,
            unmapped_evidence=signal_trace.unmapped_evidence,
            composition_gaps=applicability_result.composition_gaps,
            knowledge_gaps=applicability_result.knowledge_gaps,
            disclaimer=DISCLAIMER,
        )
