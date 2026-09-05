import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.data_store import DataStore
from src.inspection_runtime import (
    INSPECTION_CONTEXT_FILE,
    INSPECTION_RECOMMENDATION_FILE,
    InspectionRuntime,
    bootstrap_inspection_references,
    database_path_for_output_root,
)
from src.runtime import read_json, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INSPECTION_CONFIG = PROJECT_ROOT / "config" / "inspection_reference.json"
RISK_CONFIG = PROJECT_ROOT / "config" / "risk_substance_reference.json"


def weight_loss_analysis() -> dict:
    return {
        "product_id": "product-123",
        "product_name": "测试减肥饼干",
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


class InspectionRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.output_root = self.root / "output"
        self.product_root = self.output_root / "run" / "products" / "product-123"
        write_json(self.product_root / "analysis.json", weight_loss_analysis())
        self.runtime = InspectionRuntime.create(self.output_root)

    def tearDown(self):
        self.temporary.cleanup()

    def test_missing_context_uses_explicit_unknown_context(self):
        result = self.runtime.generate(self.product_root)

        self.assertEqual(
            result["product_context"],
            {
                "product_category": None,
                "product_form": None,
                "confirmed_ingredient_contexts": [],
                "context_evidence": [],
            },
        )
        self.assertTrue(
            (self.product_root / INSPECTION_RECOMMENDATION_FILE).is_file()
        )

    def test_exact_context_generates_seller_testing_suggestion(self):
        write_json(
            self.product_root / INSPECTION_CONTEXT_FILE,
            {
                "product_category": "饼干",
                "product_form": None,
                "confirmed_ingredient_contexts": [],
                "context_evidence": [],
            },
        )

        result = self.runtime.generate(self.product_root)
        finding = next(
            item for item in result["risk_findings"]
            if item["risk_category"] == "weight_loss"
        )
        follow_up = finding["substance_follow_ups"][0]

        self.assertEqual(finding["evidence_qualification"], "seller_managed_primary")
        self.assertEqual(follow_up["follow_up_status"], "suggest_testing")
        self.assertIn(
            "BJS 201701",
            [item["method_no"] for item in follow_up["suggested_methods"]],
        )

    def test_recommendation_is_atomically_written_as_complete_json(self):
        expected = self.runtime.generate(self.product_root)
        destination = self.product_root / INSPECTION_RECOMMENDATION_FILE

        self.assertEqual(read_json(destination), expected)
        self.assertEqual(list(self.product_root.glob(".*.tmp")), [])

    def test_reference_bootstrap_is_idempotent_and_schema_stays_seven(self):
        store = DataStore(self.root / "second.db", self.output_root)
        first = bootstrap_inspection_references(
            store, INSPECTION_CONFIG, RISK_CONFIG
        )
        second = bootstrap_inspection_references(
            store, INSPECTION_CONFIG, RISK_CONFIG
        )

        self.assertEqual(first, second)
        self.assertEqual(store.table_counts()["inspection_methods"], 5)
        self.assertEqual(store.table_counts()["risk_substance_mappings"], 8)
        with sqlite3.connect(store.database_path) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 7)

    def test_context_options_come_from_verified_sqlite_reference(self):
        options = self.runtime.store.list_inspection_context_options()

        self.assertIn("饼干", options["product_categories"])
        self.assertIn("片剂", options["product_forms"])
        self.assertTrue(all(options.values()))
        self.assertNotIn("", options["product_categories"])

    def test_custom_output_root_uses_existing_local_api_database_rule(self):
        self.assertEqual(
            database_path_for_output_root(self.root / "custom-output"),
            self.root / "data" / "app.db",
        )


if __name__ == "__main__":
    unittest.main()
