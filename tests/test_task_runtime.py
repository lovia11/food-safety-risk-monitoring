import threading
import tempfile
import unittest
from pathlib import Path

from src.runtime import write_json
from src.task_runtime import (
    ActiveTaskError,
    TaskManager,
    TaskNotResumableError,
    TaskValidationError,
    validate_task_request,
)
from src.web_contract import write_web_snapshot


def write_completed_snapshot(options, review_required=False):
    run_root = options.output_root / options.run_id
    candidate = {
        "product_id": "123",
        "product_name": "测试商品",
        "product_url": "https://item.taobao.com/item.htm?id=123",
        "keyword": options.keyword,
        "rank": 1,
    }
    record = {
        "keyword": options.keyword,
        "product_id": "123",
        "product_name": "测试商品",
        "product_url": candidate["product_url"],
        "original_image_count": 1,
        "ocr_image_count": 1,
        "detected_effects": ["助眠"] if review_required else [],
        "review_required": review_required,
        "crawl_status": "success",
        "errors": [],
    }
    payload = {
        "keyword": options.keyword,
        "search_raw_count": 1,
        "search_deduplicated_count": 1,
        "candidates": [candidate],
    }
    write_web_snapshot(run_root, payload, [record], "completed", "任务完成")


class SuccessfulPipeline:
    def __init__(self, options):
        self.options = options

    def run(self):
        write_completed_snapshot(self.options)


class FailingPipeline:
    def __init__(self, options):
        self.options = options

    def run(self):
        raise RuntimeError("fake collector failure")


