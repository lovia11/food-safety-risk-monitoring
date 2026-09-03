import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from src.data_store import DataStore
from src.local_api import create_handler, list_run_snapshots, resolve_run_file, resolve_run_root
from src.runtime import write_json
from src.task_runtime import TaskManager
from src.web_contract import write_web_snapshot


def write_test_monitor_config(path: Path) -> None:
    write_json(
        path,
        {
            "schema_version": 2,
            "dataset_id": "local-api-test-dataset",
            "dataset_version": "1",
            "dataset_status": "development_seed",
            "source_name": "离线API测试",
            "source_reference": "仅用于测试",
            "source_date": None,
            "collected_at": None,
            "verified_at": None,
            "targets": [
                {
                    "target_id": "target-1",
                    "dataset_id": "local-api-test-dataset",
                    "standard_name": "酸枣仁",
                    "target_type": "food_medicine",
                    "source_name": "离线API测试",
                    "source_reference": "仅用于测试",
                    "source_date": None,
                    "enabled": True,
                    "queries": [
                        {
                            "query_id": "target-1-base",
                            "query_text": "酸枣仁",
                            "query_type": "base",
                            "query_source": "standard_name",
                            "validation_status": "search_validated",
                            "query_note": "离线测试Query",
                            "order": 1,
                            "enabled": True,
                        }
                    ],
                }
            ],
        },
    )


