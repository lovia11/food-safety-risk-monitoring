import tempfile
import unittest
from pathlib import Path

from src.data_store import DataStore
from src.sampling_store import (
    SamplingMembershipNotFoundError,
    SamplingStore,
    SamplingValidationError,
)
from tests.test_data_store import create_run


class SamplingStoreTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.output_root = self.root / "output"
        create_run(self.output_root, "run-a", product_id="123")
        create_run(
            self.output_root,
            "run-b",
            product_id="123",
            collected_at="2026-09-03T10:00:00+08:00",
        )
        self.data_store = DataStore(self.root / "data" / "app.db", self.output_root)
        self.data_store.initialize()
        self.data_store.import_all_runs()
        self.store = SamplingStore(self.data_store.database_path)
        self.snapshots = self.data_store.list_product_snapshots("123")

    def tearDown(self):
        self.temporary.cleanup()

    def test_add_is_idempotent_and_does_not_replace_source_snapshot(self):
        first = self.store.add_from_snapshot(
            self.snapshots[1]["snapshotId"], "product_overview"
        )
        repeated = self.store.add_from_snapshot(
            self.snapshots[0]["snapshotId"], "inspection_workspace"
        )
        self.assertEqual(repeated["sourceSnapshotId"], first["sourceSnapshotId"])
        self.assertEqual(repeated["sourceTaskId"], first["sourceTaskId"])
        self.assertEqual(self.store.count_current(), 1)

    def test_low_level_add_and_remove_never_change_review(self):
        snapshot_id = self.snapshots[0]["snapshotId"]
        self.data_store.update_review(snapshot_id, "no_further_action", "保留")
        membership = self.store.add_from_snapshot(snapshot_id, "product_overview")
        removed = self.store.remove("123")
        self.assertEqual(removed, membership)
        review = self.data_store.get_snapshot(snapshot_id)["review"]
        self.assertEqual(review["status"], "no_further_action")
        self.assertEqual(review["note"], "保留")

    def test_remove_missing_and_invalid_origin_are_rejected(self):
        with self.assertRaises(SamplingMembershipNotFoundError):
            self.store.remove("missing")
        with self.assertRaises(SamplingValidationError):
            self.store.add_from_snapshot(self.snapshots[0]["snapshotId"], "forged")
        with self.assertRaises(SamplingValidationError):
            self.store.add(
                "forged-product",
                self.snapshots[0]["snapshotId"],
                "product_overview",
            )


if __name__ == "__main__":
    unittest.main()
