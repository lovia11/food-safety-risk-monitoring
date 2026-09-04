import copy
import contextlib
import io
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.data_store import DataStore, DataStoreError, main as data_store_main
from src.risk_substance_reference import (
    RiskSubstanceConfigValidationError,
    validate_risk_substance_config,
)
from src.runtime import write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INSPECTION_CONFIG = PROJECT_ROOT / "config" / "inspection_reference.json"
RISK_TABLES = {"risk_mapping_datasets", "risk_substance_mappings"}


def risk_dataset(
    *,
    dataset_id: str = "synthetic-risk-dataset",
    status: str = "development_seed",
    include_mapping: bool = True,
    target_type: str = "substance",
) -> dict:
    payload = {
        "schema_version": 1,
        "dataset_id": dataset_id,
        "dataset_version": "test-1",
        "dataset_status": status,
        "source_name": "合成测试数据源",
        "source_reference": "test://synthetic-risk-dataset",
        "source_date": "2026-09-01",
        "collected_at": "2026-09-04T10:00:00+08:00",
        "verified_at": (
            "2026-09-04T11:00:00+08:00"
            if status == "verified_reference"
            else None
        ),
        "description": "仅用于自动化测试，不是正式风险映射。",
        "mappings": [],
    }
    if not include_mapping:
        return payload
    payload["mappings"] = [
        {
            "mapping_id": "synthetic-mapping-1",
            "dataset_id": dataset_id,
            "risk_category": "synthetic_risk",
            "risk_label": "合成测试风险",
            "target_type": target_type,
            "substance_id": (
                "synthetic-substance-1" if target_type == "substance" else None
            ),
            "target_group_label": (
                "合成测试物质组" if target_type == "substance_group" else None
            ),
            "evidence_grade": "A" if status == "verified_reference" else "C",
            "basis_type": (
                "current_official_guidance"
                if status == "verified_reference"
                else "research_evidence"
            ),
            "temporal_status": "current",
            "product_scope": "合成测试产品范围",
            "source_name": "合成测试映射来源",
            "source_reference": "test://synthetic-mapping-1",
            "source_date": "2026-09-01",
            "source_basis_text": "合成测试来源摘要。",
            "note": "synthetic test only",
        }
    ]
    return payload


