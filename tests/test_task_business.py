import tempfile
import unittest
from pathlib import Path

from src.data_store import DataStore
from src.local_api import task_business_dto
from src.sampling_store import SamplingStore
from tests.test_data_store import create_run


class TaskBusinessSummaryTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.output = self.root / "output"
        create_run(
            self.output,
            "run-a",
            product_id="123",
            display_name="显式排查名称",
        )
        create_run(
            self.output,
            "run-a-2",
            product_id="456",
            display_name="另一个任务",
        )
        self.store = DataStore(self.root / "data" / "app.db", self.output)
        self.store.initialize()
        self.store.import_all_runs()

    def tearDown(self):
        self.temporary.cleanup()

    def test_summary_uses_persistent_review_counts_and_secondary_current_count(self):
        first = self.store.list_products(task_id="run-a")[0]
        self.store.update_review(first["snapshotId"], "recommend_follow_up", "保留")
        SamplingStore(self.store.database_path).add_from_snapshot(
            first["snapshotId"], "inspection_workspace"
        )
        summary = self.store.get_task_business_summary("run-a")
        self.assertEqual(summary["displayName"], "显式排查名称")
        self.assertEqual(summary["archiveSummary"]["recommendFollowUpCount"], 1)
        self.assertEqual(summary["archiveSummary"]["currentSamplingItems"], 1)
        SamplingStore(self.store.database_path).remove("123")
        after_remove = self.store.get_task_business_summary("run-a")["archiveSummary"]
        self.assertEqual(after_remove["recommendFollowUpCount"], 1)
        self.assertEqual(after_remove["currentSamplingItems"], 0)

    def test_business_status_distinguishes_manual_validation_and_review(self):
        summary = self.store.get_task_business_summary("run-a")
        waiting = task_business_dto(
            {
                "task": {"stage": "waiting_for_manual_action"},
                "runtime": {"active": True, "resumable": False},
            },
            summary,
        )
        self.assertEqual(waiting["businessStatus"], "waiting_for_manual_action")
        self.assertEqual(waiting["businessStatusLabel"], "等待淘宝验证")
        review = task_business_dto(
            {
                "task": {"stage": "completed"},
                "runtime": {"active": False, "resumable": False},
            },
            summary,
        )
        self.assertEqual(review["businessStatus"], "awaiting_review")
        self.assertEqual(review["businessStatusLabel"], "待人工复核")
        self.assertEqual(review["actionLabel"], "继续人工复核")


if __name__ == "__main__":
    unittest.main()
