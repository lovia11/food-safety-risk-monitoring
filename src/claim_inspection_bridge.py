"""Governed V2 ClaimMention-to-inspection-direction bridge.

This is the V2 production bridge from page Claim records to the existing
inspection knowledge chain. Relations are expression-specific and must point to
an already verified Risk Reference. The bridge never infers synonyms, expands a
whole Claim type, reverse-maps inspection methods, or creates Risk->Substance
knowledge.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, TypedDict

from src.claim_analysis import (
    load_claim_taxonomy,
    validate_claim_analysis,
    validate_claim_taxonomy,
)
from src.effect_risk_bridge import load_effect_risk_bridge_config
from src.risk_substance_reference import (
    RiskSubstanceConfigValidationError,
    validate_risk_substance_config,
)
from src.runtime import read_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BRIDGE_CONFIG = PROJECT_ROOT / "config" / "claim_inspection_bridge_v2.json"
DEFAULT_RISK_REFERENCE_CONFIG = PROJECT_ROOT / "config" / "risk_substance_reference.json"

_TOP_LEVEL_FIELDS = {
    "schema_version",
    "bridge_id",
    "bridge_version",
    "description",
    "mappings",
    "metadata",
}
_MAPPING_FIELDS = {
    "bridge_mapping_id",
    "claim_type",
    "expression_id",
    "matched_expression",
    "risk_category",
    "reference_mapping_id",
    "authorized_historical_mapping_ids",
    "temporal_policy",
    "governance_basis",
    "migrated_from_bridge_mapping_id",
    "note",
}
_ALLOWED_GOVERNANCE_BASES = {
    "legacy_verified_migration",
    "direct_verified_reference",
}
_ALLOWED_TEMPORAL_POLICIES = {
    "current_only",
    "historical_reference_allowed",
}


class ClaimInspectionBridgeConfigValidationError(ValueError):
    """The governed Claim-to-inspection bridge is invalid."""


class ClaimTriggerEvidence(TypedDict):
    effect: str
    text: str
    matched_keywords: list[str]
    bridge_matched_keywords: list[str]
    source_type: str
    source_label: str
    content_origin: str
    source_path: str
    line_number: int | None
    claimMentionId: str
    claimType: str
    claimDisplayLabel: str
    expressionId: str
    matchedExpression: str
    evidenceId: str


class UnmappedClaimEvidence(TypedDict):
    effect: str
    text: str
    matched_keywords: list[str]
    unmapped_keywords: list[str]
    source_type: str
    source_label: str
    content_origin: str
    source_path: str
    line_number: int | None
    claimMentionId: str
    claimType: str
    claimDisplayLabel: str
    expressionId: str
    matchedExpression: str
    evidenceId: str
    reason: str


class ClaimRiskSignal(TypedDict):
    risk_category: str
    bridge_mapping_ids: list[str]
    trigger_evidence: list[ClaimTriggerEvidence]


@dataclass(frozen=True)
class ClaimInspectionBridgeResult(Mapping[str, Any]):
    bridge_id: str
    bridge_version: str
    risk_signals: list[ClaimRiskSignal]
    unmapped_evidence: list[UnmappedClaimEvidence]

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


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ClaimInspectionBridgeConfigValidationError(f"{field}不能为空")
    return value.strip()


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ClaimInspectionBridgeConfigValidationError(f"{field}必须是非空字符串或null")
    return value.strip()


def _text_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ClaimInspectionBridgeConfigValidationError(f"{field}必须是字符串数组")
    result: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        text = _required_text(item, f"{field}[{index}]")
        if text in seen:
            raise ClaimInspectionBridgeConfigValidationError(
                f"{field}包含重复值：{text}"
            )
        seen.add(text)
        result.append(text)
    return result


def _require_exact_fields(item: Mapping[str, Any], expected: set[str], field: str) -> None:
    missing = sorted(expected - set(item))
    if missing:
        raise ClaimInspectionBridgeConfigValidationError(
            f"{field}缺少字段：{', '.join(missing)}"
        )
    unexpected = sorted(set(item) - expected)
    if unexpected:
        raise ClaimInspectionBridgeConfigValidationError(
            f"{field}包含未定义字段：{', '.join(unexpected)}"
        )


def validate_claim_inspection_bridge_config(
    payload: Any,
    *,
    taxonomy: dict[str, Any] | None = None,
    risk_reference_config: Any | None = None,
    legacy_bridge_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate each Claim relation against the Claim and Risk authorities."""

    if not isinstance(payload, Mapping):
        raise ClaimInspectionBridgeConfigValidationError("Claim Inspection Bridge根节点必须是对象")
    _require_exact_fields(payload, _TOP_LEVEL_FIELDS, "Claim Inspection Bridge根节点")
    if payload.get("schema_version") != 1 or isinstance(payload.get("schema_version"), bool):
        raise ClaimInspectionBridgeConfigValidationError("schema_version必须为1")

    taxonomy = validate_claim_taxonomy(taxonomy or load_claim_taxonomy())
    active_types = {
        str(item["id"]): item
        for item in taxonomy["claim_types"]
        if str(item.get("status") or "") == "active"
    }
    active_expressions = {
        str(item["expression_id"]): item
        for item in taxonomy["expressions"]
        if str(item.get("status") or "") == "active"
    }

    if risk_reference_config is None:
        risk_reference_config = read_json(DEFAULT_RISK_REFERENCE_CONFIG)
    try:
        risk_reference = validate_risk_substance_config(risk_reference_config)
    except RiskSubstanceConfigValidationError as exc:
        raise ClaimInspectionBridgeConfigValidationError(
            f"Risk Reference配置无效：{exc}"
        ) from exc
    if risk_reference["dataset_status"] != "verified_reference":
        raise ClaimInspectionBridgeConfigValidationError(
            "Claim Inspection Bridge只能引用verified_reference Risk Mapping"
        )
    risk_mapping_by_id = {
        str(item["mapping_id"]): item for item in risk_reference["mappings"]
    }

    legacy_bridge = legacy_bridge_config or load_effect_risk_bridge_config()
    legacy_mapping_by_id = {
        str(item["bridge_mapping_id"]): item for item in legacy_bridge["mappings"]
    }

    bridge_id = _required_text(payload.get("bridge_id"), "bridge_id")
    bridge_version = _required_text(payload.get("bridge_version"), "bridge_version")
    description = _required_text(payload.get("description"), "description")
    mappings_raw = payload.get("mappings")
    if not isinstance(mappings_raw, list):
        raise ClaimInspectionBridgeConfigValidationError("mappings必须是数组")
    metadata = payload.get("metadata")
    if not isinstance(metadata, Mapping):
        raise ClaimInspectionBridgeConfigValidationError("metadata必须是对象")
    historical_disclosure = _required_text(
        metadata.get("historical_reference_disclosure"),
        "metadata.historical_reference_disclosure",
    )

    normalized: list[dict[str, Any]] = []
    seen_mapping_ids: set[str] = set()
    seen_expression_ids: set[str] = set()
    for index, raw in enumerate(mappings_raw, start=1):
        if not isinstance(raw, Mapping):
            raise ClaimInspectionBridgeConfigValidationError(f"mappings[{index}]必须是对象")
        context = f"mappings[{index}]"
        _require_exact_fields(raw, _MAPPING_FIELDS, context)
        item: dict[str, Any] = {
            key: _required_text(raw.get(key), f"{context}.{key}")
            for key in _MAPPING_FIELDS
            if key not in {
                "migrated_from_bridge_mapping_id",
                "authorized_historical_mapping_ids",
            }
        }
        item["authorized_historical_mapping_ids"] = _text_list(
            raw.get("authorized_historical_mapping_ids"),
            f"{context}.authorized_historical_mapping_ids",
        )
        item["migrated_from_bridge_mapping_id"] = _optional_text(
            raw.get("migrated_from_bridge_mapping_id"),
            f"{context}.migrated_from_bridge_mapping_id",
        )

        mapping_id = str(item["bridge_mapping_id"])
        if mapping_id in seen_mapping_ids:
            raise ClaimInspectionBridgeConfigValidationError(f"bridge_mapping_id重复：{mapping_id}")
        seen_mapping_ids.add(mapping_id)

        governance_basis = str(item["governance_basis"])
        if governance_basis not in _ALLOWED_GOVERNANCE_BASES:
            raise ClaimInspectionBridgeConfigValidationError(
                f"{mapping_id}的governance_basis不受支持：{governance_basis}"
            )
        temporal_policy = str(item["temporal_policy"])
        if temporal_policy not in _ALLOWED_TEMPORAL_POLICIES:
            raise ClaimInspectionBridgeConfigValidationError(
                f"{mapping_id}的temporal_policy不受支持：{temporal_policy}"
            )

        expression_id = str(item["expression_id"])
        if expression_id in seen_expression_ids:
            raise ClaimInspectionBridgeConfigValidationError(
                f"同一Claim expression不能重复桥接：{expression_id}"
            )
        seen_expression_ids.add(expression_id)
        expression = active_expressions.get(expression_id)
        if expression is None:
            raise ClaimInspectionBridgeConfigValidationError(
                f"引用的active Claim expression不存在：{expression_id}"
            )
        claim_type = str(item["claim_type"])
        if claim_type not in active_types or str(expression["claim_type"]) != claim_type:
            raise ClaimInspectionBridgeConfigValidationError(
                f"{expression_id}的claim_type与治理词表不一致"
            )
        if str(expression["text"]) != str(item["matched_expression"]):
            raise ClaimInspectionBridgeConfigValidationError(
                f"{expression_id}的matched_expression与治理词表不一致"
            )

        reference_mapping_id = str(item["reference_mapping_id"])
        reference = risk_mapping_by_id.get(reference_mapping_id)
        if reference is None:
            raise ClaimInspectionBridgeConfigValidationError(
                f"Risk reference mapping不存在：{reference_mapping_id}"
            )
        if str(reference["risk_category"]) != str(item["risk_category"]):
            raise ClaimInspectionBridgeConfigValidationError(
                f"{mapping_id}的risk_category与Risk Reference不一致"
            )

        reference_temporal_status = str(reference["temporal_status"])
        authorized_historical_mapping_ids = list(
            item["authorized_historical_mapping_ids"]
        )
        if temporal_policy == "current_only":
            if reference_temporal_status != "current":
                raise ClaimInspectionBridgeConfigValidationError(
                    f"{mapping_id}声明current_only但引用了historical Risk Reference"
                )
            if authorized_historical_mapping_ids:
                raise ClaimInspectionBridgeConfigValidationError(
                    f"{mapping_id}为current_only时不得授权historical Risk Mapping"
                )
        else:
            if reference_temporal_status != "historical":
                raise ClaimInspectionBridgeConfigValidationError(
                    f"{mapping_id}声明historical_reference_allowed但引用的不是historical Risk Reference"
                )
            if str(reference["basis_type"]) != "historical_sampling_plan":
                raise ClaimInspectionBridgeConfigValidationError(
                    f"{mapping_id}只能选择性启用historical_sampling_plan，不能启用其他historical来源"
                )
            if governance_basis != "direct_verified_reference":
                raise ClaimInspectionBridgeConfigValidationError(
                    f"{mapping_id}的historical Reference必须使用direct_verified_reference治理"
                )
            if not historical_disclosure:
                raise ClaimInspectionBridgeConfigValidationError(
                    f"{mapping_id}启用historical Reference时必须提供展示边界"
                )
            if reference_mapping_id not in authorized_historical_mapping_ids:
                raise ClaimInspectionBridgeConfigValidationError(
                    f"{mapping_id}的authorized_historical_mapping_ids必须包含reference_mapping_id"
                )
            for historical_mapping_id in authorized_historical_mapping_ids:
                historical_mapping = risk_mapping_by_id.get(historical_mapping_id)
                if historical_mapping is None:
                    raise ClaimInspectionBridgeConfigValidationError(
                        f"{mapping_id}授权的Risk mapping不存在：{historical_mapping_id}"
                    )
                if str(historical_mapping["risk_category"]) != str(item["risk_category"]):
                    raise ClaimInspectionBridgeConfigValidationError(
                        f"{mapping_id}授权的historical mapping必须属于同一risk_category"
                    )
                if (
                    str(historical_mapping["temporal_status"]) != "historical"
                    or str(historical_mapping["basis_type"]) != "historical_sampling_plan"
                ):
                    raise ClaimInspectionBridgeConfigValidationError(
                        f"{mapping_id}只能授权historical_sampling_plan类型的historical mapping"
                    )
                for source_field in ("source_reference", "source_date", "product_scope"):
                    if historical_mapping[source_field] != reference[source_field]:
                        raise ClaimInspectionBridgeConfigValidationError(
                            f"{mapping_id}授权的historical mapping必须与reference_mapping_id共享{source_field}"
                        )

        migration_id = item["migrated_from_bridge_mapping_id"]
        if governance_basis == "legacy_verified_migration":
            if temporal_policy != "current_only":
                raise ClaimInspectionBridgeConfigValidationError(
                    f"{mapping_id}的legacy迁移只能引用current Risk Reference"
                )
            if migration_id is None:
                raise ClaimInspectionBridgeConfigValidationError(
                    f"{mapping_id}缺少legacy迁移来源"
                )
            legacy = legacy_mapping_by_id.get(str(migration_id))
            if legacy is None:
                raise ClaimInspectionBridgeConfigValidationError(
                    f"迁移来源legacy bridge不存在：{migration_id}"
                )
            legacy_ref = expression.get("legacy_reference")
            if not isinstance(legacy_ref, Mapping):
                raise ClaimInspectionBridgeConfigValidationError(
                    f"{expression_id}缺少legacy_reference，不能证明精确迁移"
                )
            if (
                str(legacy_ref.get("effect") or "") != str(legacy["effect_label"])
                or str(legacy_ref.get("keyword") or "") != str(legacy["matched_keyword"])
                or str(item["risk_category"]) != str(legacy["risk_category"])
                or reference_mapping_id != str(legacy["reference_mapping_id"])
            ):
                raise ClaimInspectionBridgeConfigValidationError(
                    f"{mapping_id}与既有已核验legacy bridge关系不一致"
                )
        elif migration_id is not None:
            raise ClaimInspectionBridgeConfigValidationError(
                f"{mapping_id}为direct_verified_reference时不得伪装legacy迁移来源"
            )
        normalized.append(item)

    return {
        "schema_version": 1,
        "bridge_id": bridge_id,
        "bridge_version": bridge_version,
        "description": description,
        "mappings": normalized,
        "metadata": dict(metadata),
    }


