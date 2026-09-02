import logging
import tempfile
import unittest
from pathlib import Path

from src.runtime import read_json
from src.search_query_validation import run_search_validation, select_queries


class FakeCollector:
    calls = []

    def __init__(self, **kwargs):
        self.run_root = kwargs["run_root"]

    def collect(self, keyword, candidate_limit, detail_limit):
        self.calls.append((keyword, candidate_limit, detail_limit, self.run_root))
        return {
            "raw_card_count": 12,
            "search_stop_reason": "candidate_limit_reached",
            "selector_health": {"status": "healthy"},
            "candidates": [
                {
                    "rank": index,
                    "product_id": str(index),
                    "product_name": f"{keyword}商品{index}",
                    "shop_name": "测试店铺",
                    "region": "浙江",
                }
                for index in range(1, candidate_limit + 1)
            ],
        }


class SearchQueryValidationTest(unittest.TestCase):
    def setUp(self):
        FakeCollector.calls = []

    def test_select_queries_preserves_target_and_query_order(self):
        config = {
            "targets": [
                {
                    "target_id": "target-b",
                    "queries": [{"query_id": "q-b", "order": 1}],
                },
                {
                    "target_id": "target-a",
                    "queries": [
                        {"query_id": "q-a2", "order": 2},
                        {"query_id": "q-a1", "order": 1},
                    ],
                },
            ]
        }
        selected = select_queries(config, ("target-a", "target-b"))
        self.assertEqual(
            [query["query_id"] for _, query in selected],
            ["q-a1", "q-a2", "q-b"],
        )

    def test_search_only_runner_records_titles_and_diagnostics(self):
        selected = [
            (
                {"target_id": "target-1", "standard_name": "酸枣仁"},
                {
                    "query_id": "query-1",
                    "query_text": "酸枣仁",
                    "query_source": "standard_name",
                    "validation_status": "unvalidated",
                },
            )
        ]
        with tempfile.TemporaryDirectory() as temporary:
            run_root = Path(temporary) / "pilot-run"
            summary = run_search_validation(
                context=object(),
                run_root=run_root,
                logger=logging.getLogger("search-query-validation-test"),
                selected=selected,
                candidate_limit=10,
                pause_seconds=0,
                collector_factory=FakeCollector,
            )
            saved = read_json(run_root / "query_validation_results.json")
        self.assertEqual(summary["status"], "completed")
        self.assertEqual(len(saved["results"][0]["titles"]), 10)
        self.assertEqual(saved["results"][0]["actual_candidates"], 10)
        self.assertEqual(saved["results"][0]["stop_reason"], "candidate_limit_reached")
        self.assertEqual(FakeCollector.calls[0][1:3], (10, 1))

    def test_unknown_query_id_is_rejected_before_browser_use(self):
        config = {
            "targets": [
                {
                    "target_id": "target-1",
                    "queries": [{"query_id": "query-1", "order": 1}],
                }
            ]
        }
        with self.assertRaisesRegex(ValueError, "不存在SearchQuery"):
            select_queries(config, ("target-1",), {"missing"})


if __name__ == "__main__":
    unittest.main()
