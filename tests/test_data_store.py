import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.data_store import (
    DataStore,
    ReviewValidationError,
    SnapshotNotFoundError,
)
from src.runtime import read_json, write_json
from src.web_contract import write_web_snapshot


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRESERVED_OUTPUT_ROOT = PROJECT_ROOT / "output"
PRESERVED_RUN_IDS = ("20260901_collector_v02_e2e", "20260902T005526_task")


def create_run(
    output_root: Path,
    run_id: str,
    *,
    product_id: str = "123",
    product_name: str = "酸枣仁测试商品",
    effect: str = "助眠",
    stage: str = "completed",
    collected_at: str = "2026-09-02T10:00:00+08:00",
    target_id: str | None = None,
) -> Path:
    run_root = output_root / run_id
    task_request = {
        "task_id": run_id,
        "keyword": "酸枣仁",
        "candidate_limit": 10,
        "detail_limit": 2,
        "created_at": "2026-09-02T09:59:00+08:00",
        "runtime_owned": True,
    }
    if target_id:
        task_request.update(
            {
                "task_type": "monitor",
                "target_id": target_id,
                "per_query_candidate_limit": 10,
            }
        )
    write_json(
        run_root / "task_request.json",
        task_request,
    )
    write_json(
        run_root / "products" / product_id / "meta.json",
        {
            "rank": 1,
            "crawlTime": collected_at,
            "screenshots": [],
            "images": [],
        },
    )
    write_json(
        run_root / "products" / product_id / "analysis.json",
        {
            "detected_effects": [effect] if effect else [],
            "review_required": bool(effect),
            "risk_reason": "检测到助眠表达" if effect else "未发现明显表达",
            "evidence_details": [
                {
                    "effect": effect,
                    "text": "帮助睡眠",
                    "matched_keywords": ["睡眠"],
                    "source_type": "ocr",
                    "source_label": "详情图 OCR",
                    "content_origin": "seller_managed",
                    "source_path": "ocr/original_001.txt",
                    "line_number": 2,
                }
            ]
            if effect
            else [],
        },
    )
    record = {
        "keyword": "酸枣仁",
        "product_id": product_id,
        "product_name": product_name,
        "shop_name": "测试店铺",
        "region": "浙江 杭州",
        "product_url": f"https://item.taobao.com/item.htm?id={product_id}",
        "original_image_count": 2,
        "ocr_image_count": 1,
        "detected_effects": [effect] if effect else [],
        "review_required": bool(effect),
        "risk_reason": "检测到助眠表达" if effect else "未发现明显表达",
        "evidence_details": [],
        "crawl_status": "success",
        "errors": [],
    }
    write_web_snapshot(
        run_root,
        {
            "keyword": "酸枣仁",
            "search_raw_count": 3,
            "search_deduplicated_count": 3,
            "candidates": [{"product_id": product_id, "rank": 1}],
        },
        [record],
        stage,
        "测试任务状态",
    )
    return run_root


class DataStoreTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.output_root = self.root / "output"
        self.store = DataStore(self.root / "data" / "app.db", self.output_root)
        self.store.initialize()

    def tearDown(self):
        self.temporary.cleanup()

    def test_initializes_schema_and_version(self):
        connection = sqlite3.connect(self.store.database_path)
        try:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            version = connection.execute("PRAGMA user_version").fetchone()[0]
        finally:
            connection.close()
        self.assertTrue(
            {
                "tasks",
                "products",
                "product_snapshots",
                "evidence",
                "reviews",
                "monitor_datasets",
                "monitor_targets",
                "search_queries",
                "candidate_hits",
                "inspection_datasets",
                "inspection_methods",
                "inspection_substances",
                "inspection_method_substances",
                "inspection_method_applicabilities",
                "substance_regulatory_contexts",
            }
            <= tables
        )
        self.assertEqual(version, 5)

    def _import_monitor_seed(self, *, include_second_target: bool = False):
        config = self.root / "monitor_targets.json"
        targets = [
            {
                "target_id": "target-1",
                "dataset_id": "test-development-dataset",
                "standard_name": "酸枣仁",
                "target_type": "food_medicine",
                "source_name": "开发种子",
                "source_reference": "仅用于开发验证",
                "source_date": None,
                "enabled": True,
                "queries": [
                    {
                        "query_id": "query-base",
                        "query_text": "酸枣仁",
                        "query_type": "base",
                        "query_source": "standard_name",
                        "validation_status": "search_validated",
                        "query_note": "离线测试中的已验证基础词。",
                        "order": 1,
                        "enabled": True,
                    },
                    {
                        "query_id": "query-tea",
                        "query_text": "酸枣仁茶",
                        "query_type": "product_form",
                        "query_source": "observed_product_form",
                        "validation_status": "search_validated",
                        "query_note": "离线测试中观察到的产品形态。",
                        "order": 2,
                        "enabled": True,
                    },
                ],
            }
        ]
        if include_second_target:
            targets.append(
                {
                    "target_id": "target-2",
                    "dataset_id": "test-development-dataset",
                    "standard_name": "茯苓",
                    "target_type": "food_medicine",
                    "source_name": "开发种子",
                    "source_reference": "仅用于开发验证",
                    "source_date": None,
                    "enabled": True,
                    "queries": [
                        {
                            "query_id": "query-fuling",
                            "query_text": "茯苓",
                            "query_type": "base",
                            "query_source": "standard_name",
                            "validation_status": "search_validated",
                            "query_note": "离线测试中的第二个已验证基础词。",
                            "order": 1,
                            "enabled": True,
                        }
                    ],
                }
            )
        write_json(
            config,
            {
                "schema_version": 2,
                "dataset_id": "test-development-dataset",
                "dataset_version": "1",
                "dataset_status": "development_seed",
                "source_name": "开发种子",
                "source_reference": "仅用于开发验证",
                "source_date": None,
                "collected_at": None,
                "verified_at": None,
                "targets": targets,
            },
        )
        return self.store.import_monitor_config(config)

    def test_monitor_target_and_queries_preserve_configured_order(self):
        self.assertEqual(
            self._import_monitor_seed(),
            {"datasets": 1, "targets": 1, "queries": 2},
        )
        target = self.store.get_monitor_target("target-1")
        self.assertEqual(target["standard_name"], "酸枣仁")
        self.assertEqual(target["dataset_status"], "development_seed")
        self.assertEqual(
            [item["query_text"] for item in target["queries"]],
            ["酸枣仁", "酸枣仁茶"],
        )

    def test_candidate_hits_are_idempotent_and_survive_reopen(self):
        self._import_monitor_seed()
        run_root = create_run(self.output_root, "monitor_run")
        request = read_json(run_root / "task_request.json")
        request.update(
            {
                "task_type": "monitor",
                "target_id": "target-1",
                "per_query_candidate_limit": 10,
            }
        )
        write_json(run_root / "task_request.json", request)
        write_json(
            run_root / "search" / "discovery_summary.json",
            {
                "candidate_hits": [
                    {
                        "product_id": "123",
                        "query_id": "query-base",
                        "query_text": "酸枣仁",
                        "rank": 1,
                        "discovered_at": "2026-09-02T10:00:00+08:00",
                    },
                    {
                        "product_id": "123",
                        "query_id": "query-tea",
                        "query_text": "酸枣仁茶",
                        "rank": 2,
                        "discovered_at": "2026-09-02T10:01:00+08:00",
                    },
                ]
            },
        )
        self.store.import_run(run_root)
        self.store.import_run(run_root)
        self.assertEqual(self.store.table_counts()["candidate_hits"], 2)
        reopened = DataStore(self.store.database_path, self.output_root)
        reopened.initialize()
        hits = reopened.list_candidate_hits("monitor_run")
        self.assertEqual([item["queryText"] for item in hits], ["酸枣仁", "酸枣仁茶"])

    def test_imports_task_fields(self):
        self.store.import_run(create_run(self.output_root, "run_a"))
        with sqlite3.connect(self.store.database_path) as connection:
            row = connection.execute(
                "SELECT keyword, candidate_limit, detail_limit, stage, run_path FROM tasks"
            ).fetchone()
        self.assertEqual(row, ("酸枣仁", 10, 2, "completed", "run_a"))

    def test_imports_product_and_snapshot(self):
        self.store.import_run(create_run(self.output_root, "run_a"))
        counts = self.store.table_counts()
        self.assertEqual(counts["products"], 1)
        self.assertEqual(counts["product_snapshots"], 1)
        product = self.store.list_products(task_id="run_a")[0]
        self.assertEqual(product["productId"], "123")
        self.assertEqual(product["counts"]["originalImages"], 2)

    def test_imports_structured_evidence(self):
        self.store.import_run(create_run(self.output_root, "run_a"))
        product = self.store.list_products()[0]
        detail = self.store.get_snapshot(product["snapshotId"])
        self.assertEqual(len(detail["evidence"]), 1)
        self.assertEqual(detail["evidence"][0]["sourceType"], "ocr")
        self.assertEqual(detail["evidence"][0]["contentOrigin"], "seller_managed")

    def test_review_starts_pending(self):
        self.store.import_run(create_run(self.output_root, "run_a"))
        self.assertEqual(self.store.list_products()[0]["review"]["status"], "pending")

    def test_review_can_be_updated(self):
        self.store.import_run(create_run(self.output_root, "run_a"))
        snapshot_id = self.store.list_products()[0]["snapshotId"]
        review = self.store.update_review(
            snapshot_id, "recommend_follow_up", "建议核对商品资质"
        )
        self.assertEqual(review["status"], "recommend_follow_up")
        self.assertEqual(review["note"], "建议核对商品资质")
        self.assertIsNotNone(review["reviewedAt"])

    def test_review_persists_in_new_repository_instance(self):
        self.store.import_run(create_run(self.output_root, "run_a"))
        snapshot_id = self.store.list_products()[0]["snapshotId"]
        self.store.update_review(snapshot_id, "no_further_action", "页面语境无异常")
        reopened = DataStore(self.store.database_path, self.output_root)
        reopened.initialize()
        self.assertEqual(
            reopened.get_snapshot(snapshot_id)["review"]["status"],
            "no_further_action",
        )

    def test_invalid_review_status_is_rejected(self):
        self.store.import_run(create_run(self.output_root, "run_a"))
        snapshot_id = self.store.list_products()[0]["snapshotId"]
        with self.assertRaises(ReviewValidationError):
            self.store.update_review(snapshot_id, "approved")

    def test_missing_snapshot_review_is_rejected(self):
        with self.assertRaises(SnapshotNotFoundError):
            self.store.update_review("missing", "recommend_follow_up")

    def test_import_is_idempotent(self):
        run_root = create_run(self.output_root, "run_a")
        self.store.import_run(run_root)
        first = self.store.table_counts()
        self.store.import_run(run_root)
        self.assertEqual(first, self.store.table_counts())

    def test_reimport_preserves_human_review(self):
        run_root = create_run(self.output_root, "run_a")
        self.store.import_run(run_root)
        snapshot_id = self.store.list_products()[0]["snapshotId"]
        self.store.update_review(snapshot_id, "recommend_follow_up", "保留此备注")
        self.store.import_run(run_root)
        self.assertEqual(
            self.store.get_snapshot(snapshot_id)["review"]["note"], "保留此备注"
        )

    def test_same_product_has_multiple_task_snapshots(self):
        self.store.import_run(create_run(self.output_root, "run_a"))
        self.store.import_run(
            create_run(
                self.output_root,
                "run_b",
                product_name="第二次采集的商品名称",
                collected_at="2026-09-03T10:00:00+08:00",
            )
        )
        counts = self.store.table_counts()
        self.assertEqual(counts["products"], 1)
        self.assertEqual(counts["product_snapshots"], 2)
        self.assertEqual(len(self.store.list_product_snapshots("123")), 2)
        self.assertEqual(self.store.list_products()[0]["productName"], "第二次采集的商品名称")

    def test_product_filters_use_business_index(self):
        self.store.import_run(create_run(self.output_root, "run_a"))
        product = self.store.list_products(query="测试店铺", effect="助眠")[0]
        self.store.update_review(product["snapshotId"], "recommend_follow_up")
        filtered = self.store.list_products(
            task_id="run_a", review_status="recommend_follow_up", effect="助眠"
        )
        self.assertEqual([item["productId"] for item in filtered], ["123"])
        self.assertEqual(self.store.list_products(query="不存在"), [])

    def test_product_query_uses_global_latest_snapshot_by_default(self):
        self._import_monitor_seed(include_second_target=True)
        self.store.import_run(
            create_run(
                self.output_root,
                "run_target_1",
                product_name="较早的酸枣仁快照",
                collected_at="2026-09-02T10:00:00+08:00",
                target_id="target-1",
            )
        )
        self.store.import_run(
            create_run(
                self.output_root,
                "run_target_2",
                product_name="较新的茯苓快照",
                collected_at="2026-09-03T10:00:00+08:00",
                target_id="target-2",
            )
        )
        product = self.store.list_products()[0]
        self.assertEqual(product["productName"], "较新的茯苓快照")
        self.assertEqual(product["targetId"], "target-2")
        self.assertEqual(product["targetName"], "茯苓")

    def test_product_query_paginates_with_stable_total(self):
        for index in range(23):
            self.store.import_run(
                create_run(
                    self.output_root,
                    f"run_{index:02d}",
                    product_id=f"product-{index:02d}",
                    product_name=f"分页商品 {index:02d}",
                    collected_at=f"2026-09-02T{index:02d}:00:00+08:00",
                )
            )
        first = self.store.list_products(page=1, page_size=20)
        second = self.store.list_products(page=2, page_size=20)
        beyond = self.store.list_products(page=3, page_size=20)
        self.assertEqual(len(first), 20)
        self.assertEqual(len(second), 3)
        self.assertEqual(beyond, [])
        self.assertEqual(self.store.count_products(), 23)
        self.assertTrue(set(item["productId"] for item in first).isdisjoint(
            item["productId"] for item in second
        ))

    def test_target_filter_uses_latest_snapshot_within_target(self):
        self._import_monitor_seed(include_second_target=True)
        for run_id, name, collected_at, target_id in (
            ("acid_old", "酸枣仁旧快照", "2026-09-01T10:00:00+08:00", "target-1"),
            ("acid_new", "酸枣仁范围最新快照", "2026-09-02T10:00:00+08:00", "target-1"),
            ("fuling_new", "全局最新茯苓快照", "2026-09-03T10:00:00+08:00", "target-2"),
        ):
            self.store.import_run(
                create_run(
                    self.output_root,
                    run_id,
                    product_name=name,
                    collected_at=collected_at,
                    target_id=target_id,
                )
            )
        product = self.store.list_products(target_id="target-1")[0]
        self.assertEqual(product["productName"], "酸枣仁范围最新快照")
        self.assertEqual(product["targetId"], "target-1")
        self.assertEqual(product["targetName"], "酸枣仁")
        self.assertEqual(self.store.count_products(target_id="target-1"), 1)

    def test_task_and_target_filters_are_combined(self):
        self._import_monitor_seed(include_second_target=True)
        self.store.import_run(
            create_run(self.output_root, "acid_run", target_id="target-1")
        )
        self.assertEqual(
            len(self.store.list_products(task_id="acid_run", target_id="target-1")),
            1,
        )
        self.assertEqual(
            self.store.list_products(task_id="acid_run", target_id="target-2"),
            [],
        )

    def test_quick_task_has_null_target_metadata(self):
        self.store.import_run(create_run(self.output_root, "quick_run"))
        product = self.store.list_products(task_id="quick_run")[0]
        self.assertIsNone(product["targetId"])
        self.assertIsNone(product["targetName"])

    def test_filtered_count_matches_paginated_product_query(self):
        for index in range(3):
            self.store.import_run(
                create_run(
                    self.output_root,
                    f"filtered_{index}",
                    product_id=f"filtered-product-{index}",
                    product_name=(
                        f"匹配商品 {index}" if index < 2 else "其他商品"
                    ),
                    effect="助眠" if index < 2 else "",
                    collected_at=f"2026-09-02T1{index}:00:00+08:00",
                )
            )
        for product in self.store.list_products(query="匹配", effect="助眠"):
            self.store.update_review(product["snapshotId"], "recommend_follow_up")
        filters = {
            "query": "匹配",
            "review_status": "recommend_follow_up",
            "effect": "助眠",
        }
        self.assertEqual(self.store.count_products(**filters), 2)
        self.assertEqual(
            len(self.store.list_products(**filters, page=1, page_size=1)), 1
        )
        self.assertEqual(
            len(self.store.list_products(**filters, page=2, page_size=1)), 1
        )

    def test_import_all_discovers_only_valid_run_snapshots(self):
        create_run(self.output_root, "run_a")
        (self.output_root / "not_a_run").mkdir(parents=True)
        result = self.store.import_all_runs()
        self.assertEqual(result, {"discovered": 1, "imported": 1, "skipped": 0})

    def test_task_status_is_updated_by_reimport(self):
        run_root = create_run(self.output_root, "run_a", stage="initializing")
        self.store.import_run(run_root)
        snapshot = read_json(run_root / "web_snapshot.json")
        snapshot["task"].update({"stage": "failed", "terminal": True})
        write_json(run_root / "web_snapshot.json", snapshot)
        self.store.import_run(run_root)
        with sqlite3.connect(self.store.database_path) as connection:
            stage = connection.execute(
                "SELECT stage FROM tasks WHERE task_id='run_a'"
            ).fetchone()[0]
        self.assertEqual(stage, "failed")


class PreservedRunIndexTest(unittest.TestCase):
    @unittest.skipUnless(
        all(
            (PRESERVED_OUTPUT_ROOT / run_id / "web_snapshot.json").is_file()
            for run_id in PRESERVED_RUN_IDS
        ),
        "保留的真实验收run不在当前检出目录",
    )
    def test_preserved_real_runs_build_business_index(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = DataStore(Path(temporary) / "app.db", PRESERVED_OUTPUT_ROOT)
            store.initialize()
            for run_id in PRESERVED_RUN_IDS:
                result = store.import_run(PRESERVED_OUTPUT_ROOT / run_id)
                self.assertEqual(result["products"], 10)
                self.assertEqual(len(store.list_products(task_id=run_id)), 10)
            self.assertGreater(store.table_counts()["evidence"], 0)


if __name__ == "__main__":
    unittest.main()
