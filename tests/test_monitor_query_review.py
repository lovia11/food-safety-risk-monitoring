import tempfile
import unittest
from pathlib import Path

from src.monitor_query_validation import (
    calculate_review_metrics,
    finalize_review_queue,
    normalize_review_label,
    normalize_validation_decision,
    review_label_zh,
)
from src.runtime import read_json, write_json
from tools.finalize_monitor_query_reviews import finalize_batch, sha256_file


def review_queue(result_count=11):
    return {
        "batchId": "batch-1",
        "targetId": "target-1",
        "queryId": "query-1",
        "queryText": "山楂",
        "reviewStatus": "pending_manual_review",
        "results": [
            {
                "rank": rank,
                "productId": str(1000 + rank),
                "title": f"商品{rank}",
                "shop": "测试店铺",
                "price": "10.00",
                "cardMetadata": {"searchRegion": "浙江"},
                "duplicateOccurrences": [],
                "rawArtifactRefs": ["raw/search_candidates.json"],
                "reviewedLabel": None,
                "reviewedAt": None,
                "reviewNote": None,
            }
            for rank in range(1, result_count + 1)
        ],
    }


class MonitorQueryReviewTest(unittest.TestCase):
    def test_chinese_aliases_normalize_to_stable_english_enums(self):
        self.assertEqual(normalize_review_label("食品相关"), "relevant_food")
        self.assertEqual(
            normalize_review_label("药材/非食品监管范围"),
            "raw_medicinal_or_nonfood_scope",
        )
        self.assertEqual(review_label_zh("ambiguous"), "信息不足，无法判断")
        self.assertEqual(normalize_validation_decision("暂缓启用"), "hold")
        self.assertEqual(normalize_validation_decision("promote"), "promote")

    def test_metrics_skip_ambiguous_and_take_next_assessable_rank(self):
        rows = review_queue()["results"]
        rows[0]["reviewedLabel"] = "信息不足，无法判断"
        for row in rows[1:]:
            row["reviewedLabel"] = "食品相关"
        metrics = calculate_review_metrics(rows)
        self.assertEqual(metrics["evaluationRanks"], list(range(2, 12)))
        self.assertEqual(metrics["assessableCount"], 10)
        self.assertEqual(metrics["relevantCount"], 10)
        self.assertEqual(metrics["ambiguousSkipped"], 1)
        self.assertEqual(metrics["relevanceRate"], 1.0)

    def test_lotus_metrics_skip_rank_four_and_use_rank_eleven(self):
        rows = review_queue()["results"]
        for row in rows:
            rank = row["rank"]
            if rank == 1:
                row["reviewedLabel"] = "raw_medicinal_or_nonfood_scope"
            elif rank == 4:
                row["reviewedLabel"] = "ambiguous"
            else:
                row["reviewedLabel"] = "relevant_food"
        metrics = calculate_review_metrics(rows)
        self.assertEqual(metrics["evaluationRanks"], [1, 2, 3, 5, 6, 7, 8, 9, 10, 11])
        self.assertEqual(metrics["assessableCount"], 10)
        self.assertEqual(metrics["relevantCount"], 9)
        self.assertEqual(metrics["rawMedicinalOrNonfoodScopeCount"], 1)
        self.assertEqual(metrics["ambiguousSkipped"], 1)
        self.assertEqual(metrics["relevanceRate"], 0.9)

    def test_refined_lily_metrics_skip_rank_eight_and_promote(self):
        assignments = []
        for rank in range(1, 12):
            if rank == 8:
                label = "ambiguous"
            elif rank == 9:
                label = "raw_medicinal_or_nonfood_scope"
            else:
                label = "relevant_food"
            assignments.append({"rank": rank, "label": label})
        reviewed = finalize_review_queue(
            review_queue(),
            assignments=assignments,
            decision="promote",
            decision_note="食用百合通过固定Gate。",
            systematic_scope_issue=False,
            observed_product_forms=[],
            reviewed_at="2026-09-14T02:47:03+08:00",
        )
        metrics = reviewed["metrics"]
        self.assertEqual(metrics["evaluationRanks"], [1, 2, 3, 4, 5, 6, 7, 9, 10, 11])
        self.assertEqual(metrics["assessableCount"], 10)
        self.assertEqual(metrics["relevantCount"], 9)
        self.assertEqual(metrics["rawMedicinalOrNonfoodScopeCount"], 1)
        self.assertEqual(metrics["nonFoodCount"], 0)
        self.assertEqual(metrics["ambiguousSkipped"], 1)
        self.assertEqual(metrics["relevanceRate"], 0.9)
        self.assertTrue(reviewed["numericGatePassed"])
        self.assertEqual(reviewed["decision"], "promote")

    def test_wave_two_b_metrics_preserve_lily_rejection_and_chrysanthemum_promotion(self):
        lily_rows = review_queue(10)["results"]
        for row in lily_rows:
            row["reviewedLabel"] = (
                "relevant_food"
                if row["rank"] in {1, 3, 5, 6, 10}
                else "raw_medicinal_or_nonfood_scope"
            )
        lily = calculate_review_metrics(lily_rows)
        self.assertEqual(lily["assessableCount"], 10)
        self.assertEqual(lily["relevantCount"], 5)
        self.assertEqual(lily["rawMedicinalOrNonfoodScopeCount"], 5)
        self.assertEqual(lily["relevanceRate"], 0.5)

        chrysanthemum_rows = review_queue(10)["results"]
        for row in chrysanthemum_rows:
            row["reviewedLabel"] = "relevant_food"
        chrysanthemum = calculate_review_metrics(chrysanthemum_rows)
        self.assertEqual(chrysanthemum["assessableCount"], 10)
        self.assertEqual(chrysanthemum["relevantCount"], 10)
        self.assertEqual(chrysanthemum["rawMedicinalOrNonfoodScopeCount"], 0)
        self.assertEqual(chrysanthemum["relevanceRate"], 1.0)

    def test_hold_preserves_numeric_pass_and_systematic_scope_issue(self):
        assignments = [
            {
                "rank": rank,
                "label": "relevant_food"
                if rank <= 7
                else "raw_medicinal_or_nonfood_scope",
            }
            for rank in range(1, 11)
        ]
        reviewed = finalize_review_queue(
            review_queue(10),
            assignments=assignments,
            decision="hold",
            decision_note="存在稳定的药材销售语境混入。",
            systematic_scope_issue=True,
            observed_product_forms=[],
            reviewed_at="2026-09-13T22:00:00+08:00",
        )
        self.assertEqual(reviewed["metrics"]["relevantCount"], 7)
        self.assertEqual(reviewed["metrics"]["relevanceRate"], 0.7)
        self.assertTrue(reviewed["numericGatePassed"])
        self.assertEqual(reviewed["decision"], "hold")
        with self.assertRaisesRegex(ValueError, "系统性范围问题"):
            finalize_review_queue(
                review_queue(10),
                assignments=assignments,
                decision="promote",
                decision_note="错误晋级。",
                systematic_scope_issue=True,
                observed_product_forms=[],
                reviewed_at="2026-09-13T22:00:00+08:00",
            )

    def test_batch_finalization_keeps_query_collection_immutable_and_hashes_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "batch-1"
            queue = review_queue()
            query_artifact = {
                "batchId": queue["batchId"],
                "targetId": queue["targetId"],
                "queryId": queue["queryId"],
                "queryText": queue["queryText"],
                "executionStatus": "completed",
                "resultCards": [
                    {
                        key: value
                        for key, value in item.items()
                        if key not in {"reviewedLabel", "reviewedAt", "reviewNote"}
                    }
                    for item in queue["results"]
                ],
            }
            write_json(root / "queries" / "query-1.json", query_artifact)
            write_json(root / "review" / "query-1.json", queue)
            write_json(
                root / "manifest.json",
                {
                    "batchId": "batch-1",
                    "status": "complete",
                    "searchOnly": True,
                    "startedAt": "2026-09-13T20:00:00+08:00",
                    "completedAt": "2026-09-13T20:01:00+08:00",
                    "queries": [
                        {"queryId": "query-1", "artifact": "queries/query-1.json"}
                    ],
                },
            )
            query_hash = sha256_file(root / "queries" / "query-1.json")
            manifest_hash = sha256_file(root / "manifest.json")
            summary = finalize_batch(
                batch_root=root,
                review_input={
                    "reviewedBy": "human_review",
                    "reviews": [
                        {
                            "queryId": "query-1",
                            "decision": "通过验证，可启用",
                            "decisionNote": "人工确认通过。",
                            "assignments": [
                                {"rank": 1, "label": "信息不足，无法判断"},
                                *[
                                    {"rank": rank, "label": "食品相关"}
                                    for rank in range(2, 12)
                                ],
                            ],
                        }
                    ],
                },
                reviewed_at="2026-09-13T22:00:00+08:00",
            )
            reviewed = read_json(root / "review" / "query-1.json")
            markdown = (root / "review" / "query-1.md").read_text(encoding="utf-8")
            self.assertEqual(sha256_file(root / "queries" / "query-1.json"), query_hash)
        self.assertEqual(summary["manifestSha256"], manifest_hash)
        self.assertEqual(summary["records"][0]["artifact_manifest_sha256"], manifest_hash)
        self.assertEqual(summary["records"][0]["decision_note"], "人工确认通过。")
        self.assertEqual(reviewed["metrics"]["ambiguousSkipped"], 1)
        self.assertIn("人工标签", markdown)
        self.assertIn("食品相关", markdown)
        self.assertIn("机器标签", markdown)


if __name__ == "__main__":
    unittest.main()