def load_claim_inspection_bridge_config(
    path: Path = DEFAULT_BRIDGE_CONFIG,
) -> dict[str, Any]:
    return validate_claim_inspection_bridge_config(read_json(path.resolve()))


def _claim_display_labels(taxonomy: Mapping[str, Any]) -> dict[str, str]:
    return {
        str(item["id"]): str(item["label_zh"])
        for item in taxonomy["claim_types"]
        if str(item.get("status") or "") == "active"
    }


def _base_claim_evidence(
    mention: Mapping[str, Any],
    *,
    display_label: str,
) -> dict[str, Any]:
    locator = mention.get("sourceLocator")
    locator = locator if isinstance(locator, Mapping) else {}
    matched_expression = str(mention["matchedExpression"])
    return {
        # Compatibility keys retained for downstream presentation/export only.
        "effect": display_label,
        "text": str(mention["rawText"]),
        "matched_keywords": [matched_expression],
        "source_type": str(mention["sourceAssetType"]),
        "source_label": "V2页面宣传线索",
        "content_origin": "seller_managed",
        "source_path": str(locator.get("sourcePath") or ""),
        "line_number": locator.get("lineNumber"),
        # These identities make Claim, rather than legacy Effect, authoritative.
        "claimMentionId": str(mention["claimMentionId"]),
        "claimType": str(mention["claimType"]),
        "claimDisplayLabel": display_label,
        "expressionId": str(mention["expressionId"]),
        "matchedExpression": matched_expression,
        "evidenceId": str(mention["evidenceId"]),
    }


