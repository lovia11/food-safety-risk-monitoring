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
) -> Path:
    run_root = output_root / run_id
    write_json(
        run_root / "task_request.json",
        {
            "task_id": run_id,
            "keyword": "酸枣仁",
            "candidate_limit": 10,
            "detail_limit": 2,
            "created_at": "2026-09-02T09:59:00+08:00",
            "runtime_owned": True,
        },
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
        with sqlite3.connect(self.store.database_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            version = connection.execute("PRAGMA user_version").fetchone()[0]
        self.assertTrue(
            {"tasks", "products", "product_snapshots", "evidence", "reviews"}
            <= tables
        )
        self.assertEqual(version, 1)

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
