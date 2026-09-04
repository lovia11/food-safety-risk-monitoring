import copy
import unittest
from pathlib import Path

from src.effect_risk_bridge import (
    EffectRiskBridgeConfigValidationError,
    RiskSignalBridgeResult,
    bridge_analysis_evidence,
    load_effect_risk_bridge_config,
    validate_effect_risk_bridge_config,
)
from src.runtime import read_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BRIDGE_CONFIG = PROJECT_ROOT / "config" / "effect_risk_bridge.json"
EFFECT_CONFIG = PROJECT_ROOT / "config" / "effect_keywords.json"
RISK_REFERENCE_CONFIG = PROJECT_ROOT / "config" / "risk_substance_reference.json"

EXPECTED_MAPPINGS = {
    ("减脂", "减肥", "weight_loss"): (
        "jianfei-to-weight-loss",
        "weight-loss-sibutramine-group-cn-2025",
    ),
    ("男性相关", "壮阳", "male_function"): (
        "zhuangyang-to-male-function",
        "male-function-nafei-lafei-group-cn-2025",
    ),
    ("男性相关", "补肾", "male_function"): (
        "bushen-to-male-function",
        "male-function-nafei-lafei-group-cn-2025",
    ),
}


def evidence(
    effect: str,
    keywords: list[str],
    *,
    text: str | None = None,
    content_origin: str = "seller_managed",
    line_number: int = 1,
) -> dict:
    user_generated = content_origin == "user_generated"
    return {
        "effect": effect,
        "text": text or "、".join(keywords),
        "matched_keywords": keywords,
        "source_type": "dom_qa" if user_generated else "dom_product",
        "source_label": "用户问答" if user_generated else "当前商品 DOM",
        "content_origin": content_origin,
        "source_path": "dom_text.txt",
        "line_number": line_number,
    }


def bridge_one(item: dict, *, detected_effects: list[str] | None = None):
    return bridge_analysis_evidence(
        {
            "detected_effects": detected_effects or [item["effect"]],
            "evidence_details": [item],
        }
    )


