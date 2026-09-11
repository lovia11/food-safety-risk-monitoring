import tempfile
import unittest
from pathlib import Path

from src.data_store import DataStore
from src.local_api import task_business_dto
from src.pipeline_contract import project_task_flow
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

    def test_failed_task_is_interrupted_and_only_resumable_failure_can_continue(self):
        summary = self.store.get_task_business_summary("run-a")
        resumable = task_business_dto(
            {
                "task": {"stage": "failed"},
                "runtime": {"active": False, "resumable": True},
            },
            summary,
        )
        self.assertEqual(resumable["businessStatus"], "interrupted")
        self.assertEqual(resumable["actionLabel"], "继续任务")

        not_resumable = task_business_dto(
            {
                "task": {"stage": "failed"},
                "runtime": {"active": False, "resumable": False},
            },
            summary,
        )
        self.assertEqual(not_resumable["businessStatus"], "interrupted")
        self.assertEqual(not_resumable["actionLabel"], "查看执行结果")

        partial = task_business_dto(
            {
                "task": {"stage": "completed_with_errors"},
                "runtime": {"active": False, "resumable": True},
            },
            summary,
        )
        self.assertEqual(partial["businessStatus"], "partial_error")
        self.assertEqual(partial["actionLabel"], "查看执行结果")

    def test_terminal_task_does_not_mark_zero_of_one_analysis_as_done(self):
        summary = self.store.get_task_business_summary("run-a")
        archive = {
            **summary["archiveSummary"],
            "detailCompleted": 1,
            "detailTarget": 1,
            "analysisCompleted": 0,
            "analysisTarget": 1,
            "analysisFailed": 1,
            "pendingReview": 0,
            "completedReview": 0,
        }
        projected = task_business_dto(
            {
                "task": {"stage": "completed_with_errors"},
                "runtime": {"active": False, "resumable": False},
            },
            {**summary, "archiveSummary": archive},
        )
        states = {item["key"]: item["state"] for item in projected["flow"]}
        self.assertEqual(states["detail"], "done")
        self.assertEqual(states["analysis"], "failed")
        self.assertEqual(states["review"], "future")

    def test_analysis_flow_requires_real_failure_evidence(self):
        base = {
            "searchCandidates": 1,
            "detailCompleted": 1,
            "detailTarget": 1,
            "detailFailed": 0,
            "analysisTarget": 1,
            "pendingReview": 0,
            "completedReview": 0,
        }
        cases = (
            ("collection_completed", 0, 0, "future"),
            ("interrupted", 0, 0, "future"),
            ("completed_with_errors", 0, 1, "failed"),
            ("completed_with_errors", 1, 1, "partial"),
        )
        for stage, completed, failed, expected in cases:
            with self.subTest(stage=stage, completed=completed, failed=failed):
                flow = project_task_flow(
                    stage,
                    False,
                    {
                        **base,
                        "analysisCompleted": completed,
                        "analysisFailed": failed,
                        "analysisTarget": max(1, completed + failed),
                    },
                )
                states = {item["key"]: item["state"] for item in flow}
                self.assertEqual(states["analysis"], expected)


if __name__ == "__main__":
    unittest.main()