class RiskSubstanceReferenceValidationTest(unittest.TestCase):
    def test_valid_development_fixture_is_normalized(self):
        normalized = validate_risk_substance_config(risk_dataset())
        self.assertEqual(normalized["dataset_status"], "development_seed")
        self.assertEqual(normalized["mappings"][0]["risk_category"], "synthetic_risk")

    def test_all_contract_fields_must_be_present(self):
        payload = risk_dataset()
        del payload["mappings"][0]["product_scope"]
        with self.assertRaisesRegex(RiskSubstanceConfigValidationError, "缺少字段"):
            validate_risk_substance_config(payload)

    def test_reference_pending_mappings_must_be_empty(self):
        pending = risk_dataset(status="reference_pending", include_mapping=False)
        self.assertEqual(
            validate_risk_substance_config(pending)["mappings"], []
        )
        pending["mappings"] = risk_dataset()["mappings"]
        with self.assertRaisesRegex(
            RiskSubstanceConfigValidationError, "reference_pending"
        ):
            validate_risk_substance_config(pending)

    def test_verified_reference_requires_verified_at(self):
        payload = risk_dataset(status="verified_reference")
        payload["verified_at"] = None
        with self.assertRaisesRegex(RiskSubstanceConfigValidationError, "verified_at"):
            validate_risk_substance_config(payload)

    def test_verified_reference_requires_at_least_one_mapping(self):
        payload = risk_dataset(status="verified_reference", include_mapping=False)
        with self.assertRaisesRegex(RiskSubstanceConfigValidationError, "一条Mapping"):
            validate_risk_substance_config(payload)

    def test_verified_mapping_requires_complete_provenance(self):
        for field, value in (
            ("source_name", None),
            ("source_reference", ""),
            ("source_date", None),
            ("source_basis_text", ""),
        ):
            with self.subTest(field=field):
                payload = risk_dataset(status="verified_reference")
                payload["mappings"][0][field] = value
                with self.assertRaisesRegex(
                    RiskSubstanceConfigValidationError, field
                ):
                    validate_risk_substance_config(payload)

    def test_verified_reference_rejects_placeholder_values(self):
        payload = risk_dataset(status="verified_reference")
        payload["mappings"][0]["note"] = "unknown"
        with self.assertRaisesRegex(RiskSubstanceConfigValidationError, "占位值"):
            validate_risk_substance_config(payload)

    def test_duplicate_mapping_id_is_rejected(self):
        payload = risk_dataset()
        payload["mappings"].append(copy.deepcopy(payload["mappings"][0]))
        with self.assertRaisesRegex(RiskSubstanceConfigValidationError, "mapping_id重复"):
            validate_risk_substance_config(payload)

    def test_substance_target_requires_only_substance_id(self):
        normalized = validate_risk_substance_config(risk_dataset())
        mapping = normalized["mappings"][0]
        self.assertEqual(mapping["substance_id"], "synthetic-substance-1")
        self.assertIsNone(mapping["target_group_label"])

    def test_substance_group_target_requires_only_group_label(self):
        normalized = validate_risk_substance_config(
            risk_dataset(target_type="substance_group")
        )
        mapping = normalized["mappings"][0]
        self.assertIsNone(mapping["substance_id"])
        self.assertEqual(mapping["target_group_label"], "合成测试物质组")

    def test_target_rejects_both_substance_and_group(self):
        payload = risk_dataset()
        payload["mappings"][0]["target_group_label"] = "合成测试物质组"
        with self.assertRaisesRegex(RiskSubstanceConfigValidationError, "必须仅包含"):
            validate_risk_substance_config(payload)

    def test_target_rejects_neither_substance_nor_group(self):
        payload = risk_dataset()
        payload["mappings"][0]["substance_id"] = None
        with self.assertRaisesRegex(RiskSubstanceConfigValidationError, "必须仅包含"):
            validate_risk_substance_config(payload)

    def test_evidence_grade_is_closed(self):
        payload = risk_dataset()
        payload["mappings"][0]["evidence_grade"] = "D"
        with self.assertRaisesRegex(RiskSubstanceConfigValidationError, "evidence_grade"):
            validate_risk_substance_config(payload)

    def test_grade_a_cannot_be_historical(self):
        payload = risk_dataset(status="verified_reference")
        payload["mappings"][0]["temporal_status"] = "historical"
        with self.assertRaisesRegex(RiskSubstanceConfigValidationError, "A级"):
            validate_risk_substance_config(payload)

    def test_current_regulatory_source_rejects_historical_for_grade_b(self):
        payload = risk_dataset()
        mapping = payload["mappings"][0]
        mapping["basis_type"] = "current_regulatory_source"
        mapping["evidence_grade"] = "B"
        mapping["temporal_status"] = "historical"
        with self.assertRaisesRegex(
            RiskSubstanceConfigValidationError, "current_regulatory_source"
        ):
            validate_risk_substance_config(payload)

        mapping["basis_type"] = "official_case"
        self.assertEqual(
            validate_risk_substance_config(payload)["mappings"][0][
                "temporal_status"
            ],
            "historical",
        )

    def test_current_official_guidance_rejects_historical_for_grade_c(self):
        payload = risk_dataset()
        mapping = payload["mappings"][0]
        mapping["basis_type"] = "current_official_guidance"
        mapping["evidence_grade"] = "C"
        mapping["temporal_status"] = "historical"
        with self.assertRaisesRegex(
            RiskSubstanceConfigValidationError, "current_official_guidance"
        ):
            validate_risk_substance_config(payload)

        mapping["basis_type"] = "research_evidence"
        self.assertEqual(
            validate_risk_substance_config(payload)["mappings"][0][
                "temporal_status"
            ],
            "historical",
        )

    def test_historical_sampling_plan_cannot_be_current(self):
        payload = risk_dataset()
        mapping = payload["mappings"][0]
        mapping["basis_type"] = "historical_sampling_plan"
        mapping["evidence_grade"] = "B"
        mapping["temporal_status"] = "current"
        with self.assertRaisesRegex(RiskSubstanceConfigValidationError, "historical"):
            validate_risk_substance_config(payload)

    def test_historical_sampling_plan_cannot_be_grade_a(self):
        payload = risk_dataset()
        mapping = payload["mappings"][0]
        mapping["basis_type"] = "historical_sampling_plan"
        mapping["evidence_grade"] = "A"
        mapping["temporal_status"] = "historical"
        with self.assertRaises(RiskSubstanceConfigValidationError):
            validate_risk_substance_config(payload)

    def test_basis_type_is_closed(self):
        payload = risk_dataset()
        payload["mappings"][0]["basis_type"] = "synthetic_unknown_basis"
        with self.assertRaisesRegex(RiskSubstanceConfigValidationError, "basis_type"):
            validate_risk_substance_config(payload)

    def test_temporal_status_is_closed(self):
        payload = risk_dataset()
        payload["mappings"][0]["temporal_status"] = "future"
        with self.assertRaisesRegex(RiskSubstanceConfigValidationError, "temporal_status"):
            validate_risk_substance_config(payload)

    def test_risk_category_must_be_identifier_but_is_not_closed_enum(self):
        payload = risk_dataset()
        payload["mappings"][0]["risk_category"] = "future_category_42"
        self.assertEqual(
            validate_risk_substance_config(payload)["mappings"][0]["risk_category"],
            "future_category_42",
        )
        payload["mappings"][0]["risk_category"] = "不合法 分类"
        with self.assertRaisesRegex(RiskSubstanceConfigValidationError, "risk_category"):
            validate_risk_substance_config(payload)


class RiskSubstanceReferencePersistenceTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.store = DataStore(self.root / "data" / "app.db", self.root / "output")
        self.store.initialize()

    def tearDown(self):
        self.temporary.cleanup()

    def _write(self, payload: dict, name: str = "risk.json") -> Path:
        path = self.root / name
        write_json(path, payload)
        return path

    def _seed_substances(
        self,
        *substance_ids: str,
        dataset_status: str = "development_seed",
    ) -> None:
        now = "2026-09-04T10:00:00+08:00"
        with sqlite3.connect(self.store.database_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                """
                INSERT OR IGNORE INTO inspection_datasets (
                    dataset_id, dataset_version, dataset_status, source_name,
                    source_reference, description, imported_at, updated_at
                ) VALUES ('synthetic-inspection', 'test-1', ?,
                    '合成测试来源', 'test://synthetic-inspection', '', ?, ?)
                """,
                (dataset_status, now, now),
            )
            for ordinal, substance_id in enumerate(substance_ids, start=1):
                connection.execute(
                    """
                    INSERT OR IGNORE INTO inspection_substances (
                        substance_id, dataset_id, canonical_name, updated_at
                    ) VALUES (?, 'synthetic-inspection', ?, ?)
                    """,
                    (substance_id, f"合成测试物质{ordinal}", now),
                )

    def test_import_existing_substance_target_succeeds(self):
        self._seed_substances("synthetic-substance-1")
        result = self.store.import_risk_substance_config(self._write(risk_dataset()))
        self.assertEqual(result, {"dataset": 1, "mappings": 1})
        self.assertEqual(self.store.table_counts()["risk_substance_mappings"], 1)

    def test_import_unknown_substance_rejects_entire_transaction(self):
        with self.assertRaisesRegex(DataStoreError, "substance_id不存在"):
            self.store.import_risk_substance_config(self._write(risk_dataset()))
        counts = self.store.table_counts()
        self.assertEqual(counts["risk_mapping_datasets"], 0)
        self.assertEqual(counts["risk_substance_mappings"], 0)

    def test_verified_risk_rejects_non_verified_inspection_substance_and_rolls_back(self):
        self._seed_substances("synthetic-substance-1")

        for inspection_status in ("development_seed", "reference_pending"):
            with self.subTest(inspection_status=inspection_status):
                with sqlite3.connect(self.store.database_path) as connection:
                    connection.execute(
                        "UPDATE inspection_datasets SET dataset_status = ?",
                        (inspection_status,),
                    )
                with self.assertRaisesRegex(
                    DataStoreError, "verified_reference Dataset"
                ):
                    self.store.import_risk_substance_config(
                        self._write(risk_dataset(status="verified_reference"))
                    )
                counts = self.store.table_counts()
                self.assertEqual(counts["risk_mapping_datasets"], 0)
                self.assertEqual(counts["risk_substance_mappings"], 0)

    def test_verified_risk_accepts_verified_inspection_substance(self):
        self._seed_substances(
            "synthetic-substance-1", dataset_status="verified_reference"
        )

        result = self.store.import_risk_substance_config(
            self._write(risk_dataset(status="verified_reference"))
        )
        self.assertEqual(result, {"dataset": 1, "mappings": 1})
        self.assertEqual(self.store.table_counts()["risk_substance_mappings"], 1)

    def test_group_target_does_not_require_substance_foreign_key(self):
        payload = risk_dataset(target_type="substance_group")
        self.store.import_risk_substance_config(self._write(payload))
        self.assertEqual(self.store.table_counts()["risk_substance_mappings"], 1)

    def test_repeated_import_is_idempotent(self):
        payload = risk_dataset(target_type="substance_group")
        path = self._write(payload)
        expected = {"dataset": 1, "mappings": 1}
        self.assertEqual(self.store.import_risk_substance_config(path), expected)
        first = self.store.table_counts()
        self.assertEqual(self.store.import_risk_substance_config(path), expected)
        self.assertEqual(self.store.table_counts(), first)

    def test_cli_import_is_explicit_and_supported(self):
        config_path = self._write(
            risk_dataset(target_type="substance_group"), "cli-risk.json"
        )
        database = self.root / "cli" / "app.db"
        with contextlib.redirect_stdout(io.StringIO()):
            result = data_store_main(
                [
                    "--output-root",
                    str(self.root / "cli-output"),
                    "--database",
                    str(database),
                    "--import-risk-substance-config",
                    str(config_path),
                ]
            )
        self.assertEqual(result, 0)
        with sqlite3.connect(database) as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM risk_substance_mappings"
            ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_mapping_id_cannot_change_risk_category(self):
        self._seed_substances("synthetic-substance-1")
        payload = risk_dataset()
        self.store.import_risk_substance_config(self._write(payload, "initial.json"))
        changed = copy.deepcopy(payload)
        changed["mappings"][0]["risk_category"] = "changed_risk"
        with self.assertRaisesRegex(DataStoreError, "不能改绑"):
            self.store.import_risk_substance_config(self._write(changed, "changed.json"))

    def test_mapping_id_cannot_change_substance_to_group(self):
        self._seed_substances("synthetic-substance-1")
        payload = risk_dataset()
        self.store.import_risk_substance_config(self._write(payload, "initial.json"))
        changed = copy.deepcopy(payload)
        mapping = changed["mappings"][0]
        mapping["target_type"] = "substance_group"
        mapping["substance_id"] = None
        mapping["target_group_label"] = "合成测试物质组"
        with self.assertRaisesRegex(DataStoreError, "不能改绑"):
            self.store.import_risk_substance_config(self._write(changed, "changed.json"))

    def test_mapping_id_cannot_change_substance_id(self):
        self._seed_substances("synthetic-substance-1", "synthetic-substance-2")
        payload = risk_dataset()
        self.store.import_risk_substance_config(self._write(payload, "initial.json"))
        changed = copy.deepcopy(payload)
        changed["mappings"][0]["substance_id"] = "synthetic-substance-2"
        with self.assertRaisesRegex(DataStoreError, "不能改绑"):
            self.store.import_risk_substance_config(self._write(changed, "changed.json"))

    def test_mapping_id_cannot_change_dataset_or_group_label(self):
        payload = risk_dataset(target_type="substance_group")
        self.store.import_risk_substance_config(self._write(payload, "initial.json"))

        changed_dataset = copy.deepcopy(payload)
        changed_dataset["dataset_id"] = "another-risk-dataset"
        changed_dataset["mappings"][0]["dataset_id"] = "another-risk-dataset"
        with self.assertRaisesRegex(DataStoreError, "不能改绑"):
            self.store.import_risk_substance_config(
                self._write(changed_dataset, "changed-dataset.json")
            )

        changed_group = copy.deepcopy(payload)
        changed_group["mappings"][0]["target_group_label"] = "另一个合成测试组"
        with self.assertRaisesRegex(DataStoreError, "不能改绑"):
            self.store.import_risk_substance_config(
                self._write(changed_group, "changed-group.json")
            )

    def test_dataset_only_allows_pending_to_verified_transition(self):
        pending = risk_dataset(status="reference_pending", include_mapping=False)
        self.store.import_risk_substance_config(self._write(pending, "pending.json"))
        verified = risk_dataset(
            status="verified_reference", target_type="substance_group"
        )
        self.store.import_risk_substance_config(self._write(verified, "verified.json"))
        downgrade = risk_dataset(status="reference_pending", include_mapping=False)
        with self.assertRaisesRegex(RiskSubstanceConfigValidationError, "不能从"):
            self.store.import_risk_substance_config(
                self._write(downgrade, "downgrade.json")
            )

    def test_failed_import_rolls_back_dataset_and_all_mappings(self):
        initial = risk_dataset(include_mapping=False)
        self.store.import_risk_substance_config(self._write(initial, "initial.json"))
        failing = risk_dataset(target_type="substance_group")
        failing["dataset_version"] = "must-rollback"
        unknown = copy.deepcopy(risk_dataset()["mappings"][0])
        unknown["mapping_id"] = "synthetic-mapping-unknown-substance"
        unknown["dataset_id"] = failing["dataset_id"]
        unknown["substance_id"] = "missing-substance"
        failing["mappings"].append(unknown)

        with self.assertRaisesRegex(DataStoreError, "substance_id不存在"):
            self.store.import_risk_substance_config(
                self._write(failing, "failing.json")
            )
        with sqlite3.connect(self.store.database_path) as connection:
            version = connection.execute(
                "SELECT dataset_version FROM risk_mapping_datasets"
            ).fetchone()[0]
            mapping_count = connection.execute(
                "SELECT COUNT(*) FROM risk_substance_mappings"
            ).fetchone()[0]
        self.assertEqual(version, "test-1")
        self.assertEqual(mapping_count, 0)

    def test_v6_upgrade_preserves_all_old_business_and_inspection_data(self):
        database = self.root / "legacy-v6.db"
        legacy = DataStore(database, self.root / "legacy-output")
        legacy.initialize()
        legacy.import_inspection_config(INSPECTION_CONFIG)
        now = "2026-09-04T10:00:00+08:00"
        with sqlite3.connect(database) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(
                f"""
                INSERT INTO tasks (
                    task_id, keyword, stage, run_path, updated_at, task_type
                ) VALUES ('v6-task', '测试', 'completed', 'v6-task', '{now}', 'quick');
                INSERT INTO products VALUES ('v6-product', '{now}', '{now}');
                INSERT INTO product_snapshots (
                    snapshot_id, product_id, task_id, product_name, product_path,
                    updated_at
                ) VALUES (
                    'v6-snapshot', 'v6-product', 'v6-task', '旧商品',
                    'products/v6-product', '{now}'
                );
                INSERT INTO reviews VALUES (
                    'v6-snapshot', 'recommend_follow_up', 'v6人工备注', '{now}'
                );
                INSERT INTO monitor_datasets VALUES (
                    'v6-monitor-dataset', '1', 'development_seed', '旧来源',
                    '旧引用', NULL, NULL, NULL, '', '{now}', '{now}'
                );
                INSERT INTO monitor_targets (
                    target_id, dataset_id, standard_name, target_type, source_name,
                    source_reference, enabled, updated_at
                ) VALUES (
                    'v6-target', 'v6-monitor-dataset', '旧对象', 'food_medicine',
                    '旧来源', '旧引用', 1, '{now}'
                );
                DROP TABLE risk_substance_mappings;
                DROP TABLE risk_mapping_datasets;
                PRAGMA user_version = 6;
                """
            )

        upgraded = DataStore(database, self.root / "legacy-output")
        upgraded.initialize()
        with sqlite3.connect(database) as connection:
            schema_version = connection.execute("PRAGMA user_version").fetchone()[0]
            inspection_counts = {
                "methods": connection.execute(
                    "SELECT COUNT(*) FROM inspection_methods"
                ).fetchone()[0],
                "substances": connection.execute(
                    "SELECT COUNT(*) FROM inspection_substances"
                ).fetchone()[0],
                "method_substances": connection.execute(
                    "SELECT COUNT(*) FROM inspection_method_substances"
                ).fetchone()[0],
                "applicabilities": connection.execute(
                    "SELECT COUNT(*) FROM inspection_method_applicabilities"
                ).fetchone()[0],
                "contexts": connection.execute(
                    "SELECT COUNT(*) FROM substance_regulatory_contexts"
                ).fetchone()[0],
            }
            old_counts = {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in (
                    "products",
                    "reviews",
                    "monitor_datasets",
                    "monitor_targets",
                )
            }
            risk_counts = {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in RISK_TABLES
            }
            review_note = connection.execute(
                "SELECT review_note FROM reviews WHERE snapshot_id='v6-snapshot'"
            ).fetchone()[0]

        self.assertEqual(schema_version, 7)
        self.assertEqual(
            inspection_counts,
            {
                "methods": 5,
                "substances": 117,
                "method_substances": 132,
                "applicabilities": 37,
                "contexts": 1,
            },
        )
        self.assertEqual(set(old_counts.values()), {1})
        self.assertEqual(review_note, "v6人工备注")
        self.assertEqual(set(risk_counts.values()), {0})


if __name__ == "__main__":
    unittest.main()
