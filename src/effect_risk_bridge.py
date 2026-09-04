"""Deterministic Phase 3 evidence-to-Risk Category taxonomy bridge.

The bridge consumes existing Phase 3 ``evidence_details`` only.  It does not
read OCR files, rerun keyword detection, infer synonyms, resolve inspection
knowledge, query methods, or generate inspection recommendations.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, TypedDict

from src.risk_substance_reference import (
    RiskSubstanceConfigValidationError,
    validate_risk_substance_config,
)
from src.runtime import read_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BRIDGE_CONFIG = PROJECT_ROOT / "config" / "effect_risk_bridge.json"
DEFAULT_EFFECT_CONFIG = PROJECT_ROOT / "config" / "effect_keywords.json"
DEFAULT_RISK_REFERENCE_CONFIG = (
    PROJECT_ROOT / "config" / "risk_substance_reference.json"
)

_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_TOP_LEVEL_FIELDS = {
    "schema_version",
    "bridge_id",
    "bridge_version",
    "description",
    "mappings",
}
_MAPPING_FIELDS = {
    "bridge_mapping_id",
    "effect_label",
    "matched_keyword",
    "risk_category",
    "reference_mapping_id",
    "note",
}
_EVIDENCE_FIELDS = (
    "effect",
    "text",
    "matched_keywords",
    "source_type",
    "source_label",
    "content_origin",
    "source_path",
    "line_number",
)


class EffectRiskBridgeConfigValidationError(ValueError):
    """The bridge config is invalid or inconsistent with its references."""


class TriggerEvidence(TypedDict):
    effect: str
    text: str
    matched_keywords: list[str]
    bridge_matched_keywords: list[str]
    source_type: str
    source_label: str
    content_origin: str
    source_path: str
    line_number: int


class RiskSignal(TypedDict):
    risk_category: str
    bridge_mapping_ids: list[str]
    trigger_evidence: list[TriggerEvidence]


class UnmappedEvidence(TypedDict):
    effect: str
    text: str
    matched_keywords: list[str]
    unmapped_keywords: list[str]
    source_type: str
    source_label: str
    content_origin: str
    source_path: str
    line_number: int
    reason: str


@dataclass(frozen=True)
class RiskSignalBridgeResult(Mapping[str, Any]):
    """Stable JSON-compatible output from evidence taxonomy bridging."""

    bridge_id: str
    bridge_version: str
    risk_signals: list[RiskSignal]
    unmapped_evidence: list[UnmappedEvidence]

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


def _object(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise EffectRiskBridgeConfigValidationError(f"{field}必须是JSON对象")
    return value


def _array(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise EffectRiskBridgeConfigValidationError(f"{field}必须是数组")
    return value


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EffectRiskBridgeConfigValidationError(f"{field}不能为空")
    return value.strip()


def _identifier(value: Any, field: str) -> str:
    text = _required_text(value, field)
    if not _IDENTIFIER_PATTERN.fullmatch(text):
        raise EffectRiskBridgeConfigValidationError(
            f"{field}只能包含字母、数字、点、下划线、冒号和连字符"
        )
    return text


def _require_exact_fields(
    item: Mapping[str, Any], expected: set[str], field: str
) -> None:
    missing = sorted(expected - set(item))
    if missing:
        raise EffectRiskBridgeConfigValidationError(
            f"{field}缺少字段：{', '.join(missing)}"
        )
    unexpected = sorted(set(item) - expected)
    if unexpected:
        raise EffectRiskBridgeConfigValidationError(
            f"{field}包含未定义字段：{', '.join(unexpected)}"
        )


def _effect_categories(effect_config: Any) -> Mapping[str, list[Any]]:
    root = _object(effect_config, "effect_keywords根节点")
    categories = root.get("effect_categories")
    if not isinstance(categories, Mapping) or not categories:
        raise EffectRiskBridgeConfigValidationError(
            "effect_keywords.effect_categories必须是非空JSON对象"
        )
    for effect_label, keywords in categories.items():
        if not isinstance(effect_label, str) or not effect_label.strip():
            raise EffectRiskBridgeConfigValidationError(
                "effect_keywords中的effect label不能为空"
            )
        if not isinstance(keywords, list) or any(
            not isinstance(keyword, str) or not keyword for keyword in keywords
        ):
            raise EffectRiskBridgeConfigValidationError(
                f"effect_keywords.effect_categories.{effect_label}必须是非空字符串数组"
            )
    return categories


def validate_effect_risk_bridge_config(
    payload: Any,
    *,
    effect_config: Any | None = None,
    risk_reference_config: Any | None = None,
) -> dict[str, Any]:
    """Validate and normalize a bridge against Phase 3 and Risk references.

    When reference payloads are omitted, the committed Phase 3 effect config
    and verified Risk-Substance Reference config are loaded.  No provenance is
    copied into the normalized bridge; mappings retain only their internal
    taxonomy relation and ``reference_mapping_id``.
    """

    root = _object(payload, "Effect-Risk Bridge根节点")
    _require_exact_fields(root, _TOP_LEVEL_FIELDS, "Effect-Risk Bridge根节点")
    if root.get("schema_version") != 1 or isinstance(
        root.get("schema_version"), bool
    ):
        raise EffectRiskBridgeConfigValidationError("schema_version必须为1")

    if effect_config is None:
        effect_config = read_json(DEFAULT_EFFECT_CONFIG)
    categories = _effect_categories(effect_config)

    if risk_reference_config is None:
        risk_reference_config = read_json(DEFAULT_RISK_REFERENCE_CONFIG)
    try:
        risk_reference = validate_risk_substance_config(risk_reference_config)
    except RiskSubstanceConfigValidationError as error:
        raise EffectRiskBridgeConfigValidationError(
            f"Risk Reference配置无效：{error}"
        ) from error
    if risk_reference["dataset_status"] != "verified_reference":
        raise EffectRiskBridgeConfigValidationError(
            "Bridge只能引用dataset_status=verified_reference的Risk Mapping"
        )
    reference_by_id = {
        mapping["mapping_id"]: mapping for mapping in risk_reference["mappings"]
    }

    bridge_id = _identifier(root.get("bridge_id"), "bridge_id")
    bridge_version = _required_text(root.get("bridge_version"), "bridge_version")
    description = _required_text(root.get("description"), "description")
    mappings_raw = _array(root.get("mappings"), "mappings")

    mappings: list[dict[str, Any]] = []
    mapping_ids: set[str] = set()
    pair_categories: dict[tuple[str, str], str] = {}
    for position, value in enumerate(mappings_raw, start=1):
        item = _object(value, f"mappings[{position}]")
        _require_exact_fields(item, _MAPPING_FIELDS, f"mappings[{position}]")
        mapping_id = _identifier(
            item.get("bridge_mapping_id"),
            f"mappings[{position}].bridge_mapping_id",
        )
        if mapping_id in mapping_ids:
            raise EffectRiskBridgeConfigValidationError(
                f"bridge_mapping_id重复：{mapping_id}"
            )
        mapping_ids.add(mapping_id)

        effect_label = _required_text(
            item.get("effect_label"), f"Bridge Mapping {mapping_id} 的effect_label"
        )
        if effect_label not in categories:
            raise EffectRiskBridgeConfigValidationError(
                f"Bridge Mapping {mapping_id} 引用的effect_label不存在：{effect_label}"
            )
        matched_keyword = _required_text(
            item.get("matched_keyword"),
            f"Bridge Mapping {mapping_id} 的matched_keyword",
        )
        if matched_keyword not in categories[effect_label]:
            raise EffectRiskBridgeConfigValidationError(
                f"Bridge Mapping {mapping_id} 的matched_keyword不属于"
                f"effect_label {effect_label}：{matched_keyword}"
            )

        risk_category = _identifier(
            item.get("risk_category"),
            f"Bridge Mapping {mapping_id} 的risk_category",
        )
        reference_mapping_id = _identifier(
            item.get("reference_mapping_id"),
            f"Bridge Mapping {mapping_id} 的reference_mapping_id",
        )
        reference = reference_by_id.get(reference_mapping_id)
        if reference is None:
            raise EffectRiskBridgeConfigValidationError(
                f"Bridge Mapping {mapping_id} 引用的reference_mapping_id不存在："
                f"{reference_mapping_id}"
            )
        if reference["risk_category"] != risk_category:
            raise EffectRiskBridgeConfigValidationError(
                f"Bridge Mapping {mapping_id} 的risk_category与Reference Mapping"
                f" {reference_mapping_id} 不一致"
            )
        if reference["temporal_status"] != "current":
            raise EffectRiskBridgeConfigValidationError(
                f"Bridge Mapping {mapping_id} 不能引用historical Reference Mapping："
                f"{reference_mapping_id}"
            )

        pair = (effect_label, matched_keyword)
        previous_category = pair_categories.get(pair)
        if previous_category is not None and previous_category != risk_category:
            raise EffectRiskBridgeConfigValidationError(
                "同一(effect_label, matched_keyword)不能映射到两个不同"
                f"risk_category：{effect_label} + {matched_keyword}"
            )
        pair_categories[pair] = risk_category
        mappings.append(
            {
                "bridge_mapping_id": mapping_id,
                "effect_label": effect_label,
                "matched_keyword": matched_keyword,
                "risk_category": risk_category,
                "reference_mapping_id": reference_mapping_id,
                "note": _required_text(
                    item.get("note"), f"Bridge Mapping {mapping_id} 的note"
                ),
            }
        )

    return {
        "schema_version": 1,
        "bridge_id": bridge_id,
        "bridge_version": bridge_version,
        "description": description,
        "mappings": mappings,
    }


def load_effect_risk_bridge_config(
    config_path: Path = DEFAULT_BRIDGE_CONFIG,
) -> dict[str, Any]:
    """Load the bridge config and validate all cross-reference identities."""

    return validate_effect_risk_bridge_config(read_json(config_path))


def _unique_in_order(values: list[Any]) -> list[Any]:
    unique: list[Any] = []
    for value in values:
        if value not in unique:
            unique.append(value)
    return unique


def _evidence_identity(item: Mapping[str, Any]) -> tuple[Any, ...]:
    return tuple(item[field] for field in _EVIDENCE_FIELDS if field != "matched_keywords")


def _base_evidence(item: Mapping[str, Any]) -> dict[str, Any]:
    return {field: item[field] for field in _EVIDENCE_FIELDS}


def bridge_analysis_evidence(
    analysis: Mapping[str, Any],
) -> RiskSignalBridgeResult:
    """Bridge exact Phase 3 ``(effect, matched_keyword)`` evidence pairs.

    Risk signals are unique and sorted by ``risk_category``.  Mapping IDs are
    sorted, while trigger evidence and keyword lists retain input order.
    Keywords without an explicit verified pair are returned as unmapped rather
    than being discarded.
    """

    if not isinstance(analysis, Mapping):
        raise TypeError("analysis must be a mapping")
    evidence_details = analysis.get("evidence_details", [])
    if evidence_details is None:
        evidence_details = []
    if not isinstance(evidence_details, list):
        raise TypeError("analysis.evidence_details must be a list")

    config = load_effect_risk_bridge_config()
    mapping_index: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for mapping in config["mappings"]:
        key = (mapping["effect_label"], mapping["matched_keyword"])
        mapping_index.setdefault(key, []).append(mapping)

    signal_accumulators: dict[str, dict[str, Any]] = {}
    unmapped_evidence: list[UnmappedEvidence] = []
    for position, raw_evidence in enumerate(evidence_details, start=1):
        if not isinstance(raw_evidence, Mapping):
            raise TypeError(f"analysis.evidence_details[{position}] must be a mapping")
        missing = [field for field in _EVIDENCE_FIELDS if field not in raw_evidence]
        if missing:
            raise ValueError(
                f"analysis.evidence_details[{position}]缺少字段：{', '.join(missing)}"
            )
        raw_keywords = raw_evidence["matched_keywords"]
        if not isinstance(raw_keywords, list):
            raise TypeError(
                f"analysis.evidence_details[{position}].matched_keywords must be a list"
            )
        keywords = _unique_in_order(raw_keywords)
        effect = raw_evidence["effect"]

        mapped_keywords: list[Any] = []
        category_matches: dict[str, dict[str, list[str]]] = {}
        for keyword in keywords:
            mappings = mapping_index.get((effect, keyword), [])
            if not mappings:
                continue
            mapped_keywords.append(keyword)
            for mapping in mappings:
                category = mapping["risk_category"]
                matched = category_matches.setdefault(
                    category, {"keywords": [], "mapping_ids": []}
                )
                if keyword not in matched["keywords"]:
                    matched["keywords"].append(keyword)
                mapping_id = mapping["bridge_mapping_id"]
                if mapping_id not in matched["mapping_ids"]:
                    matched["mapping_ids"].append(mapping_id)

        identity = _evidence_identity(raw_evidence)
        for category, matched in category_matches.items():
            signal = signal_accumulators.setdefault(
                category,
                {
                    "mapping_ids": set(),
                    "trigger_evidence": [],
                    "trigger_by_identity": {},
                },
            )
            signal["mapping_ids"].update(matched["mapping_ids"])
            trigger = signal["trigger_by_identity"].get(identity)
            if trigger is None:
                trigger = {
                    **_base_evidence(raw_evidence),
                    "matched_keywords": list(keywords),
                    "bridge_matched_keywords": list(matched["keywords"]),
                }
                signal["trigger_by_identity"][identity] = trigger
                signal["trigger_evidence"].append(trigger)
            else:
                trigger["matched_keywords"] = _unique_in_order(
                    trigger["matched_keywords"] + keywords
                )
                trigger["bridge_matched_keywords"] = _unique_in_order(
                    trigger["bridge_matched_keywords"] + matched["keywords"]
                )

        unmapped_keywords = [
            keyword for keyword in keywords if keyword not in mapped_keywords
        ]
        if unmapped_keywords or not keywords:
            base = _base_evidence(raw_evidence)
            unmapped_evidence.append(
                {
                    **base,
                    "matched_keywords": list(keywords),
                    "unmapped_keywords": unmapped_keywords,
                    "reason": "no_verified_keyword_bridge",
                }
            )

    risk_signals: list[RiskSignal] = []
    for risk_category in sorted(signal_accumulators):
        signal = signal_accumulators[risk_category]
        risk_signals.append(
            {
                "risk_category": risk_category,
                "bridge_mapping_ids": sorted(signal["mapping_ids"]),
                "trigger_evidence": signal["trigger_evidence"],
            }
        )

    return RiskSignalBridgeResult(
        bridge_id=config["bridge_id"],
        bridge_version=config["bridge_version"],
        risk_signals=risk_signals,
        unmapped_evidence=unmapped_evidence,
    )
