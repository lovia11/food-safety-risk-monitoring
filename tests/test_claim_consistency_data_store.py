from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.claim_consistency import write_claim_consistency_from_artifacts
from src.data_store import DataStore, make_snapshot_id
from src.runtime import read_json, write_json
from tests.test_claim_data_store import write_claim_artifact
from tests.test_data_store import create_run, write_health_food_identity_artifact


FRAMEWORK_ID = "hf-framework-non-nutrient-cn-2023"


def write_consistency_artifact(run_root: Path, product_id: str = "123") -> dict:
    write_claim_artifact(run_root, product_id)
    write_health_food_identity_artifact(run_root, product_id)
    identity_path = run_root / "products" / product_id / "health_food_identity.json"
    identity = read_json(identity_path)
    record = identity["officialLookup"]["record"]
    record["officialHealthFunctions"] = ["改善睡眠"]
    record["frameworkId"] = FRAMEWORK_ID
    write_json(identity_path, identity)
    return write_claim_consistency_from_artifacts(
        run_root / "products" / product_id,
        make_snapshot_id(run_root.name, product_id),
    )


class ClaimConsistencyDataStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.output_root = self.root / "output"
        self.database_path = self.root / "data" / "app.db"
        self.store = DataStore(self.database_path, self.output_root)
        self.store.initialize()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_schema_11_to_12_is_additive_and_preserves_business_state(self) -> None:
        run_root = create_run(self.output_root, "schema11_consistency")
        write_claim_artifact(run_root)
        write_health_food_identity_artifact(run_root, "123")
        self.store.import_run(run_root)
        snapshot_id = make_snapshot_id(run_root.name, "123")
        self.store.update_review(snapshot_id, "recommend_follow_up", "保留人工结论")
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                "INSERT INTO sampling_list_memberships VALUES (?, ?, ?, ?, ?, ?)",
                (
                    "123",
                    snapshot_id,
                    run_root.name,
                    "product_overview",
                    "2026-09-15T00:00:00+08:00",
                    "2026-09-15T00:00:00+08:00",
                ),
            )
        before = self.store.table_counts()
        with sqlite3.connect(self.database_path) as connection:
            connection.executescript(
                """
                DROP TABLE claim_consistency_claims;
                DROP TABLE claim_consistency_official_functions;
                DROP TABLE claim_consistency_assessments;
                ALTER TABLE product_snapshots DROP COLUMN claim_consistency_path;
                ALTER TABLE product_snapshots DROP COLUMN claim_consistency_status;
                PRAGMA user_version = 11;
                """
            )

        migrated = DataStore(self.database_path, self.output_root)
        migrated.initialize()
        after = migrated.table_counts()
        with sqlite3.connect(self.database_path) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(product_snapshots)")
            }
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        self.assertEqual(version, 14)
        self.assertTrue(
            {"claim_consistency_status", "claim_consistency_path"} <= columns
        )
        self.assertTrue(
            {
                "claim_consistency_assessments",
                "claim_consistency_official_functions",
                "claim_consistency_claims",
            }
            <= tables
        )
        for table, count in before.items():
            if not table.startswith("claim_consistency_"):
                self.assertEqual(after[table], count, table)
        detail = migrated.get_snapshot(snapshot_id)
        self.assertEqual(detail["review"]["note"], "保留人工结论")
        self.assertTrue(detail["sampling"]["inCurrentList"])
        self.assertEqual(detail["claimAnalysisStatus"], "complete")
        self.assertEqual(detail["healthFoodIdentity"]["state"], "verified_match")

    def test_artifact_projects_idempotently_and_rebuilds_without_upstream(self) -> None:
        run_root = create_run(self.output_root, "consistency_rebuild")
        artifact = write_consistency_artifact(run_root)
        first = self.store.import_run(run_root)
        second = self.store.import_run(run_root)
        snapshot_id = make_snapshot_id(run_root.name, "123")
        detail = self.store.get_snapshot(snapshot_id)
        self.assertEqual(first["claim_consistency_assessments"], 1)
        self.assertEqual(second["claim_consistency_assessments"], 1)
        self.assertEqual(detail["claimConsistencyStatus"], "complete")
        self.assertEqual(detail["claimConsistency"], artifact)
        self.assertEqual(
            detail["paths"]["claimConsistency"],
            "products/123/claim_consistency.json",
        )

        rebuilt = DataStore(self.root / "rebuilt" / "app.db", self.output_root)
        rebuilt.initialize()
        rebuilt.import_run(run_root)
        self.assertEqual(rebuilt.get_snapshot(snapshot_id)["claimConsistency"], artifact)

    def test_missing_error_and_invalid_reimport_have_distinct_atomic_states(self) -> None:
        missing_run = create_run(self.output_root, "consistency_missing")
        self.store.import_run(missing_run)
        missing = self.store.get_snapshot(
            make_snapshot_id(missing_run.name, "123")
        )
        self.assertEqual(missing["claimConsistencyStatus"], "not_generated")
        self.assertIsNone(missing["claimConsistency"])

        run_root = create_run(self.output_root, "consistency_invalid")
        write_consistency_artifact(run_root)
        self.store.import_run(run_root)
        snapshot_id = make_snapshot_id(run_root.name, "123")
        self.store.update_review(snapshot_id, "recommend_follow_up", "不得被副作用修改")
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                "INSERT INTO sampling_list_memberships VALUES (?, ?, ?, ?, ?, ?)",
                (
                    "123",
                    snapshot_id,
                    run_root.name,
                    "product_overview",
                    "2026-09-15T00:00:00+08:00",
                    "2026-09-15T00:00:00+08:00",
                ),
            )
        path = run_root / "products" / "123" / "claim_consistency.json"
        invalid = read_json(path)
        invalid["state"] = "compliant"
        write_json(path, invalid)
        self.store.import_run(run_root)
        detail = self.store.get_snapshot(snapshot_id)
        self.assertEqual(detail["claimConsistencyStatus"], "error")
        self.assertIsNone(detail["claimConsistency"])
        self.assertIsNone(detail["paths"]["claimConsistency"])
        self.assertEqual(detail["review"]["note"], "不得被副作用修改")
        self.assertTrue(detail["sampling"]["inCurrentList"])
        self.assertEqual(detail["detectedEffects"], ["助眠"])
        counts = self.store.table_counts()
        self.assertEqual(counts["claim_consistency_assessments"], 0)
        self.assertEqual(counts["claim_consistency_official_functions"], 0)
        self.assertEqual(counts["claim_consistency_claims"], 0)


if __name__ == "__main__":
    unittest.main()
