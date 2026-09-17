import unittest

from src.claim_analysis import derive_claim_analysis, load_claim_taxonomy
from src.claim_inspection_bridge import (
    bridge_claim_analysis,
    load_claim_inspection_bridge_config,
)


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

    def test_bridge_contains_only_three_migrated_verified_relations(self):
        config = load_claim_inspection_bridge_config()

        self.assertEqual(len(config["mappings"]), 3)
        self.assertEqual(
            {item["matched_expression"] for item in config["mappings"]},
            {"减肥", "壮阳", "补肾"},
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
