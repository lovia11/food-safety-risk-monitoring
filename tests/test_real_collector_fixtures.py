import unittest
from pathlib import Path

from src.phase4_search_snapshot import (
    canonical_product_url,
    deduplicate_cards,
    parse_snapshot,
)
from src.runtime import extract_product_id, file_sha256, read_json


REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_SEARCH_HTML = REPO_ROOT / "manual_input" / "taobao_search.html"
REAL_BATCH_ROOT = REPO_ROOT / "output" / "20260817T181659_batch"
REAL_SEARCH_SHA256 = "e018be570d6829f97692b9c9b116565c91cd313f22622383b3fe718321d10126"


class RealCollectorFixtureRegressionTest(unittest.TestCase):
    """Freeze contracts observed in saved real Taobao artifacts; never uses network."""

    @classmethod
    def setUpClass(cls):
        document = REAL_SEARCH_HTML.read_text(encoding="utf-8")
        cls.cards, cls.selectors = parse_snapshot(document)
        cls.unique_cards = deduplicate_cards(cls.cards)

    def test_saved_search_fixture_identity_and_fixed_card_count(self):
        self.assertEqual(file_sha256(REAL_SEARCH_HTML), REAL_SEARCH_SHA256)
        self.assertEqual(len(self.cards), 46)
        self.assertEqual(len(self.unique_cards), 46)

    def test_saved_search_preserves_order_and_observed_fields(self):
        self.assertEqual(
            [item["product_id"] for item in self.unique_cards[:3]],
            ["606232126144", "600949052422", "634471255780"],
        )
        for item in self.unique_cards:
            self.assertTrue(item["product_name"])
            self.assertTrue(item["shop_name"])
            self.assertTrue(item["region"])
        self.assertTrue(self.selectors["title"])
        self.assertTrue(self.selectors["shop"])
        self.assertTrue(self.selectors["region"])

    def test_product_id_and_url_normalization_on_saved_real_cards(self):
        first_tmall = next(
            item
            for item in self.unique_cards
            if "detail.tmall.com" in item["source_product_url"]
        )
        product_id = first_tmall["product_id"]
        self.assertEqual(extract_product_id(first_tmall["source_product_url"]), product_id)
        self.assertEqual(
            canonical_product_url(first_tmall["source_product_url"], product_id),
            f"https://detail.tmall.com/item.htm?id={product_id}",
        )

    def test_saved_analysis_keeps_content_origin_attribution(self):
        analysis = read_json(
            REAL_BATCH_ROOT / "products" / "600949052422" / "analysis.json"
        )
        origins = {item["content_origin"] for item in analysis["evidence_details"]}
        self.assertEqual(analysis["detected_effects"], ["助眠"])
        self.assertEqual(origins, {"seller_managed", "user_generated"})
        self.assertTrue(analysis["review_required"])

    def test_saved_recommendation_evidence_remains_excluded(self):
        analysis = read_json(
            REAL_BATCH_ROOT / "products" / "606232126144" / "analysis.json"
        )
        self.assertEqual(len(analysis["excluded_evidence"]), 2)
        self.assertTrue(
            all(
                item["source_type"] == "dom_recommendation"
                for item in analysis["excluded_evidence"]
            )
        )

    def test_saved_batch_state_is_ordered_and_resumable(self):
        states = read_json(REAL_BATCH_ROOT / "batch_state.json")
        self.assertEqual(len(states), 20)
        self.assertEqual([item["rank"] for item in states], list(range(1, 21)))
        self.assertEqual(len({item["product_id"] for item in states}), 20)
        self.assertTrue(
            all(
                item["status"]
                in {
                    "pending_detail_collection",
                    "detail_collected",
                    "success",
                    "failed_collection",
                    "failed_processing",
                }
                for item in states
            )
        )


if __name__ == "__main__":
    unittest.main()
