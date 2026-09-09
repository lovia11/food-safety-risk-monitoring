import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.data_store import DataStore
from src.review_decision import ReviewDecisionService, ReviewDecisionValidationError
from src.sampling_store import SamplingStore
from tests.test_data_store import create_run


class ReviewDecisionServiceTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.output_root = self.root / "output"
        create_run(self.output_root, "run-a", product_id="123")
        self.data_store = DataStore(self.root / "data" / "app.db", self.output_root)
        self.data_store.initialize()
        self.data_store.import_all_runs()
        self.sampling_store = SamplingStore(self.data_store.database_path)
        self.service = ReviewDecisionService(self.data_store, self.sampling_store)
        self.snapshot_id = self.data_store.list_products()[0]["snapshotId"]

    def tearDown(self):
        self.temporary.cleanup()

    def test_recommend_follow_up_updates_review_and_membership_atomically(self):
        result = self.service.decide(
            self.snapshot_id,
            "recommend_follow_up",
            "product_overview",
            "建议跟进",
        )
        self.assertEqual(result["review"]["status"], "recommend_follow_up")
        self.assertEqual(result["review"]["note"], "建议跟进")
        self.assertEqual(result["membership"]["sourceSnapshotId"], self.snapshot_id)
        self.assertEqual(result["sampling"]["decisionStatus"], "current")

    def test_no_further_action_removes_membership_in_same_decision(self):
        self.service.decide(
            self.snapshot_id, "recommend_follow_up", "inspection_workspace"
        )
        result = self.service.decide(
            self.snapshot_id,
            "no_further_action",
            "inspection_workspace",
            "语境无异常",
        )
        self.assertIsNone(result["membership"])
        self.assertIsNone(self.sampling_store.get("123"))
        self.assertEqual(result["review"]["status"], "no_further_action")
        self.assertEqual(result["sampling"]["decisionStatus"], "no_further_action")

    def test_manual_remove_preserves_follow_up_review_projection(self):
        self.service.decide(
            self.snapshot_id, "recommend_follow_up", "product_overview"
        )
        self.sampling_store.remove("123")
        snapshot = self.data_store.get_snapshot(self.snapshot_id)
        self.assertEqual(snapshot["review"]["status"], "recommend_follow_up")
        self.assertEqual(snapshot["sampling"]["decisionStatus"], "reviewed_follow_up")

    def test_membership_failure_rolls_back_review(self):
        class FailingSamplingStore(SamplingStore):
            def ensure_membership(self, connection, **kwargs):
                super().ensure_membership(connection, **kwargs)
                raise RuntimeError("injected membership failure")

        service = ReviewDecisionService(
            self.data_store, FailingSamplingStore(self.data_store.database_path)
        )
        with self.assertRaises(RuntimeError):
            service.decide(
                self.snapshot_id, "recommend_follow_up", "product_overview", "不得保存"
            )
        self.assertEqual(
            self.data_store.get_snapshot(self.snapshot_id)["review"]["status"],
            "pending",
        )
        with sqlite3.connect(self.data_store.database_path) as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM sampling_list_memberships"
            ).fetchone()[0]
        self.assertEqual(count, 0)

    def test_rejects_invalid_decision_and_origin(self):
        with self.assertRaises(ReviewDecisionValidationError):
            self.service.decide(self.snapshot_id, "pending", "product_overview")
        with self.assertRaises(ReviewDecisionValidationError):
            self.service.decide(self.snapshot_id, "recommend_follow_up", "forged")


if __name__ == "__main__":
    unittest.main()