def bridge_claim_analysis(claim_analysis: Mapping[str, Any]) -> ClaimInspectionBridgeResult:
    """Bridge exact governed Claim expressions into existing Risk categories."""

    taxonomy = load_claim_taxonomy()
    validated = validate_claim_analysis(dict(claim_analysis), taxonomy=taxonomy)
    config = load_claim_inspection_bridge_config()
    display_labels = _claim_display_labels(taxonomy)
    mapping_by_expression = {
        str(item["expression_id"]): item for item in config["mappings"]
    }

    accumulators: dict[str, dict[str, Any]] = {}
    unmapped: list[UnmappedClaimEvidence] = []
    for mention in validated["claimMentions"]:
        claim_type = str(mention["claimType"])
        display_label = display_labels.get(claim_type, claim_type)
        base = _base_claim_evidence(mention, display_label=display_label)
        mapping = mapping_by_expression.get(str(mention["expressionId"]))
        if mapping is None:
            unmapped.append(
                {
                    **base,
                    "unmapped_keywords": [str(mention["matchedExpression"])],
                    "reason": "no_governed_claim_inspection_bridge",
                }
            )
            continue

        risk_category = str(mapping["risk_category"])
        accumulator = accumulators.setdefault(
            risk_category,
            {"mapping_ids": set(), "trigger_evidence": []},
        )
        accumulator["mapping_ids"].add(str(mapping["bridge_mapping_id"]))
        accumulator["trigger_evidence"].append(
            {
                **base,
                "bridge_matched_keywords": [str(mention["matchedExpression"])],
            }
        )

    risk_signals: list[ClaimRiskSignal] = []
    for risk_category in sorted(accumulators):
        accumulator = accumulators[risk_category]
        risk_signals.append(
            {
                "risk_category": risk_category,
                "bridge_mapping_ids": sorted(accumulator["mapping_ids"]),
                "trigger_evidence": accumulator["trigger_evidence"],
            }
        )

    return ClaimInspectionBridgeResult(
        bridge_id=str(config["bridge_id"]),
        bridge_version=str(config["bridge_version"]),
        risk_signals=risk_signals,
        unmapped_evidence=unmapped,
    )
