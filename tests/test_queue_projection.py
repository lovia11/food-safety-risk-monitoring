import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.data_store import DataStore
from src.sampling_store import SamplingStore
from tests.test_data_store import create_run


class QueueProjectionTest(unittest.TestCase):
    def test_pending_new_snapshot_stays_pending_when_product_membership_uses_old_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            create_run(output, "run-old", product_id="123")
            create_run(output, "run-new", product_id="123")
            store = DataStore(root / "app.db", output)
            store.initialize()
            store.import_all_runs()

            old_snapshot = store.list_products(task_id="run-old")[0]
            store.update_review(
                old_snapshot["snapshotId"], "recommend_follow_up", "旧快照建议跟进"
            )
            SamplingStore(store.database_path).add_from_snapshot(
                old_snapshot["snapshotId"], "inspection_workspace"
            )

            new_snapshot = store.list_products(task_id="run-new")[0]
            self.assertEqual(new_snapshot["review"]["status"], "pending")
            self.assertTrue(new_snapshot["sampling"]["inCurrentList"])
            self.assertEqual(
                new_snapshot["sampling"]["sourceSnapshotId"],
                old_snapshot["snapshotId"],
            )
            self.assertEqual(new_snapshot["sampling"]["decisionStatus"], "pending")
            pending_queue = [
                item
                for item in store.list_products(task_id="run-new")
                if item["sampling"]["decisionStatus"] == "pending"
            ]
            self.assertEqual(
                [item["snapshotId"] for item in pending_queue],
                [new_snapshot["snapshotId"]],
            )

    def test_product_snapshot_projection_includes_one_representative_evidence_and_counts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            create_run(output, "run-a", product_id="123")
            store = DataStore(root / "app.db", output)
            store.initialize()
            store.import_all_runs()
            snapshot_id = store.list_products(task_id="run-a")[0]["snapshotId"]
            connection = sqlite3.connect(store.database_path)
            try:
                connection.execute(
                    """
                    INSERT INTO evidence (
                        evidence_id, snapshot_id, ordinal, effect, text,
                        matched_keywords_json, source_type, source_label,
                        content_origin, source_path, line_number
                    ) VALUES (?, ?, ?, ?, ?, '[]', ?, ?, ?, ?, ?)
                    """,
                    (
                        "aaa-ugc", snapshot_id, 99, "助眠", "用户评价辅助线索",
                        "review", "用户评价", "user_generated", "reviews.json", 1,
                    ),
                )
                connection.commit()
            finally:
                connection.close()
            projected = store.list_products(task_id="run-a")[0]
            self.assertEqual(projected["counts"]["evidence"], 2)
            self.assertEqual(projected["counts"]["sellerManagedEvidence"], 1)
            self.assertEqual(projected["counts"]["ugcEvidence"], 1)
            self.assertEqual(
                projected["representativeEvidence"],
                {
                    "text": "帮助睡眠",
                    "contentOrigin": "seller_managed",
                    "sourceLabel": "详情图 OCR",
                },
            )


if __name__ == "__main__":
    unittest.main()