class EffectRiskBridgeRuntimeTest(unittest.TestCase):
    def test_jianfei_keyword_bridges_to_weight_loss_and_preserves_seller_origin(self):
        item = evidence("减脂", ["减肥"], text="帮助减肥")
        result = bridge_one(item)

        self.assertIsInstance(result, RiskSignalBridgeResult)
        self.assertEqual(result.bridge_id, "phase3-effect-risk-bridge")
        self.assertEqual(result.bridge_version, "2026.09-d2")
        self.assertEqual(len(result.risk_signals), 1)
        signal = result.risk_signals[0]
        self.assertEqual(signal["risk_category"], "weight_loss")
        self.assertEqual(
            signal["bridge_mapping_ids"], ["jianfei-to-weight-loss"]
        )
        self.assertEqual(signal["trigger_evidence"][0]["content_origin"], "seller_managed")
        self.assertEqual(signal["trigger_evidence"][0]["text"], "帮助减肥")
        self.assertEqual(signal["trigger_evidence"][0]["bridge_matched_keywords"], ["减肥"])
        self.assertEqual(result.unmapped_evidence, [])

    def test_ranzhi_keyword_is_explicitly_unmapped(self):
        result = bridge_one(evidence("减脂", ["燃脂"]), detected_effects=["减脂"])
        self.assertEqual(result.risk_signals, [])
        self.assertEqual(result.unmapped_evidence[0]["unmapped_keywords"], ["燃脂"])

    def test_shoushen_keyword_is_explicitly_unmapped(self):
        result = bridge_one(evidence("减脂", ["瘦身"]))
        self.assertEqual(result.risk_signals, [])
        self.assertEqual(result.unmapped_evidence[0]["unmapped_keywords"], ["瘦身"])

    def test_zhuangyang_keyword_bridges_to_male_function(self):
        result = bridge_one(evidence("男性相关", ["壮阳"]))
        self.assertEqual(
            result.risk_signals[0]["risk_category"], "male_function"
        )
        self.assertEqual(
            result.risk_signals[0]["bridge_mapping_ids"],
            ["zhuangyang-to-male-function"],
        )

    def test_bushen_keyword_bridges_to_male_function(self):
        result = bridge_one(evidence("男性相关", ["补肾"]))
        self.assertEqual(
            result.risk_signals[0]["risk_category"], "male_function"
        )
        self.assertEqual(
            result.risk_signals[0]["bridge_mapping_ids"],
            ["bushen-to-male-function"],
        )

    def test_zaoxie_keyword_is_explicitly_unmapped(self):
        result = bridge_one(evidence("男性相关", ["早泄"]))
        self.assertEqual(result.risk_signals, [])
        self.assertEqual(result.unmapped_evidence[0]["unmapped_keywords"], ["早泄"])

    def test_zhumian_keyword_is_explicitly_unmapped(self):
        result = bridge_one(evidence("助眠", ["助眠"]))
        self.assertEqual(result.risk_signals, [])
        self.assertEqual(result.unmapped_evidence[0]["unmapped_keywords"], ["助眠"])

    def test_one_evidence_with_both_keywords_produces_one_deterministic_signal(self):
        item = evidence("男性相关", ["补肾", "壮阳"], text="补肾壮阳")
        result = bridge_one(item)

        self.assertEqual(len(result.risk_signals), 1)
        signal = result.risk_signals[0]
        self.assertEqual(signal["risk_category"], "male_function")
        self.assertEqual(
            signal["bridge_mapping_ids"],
            ["bushen-to-male-function", "zhuangyang-to-male-function"],
        )
        self.assertEqual(len(signal["trigger_evidence"]), 1)
        self.assertEqual(
            signal["trigger_evidence"][0]["bridge_matched_keywords"],
            ["补肾", "壮阳"],
        )

    def test_multiple_evidence_units_share_one_risk_signal_and_remain_complete(self):
        seller = evidence("男性相关", ["补肾"], text="补肾配方", line_number=3)
        ugc = evidence(
            "男性相关",
            ["壮阳"],
            text="有人说壮阳",
            content_origin="user_generated",
            line_number=9,
        )
        result = bridge_analysis_evidence(
            {"detected_effects": ["男性相关"], "evidence_details": [seller, ugc]}
        )

        self.assertEqual(len(result.risk_signals), 1)
        signal = result.risk_signals[0]
        self.assertEqual(len(signal["trigger_evidence"]), 2)
        self.assertEqual(signal["trigger_evidence"][0]["source_path"], "dom_text.txt")
        self.assertEqual(signal["trigger_evidence"][0]["line_number"], 3)
        self.assertEqual(signal["trigger_evidence"][1]["text"], "有人说壮阳")
        self.assertEqual(signal["trigger_evidence"][1]["content_origin"], "user_generated")
        self.assertEqual(signal["trigger_evidence"][1]["source_type"], "dom_qa")

    def test_user_generated_weight_loss_evidence_is_not_filtered(self):
        item = evidence(
            "减脂",
            ["减肥"],
            text="评论里说可以减肥",
            content_origin="user_generated",
        )
        result = bridge_one(item)
        trigger = result.risk_signals[0]["trigger_evidence"][0]
        self.assertEqual(trigger["content_origin"], "user_generated")
        self.assertEqual(trigger["source_label"], "用户问答")

    def test_mapped_and_unmapped_keywords_are_both_retained(self):
        item = evidence("男性相关", ["补肾", "早泄"], text="补肾早泄")
        result = bridge_one(item)

        self.assertEqual(len(result.risk_signals), 1)
        trigger = result.risk_signals[0]["trigger_evidence"][0]
        self.assertEqual(trigger["matched_keywords"], ["补肾", "早泄"])
        self.assertEqual(trigger["bridge_matched_keywords"], ["补肾"])
        self.assertEqual(len(result.unmapped_evidence), 1)
        unmapped = result.unmapped_evidence[0]
        self.assertEqual(unmapped["matched_keywords"], ["补肾", "早泄"])
        self.assertEqual(unmapped["unmapped_keywords"], ["早泄"])
        self.assertEqual(unmapped["reason"], "no_verified_keyword_bridge")

    def test_unmapped_evidence_keeps_all_provenance_fields(self):
        item = evidence(
            "减脂",
            ["燃脂"],
            text="评论称燃脂",
            content_origin="user_generated",
            line_number=18,
        )
        unmapped = bridge_one(item).unmapped_evidence[0]
        self.assertEqual(
            unmapped,
            {
                **item,
                "unmapped_keywords": ["燃脂"],
                "reason": "no_verified_keyword_bridge",
            },
        )

    def test_empty_evidence_returns_empty_result_arrays(self):
        result = bridge_analysis_evidence(
            {"detected_effects": ["减脂"], "evidence_details": []}
        )
        self.assertEqual(result.risk_signals, [])
        self.assertEqual(result.unmapped_evidence, [])

    def test_unknown_effect_is_unmapped_without_error(self):
        item = evidence("未知功效", ["减肥"], text="未知分类中的减肥")
        result = bridge_one(item)
        self.assertEqual(result.risk_signals, [])
        self.assertEqual(result.unmapped_evidence[0]["effect"], "未知功效")
        self.assertEqual(result.unmapped_evidence[0]["unmapped_keywords"], ["减肥"])

    def test_matching_is_exact_not_substring_based(self):
        result = bridge_one(evidence("减脂", ["帮助减肥"]))
        self.assertEqual(result.risk_signals, [])
        self.assertEqual(
            result.unmapped_evidence[0]["unmapped_keywords"], ["帮助减肥"]
        )


