import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.data_store import DataStore
from tests.test_data_store import create_run


class QueueProjectionTest(unittest.TestCase):
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
