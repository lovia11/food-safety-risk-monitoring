import json
import logging
import tempfile
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request, urlopen

from src.data_store import DataStore
from src.local_api import create_handler
from src.task_runtime import TaskManager
from tests.test_task_runtime import write_completed_snapshot


class ManualActionApiFlowTest(unittest.TestCase):
    def test_web_acknowledge_needs_worker_recheck_and_new_generation(self):
        worker_threads = []
        checker_threads = []
        remaining = iter(["淘宝人工验证", None])

        def checker(_page):
            checker_threads.append(threading.get_ident())
            return next(remaining)

        class GatePipeline:
            def __init__(self, options):
                self.options = options
                self.adapter = None

            def set_manual_action_adapter(self, adapter):
                self.adapter = adapter

            def run(self):
                worker_threads.append(threading.get_ident())
                self.adapter.wait(object(), "淘宝人工验证", logging.getLogger("gate-e2e"))
                write_completed_snapshot(self.options, review_required=True)

        with tempfile.TemporaryDirectory() as temporary, patch(
            "src.task_runtime.blocker_reason", checker
        ):
            root = Path(temporary)
            output = root / "output"
            store = DataStore(root / "data" / "app.db", output)
            store.initialize()
            manager = TaskManager(output, pipeline_factory=GatePipeline)
            web = root / "web"
            web.mkdir()
            (web / "index.html").write_text("ok", encoding="utf-8")
            server = ThreadingHTTPServer(
                ("127.0.0.1", 0),
                create_handler(
                    output, web, manager, store,
                    monitor_config=None,
                    inspection_config=None,
                    risk_substance_config=None,
                ),
            )
            server_thread = threading.Thread(target=server.serve_forever, daemon=True)
            server_thread.start()
            base = f"http://127.0.0.1:{server.server_port}"

            def request(path, payload=None):
                body = None if payload is None else json.dumps(payload).encode("utf-8")
                req = Request(
                    base + path,
                    data=body,
                    method="POST" if body else "GET",
                    headers={"Content-Type": "application/json"} if body else {},
                )
                with urlopen(req) as response:
                    return json.load(response)

            try:
                created = request(
                    "/api/tasks",
                    {"keyword": "酸枣仁", "candidate_limit": 2, "detail_limit": 1},
                )
                task_id = created["task"]["id"]

                def wait_for_generation(generation):
                    deadline = time.monotonic() + 2
                    while time.monotonic() < deadline:
                        task = request(f"/api/tasks/{task_id}")
                        if task["manualAction"]["generation"] == generation:
                            return task
                        time.sleep(0.01)
                    self.fail(f"manual action generation {generation} did not appear")

                first = wait_for_generation(1)
                self.assertEqual(first["businessStatus"], "waiting_for_manual_action")
                request(
                    f"/api/tasks/{task_id}/manual-action/acknowledge",
                    {"generation": 1},
                )
                second = wait_for_generation(2)
                self.assertTrue(second["manualAction"]["canAcknowledge"])
                request(
                    f"/api/tasks/{task_id}/manual-action/acknowledge",
                    {"generation": 2},
                )
                self.assertTrue(manager.wait_for_idle(2))
                completed = request(f"/api/tasks/{task_id}")
                self.assertEqual(completed["manualAction"]["status"], "resolved")
                self.assertEqual(checker_threads, [worker_threads[0], worker_threads[0]])
            finally:
                server.shutdown()
                server.server_close()
                server_thread.join(2)


if __name__ == "__main__":
    unittest.main()
