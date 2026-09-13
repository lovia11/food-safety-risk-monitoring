import logging
import tempfile
import unittest
from pathlib import Path

from src.runtime import read_json
from src.search_query_validation import (
    remaining_queries_for_resume,
    run_search_validation,
    select_queries,
)


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


class PartialFailureCollector(FakeCollector):
    def collect(self, keyword, candidate_limit, detail_limit):
        if keyword == "失败词":
            raise RuntimeError("offline fixture failure")
        return super().collect(keyword, candidate_limit, detail_limit)


class DuplicateCollector(FakeCollector):
    def collect(self, keyword, candidate_limit, detail_limit):
        payload = super().collect(keyword, candidate_limit, detail_limit)
        payload["candidates"] = [
            {
                "rank": 1,
                "product_id": "1001",
                "product_name": "第一件商品",
                "shop_name": "店铺一",
                "price_text": "12.80",
                "region": "浙江",
                "source_product_url": "https://item.taobao.com/item.htm?id=1001",
            },
            {
                "rank": 2,
                "product_id": "1001",
                "product_name": "第一件商品（重复推荐位）",
                "shop_name": "店铺一",
                "price_text": "13.00",
                "source_product_url": "https://item.taobao.com/item.htm?id=1001",
            },
            {
                "rank": 3,
                "product_id": "1002",
                "product_name": "第二件商品",
                "shop_name": "店铺二",
            },
        ]
        return payload


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
                    "validation_status": "candidate_unvalidated",
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
            manifest = read_json(run_root / "manifest.json")
            query_artifact = read_json(run_root / "queries" / "query-1.json")
            review_queue = read_json(run_root / "review" / "query-1.json")
            review_markdown = (run_root / "review" / "query-1.md").read_text(
                encoding="utf-8"
            )
        self.assertEqual(summary["status"], "completed")
        self.assertEqual(len(saved["results"][0]["titles"]), 10)
        self.assertEqual(saved["results"][0]["actual_candidates"], 10)
        self.assertEqual(saved["results"][0]["stop_reason"], "candidate_limit_reached")
        self.assertEqual(FakeCollector.calls[0][1:3], (10, 1))
        self.assertTrue(manifest["searchOnly"])
        self.assertEqual(manifest["status"], "complete")
        self.assertEqual(manifest["collectionRawLimit"], 10)
        self.assertEqual(manifest["evaluationSampleSize"], 10)
        self.assertEqual(manifest["queries"][0]["artifact"], "queries/query-1.json")
        self.assertEqual(query_artifact["batchId"], "pilot-run")
        self.assertEqual(query_artifact["uniqueResultCount"], 10)
        self.assertEqual(query_artifact["rawResultCount"], 10)
        self.assertEqual(query_artifact["duplicateCount"], 0)
        self.assertEqual(len(query_artifact["resultCards"]), 10)
        self.assertEqual(
            set(query_artifact["labels"]),
            {
                "relevant_food",
                "raw_medicinal_or_nonfood_scope",
                "non_food",
                "ambiguous",
                "duplicate",
            },
        )
        self.assertIsNone(query_artifact["decision"])
        self.assertTrue(
            all(item["reviewedLabel"] is None for item in review_queue["results"])
        )
        self.assertTrue(
            all(item["reviewedAt"] is None for item in review_queue["results"])
        )
        self.assertTrue(
            all(item["reviewNote"] is None for item in review_queue["results"])
        )
        self.assertIn("人工标签和复核说明保持空白", review_markdown)

    def test_review_queue_uses_stable_product_id_dedup_and_original_rank(self):
        selected = [
            (
                {"target_id": "target-1", "standard_name": "山楂"},
                {
                    "query_id": "query-1",
                    "query_text": "山楂",
                    "query_source": "standard_name",
                    "validation_status": "candidate_unvalidated",
                },
            )
        ]
        with tempfile.TemporaryDirectory() as temporary:
            run_root = Path(temporary) / "dedup-batch"
            run_search_validation(
                context=object(),
                run_root=run_root,
                logger=logging.getLogger("search-query-validation-dedup-test"),
                selected=selected,
                candidate_limit=15,
                pause_seconds=0,
                collector_factory=DuplicateCollector,
            )
            query_artifact = read_json(run_root / "queries" / "query-1.json")
            review_queue = read_json(run_root / "review" / "query-1.json")
        self.assertEqual(query_artifact["rawResultCount"], 3)
        self.assertEqual(query_artifact["uniqueResultCount"], 2)
        self.assertEqual(query_artifact["duplicateCount"], 1)
        self.assertEqual(
            [item["rank"] for item in query_artifact["resultCards"]],
            [1, 3],
        )
        self.assertEqual(
            query_artifact["resultCards"][0]["duplicateOccurrences"][0]["rank"],
            2,
        )
        self.assertIsNone(review_queue["results"][0]["reviewedLabel"])

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

    def test_partial_failure_is_auditable_and_resume_skips_completed_query(self):
        selected = [
            (
                {"target_id": "target-1", "standard_name": "对象一"},
                {
                    "query_id": "query-ok",
                    "query_text": "成功词",
                    "query_source": "standard_name",
                    "validation_status": "candidate_unvalidated",
                },
            ),
            (
                {"target_id": "target-2", "standard_name": "对象二"},
                {
                    "query_id": "query-failed",
                    "query_text": "失败词",
                    "query_source": "standard_name",
                    "validation_status": "candidate_unvalidated",
                },
            ),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            run_root = Path(temporary) / "partial-batch"
            summary = run_search_validation(
                context=object(),
                run_root=run_root,
                logger=logging.getLogger("search-query-validation-partial-test"),
                selected=selected,
                candidate_limit=10,
                pause_seconds=0,
                collector_factory=PartialFailureCollector,
            )
            remaining = remaining_queries_for_resume(run_root, selected)
            manifest = read_json(run_root / "manifest.json")
            failed = read_json(run_root / "queries" / "query-failed.json")
        self.assertEqual(summary["status"], "stopped_after_failure")
        self.assertEqual(len(manifest["queries"]), 2)
        self.assertEqual(failed["executionStatus"], "failed")
        self.assertEqual(failed["error"]["type"], "RuntimeError")
        self.assertEqual(manifest["status"], "partial")
        self.assertEqual([query["query_id"] for _, query in remaining], ["query-failed"])


if __name__ == "__main__":
    unittest.main()
