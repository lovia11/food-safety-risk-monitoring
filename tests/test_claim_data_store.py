import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.claim_analysis import write_claim_analysis
from src.data_store import (
    DataStore,
    ProductFilterValidationError,
    make_evidence_id,
    make_snapshot_id,
)
from src.runtime import read_json, write_json
from tests.test_data_store import (
    PROJECT_ROOT,
    create_run,
    write_declared_origin_artifact,
    write_health_food_identity_artifact,
)


def write_claim_artifact(run_root: Path, product_id: str = "123") -> dict:
    snapshot_id = make_snapshot_id(run_root.name, product_id)
    analysis = read_json(run_root / "products" / product_id / "analysis.json")
    records = [
        {
            **item,
            "evidenceId": make_evidence_id(snapshot_id, ordinal),
            "snapshotId": snapshot_id,
        }
        for ordinal, item in enumerate(analysis.get("evidence_details") or [], start=1)
    ]
    return write_claim_analysis(
        run_root / "products" / product_id,
        snapshot_id,
        records,
        generated_at="2026-09-14T10:00:00+08:00",
    )


class ClaimDataStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.output_root = self.root / "output"
        self.store = DataStore(self.root / "data" / "app.db", self.output_root)
        self.store.initialize()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_schema_10_to_11_is_additive_and_preserves_human_and_domain_state(self):
        run_root = create_run(self.output_root, "schema10_claim_migration")
        write_declared_origin_artifact(run_root, "123", [("中国大陆", "dom_parameter")])
        write_health_food_identity_artifact(run_root, "123")
        self.store.import_monitor_config(
            PROJECT_ROOT / "config" / "monitor_targets.development.json"
        )
        self.store.import_run(run_root)
        snapshot_id = make_snapshot_id(run_root.name, "123")
        self.store.update_review(snapshot_id, "recommend_follow_up", "保留人工复核")
        with sqlite3.connect(self.store.database_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                "INSERT INTO sampling_list_memberships VALUES (?, ?, ?, ?, ?, ?)",
                (
                    "123",
                    snapshot_id,
                    run_root.name,
                    "product_overview",
                    "2026-09-14T09:00:00+08:00",
                    "2026-09-14T09:00:00+08:00",
                ),
            )
        before = self.store.table_counts()
        with sqlite3.connect(self.store.database_path) as connection:
            connection.executescript(
                """
                DROP TABLE claim_signal_mentions;
                DROP TABLE claim_signals;
                DROP TABLE claim_mentions;
                ALTER TABLE product_snapshots DROP COLUMN claim_analysis_path;
                ALTER TABLE product_snapshots DROP COLUMN claim_analysis_status;
                PRAGMA user_version = 10;
                """
            )

        migrated = DataStore(self.store.database_path, self.output_root)
        migrated.initialize()
        after = migrated.table_counts()
        with sqlite3.connect(self.store.database_path) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            snapshot_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(product_snapshots)")
            }
        self.assertEqual(version, 12)
        self.assertTrue(
            {"claim_analysis_status", "claim_analysis_path"} <= snapshot_columns
        )
        for table, count in before.items():
            if table not in {
                "claim_mentions",
                "claim_signals",
                "claim_signal_mentions",
            }:
                self.assertEqual(after[table], count, table)
        self.assertEqual(migrated.get_snapshot(snapshot_id)["review"]["note"], "保留人工复核")
        self.assertEqual(after["sampling_list_memberships"], 1)
        self.assertEqual(after["product_facts"], 1)
        self.assertEqual(after["health_food_identities"], 1)
        self.assertGreater(after["monitor_targets"], 0)

    def test_artifact_projects_idempotently_and_rebuilds_without_upstream_stages(self):
        run_root = create_run(self.output_root, "claim_rebuild")
        artifact = write_claim_artifact(run_root)
        first = self.store.import_run(run_root)
        second = self.store.import_run(run_root)
        snapshot_id = make_snapshot_id(run_root.name, "123")
        detail = self.store.get_snapshot(snapshot_id)
        self.assertEqual(first["claim_mentions"], len(artifact["claimMentions"]))
        self.assertEqual(second["claim_mentions"], len(artifact["claimMentions"]))
        self.assertEqual(detail["claimAnalysisStatus"], "complete")
        self.assertEqual(detail["claimMentions"], artifact["claimMentions"])
        self.assertEqual(detail["claimSignals"], artifact["claimSignals"])
        self.assertEqual(detail["detectedEffects"], ["助眠"])

        rebuilt = DataStore(self.root / "rebuilt" / "app.db", self.output_root)
        rebuilt.initialize()
        rebuilt.import_run(run_root)
        rebuilt_detail = rebuilt.get_snapshot(snapshot_id)
        self.assertEqual(rebuilt_detail["claimMentions"], artifact["claimMentions"])
        self.assertEqual(rebuilt_detail["claimSignals"], artifact["claimSignals"])

    def test_complete_zero_claim_and_missing_artifact_have_distinct_statuses(self):
        zero_run = create_run(self.output_root, "claim_zero", effect="")
        write_claim_artifact(zero_run)
        missing_run = create_run(self.output_root, "claim_missing", product_id="456")
        self.store.import_run(zero_run)
        self.store.import_run(missing_run)
        zero = self.store.get_snapshot(make_snapshot_id("claim_zero", "123"))
        missing = self.store.get_snapshot(make_snapshot_id("claim_missing", "456"))
        self.assertEqual(zero["claimAnalysisStatus"], "complete")
        self.assertEqual(zero["claimMentions"], [])
        self.assertEqual(zero["claimSignals"], [])
        self.assertEqual(missing["claimAnalysisStatus"], "not_generated")
        self.assertEqual(missing["claimMentions"], [])
        self.assertEqual(missing["claimSignals"], [])

    def test_invalid_reimport_clears_projection_atomically_and_preserves_review(self):
        run_root = create_run(self.output_root, "claim_invalid_reimport")
        write_claim_artifact(run_root)
        self.store.import_run(run_root)
        snapshot_id = make_snapshot_id(run_root.name, "123")
        self.store.update_review(snapshot_id, "no_further_action", "人工结论不受影响")
        path = run_root / "products" / "123" / "claim_analysis.json"
        payload = read_json(path)
        payload["claimMentions"][0]["evidenceId"] = "unknown-evidence"
        write_json(path, payload)
        self.store.import_run(run_root)
        detail = self.store.get_snapshot(snapshot_id)
        self.assertEqual(detail["claimAnalysisStatus"], "error")
        self.assertEqual(detail["claimMentions"], [])
        self.assertEqual(detail["claimSignals"], [])
        self.assertEqual(detail["review"]["status"], "no_further_action")
        self.assertEqual(detail["review"]["note"], "人工结论不受影响")

    def test_claims_are_snapshot_scoped_for_the_same_product(self):
        first_run = create_run(self.output_root, "claim_snapshot_a", product_id="same")
        second_run = create_run(
            self.output_root, "claim_snapshot_b", product_id="same", effect=""
        )
        write_claim_artifact(first_run, "same")
        write_claim_artifact(second_run, "same")
        self.store.import_run(first_run)
        self.store.import_run(second_run)
        first = self.store.get_snapshot(make_snapshot_id("claim_snapshot_a", "same"))
        second = self.store.get_snapshot(make_snapshot_id("claim_snapshot_b", "same"))
        self.assertEqual(len(first["claimSignals"]), 1)
        self.assertEqual(second["claimSignals"], [])

    def test_product_projection_exposes_v2_claim_summary_without_legacy_fallback(self):
        claimed_run = create_run(
            self.output_root,
            "claim_list_complete",
            product_id="claimed",
            effect="助眠",
            collected_at="2026-09-13T10:00:00+08:00",
        )
        legacy_only_run = create_run(
            self.output_root,
            "claim_list_legacy_only",
            product_id="legacy-only",
            effect="助眠",
            collected_at="2026-09-14T10:00:00+08:00",
        )
        write_claim_artifact(claimed_run, "claimed")
        self.store.import_run(claimed_run)
        self.store.import_run(legacy_only_run)

        products = {
            item["productId"]: item for item in self.store.list_products()
        }
        claimed = products["claimed"]
        legacy_only = products["legacy-only"]
        self.assertEqual(claimed["claimAnalysisStatus"], "complete")
        self.assertEqual(
            claimed["claimSignalSummaries"],
            [
                {
                    "claimSignalId": claimed["claimSignalSummaries"][0]["claimSignalId"],
                    "claimType": "sleep_related",
                    "displayLabel": "睡眠相关宣传",
                    "mentionCount": 1,
                    "taxonomyVersion": "claim-taxonomy-v2.0",
                    "status": "normalized",
                }
            ],
        )
        self.assertEqual(legacy_only["detectedEffects"], ["助眠"])
        self.assertEqual(legacy_only["claimAnalysisStatus"], "not_generated")
        self.assertEqual(legacy_only["claimSignalSummaries"], [])

    def test_claim_type_filter_is_exact_snapshot_scoped_and_ignores_legacy_effect(self):
        older = create_run(
            self.output_root,
            "claim_filter_old",
            product_id="same",
            effect="助眠",
            collected_at="2026-09-12T10:00:00+08:00",
        )
        newer = create_run(
            self.output_root,
            "claim_filter_new",
            product_id="same",
            effect="助眠",
            collected_at="2026-09-13T10:00:00+08:00",
        )
        legacy_only = create_run(
            self.output_root,
            "claim_filter_legacy",
            product_id="legacy",
            effect="助眠",
            collected_at="2026-09-14T10:00:00+08:00",
        )
        write_claim_artifact(older, "same")
        self.store.import_run(older)
        self.store.import_run(newer)
        self.store.import_run(legacy_only)

        default_same = next(
            item for item in self.store.list_products() if item["productId"] == "same"
        )
        self.assertEqual(default_same["taskId"], "claim_filter_new")
        self.assertEqual(default_same["claimAnalysisStatus"], "not_generated")

        filtered = self.store.list_products(claim_type="sleep_related")
        self.assertEqual([item["productId"] for item in filtered], ["same"])
        self.assertEqual(filtered[0]["taskId"], "claim_filter_old")
        self.assertEqual(filtered[0]["claimAnalysisStatus"], "complete")
        self.assertEqual(filtered[0]["claimSignalSummaries"][0]["claimType"], "sleep_related")
        self.assertEqual(self.store.count_products(claim_type="sleep_related"), 1)
        with self.assertRaises(ProductFilterValidationError):
            self.store.list_products(claim_type="not-a-governed-claim")

    def test_filter_options_use_governed_claim_type_labels_and_keep_legacy_effects(self):
        run_root = create_run(self.output_root, "claim_filter_options", effect="助眠")
        self.store.import_run(run_root)
        options = self.store.list_product_filter_options()
        self.assertIn({"value": "助眠", "label": "助眠"}, options["effects"])
        self.assertIn(
            {"value": "sleep_related", "label": "睡眠相关宣传"},
            options["claimTypes"],
        )
        self.assertEqual(len(options["claimTypes"]), 5)


if __name__ == "__main__":
    unittest.main()