class LocalApiHelpersTest(unittest.TestCase):
    def test_paths_cannot_escape_output_or_run_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary) / "output"
            run_root = output_root / "run-1"
            run_root.mkdir(parents=True)
            self.assertEqual(resolve_run_root(output_root, "run-1"), run_root.resolve())
            with self.assertRaises(ValueError):
                resolve_run_root(output_root, "../outside")
            with self.assertRaises(ValueError):
                resolve_run_file(run_root, "../../outside.txt")

    def test_lists_only_runs_with_valid_web_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary) / "output"
            write_json(
                output_root / "run-1" / "web_snapshot.json",
                {
                    "generatedAt": "2026-08-28T19:00:00+08:00",
                    "task": {"id": "run-1", "stage": "completed"},
                    "statistics": {"selectedProducts": 1},
                },
            )
            (output_root / "run-2").mkdir()
            runs = list_run_snapshots(output_root)
            self.assertEqual([item["id"] for item in runs], ["run-1"])
            self.assertEqual(runs[0]["statistics"]["selectedProducts"], 1)

    def test_http_api_creates_task_and_discovers_completed_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_root = root / "output"
            web_root = root / "web"
            web_root.mkdir()
            (web_root / "index.html").write_text("ok", encoding="utf-8")

            class FakePipeline:
                def __init__(self, options):
                    self.options = options

                def run(self):
                    run_root = self.options.output_root / self.options.run_id
                    write_web_snapshot(
                        run_root,
                        {
                            "keyword": self.options.keyword,
                            "search_raw_count": 1,
                            "search_deduplicated_count": 1,
                            "candidates": [],
                        },
                        [],
                        "completed",
                        "任务完成",
                    )

            manager = TaskManager(output_root, pipeline_factory=FakePipeline)
            server = ThreadingHTTPServer(
                ("127.0.0.1", 0),
                create_handler(output_root, web_root, manager),
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                body = json.dumps(
                    {"keyword": "酸枣仁", "candidate_limit": 10, "detail_limit": 2}
                ).encode("utf-8")
                request = Request(
                    f"{base}/api/tasks",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(request) as response:
                    self.assertEqual(response.status, 202)
                    created = json.load(response)
                self.assertTrue(manager.wait_for_idle())
                task_id = created["task"]["id"]
                with urlopen(f"{base}/api/tasks/{task_id}") as response:
                    completed = json.load(response)
                self.assertEqual(
                    completed["task"]["stage"],
                    "completed",
                    completed["task"].get("message"),
                )
                with urlopen(f"{base}/api/runs") as response:
                    run_list = json.load(response)
                self.assertIn(task_id, [item["id"] for item in run_list["runs"]])

                with urlopen(f"{base}/api/monitor-targets") as response:
                    targets = json.load(response)["targets"]
                development_target = next(
                    target
                    for target in targets
                    if target["target_id"] == "dev-food-medicine-suanzaoren"
                )
                self.assertEqual(development_target["standard_name"], "酸枣仁")
                self.assertEqual(
                    development_target["dataset_status"], "development_seed"
                )
                self.assertEqual(
                    development_target["dataset"]["dataset_id"],
                    "monitor-targets-development",
                )
                monitor_body = json.dumps(
                    {
                        "task_type": "monitor",
                        "target_id": development_target["target_id"],
                        "per_query_candidate_limit": 10,
                        "detail_limit": 2,
                    }
                ).encode("utf-8")
                monitor_request = Request(
                    f"{base}/api/tasks",
                    data=monitor_body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(monitor_request) as response:
                    monitor_created = json.load(response)
                self.assertTrue(manager.wait_for_idle())
                self.assertEqual(
                    monitor_created["runtime"]["request"]["taskType"], "monitor"
                )
            finally:
                server.shutdown()
                server.server_close()
                thread.join(2)

    def test_business_api_reads_snapshots_and_persists_review(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_root = root / "output"
            run_root = output_root / "run-1"
            web_root = root / "web"
            web_root.mkdir()
            (web_root / "index.html").write_text("ok", encoding="utf-8")
            write_json(
                run_root / "products" / "123" / "analysis.json",
                {
                    "detected_effects": ["助眠"],
                    "review_required": True,
                    "risk_reason": "检测到助眠表达",
                    "evidence_details": [
                        {
                            "effect": "助眠",
                            "text": "帮助睡眠",
                            "matched_keywords": ["睡眠"],
                            "source_type": "ocr",
                            "source_label": "详情图 OCR",
                            "content_origin": "seller_managed",
                            "source_path": "ocr/original_001.txt",
                            "line_number": 1,
                        }
                    ],
                },
            )
            write_web_snapshot(
                run_root,
                {
                    "keyword": "酸枣仁",
                    "candidates": [{"product_id": "123", "rank": 1}],
                },
                [
                    {
                        "keyword": "酸枣仁",
                        "product_id": "123",
                        "product_name": "测试商品",
                        "product_url": "https://item.taobao.com/item.htm?id=123",
                        "crawl_status": "success",
                        "review_required": True,
                    }
                ],
                "completed",
                "完成",
            )
            database_path = root / "data" / "app.db"
            store = DataStore(database_path, output_root)
            store.initialize()
            monitor_config = root / "monitor_targets.json"
            write_test_monitor_config(monitor_config)
            store.import_monitor_config(monitor_config)

            monitor_root = output_root / "monitor-run"
            write_json(
                monitor_root / "task_request.json",
                {
                    "task_id": "monitor-run",
                    "task_type": "monitor",
                    "target_id": "target-1",
                    "per_query_candidate_limit": 10,
                    "detail_limit": 1,
                    "created_at": "2026-09-03T10:00:00+08:00",
                    "runtime_owned": True,
                },
            )
            write_web_snapshot(
                monitor_root,
                {
                    "keyword": "酸枣仁",
                    "candidates": [
                        {"product_id": str(456 + index), "rank": index + 1}
                        for index in range(21)
                    ],
                },
                [
                    {
                        "keyword": "酸枣仁",
                        "product_id": str(456 + index),
                        "product_name": f"监测对象商品 {index + 1}",
                        "product_url": (
                            f"https://item.taobao.com/item.htm?id={456 + index}"
                        ),
                        "crawl_status": "success",
                        "review_required": False,
                    }
                    for index in range(21)
                ],
                "completed",
                "完成",
            )
            manager = TaskManager(output_root)
            server = ThreadingHTTPServer(
                ("127.0.0.1", 0),
                create_handler(
                    output_root,
                    web_root,
                    manager,
                    store,
                    monitor_config=None,
                ),
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                with urlopen(f"{base}/api/products?task_id=run-1") as response:
                    product_page = json.load(response)
                products = product_page["products"]
                self.assertEqual(len(products), 1)
                self.assertEqual(
                    {
                        "count": product_page["count"],
                        "total": product_page["total"],
                        "page": product_page["page"],
                        "pageSize": product_page["pageSize"],
                        "totalPages": product_page["totalPages"],
                    },
                    {"count": 1, "total": 1, "page": 1, "pageSize": 20, "totalPages": 1},
                )
                self.assertIsNone(products[0]["targetId"])
                self.assertIsNone(products[0]["targetName"])
                snapshot_id = products[0]["snapshotId"]
                with urlopen(
                    f"{base}/api/products?target_id=target-1&page=1&page_size=20"
                ) as response:
                    target_page = json.load(response)
                self.assertEqual(target_page["count"], 20)
                self.assertEqual(target_page["total"], 21)
                self.assertEqual(target_page["totalPages"], 2)
                self.assertEqual(target_page["products"][0]["productId"], "456")
                self.assertEqual(target_page["products"][0]["targetId"], "target-1")
                self.assertEqual(target_page["products"][0]["targetName"], "酸枣仁")
                with urlopen(
                    f"{base}/api/products?target_id=target-1&page=2&page_size=20"
                ) as response:
                    second_page = json.load(response)
                self.assertEqual(second_page["count"], 1)
                self.assertEqual(second_page["total"], 21)
                self.assertEqual(second_page["products"][0]["productId"], "476")
                with urlopen(
                    f"{base}/api/products?target_id=target-1&page=3&page_size=20"
                ) as response:
                    beyond_last_page = json.load(response)
                self.assertEqual(beyond_last_page["products"], [])
                self.assertEqual(beyond_last_page["total"], 21)
                with urlopen(
                    f"{base}/api/products?task_id=run-1&target_id=target-1"
                ) as response:
                    mismatched = json.load(response)
                self.assertEqual(mismatched["products"], [])
                self.assertEqual(mismatched["total"], 0)
                for parameters in (
                    "page=0",
                    "page=invalid",
                    "page_size=0",
                    "page_size=101",
                    "review_status=invalid",
                ):
                    with self.subTest(parameters=parameters):
                        with self.assertRaises(HTTPError) as raised:
                            urlopen(f"{base}/api/products?{parameters}")
                        self.assertEqual(raised.exception.code, 400)
                with urlopen(f"{base}/api/products/123/snapshots") as response:
                    snapshots = json.load(response)["snapshots"]
                self.assertEqual(snapshots[0]["snapshotId"], snapshot_id)
                with urlopen(f"{base}/api/snapshots/{snapshot_id}") as response:
                    detail = json.load(response)
                self.assertEqual(detail["evidence"][0]["sourceType"], "ocr")
                request = Request(
                    f"{base}/api/snapshots/{snapshot_id}/review",
                    data=json.dumps(
                        {"status": "recommend_follow_up", "note": "建议进一步核对"}
                    ).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="PUT",
                )
                with urlopen(request) as response:
                    saved = json.load(response)
                self.assertEqual(saved["review"]["status"], "recommend_follow_up")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(2)

            reopened = DataStore(database_path, output_root)
            reopened.initialize()
            self.assertEqual(
                reopened.get_snapshot(snapshot_id)["review"]["note"],
                "建议进一步核对",
            )


if __name__ == "__main__":
    unittest.main()
