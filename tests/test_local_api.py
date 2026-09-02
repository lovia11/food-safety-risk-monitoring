import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

from src.local_api import create_handler, list_run_snapshots, resolve_run_file, resolve_run_root
from src.runtime import write_json
from src.task_runtime import TaskManager
from src.web_contract import write_web_snapshot


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
            finally:
                server.shutdown()
                server.server_close()
                thread.join(2)


if __name__ == "__main__":
    unittest.main()
