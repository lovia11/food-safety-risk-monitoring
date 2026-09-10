import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from src.data_store import DataStore
from src.local_api import create_handler
from src.task_runtime import TaskManager
from tests.test_data_store import create_run


class SamplingApiTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.output = self.root / "output"
        create_run(self.output, "run-a", product_id="123")
        self.store = DataStore(self.root / "data" / "app.db", self.output)
        self.store.initialize()
        self.store.import_all_runs()
        web = self.root / "web"
        web.mkdir()
        (web / "index.html").write_text("ok", encoding="utf-8")
        manager = TaskManager(self.output)
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            create_handler(
                self.output,
                web,
                manager,
                self.store,
                monitor_config=None,
                inspection_config=None,
                risk_substance_config=None,
            ),
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.snapshot_id = self.store.list_products()[0]["snapshotId"]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.temporary.cleanup()

    def request(self, path, method="GET", payload=None):
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            self.base + path,
            data=body,
            method=method,
            headers={"Content-Type": "application/json"} if body else {},
        )
        with urlopen(request) as response:
            return json.load(response)

    def test_review_decision_and_membership_lifecycle(self):
        added = self.request(
            f"/api/snapshots/{self.snapshot_id}/review-decision",
            "POST",
            {
                "decision": "recommend_follow_up",
                "added_from": "product_overview",
                "note": "人工确认",
            },
        )
        self.assertEqual(added["review"]["status"], "recommend_follow_up")
        current = self.request("/api/sampling-list")
        self.assertEqual(current["count"], 1)
        self.assertEqual(current["items"][0]["sourceTaskId"], "run-a")

        removed = self.request("/api/sampling-list/items/123", "DELETE")
        self.assertEqual(removed["membership"]["sourceSnapshotId"], self.snapshot_id)
        snapshot = self.store.get_snapshot(self.snapshot_id)
        self.assertEqual(snapshot["review"]["status"], "recommend_follow_up")
        self.assertEqual(snapshot["sampling"]["decisionStatus"], "reviewed_follow_up")

        restored = self.request(
            "/api/sampling-list/items",
            "POST",
            {
                "product_id": "123",
                "source_snapshot_id": self.snapshot_id,
                "added_from": "product_overview",
            },
        )
        self.assertEqual(restored["membership"]["productId"], "123")
        excluded = self.request(
            f"/api/snapshots/{self.snapshot_id}/review-decision",
            "POST",
            {
                "decision": "no_further_action",
                "added_from": "product_overview",
                "note": "暂不纳入",
            },
        )
        self.assertEqual(excluded["sampling"]["decisionStatus"], "no_further_action")
        self.assertEqual(self.request("/api/sampling-list")["count"], 0)
        with self.assertRaises(HTTPError) as raised:
            self.request(
                "/api/sampling-list/items",
                "POST",
                {
                    "product_id": "123",
                    "source_snapshot_id": self.snapshot_id,
                    "added_from": "product_overview",
                },
            )
        self.assertEqual(raised.exception.code, 409)
        conflict = json.load(raised.exception)
        raised.exception.close()
        self.assertEqual(
            conflict["error"]["code"], "sampling_membership_restore_conflict"
        )
        self.assertEqual(
            conflict["error"]["message"],
            "当前人工复核结论已变化，不能恢复旧的抽检清单状态。",
        )
        self.assertEqual(self.request("/api/sampling-list")["count"], 0)
        self.assertEqual(
            self.store.get_snapshot(self.snapshot_id)["review"]["status"],
            "no_further_action",
        )

    def test_pending_snapshot_cannot_be_added_through_restore_endpoint(self):
        with self.assertRaises(HTTPError) as raised:
            self.request(
                "/api/sampling-list/items",
                "POST",
                {
                    "product_id": "123",
                    "source_snapshot_id": self.snapshot_id,
                    "added_from": "inspection_workspace",
                },
            )
        self.assertEqual(raised.exception.code, 409)
        payload = json.load(raised.exception)
        raised.exception.close()
        self.assertEqual(
            payload["error"]["code"], "sampling_membership_restore_conflict"
        )
        self.assertEqual(self.request("/api/sampling-list")["count"], 0)
        self.assertEqual(
            self.store.get_snapshot(self.snapshot_id)["review"]["status"], "pending"
        )

    def test_client_cannot_forge_task_relationship(self):
        for path, payload in (
            (
                f"/api/snapshots/{self.snapshot_id}/review-decision",
                {
                    "decision": "recommend_follow_up",
                    "added_from": "product_overview",
                    "source_task_id": "forged",
                },
            ),
            (
                "/api/sampling-list/items",
                {
                    "product_id": "123",
                    "source_snapshot_id": self.snapshot_id,
                    "added_from": "product_overview",
                    "source_task_id": "forged",
                },
            ),
        ):
            with self.subTest(path=path), self.assertRaises(HTTPError) as raised:
                self.request(path, "POST", payload)
            self.assertEqual(raised.exception.code, 400)
            raised.exception.close()


if __name__ == "__main__":
    unittest.main()