class TaskRuntimeTest(unittest.TestCase):
    def test_valid_task_request(self):
        self.assertEqual(
            validate_task_request(
                {"keyword": " 酸枣仁 ", "candidate_limit": 10, "detail_limit": 2}
            ),
            {"keyword": "酸枣仁", "candidate_limit": 10, "detail_limit": 2},
        )

    def test_invalid_task_parameters(self):
        invalid = [
            {},
            {"keyword": "酸枣仁", "candidate_limit": 0, "detail_limit": 1},
            {"keyword": "酸枣仁", "candidate_limit": 10, "detail_limit": 11},
            {"keyword": "酸枣仁", "candidate_limit": "10", "detail_limit": 2},
        ]
        for payload in invalid:
            with self.subTest(payload=payload), self.assertRaises(TaskValidationError):
                validate_task_request(payload)

    def test_valid_monitor_task_request(self):
        self.assertEqual(
            validate_task_request(
                {
                    "task_type": "monitor",
                    "target_id": "target-1",
                    "per_query_candidate_limit": 10,
                    "detail_limit": 2,
                }
            ),
            {
                "task_type": "monitor",
                "target_id": "target-1",
                "per_query_candidate_limit": 10,
                "detail_limit": 2,
            },
        )

    def test_monitor_task_freezes_queries_and_calls_existing_pipeline(self):
        captured = []

        class MonitorPipeline(SuccessfulPipeline):
            def __init__(self, options):
                super().__init__(options)
                captured.append(options)

        target = {
            "target_id": "target-1",
            "standard_name": "酸枣仁",
            "target_type": "food_medicine",
            "enabled": True,
            "queries": [
                {
                    "query_id": "tea",
                    "query_text": "酸枣仁茶",
                    "query_type": "product_form",
                    "order": 2,
                    "enabled": True,
                },
                {
                    "query_id": "base",
                    "query_text": "酸枣仁",
                    "query_type": "base",
                    "order": 1,
                    "enabled": True,
                },
            ],
        }
        with tempfile.TemporaryDirectory() as temporary:
            manager = TaskManager(
                Path(temporary),
                pipeline_factory=MonitorPipeline,
                monitor_target_provider=lambda target_id: target
                if target_id == "target-1"
                else None,
            )
            created = manager.create_task(
                {
                    "task_type": "monitor",
                    "target_id": "target-1",
                    "per_query_candidate_limit": 10,
                    "detail_limit": 2,
                }
            )
            self.assertTrue(manager.wait_for_idle())
            self.assertEqual(captured[0].task_type, "monitor")
            self.assertEqual(captured[0].keyword, "酸枣仁")
            self.assertEqual(captured[0].per_query_candidate_limit, 10)
            self.assertEqual(
                [item["query_text"] for item in captured[0].search_queries],
                ["酸枣仁", "酸枣仁茶"],
            )
            request = created["runtime"]["request"]
            self.assertEqual(request["taskType"], "monitor")
            self.assertEqual(request["targetName"], "酸枣仁")

    def test_task_completes_and_can_be_read(self):
        with tempfile.TemporaryDirectory() as temporary:
            manager = TaskManager(Path(temporary), pipeline_factory=SuccessfulPipeline)
            created = manager.create_task(
                {"keyword": "酸枣仁", "candidate_limit": 10, "detail_limit": 2}
            )
            self.assertEqual(created["runtime"]["request"]["candidateLimit"], 10)
            self.assertTrue(manager.wait_for_idle())
            completed = manager.get_task(created["task"]["id"])
            self.assertEqual(completed["task"]["stage"], "completed")
            self.assertEqual(completed["statistics"]["analyzedProducts"], 1)
            self.assertFalse(completed["runtime"]["active"])

    def test_duplicate_active_task_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            started = threading.Event()
            release = threading.Event()

            class BlockingPipeline:
                def __init__(self, options):
                    self.options = options

                def run(self):
                    started.set()
                    release.wait(3)
                    write_completed_snapshot(self.options)

            manager = TaskManager(Path(temporary), pipeline_factory=BlockingPipeline)
            first = manager.create_task(
                {"keyword": "酸枣仁", "candidate_limit": 10, "detail_limit": 2}
            )
            self.assertTrue(started.wait(1))
            with self.assertRaises(ActiveTaskError) as raised:
                manager.create_task(
                    {"keyword": "茯苓", "candidate_limit": 10, "detail_limit": 2}
                )
            self.assertEqual(raised.exception.task_id, first["task"]["id"])
            release.set()
            self.assertTrue(manager.wait_for_idle())

    def test_worker_failure_becomes_terminal_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary:
            manager = TaskManager(Path(temporary), pipeline_factory=FailingPipeline)
            created = manager.create_task(
                {"keyword": "酸枣仁", "candidate_limit": 10, "detail_limit": 2}
            )
            self.assertTrue(manager.wait_for_idle())
            failed = manager.get_task(created["task"]["id"])
            self.assertEqual(failed["task"]["stage"], "failed")
            self.assertTrue(failed["task"]["terminal"])
            self.assertTrue(
                (Path(temporary) / created["task"]["id"] / "task_runtime_error.json").is_file()
            )

    def test_completed_task_is_discovered_in_task_list(self):
        with tempfile.TemporaryDirectory() as temporary:
            manager = TaskManager(Path(temporary), pipeline_factory=SuccessfulPipeline)
            created = manager.create_task(
                {"keyword": "酸枣仁", "candidate_limit": 3, "detail_limit": 1}
            )
            self.assertTrue(manager.wait_for_idle())
            ids = [item["id"] for item in manager.list_tasks()]
            self.assertIn(created["task"]["id"], ids)

    def test_non_resumable_task_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            manager = TaskManager(Path(temporary), pipeline_factory=SuccessfulPipeline)
            created = manager.create_task(
                {"keyword": "酸枣仁", "candidate_limit": 3, "detail_limit": 1}
            )
            self.assertTrue(manager.wait_for_idle())
            with self.assertRaises(TaskNotResumableError):
                manager.resume_task(created["task"]["id"])

    def test_runtime_owned_interrupted_task_can_resume(self):
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            run_root = output_root / "resume_task"
            write_json(
                run_root / "task_request.json",
                {
                    "task_id": "resume_task",
                    "keyword": "酸枣仁",
                    "candidate_limit": 2,
                    "detail_limit": 1,
                    "runtime_owned": True,
                },
            )
            write_json(
                run_root / "run_config.json",
                {
                    "keyword": "酸枣仁",
                    "resolved_candidate_limit": 2,
                    "resolved_detail_limit": 1,
                },
            )
            write_json(
                run_root / "search" / "search_candidates.json",
                {"keyword": "酸枣仁", "candidates": []},
            )
            write_json(run_root / "batch_state.json", [])
            write_web_snapshot(
                run_root,
                {"keyword": "酸枣仁", "candidates": []},
                [],
                "interrupted",
                "任务已中断",
            )

            class ResumePipeline:
                def __init__(self, options):
                    self.options = options

                def resume_processing(self, collect_pending_details=False):
                    self.assert_collect_pending = collect_pending_details
                    write_completed_snapshot(self.options)

            manager = TaskManager(output_root, pipeline_factory=ResumePipeline)
            self.assertTrue(manager.get_task("resume_task")["runtime"]["resumable"])
            manager.resume_task("resume_task")
            self.assertTrue(manager.wait_for_idle())
            self.assertEqual(manager.get_task("resume_task")["task"]["stage"], "completed")

    def test_stale_runtime_task_is_marked_interrupted(self):
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            run_root = output_root / "stale_task"
            write_json(
                run_root / "task_request.json",
                {
                    "task_id": "stale_task",
                    "keyword": "酸枣仁",
                    "candidate_limit": 10,
                    "detail_limit": 2,
                    "runtime_owned": True,
                },
            )
            write_web_snapshot(
                run_root,
                {"keyword": "酸枣仁", "candidates": []},
                [],
                "searching",
                "正在搜索",
            )
            manager = TaskManager(output_root, pipeline_factory=SuccessfulPipeline)
            snapshot = manager.get_task("stale_task")
            self.assertEqual(snapshot["task"]["stage"], "interrupted")
            self.assertTrue(snapshot["task"]["terminal"])


if __name__ == "__main__":
    unittest.main()
