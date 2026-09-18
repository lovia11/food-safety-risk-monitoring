import copy
import unittest
from pathlib import Path

from src.claim_analysis import derive_claim_analysis, load_claim_taxonomy
from src.claim_inspection_bridge import (
    ClaimInspectionBridgeConfigValidationError,
    bridge_claim_analysis,
    load_claim_inspection_bridge_config,
    validate_claim_inspection_bridge_config,
)
from src.runtime import read_json


class ClaimInspectionBridgeTest(unittest.TestCase):
    def setUp(self):
        self.taxonomy = load_claim_taxonomy()

    def _analysis(self, text: str) -> dict:
        return derive_claim_analysis(
            "snapshot-1",
            [
                {
                    "evidenceId": "evidence-1",
                    "snapshotId": "snapshot-1",
                    "text": text,
                    "sourceType": "ocr_detail_image",
                    "contentOrigin": "seller_managed",
                    "sourcePath": "ocr/original_001.txt",
                    "lineNumber": 1,
                }
            ],
            self.taxonomy,
            generated_at="2026-09-18T00:00:00+08:00",
        )

    @staticmethod
    def _historical_risk_reference() -> tuple[dict, str]:
        risk_reference = read_json(Path("config/risk_substance_reference.json"))
        mapping_id = "test-sleep-historical-sedative-group"
        risk_reference["mappings"].append(
            {
                "mapping_id": mapping_id,
                "dataset_id": risk_reference["dataset_id"],
                "risk_category": "sleep_aid",
                "risk_label": "睡眠相关宣传",
                "target_type": "substance_group",
                "substance_id": None,
                "target_group_label": "镇静催眠类物质",
                "evidence_grade": "B",
                "basis_type": "historical_sampling_plan",
                "temporal_status": "historical",
                "product_scope": "改善睡眠类样品",
                "source_name": "历史中央专项抽检测试来源",
                "source_reference": "https://example.invalid/historical-sleep",
                "source_date": "2014-01-01",
                "source_basis_text": "历史抽检资料将改善睡眠类样品与镇静催眠类检测项目关联。",
                "note": "synthetic B3 governance fixture; not production knowledge",
            }
        )
        return risk_reference, mapping_id

    @staticmethod
    def _historical_bridge_mapping(reference_mapping_id: str) -> dict:
        return {
            "bridge_mapping_id": "test-sleep-historical-bridge",
            "claim_type": "sleep_related",
            "expression_id": "legacy-sleep-related-rushui",
            "matched_expression": "入睡",
            "risk_category": "sleep_aid",
            "reference_mapping_id": reference_mapping_id,
            "authorized_historical_mapping_ids": [reference_mapping_id],
            "temporal_policy": "historical_reference_allowed",
            "governance_basis": "direct_verified_reference",
            "migrated_from_bridge_mapping_id": None,
            "note": "synthetic B3 governance fixture",
        }

    def test_bridge_preserves_three_current_relations_and_governs_sleep_scope(self):
        config = load_claim_inspection_bridge_config()

        self.assertEqual(len(config["mappings"]), 22)
        current = [
            item for item in config["mappings"]
            if item["temporal_policy"] == "current_only"
        ]
        historical = [
            item for item in config["mappings"]
            if item["temporal_policy"] == "historical_reference_allowed"
        ]
        self.assertEqual(
            {item["matched_expression"] for item in current},
            {"减肥", "壮阳", "补肾"},
        )
        self.assertEqual(
            {item["matched_expression"] for item in historical},
            {
                "改善睡眠", "有助于改善睡眠", "助眠", "安睡", "好眠", "深睡", "催眠",
                "辅助降血压", "调节血压", "有助于维持血压健康水平", "降压",
                "辅助降血脂", "调节血脂", "有助于维持血脂（胆固醇/甘油三酯）健康水平", "降脂",
                "辅助降血糖", "调节血糖", "有助于维持血糖健康水平", "降糖",
            },
        )
        self.assertEqual(
            {
                item["matched_expression"]
                for item in historical
                if item["governance_basis"] == "governed_functional_scope"
            },
            {"助眠", "安睡", "好眠", "深睡", "催眠", "降压", "降脂", "降糖"},
        )
        self.assertEqual(
            set(config["metadata"]["expression_scope_policy"]["claim_only_sleep_expressions"]),
            {"睡眠", "入睡", "失眠", "辗转反侧", "安神"},
        )
        cardiometabolic = config["metadata"]["cardiometabolic_expression_scope_policy"]["directions"]
        self.assertEqual(
            set(cardiometabolic["blood_pressure"]["claim_only"]),
            {"血压", "高血压"},
        )
        self.assertEqual(
            set(cardiometabolic["blood_lipid"]["claim_only"]),
            {"血脂", "胆固醇", "有助于维持血脂健康水平"},
        )
        self.assertEqual(cardiometabolic["blood_glucose"]["claim_only"], [])
        self.assertTrue(
            all(item["authorized_historical_mapping_ids"] == [] for item in current)
        )
        self.assertTrue(
            all(
                item["reference_mapping_id"]
                in item["authorized_historical_mapping_ids"]
                for item in historical
            )
        )
        self.assertTrue(config["metadata"]["historical_reference_disclosure"])

    def test_historical_reference_requires_explicit_per_mapping_permission(self):
        risk_reference, reference_mapping_id = self._historical_risk_reference()
        bridge = copy.deepcopy(load_claim_inspection_bridge_config())
        mapping = self._historical_bridge_mapping(reference_mapping_id)
        bridge["mappings"].append(mapping)

        validated = validate_claim_inspection_bridge_config(
            bridge,
            taxonomy=self.taxonomy,
            risk_reference_config=risk_reference,
        )
        historical = next(
            item
            for item in validated["mappings"]
            if item["bridge_mapping_id"] == "test-sleep-historical-bridge"
        )
        self.assertEqual(
            historical["temporal_policy"], "historical_reference_allowed"
        )

        bridge["mappings"][-1]["temporal_policy"] = "current_only"
        with self.assertRaises(ClaimInspectionBridgeConfigValidationError):
            validate_claim_inspection_bridge_config(
                bridge,
                taxonomy=self.taxonomy,
                risk_reference_config=risk_reference,
            )

    def test_historical_permission_rejects_non_historical_sampling_basis(self):
        risk_reference, reference_mapping_id = self._historical_risk_reference()
        risk_reference["mappings"][-1]["basis_type"] = "official_case"
        bridge = copy.deepcopy(load_claim_inspection_bridge_config())
        bridge["mappings"].append(
            self._historical_bridge_mapping(reference_mapping_id)
        )

        with self.assertRaises(ClaimInspectionBridgeConfigValidationError):
            validate_claim_inspection_bridge_config(
                bridge,
                taxonomy=self.taxonomy,
                risk_reference_config=risk_reference,
            )

    def test_historical_allowlist_must_include_primary_reference(self):
        risk_reference, reference_mapping_id = self._historical_risk_reference()
        bridge = copy.deepcopy(load_claim_inspection_bridge_config())
        mapping = self._historical_bridge_mapping(reference_mapping_id)
        mapping["authorized_historical_mapping_ids"] = []
        bridge["mappings"].append(mapping)

        with self.assertRaises(ClaimInspectionBridgeConfigValidationError):
            validate_claim_inspection_bridge_config(
                bridge,
                taxonomy=self.taxonomy,
                risk_reference_config=risk_reference,
            )

    def test_current_mapping_cannot_authorize_historical_ids(self):
        bridge = copy.deepcopy(load_claim_inspection_bridge_config())
        bridge["mappings"][0]["authorized_historical_mapping_ids"] = [
            "synthetic-historical-id"
        ]

        with self.assertRaises(ClaimInspectionBridgeConfigValidationError):
            validate_claim_inspection_bridge_config(
                bridge,
                taxonomy=self.taxonomy,
            )

    def test_current_plus_historical_policy_keeps_current_primary_and_legacy_provenance(self):
        risk_reference = read_json(Path("config/risk_substance_reference.json"))
        historical_id = "test-weight-historical-group"
        risk_reference["mappings"].append(
            {
                "mapping_id": historical_id,
                "dataset_id": risk_reference["dataset_id"],
                "risk_category": "weight_loss",
                "risk_label": "减肥宣传",
                "target_type": "substance_group",
                "substance_id": None,
                "target_group_label": "历史减肥筛查组",
                "evidence_grade": "B",
                "basis_type": "historical_sampling_plan",
                "temporal_status": "historical",
                "product_scope": "减肥类样品",
                "source_name": "历史中央抽检测试来源",
                "source_reference": "https://example.invalid/historical-weight",
                "source_date": "2014-01-01",
                "source_basis_text": "历史减肥筛查来源原文",
                "note": "synthetic current-plus-history fixture",
            }
        )
        bridge = copy.deepcopy(load_claim_inspection_bridge_config())
        mapping = next(
            item for item in bridge["mappings"]
            if item["matched_expression"] == "减肥"
        )
        mapping["temporal_policy"] = "current_plus_historical_reference_allowed"
        mapping["authorized_historical_mapping_ids"] = [historical_id]

        validated = validate_claim_inspection_bridge_config(
            bridge,
            taxonomy=self.taxonomy,
            risk_reference_config=risk_reference,
        )
        result = next(
            item for item in validated["mappings"]
            if item["matched_expression"] == "减肥"
        )
        self.assertEqual(
            result["reference_mapping_id"],
            "weight-loss-sibutramine-group-cn-2025",
        )
        self.assertEqual(
            result["migrated_from_bridge_mapping_id"],
            "jianfei-to-weight-loss",
        )
        self.assertEqual(
            result["authorized_historical_mapping_ids"],
            [historical_id],
        )

    def test_current_plus_historical_policy_requires_explicit_allowlist(self):
        bridge = copy.deepcopy(load_claim_inspection_bridge_config())
        mapping = next(
            item for item in bridge["mappings"]
            if item["matched_expression"] == "减肥"
        )
        mapping["temporal_policy"] = "current_plus_historical_reference_allowed"
        mapping["authorized_historical_mapping_ids"] = []

        with self.assertRaises(ClaimInspectionBridgeConfigValidationError):
            validate_claim_inspection_bridge_config(
                bridge,
                taxonomy=self.taxonomy,
            )

    def test_current_plus_historical_policy_rejects_mixed_historical_cohorts(self):
        risk_reference = read_json(Path("config/risk_substance_reference.json"))
        ids = []
        for index, source in enumerate(("historical-a", "historical-b"), start=1):
            mapping_id = f"test-weight-historical-{index}"
            ids.append(mapping_id)
            risk_reference["mappings"].append(
                {
                    "mapping_id": mapping_id,
                    "dataset_id": risk_reference["dataset_id"],
                    "risk_category": "weight_loss",
                    "risk_label": "减肥宣传",
                    "target_type": "substance_group",
                    "substance_id": None,
                    "target_group_label": f"历史减肥筛查组{index}",
                    "evidence_grade": "B",
                    "basis_type": "historical_sampling_plan",
                    "temporal_status": "historical",
                    "product_scope": "减肥类样品",
                    "source_name": f"历史来源{index}",
                    "source_reference": f"https://example.invalid/{source}",
                    "source_date": f"201{index}-01-01",
                    "source_basis_text": "历史来源原文",
                    "note": "synthetic mixed cohort fixture",
                }
            )
        bridge = copy.deepcopy(load_claim_inspection_bridge_config())
        mapping = next(
            item for item in bridge["mappings"]
            if item["matched_expression"] == "减肥"
        )
        mapping["temporal_policy"] = "current_plus_historical_reference_allowed"
        mapping["authorized_historical_mapping_ids"] = ids

        with self.assertRaises(ClaimInspectionBridgeConfigValidationError):
            validate_claim_inspection_bridge_config(
                bridge,
                taxonomy=self.taxonomy,
                risk_reference_config=risk_reference,
            )

    def test_official_sleep_expression_reaches_sleep_aid_direction(self):
        result = bridge_claim_analysis(self._analysis("有助于改善睡眠"))

        self.assertEqual(len(result.risk_signals), 1)
        self.assertEqual(result.risk_signals[0]["risk_category"], "sleep_aid")
        triggers = result.risk_signals[0]["trigger_evidence"]
        self.assertTrue(all(item["claimType"] == "sleep_related" for item in triggers))
        self.assertEqual(
            {item["matchedExpression"] for item in triggers},
            {"改善睡眠", "有助于改善睡眠"},
        )
        self.assertEqual(len(result.unmapped_evidence), 1)
        self.assertEqual(result.unmapped_evidence[0]["matchedExpression"], "睡眠")
        self.assertEqual(
            result.unmapped_evidence[0]["reason"],
            "no_governed_claim_inspection_bridge",
        )

    def test_explicit_sleep_benefit_expressions_reach_sleep_aid(self):
        for expression in ("助眠", "安睡", "好眠", "深睡", "催眠"):
            with self.subTest(expression=expression):
                result = bridge_claim_analysis(self._analysis(expression))
                self.assertEqual(len(result.risk_signals), 1)
                self.assertEqual(result.risk_signals[0]["risk_category"], "sleep_aid")
                self.assertIn(
                    expression,
                    {
                        item["matchedExpression"]
                        for item in result.risk_signals[0]["trigger_evidence"]
                    },
                )

    def test_broad_or_symptom_sleep_expressions_remain_claim_only(self):
        for text, expected in (
            ("睡眠", "睡眠"),
            ("难入睡", "入睡"),
            ("失眠", "失眠"),
            ("辗转反侧", "辗转反侧"),
            ("安神", "安神"),
        ):
            with self.subTest(text=text):
                result = bridge_claim_analysis(self._analysis(text))
                self.assertEqual(result.risk_signals, [])
                self.assertEqual(len(result.unmapped_evidence), 1)
                self.assertEqual(
                    result.unmapped_evidence[0]["matchedExpression"],
                    expected,
                )
                self.assertEqual(
                    result.unmapped_evidence[0]["reason"],
                    "no_governed_claim_inspection_bridge",
                )

    def test_cardiometabolic_governed_expressions_reach_expected_directions(self):
        cases = (
            ("辅助降血压", "blood_pressure"),
            ("调节血压", "blood_pressure"),
            ("有助于维持血压健康水平", "blood_pressure"),
            ("降压", "blood_pressure"),
            ("辅助降血脂", "blood_lipid"),
            ("调节血脂", "blood_lipid"),
            ("有助于维持血脂（胆固醇/甘油三酯）健康水平", "blood_lipid"),
            ("降脂", "blood_lipid"),
            ("辅助降血糖", "blood_glucose"),
            ("调节血糖", "blood_glucose"),
            ("有助于维持血糖健康水平", "blood_glucose"),
            ("降糖", "blood_glucose"),
        )
        for expression, expected_risk in cases:
            with self.subTest(expression=expression):
                result = bridge_claim_analysis(self._analysis(expression))
                self.assertEqual(len(result.risk_signals), 1)
                self.assertEqual(result.risk_signals[0]["risk_category"], expected_risk)
                self.assertIn(
                    expression,
                    {
                        item["matchedExpression"]
                        for item in result.risk_signals[0]["trigger_evidence"]
                    },
                )

    def test_cardiometabolic_broad_expressions_remain_claim_only(self):
        cases = (
            ("血压", "blood_pressure_related", "血压"),
            ("高血压", "blood_pressure_related", "高血压"),
            ("血脂", "blood_lipid_related", "血脂"),
            ("胆固醇", "blood_lipid_related", "胆固醇"),
            ("有助于维持血脂健康水平", "blood_lipid_related", "有助于维持血脂健康水平"),
        )
        for text, expected_claim_type, expected_expression in cases:
            with self.subTest(text=text):
                result = bridge_claim_analysis(self._analysis(text))
                self.assertEqual(result.risk_signals, [])
                self.assertGreaterEqual(len(result.unmapped_evidence), 1)
                self.assertTrue(
                    any(
                        item["claimType"] == expected_claim_type
                        and item["matchedExpression"] == expected_expression
                        and item["reason"] == "no_governed_claim_inspection_bridge"
                        for item in result.unmapped_evidence
                    )
                )

    def test_jianfei_reaches_existing_weight_loss_direction(self):
        result = bridge_claim_analysis(self._analysis("帮助减肥"))

        self.assertEqual(len(result.risk_signals), 1)
        self.assertEqual(result.risk_signals[0]["risk_category"], "weight_loss")
        trigger = result.risk_signals[0]["trigger_evidence"][0]
        self.assertEqual(trigger["claimType"], "weight_management")
        self.assertEqual(trigger["matchedExpression"], "减肥")
        self.assertEqual(trigger["content_origin"], "seller_managed")
        self.assertEqual(result.unmapped_evidence, [])

    def test_other_weight_expression_is_not_expanded_by_claim_type(self):
        result = bridge_claim_analysis(self._analysis("帮助减脂"))

        self.assertEqual(result.risk_signals, [])
        self.assertEqual(len(result.unmapped_evidence), 1)
        self.assertEqual(result.unmapped_evidence[0]["matchedExpression"], "减脂")
        self.assertEqual(
            result.unmapped_evidence[0]["reason"],
            "no_governed_claim_inspection_bridge",
        )

    def test_zhuangyang_and_bushen_share_existing_male_function_direction(self):
        result = bridge_claim_analysis(self._analysis("壮阳补肾"))

        self.assertEqual(len(result.risk_signals), 1)
        self.assertEqual(result.risk_signals[0]["risk_category"], "male_function")
        self.assertEqual(
            {item["matchedExpression"] for item in result.risk_signals[0]["trigger_evidence"]},
            {"壮阳", "补肾"},
        )
        self.assertEqual(result.unmapped_evidence, [])

    def test_sleep_claim_remains_explicit_knowledge_gap(self):
        result = bridge_claim_analysis(self._analysis("难入睡"))

        self.assertEqual(result.risk_signals, [])
        self.assertEqual(len(result.unmapped_evidence), 1)
        gap = result.unmapped_evidence[0]
        self.assertEqual(gap["claimType"], "sleep_related")
        self.assertEqual(gap["claimDisplayLabel"], "睡眠相关宣传")
        self.assertEqual(gap["matchedExpression"], "入睡")
        self.assertEqual(gap["reason"], "no_governed_claim_inspection_bridge")


if __name__ == "__main__":
    unittest.main()
