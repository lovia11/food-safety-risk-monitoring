import tempfile
import unittest
from pathlib import Path

from src.claim_analysis import derive_claim_analysis, load_claim_taxonomy
from src.inspection_runtime import InspectionAnalysisUnavailableError, InspectionRuntime
from src.runtime import write_json


def legacy_weight_loss_analysis() -> dict:
    return {
        "product_id": "product-123",
        "product_name": "测试商品",
        "product_url": "https://item.example/product-123",
        "detected_effects": ["减脂"],
        "evidence_details": [
            {
                "effect": "减脂",
                "text": "页面宣称帮助减肥",
                "matched_keywords": ["减肥"],
                "source_type": "dom_product",
                "source_label": "当前商品 DOM",
                "content_origin": "seller_managed",
                "source_path": "dom_text.txt",
                "line_number": 1,
            }
        ],
    }


def claim_analysis(text: str) -> dict:
    return derive_claim_analysis(
        "run:product-123",
        [
            {
                "evidenceId": "evidence-claim-1",
                "snapshotId": "run:product-123",
                "text": text,
                "sourceType": "ocr_detail_image",
                "contentOrigin": "seller_managed",
                "sourcePath": "ocr/original_001.txt",
                "lineNumber": 1,
            }
        ],
        load_claim_taxonomy(),
        generated_at="2026-09-18T00:00:00+08:00",
    )


class InspectionRuntimeClaimV2Test(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.output_root = self.root / "output"
        self.product_root = self.output_root / "run" / "products" / "product-123"
        write_json(self.product_root / "analysis.json", legacy_weight_loss_analysis())
        self.runtime = InspectionRuntime.create(self.output_root)

    def tearDown(self):
        self.temporary.cleanup()

    def test_claim_artifact_is_authoritative_over_legacy_effect(self):
        write_json(self.product_root / "claim_analysis.json", claim_analysis("难入睡"))

        result = self.runtime.generate(self.product_root)

        self.assertEqual(result["risk_findings"], [])
        self.assertEqual(len(result["unmapped_evidence"]), 1)
        self.assertEqual(result["unmapped_evidence"][0]["claimType"], "sleep_related")
        self.assertEqual(
            result["unmapped_evidence"][0]["reason"],
            "no_governed_claim_inspection_bridge",
        )

    def test_governed_claim_expression_reaches_existing_knowledge_chain(self):
        write_json(self.product_root / "claim_analysis.json", claim_analysis("帮助减肥"))

        result = self.runtime.generate(self.product_root)

        finding = next(
            item for item in result["risk_findings"]
            if item["risk_category"] == "weight_loss"
        )
        self.assertEqual(finding["trigger_evidence"][0]["claimType"], "weight_management")
        self.assertEqual(finding["trigger_evidence"][0]["matchedExpression"], "减肥")

    def test_governed_sleep_claim_reaches_historical_screening_chain(self):
        write_json(
            self.product_root / "claim_analysis.json",
            claim_analysis("有助于改善睡眠"),
        )

        result = self.runtime.generate(self.product_root)

        finding = next(
            item for item in result["risk_findings"]
            if item["risk_category"] == "sleep_aid"
        )
        self.assertEqual(finding["temporal_basis"], "historical_reference_only")
        self.assertTrue(finding["historical_reference_mapping_ids"])
        self.assertIn("历史中央专项抽检", finding["historical_reference_note"])
        self.assertEqual(
            {item["matchedExpression"] for item in finding["trigger_evidence"]},
            {"改善睡眠", "有助于改善睡眠"},
        )
        self.assertGreaterEqual(len(finding["substance_follow_ups"]), 20)
        names = {
            item["canonical_name"] for item in finding["substance_follow_ups"]
        }
        self.assertIn("艾司唑仑", names)
        self.assertIn("地西泮", names)
        self.assertIn("褪黑素", names)
        melatonin = next(
            item for item in finding["substance_follow_ups"]
            if item["canonical_name"] == "褪黑素"
        )
        self.assertEqual(
            melatonin["follow_up_status"],
            "regulatory_context_review",
        )

    def test_explicit_sleep_benefit_claim_reaches_screening_chain(self):
        write_json(
            self.product_root / "claim_analysis.json",
            claim_analysis("安睡整个夜晚"),
        )

        result = self.runtime.generate(self.product_root)

        finding = next(
            item for item in result["risk_findings"]
            if item["risk_category"] == "sleep_aid"
        )
        self.assertEqual(finding["temporal_basis"], "historical_reference_only")
        self.assertIn(
            "安睡",
            {
                item["matchedExpression"]
                for item in finding["trigger_evidence"]
            },
        )
        self.assertGreaterEqual(len(finding["substance_follow_ups"]), 20)

    def test_broad_sleep_symptom_claim_stays_unmapped(self):
        write_json(self.product_root / "claim_analysis.json", claim_analysis("难入睡"))

        result = self.runtime.generate(self.product_root)

        self.assertEqual(result["risk_findings"], [])
        self.assertEqual(len(result["unmapped_evidence"]), 1)
        self.assertEqual(
            result["unmapped_evidence"][0]["matchedExpression"],
            "入睡",
        )

    def test_legacy_effect_is_used_only_when_claim_artifact_is_absent(self):
        result = self.runtime.generate(self.product_root)

        self.assertTrue(
            any(item["risk_category"] == "weight_loss" for item in result["risk_findings"])
        )
        self.assertNotIn("claimType", result["risk_findings"][0]["trigger_evidence"][0])

    def test_claim_failure_does_not_silently_fall_back_to_legacy_effect(self):
        write_json(
            self.product_root / "claim_analysis_error.json",
            {"status": "error", "message": "injected claim failure"},
        )

        with self.assertRaisesRegex(
            InspectionAnalysisUnavailableError,
            "不回退使用旧版功效分析",
        ):
            self.runtime.generate(self.product_root)


if __name__ == "__main__":
    unittest.main()
