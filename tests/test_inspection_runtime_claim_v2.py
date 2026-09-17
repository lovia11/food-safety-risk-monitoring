import tempfile
import unittest
from pathlib import Path

from src.claim_analysis import derive_claim_analysis, load_claim_taxonomy
from src.inspection_runtime import InspectionRuntime
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

    def test_legacy_effect_is_used_only_when_claim_artifact_is_absent(self):
        result = self.runtime.generate(self.product_root)

        self.assertTrue(
            any(item["risk_category"] == "weight_loss" for item in result["risk_findings"])
        )
        self.assertNotIn("claimType", result["risk_findings"][0]["trigger_evidence"][0])


if __name__ == "__main__":
    unittest.main()
