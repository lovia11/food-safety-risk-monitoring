import copy
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.data_store import (
    DataStore,
    MonitorConfigValidationError,
)
from src.runtime import write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEVELOPMENT_CONFIG = PROJECT_ROOT / "config" / "monitor_targets.development.json"
REFERENCE_CONFIG = PROJECT_ROOT / "config" / "monitor_targets.reference.json"


def verified_dataset(
    *,
    dataset_id: str = "verified-food-medicine-test",
    target_id: str = "verified-target-1",
    query_id: str = "verified-query-1",
) -> dict:
    return {
        "schema_version": 2,
        "dataset_id": dataset_id,
        "dataset_version": "2026.09-test",
        "dataset_status": "verified_reference",
        "source_name": "测试用权威来源",
        "source_reference": "https://example.test/reference-document",
        "source_date": "2026-08-01",
        "collected_at": "2026-09-02T10:00:00+08:00",
        "verified_at": "2026-09-02T11:00:00+08:00",
        "description": "仅用于离线测试的数据集，不是项目正式目录。",
        "targets": [
            {
                "target_id": target_id,
                "dataset_id": dataset_id,
                "standard_name": "已核验测试对象",
                "target_type": "food_medicine",
                "source_name": "测试用权威来源",
                "source_reference": "https://example.test/reference-document",
                "source_date": "2026-08-01",
                "enabled": True,
                "queries": [
                    {
                        "query_id": query_id,
                        "target_id": target_id,
                        "query_text": "已核验测试对象",
                        "query_type": "base",
                        "order": 1,
                        "enabled": True,
                    }
                ],
            }
        ],
    }


class MonitorReferenceDataTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.store = DataStore(self.root / "data" / "app.db", self.root / "output")
        self.store.initialize()

    def tearDown(self):
        self.temporary.cleanup()

    def _write_config(self, payload: dict, name: str = "dataset.json") -> Path:
        path = self.root / name
        write_json(path, payload)
        return path

    def test_development_dataset_remains_importable_and_identified(self):
        result = self.store.import_monitor_config(DEVELOPMENT_CONFIG)
        self.assertEqual(result, {"datasets": 1, "targets": 1, "queries": 2})
        target = self.store.get_monitor_target("dev-food-medicine-suanzaoren")
        self.assertEqual(target["dataset_id"], "monitor-targets-development")
        self.assertEqual(target["dataset_status"], "development_seed")
        self.assertEqual(
            [query["query_text"] for query in target["queries"]],
            ["酸枣仁", "酸枣仁茶"],
        )

    def test_verified_reference_file_imports_all_disabled_targets(self):
        result = self.store.import_monitor_config(REFERENCE_CONFIG)
        self.assertEqual(result, {"datasets": 1, "targets": 106, "queries": 0})
        self.assertEqual(self.store.table_counts()["monitor_datasets"], 1)
        targets = self.store.list_monitor_targets()
        self.assertEqual(len(targets), 106)
        self.assertTrue(all(not target["enabled"] for target in targets))
        self.assertTrue(
            all(target["dataset_status"] == "verified_reference" for target in targets)
        )

    def test_verified_dataset_source_is_saved_and_returned(self):
        self.store.import_monitor_config(self._write_config(verified_dataset()))
        target = self.store.get_monitor_target("verified-target-1")
        self.assertEqual(target["dataset_status"], "verified_reference")
        self.assertEqual(target["source_name"], "测试用权威来源")
        self.assertEqual(target["source_reference"], "https://example.test/reference-document")
        self.assertEqual(target["source_date"], "2026-08-01")
        self.assertEqual(target["dataset"]["dataset_version"], "2026.09-test")
        self.assertEqual(
            target["dataset"]["verified_at"], "2026-09-02T11:00:00+08:00"
        )

    def test_verified_dataset_reimport_is_idempotent(self):
        path = self._write_config(verified_dataset())
        self.store.import_monitor_config(path)
        first = self.store.table_counts()
        self.store.import_monitor_config(path)
        self.assertEqual(first, self.store.table_counts())

    def test_invalid_dataset_status_is_rejected(self):
        payload = verified_dataset()
        payload["dataset_status"] = "official"
        with self.assertRaisesRegex(MonitorConfigValidationError, "dataset_status"):
            self.store.import_monitor_config(self._write_config(payload))

    def test_verified_dataset_without_source_is_rejected(self):
        payload = verified_dataset()
        payload["source_name"] = None
        payload["source_reference"] = None
        with self.assertRaisesRegex(MonitorConfigValidationError, "source_name"):
            self.store.import_monitor_config(self._write_config(payload))

    def test_invalid_source_date_is_rejected(self):
        payload = verified_dataset()
        payload["source_date"] = "2026-02-30"
        with self.assertRaisesRegex(MonitorConfigValidationError, "有效日期"):
            self.store.import_monitor_config(self._write_config(payload))

    def test_duplicate_target_id_is_rejected(self):
        payload = verified_dataset()
        payload["targets"].append(copy.deepcopy(payload["targets"][0]))
        with self.assertRaisesRegex(MonitorConfigValidationError, "target_id重复"):
            self.store.import_monitor_config(self._write_config(payload))

    def test_query_target_association_is_validated(self):
        payload = verified_dataset()
        payload["targets"][0]["queries"][0]["target_id"] = "missing-target"
        with self.assertRaisesRegex(MonitorConfigValidationError, "target_id不存在"):
            self.store.import_monitor_config(self._write_config(payload))

    def test_query_text_and_order_are_validated(self):
        invalid_payloads = []
        empty_text = verified_dataset()
        empty_text["targets"][0]["queries"][0]["query_text"] = " "
        invalid_payloads.append(empty_text)
        duplicate_order = verified_dataset()
        second = copy.deepcopy(duplicate_order["targets"][0]["queries"][0])
        second.update({"query_id": "verified-query-2", "query_text": "第二个词"})
        duplicate_order["targets"][0]["queries"].append(second)
        invalid_payloads.append(duplicate_order)
        for payload in invalid_payloads:
            with self.subTest(payload=payload), self.assertRaises(
                MonitorConfigValidationError
            ):
                self.store.import_monitor_config(self._write_config(payload))

    def test_target_cannot_be_silently_moved_between_datasets(self):
        development = verified_dataset(
            dataset_id="development-owner", target_id="shared-target"
        )
        development.update(
            {
                "dataset_status": "development_seed",
                "verified_at": None,
                "source_name": "开发来源",
                "source_reference": "开发配置",
            }
        )
        self.store.import_monitor_config(self._write_config(development, "dev.json"))
        reference = verified_dataset(
            dataset_id="verified-owner", target_id="shared-target", query_id="other-query"
        )
        with self.assertRaisesRegex(MonitorConfigValidationError, "不能自动转入"):
            self.store.import_monitor_config(self._write_config(reference, "verified.json"))
        target = self.store.get_monitor_target("shared-target")
        self.assertEqual(target["dataset_id"], "development-owner")
        self.assertEqual(self.store.table_counts()["monitor_datasets"], 1)

    def test_development_dataset_cannot_be_silently_promoted(self):
        development = verified_dataset(dataset_id="same-dataset")
        development.update(
            {
                "dataset_status": "development_seed",
                "verified_at": None,
                "source_name": "开发来源",
                "source_reference": "开发配置",
            }
        )
        self.store.import_monitor_config(self._write_config(development, "dev.json"))
        promoted = verified_dataset(dataset_id="same-dataset")
        with self.assertRaisesRegex(MonitorConfigValidationError, "不能从"):
            self.store.import_monitor_config(self._write_config(promoted, "verified.json"))
        target = self.store.get_monitor_target("verified-target-1")
        self.assertEqual(target["dataset_status"], "development_seed")

    def test_pending_reference_can_become_verified_after_records_are_supplied(self):
        pending = {
            "schema_version": 2,
            "dataset_id": "food-medicine-reference",
            "dataset_version": "0",
            "dataset_status": "reference_pending",
            "source_name": None,
            "source_reference": None,
            "source_date": None,
            "collected_at": None,
            "verified_at": None,
            "description": "测试用待核验数据集。",
            "targets": [],
        }
        self.store.import_monitor_config(self._write_config(pending, "pending.json"))
        verified = verified_dataset(dataset_id="food-medicine-reference")
        self.store.import_monitor_config(
            self._write_config(verified, "verified-reference.json")
        )
        target = self.store.get_monitor_target("verified-target-1")
        self.assertEqual(target["dataset_status"], "verified_reference")
        self.assertEqual(self.store.table_counts()["monitor_datasets"], 1)

    def test_schema_version_two_database_upgrades_without_losing_targets(self):
        database = self.root / "legacy.db"
        with sqlite3.connect(database) as connection:
            connection.executescript(
                """
                PRAGMA user_version = 2;
                CREATE TABLE monitor_targets (
                    target_id TEXT PRIMARY KEY,
                    standard_name TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    source_reference TEXT NOT NULL,
                    source_date TEXT,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL
                );
                INSERT INTO monitor_targets VALUES (
                    'legacy-target', '旧监测对象', 'food_medicine',
                    '旧来源', '旧引用', NULL, 1, '2026-09-01T00:00:00+08:00'
                );
                """
            )
        upgraded = DataStore(database, self.root / "output")
        upgraded.initialize()
        with sqlite3.connect(database) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(monitor_targets)")
            }
            legacy_name = connection.execute(
                "SELECT standard_name FROM monitor_targets WHERE target_id='legacy-target'"
            ).fetchone()[0]
        self.assertEqual(version, 3)
        self.assertIn("dataset_id", columns)
        self.assertEqual(legacy_name, "旧监测对象")


if __name__ == "__main__":
    unittest.main()
