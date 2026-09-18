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

        self.assertEqual(len(config["mappings"]), 10)
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
            {"改善睡眠", "有助于改善睡眠", "助眠", "安睡", "好眠", "深睡", "催眠"},
        )
        self.assertEqual(
            {
                item["matched_expression"]
                for item in historical
                if item["governance_basis"] == "governed_functional_scope"
            },
            {"助眠", "安睡", "好眠", "深睡", "催眠"},
        )
        self.assertEqual(
            set(config["metadata"]["expression_scope_policy"]["claim_only_sleep_expressions"]),
            {"睡眠", "入睡", "失眠", "辗转反侧", "安神"},
        )
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