class EffectRiskBridgeValidationTest(unittest.TestCase):
    def setUp(self):
        self.bridge = read_json(BRIDGE_CONFIG)
        self.effects = read_json(EFFECT_CONFIG)
        self.risk_reference = read_json(RISK_REFERENCE_CONFIG)

    def validate(self, bridge: dict | None = None, risk_reference: dict | None = None):
        return validate_effect_risk_bridge_config(
            bridge if bridge is not None else self.bridge,
            effect_config=self.effects,
            risk_reference_config=(
                risk_reference if risk_reference is not None else self.risk_reference
            ),
        )

    def test_formal_bridge_config_passes_cross_reference_validation(self):
        self.assertEqual(self.validate(), load_effect_risk_bridge_config(BRIDGE_CONFIG))

    def test_missing_effect_label_is_rejected(self):
        self.bridge["mappings"][0]["effect_label"] = "不存在分类"
        with self.assertRaisesRegex(
            EffectRiskBridgeConfigValidationError, "effect_label不存在"
        ):
            self.validate()

    def test_keyword_outside_effect_label_is_rejected(self):
        self.bridge["mappings"][0]["matched_keyword"] = "壮阳"
        with self.assertRaisesRegex(
            EffectRiskBridgeConfigValidationError, "matched_keyword不属于"
        ):
            self.validate()

    def test_missing_reference_mapping_id_is_rejected(self):
        self.bridge["mappings"][0]["reference_mapping_id"] = "does-not-exist"
        with self.assertRaisesRegex(
            EffectRiskBridgeConfigValidationError, "reference_mapping_id不存在"
        ):
            self.validate()

    def test_reference_risk_category_mismatch_is_rejected(self):
        self.bridge["mappings"][0]["risk_category"] = "male_function"
        with self.assertRaisesRegex(
            EffectRiskBridgeConfigValidationError, "risk_category与Reference"
        ):
            self.validate()

    def test_historical_reference_mapping_is_rejected(self):
        reference = next(
            item
            for item in self.risk_reference["mappings"]
            if item["mapping_id"] == "weight-loss-sibutramine-group-cn-2025"
        )
        reference["evidence_grade"] = "B"
        reference["basis_type"] = "official_case"
        reference["temporal_status"] = "historical"
        with self.assertRaisesRegex(
            EffectRiskBridgeConfigValidationError, "historical Reference Mapping"
        ):
            self.validate(risk_reference=self.risk_reference)

    def test_non_verified_risk_dataset_is_rejected(self):
        self.risk_reference["dataset_status"] = "development_seed"
        self.risk_reference["verified_at"] = None
        with self.assertRaisesRegex(
            EffectRiskBridgeConfigValidationError,
            "dataset_status=verified_reference",
        ):
            self.validate(risk_reference=self.risk_reference)

    def test_duplicate_bridge_mapping_id_is_rejected(self):
        self.bridge["mappings"].append(copy.deepcopy(self.bridge["mappings"][0]))
        with self.assertRaisesRegex(
            EffectRiskBridgeConfigValidationError, "bridge_mapping_id重复"
        ):
            self.validate()

    def test_duplicate_effect_keyword_pair_cannot_map_to_two_categories(self):
        duplicate = copy.deepcopy(self.bridge["mappings"][0])
        duplicate.update(
            {
                "bridge_mapping_id": "duplicate-pair-to-male-function",
                "risk_category": "male_function",
                "reference_mapping_id": "male-function-nafei-lafei-group-cn-2025",
            }
        )
        self.bridge["mappings"].append(duplicate)
        with self.assertRaisesRegex(
            EffectRiskBridgeConfigValidationError, "不能映射到两个不同"
        ):
            self.validate()

    def test_bridge_mapping_rejects_copied_reference_provenance(self):
        self.bridge["mappings"][0]["source_reference"] = "should-not-be-copied"
        with self.assertRaisesRegex(
            EffectRiskBridgeConfigValidationError, "未定义字段"
        ):
            self.validate()


