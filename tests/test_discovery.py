import logging
import tempfile
import unittest
from pathlib import Path

from src.discovery import DiscoveryCoordinator
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


def candidate(product_id, rank):
    return {
        "product_id": product_id,
        "product_name": f"商品{product_id}",
        "product_url": f"https://item.taobao.com/item.htm?id={product_id}",
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
            ).discover(
                target={"target_id": "target-1", "standard_name": "酸枣仁"},
                queries=[
                    {
                        "query_id": "tea",
                        "query_text": "酸枣仁茶",
                        "order": 2,
                        "enabled": True,
                    },
                    {
                        "query_id": "base",
                        "query_text": "酸枣仁",
                        "order": 1,
                        "enabled": True,
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
            self.assertEqual(len(result["candidate_hits"]), 4)
            self.assertEqual(
                [item["query_id"] for item in result["candidate_hits"] if item["product_id"] == "B"],
                ["base", "tea"],
            )
            saved = read_json(run_root / "search" / "discovery_summary.json")
            self.assertEqual(saved["deduplicated_count"], 3)
            self.assertEqual(saved["query_results"][0]["raw_card_count"], 4)

    def test_disabled_query_is_not_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = DiscoveryCoordinator(
                context=object(),
                run_root=Path(temporary) / "run",
                logger=logging.getLogger("test.discovery.disabled"),
                collector_factory=FakeCollector,
            ).discover(
                target={"target_id": "target-1", "standard_name": "酸枣仁"},
                queries=[
                    {"query_id": "base", "query_text": "酸枣仁", "order": 1},
                    {"query_id": "off", "query_text": "未执行", "order": 2, "enabled": False},
                ],
                per_query_candidate_limit=3,
                detail_limit=1,
            )
            self.assertEqual([item["query_text"] for item in result["query_results"]], ["酸枣仁"])


if __name__ == "__main__":
    unittest.main()
