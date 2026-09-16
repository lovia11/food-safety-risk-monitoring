import logging
import tempfile
import unittest
from pathlib import Path

from src.discovery import DiscoveryCoordinator, select_detail_candidates
from src.runtime import read_json


class FakeCollector:
    responses = {}
    calls = []

    def __init__(self, **kwargs):
        self.run_root = kwargs["run_root"]

    def collect(self, keyword, candidate_limit, detail_limit=None):
        self.__class__.calls.append(
            (keyword, candidate_limit, detail_limit, self.run_root)
        )
        return self.__class__.responses[keyword]


def candidate(product_id, rank, product_name=None, shop_name=""):
    return {
        "product_id": product_id,
        "product_name": product_name or f"商品{product_id}",
        "product_url": f"https://item.taobao.com/item.htm?id={product_id}",
        "shop_name": shop_name,
        "rank": rank,
    }


class DiscoveryCoordinatorTest(unittest.TestCase):
    def setUp(self):
        FakeCollector.calls = []
        FakeCollector.responses = {
            "酸枣仁": {
                "candidates": [candidate("A", 1), candidate("B", 2)],
                "raw_card_count": 4,
                "search_stop_reason": "candidate_limit_reached",
                "completed_at": "2026-09-02T10:00:00+08:00",
            },
            "酸枣仁茶": {
                "candidates": [candidate("B", 1), candidate("C", 2)],
                "raw_card_count": 5,
                "search_stop_reason": "candidate_limit_reached",
                "completed_at": "2026-09-02T10:01:00+08:00",
            },
        }

    def test_query_order_dedupe_hits_and_limits_are_deterministic(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_root = Path(temporary) / "monitor_run"
            result = DiscoveryCoordinator(
                context=object(),
                run_root=run_root,
                logger=logging.getLogger("test.discovery"),
                collector_factory=FakeCollector,
                clue_keywords=("助眠",),
            ).discover(
                target={"target_id": "target-1", "standard_name": "酸枣仁"},
                queries=[
                    {
                        "query_id": "tea",
                        "query_text": "酸枣仁茶",
                        "order": 2,
                        "enabled": True,
                        "validation_status": "search_validated",
                    },
                    {
                        "query_id": "base",
                        "query_text": "酸枣仁",
                        "order": 1,
                        "enabled": True,
                        "validation_status": "search_validated",
                    },
                ],
                per_query_candidate_limit=10,
                detail_limit=2,
            )

            self.assertEqual([call[:3] for call in FakeCollector.calls], [
                ("酸枣仁", 10, 2),
                ("酸枣仁茶", 10, 2),
            ])
            self.assertEqual([item["product_id"] for item in result["candidates"]], ["A", "B", "C"])
            self.assertEqual([item["rank"] for item in result["candidates"]], [1, 2, 3])
            self.assertEqual(result["selected_for_detail"], 2)
            self.assertEqual(result["selection_strategy"]["name"], "balanced_exposure_clue_exploration_v2")
            self.assertEqual(
                [item["product_id"] for item in result["candidates"] if item["selected_for_detail"]],
                ["A", "B"],
            )
            self.assertEqual(result["target_id"], "target-1")
            self.assertEqual(result["target_name"], "酸枣仁")
            self.assertEqual(len(result["candidate_hits"]), 4)
            self.assertTrue(all(item["task_id"] == "monitor_run" for item in result["candidate_hits"]))
            self.assertTrue(all(item["query_id"] and item["query_text"] for item in result["candidate_hits"]))
            self.assertEqual(
                [item["query_id"] for item in result["candidate_hits"] if item["product_id"] == "B"],
                ["base", "tea"],
            )
            saved = read_json(run_root / "search" / "discovery_summary.json")
            self.assertEqual(saved["target_id"], "target-1")
            self.assertEqual(saved["deduplicated_count"], 3)
            self.assertEqual(saved["query_results"][0]["raw_card_count"], 4)

    def test_balanced_selection_uses_exposure_visible_clues_and_exploration(self):
        source = [
            candidate("A", 1, "普通酸枣仁A"),
            candidate("B", 2, "普通酸枣仁B"),
            candidate("C", 3, "普通酸枣仁C"),
            candidate("D", 4, "酸枣仁助眠茶"),
            candidate("E", 5, "酸枣仁深睡膏"),
        ]
        selected, strategy = select_detail_candidates(
            source,
            detail_limit=5,
            target_id="target-sleep",
            clue_keywords=("助眠", "深睡"),
        )

        selected_items = [item for item in selected if item["selected_for_detail"]]
        self.assertEqual(len(selected_items), 5)
        self.assertEqual(strategy["exposure_target"], 2)
        self.assertEqual(strategy["clue_target"], 2)
        self.assertEqual(strategy["exploration_target"], 1)
        by_id = {item["product_id"]: item for item in selected_items}
        self.assertEqual(by_id["A"]["selection_group"], "exposure")
        self.assertEqual(by_id["B"]["selection_group"], "exposure")
        self.assertEqual(by_id["D"]["selection_group"], "visible_clue")
        self.assertEqual(by_id["E"]["selection_group"], "visible_clue")
        self.assertEqual(by_id["C"]["selection_group"], "exploration")
        self.assertIn("助眠", by_id["D"]["title_clue_terms"])
        self.assertIn("深睡", by_id["E"]["title_clue_terms"])

    def test_diversity_skips_near_duplicate_shop_variants_when_alternatives_exist(self):
        source = [
            candidate("A", 1, "酸枣仁茶500g家庭装", "同一店铺"),
            candidate("B", 2, "酸枣仁茶1000g家庭装", "同一店铺"),
            candidate("C", 3, "酸枣仁膏传统风味", "另一店铺"),
            candidate("D", 4, "酸枣仁粉冲饮装", "第三店铺"),
            candidate("E", 5, "酸枣仁颗粒食品", "第四店铺"),
            candidate("F", 6, "酸枣仁饮品", "第五店铺"),
        ]
        selected, strategy = select_detail_candidates(
            source,
            detail_limit=4,
            target_id="target-diversity",
            clue_keywords=(),
        )

        selected_items = [item for item in selected if item["selected_for_detail"]]
        selected_ids = [item["product_id"] for item in selected_items]
        exposure_ids = [
            item["product_id"]
            for item in selected_items
            if item["selection_group"] == "exposure"
        ]
        self.assertIn("A", exposure_ids)
        self.assertIn("C", exposure_ids)
        self.assertNotIn("B", exposure_ids)
        self.assertEqual(len(selected_ids), 4)
        self.assertEqual(strategy["diversity"]["max_per_shop"], 2)
        self.assertEqual(strategy["diversity"]["relaxed_fill_count"], 0)

    def test_diversity_relaxes_only_when_needed_to_reach_detail_limit(self):
        source = [
            candidate("A", 1, "酸枣仁茶500g家庭装", "同一店铺"),
            candidate("B", 2, "酸枣仁茶1000g家庭装", "同一店铺"),
            candidate("C", 3, "酸枣仁茶1500g家庭装", "同一店铺"),
        ]
        selected, strategy = select_detail_candidates(
            source,
            detail_limit=3,
            target_id="target-narrow",
            clue_keywords=(),
        )

        selected_items = [item for item in selected if item["selected_for_detail"]]
        self.assertEqual(len(selected_items), 3)
        self.assertGreater(strategy["diversity"]["relaxed_fill_count"], 0)
        self.assertTrue(
            any(
                "放宽多样性限制" in reason
                for item in selected_items
                for reason in item["selection_reasons"]
            )
        )

    def test_disabled_query_is_not_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = DiscoveryCoordinator(
                context=object(),
                run_root=Path(temporary) / "run",
                logger=logging.getLogger("test.discovery.disabled"),
                collector_factory=FakeCollector,
                clue_keywords=(),
            ).discover(
                target={"target_id": "target-1", "standard_name": "酸枣仁"},
                queries=[
                    {"query_id": "base", "query_text": "酸枣仁", "order": 1, "enabled": True, "validation_status": "search_validated"},
                    {"query_id": "off", "query_text": "未执行", "order": 2, "enabled": False, "validation_status": "search_validated"},
                    {"query_id": "candidate", "query_text": "候选词", "order": 3, "enabled": False, "validation_status": "candidate_unvalidated"},
                    {"query_id": "paused", "query_text": "暂缓词", "order": 4, "enabled": False, "validation_status": "paused_scope_issue"},
                ],
                per_query_candidate_limit=3,
                detail_limit=1,
            )
            self.assertEqual([item["query_text"] for item in result["query_results"]], ["酸枣仁"])


if __name__ == "__main__":
    unittest.main()