class VerifiedEffectRiskBridgeDataTest(unittest.TestCase):
    def test_formal_identity_version_and_exactly_three_mappings_are_locked(self):
        payload = load_effect_risk_bridge_config(BRIDGE_CONFIG)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["bridge_id"], "phase3-effect-risk-bridge")
        self.assertEqual(payload["bridge_version"], "2026.09-d2")
        self.assertEqual(len(payload["mappings"]), 3)

        actual = {
            (
                mapping["effect_label"],
                mapping["matched_keyword"],
                mapping["risk_category"],
            ): (
                mapping["bridge_mapping_id"],
                mapping["reference_mapping_id"],
            )
            for mapping in payload["mappings"]
        }
        self.assertEqual(actual, EXPECTED_MAPPINGS)

    def test_no_other_current_effect_keyword_is_auto_bridged(self):
        effects = read_json(EFFECT_CONFIG)["effect_categories"]
        configured_pairs = {
            (mapping["effect_label"], mapping["matched_keyword"])
            for mapping in load_effect_risk_bridge_config(BRIDGE_CONFIG)["mappings"]
        }
        expected_pairs = {
            (effect, keyword) for effect, keyword, _category in EXPECTED_MAPPINGS
        }
        self.assertEqual(configured_pairs, expected_pairs)

        all_effect_pairs = {
            (effect, keyword)
            for effect, keywords in effects.items()
            for keyword in keywords
        }
        self.assertEqual(all_effect_pairs & configured_pairs, expected_pairs)
        self.assertNotIn(("助眠", "助眠"), configured_pairs)
        self.assertNotIn(("降压", "降压"), configured_pairs)
        self.assertNotIn(("降脂", "降脂"), configured_pairs)
        self.assertNotIn(("减脂", "燃脂"), configured_pairs)
        self.assertNotIn(("男性相关", "早泄"), configured_pairs)
        self.assertFalse(any(effect == "抗疲劳" for effect, _ in configured_pairs))

    def test_bridge_contains_only_internal_taxonomy_fields(self):
        payload = read_json(BRIDGE_CONFIG)
        expected_fields = {
            "bridge_mapping_id",
            "effect_label",
            "matched_keyword",
            "risk_category",
            "reference_mapping_id",
            "note",
        }
        for mapping in payload["mappings"]:
            self.assertEqual(set(mapping), expected_fields)
            self.assertNotIn("source_reference", mapping)
            self.assertNotIn("source_date", mapping)
            self.assertNotIn("source_basis_text", mapping)
            self.assertNotIn("evidence_grade", mapping)


if __name__ == "__main__":
    unittest.main()
