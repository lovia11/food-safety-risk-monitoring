import copy
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.data_store import (
    DataStore,
    MonitorConfigValidationError,
    validate_monitor_config,
)
from src.runtime import write_json


def query_dataset() -> dict:
    return {
        "schema_version": 3,
        "dataset_id": "query-policy-test",
        "dataset_version": "1",
        "dataset_status": "verified_reference",
        "source_name": "测试来源",
        "source_reference": "https://example.test/official",
        "source_date": "2026-09-01",
        "collected_at": "2026-09-02T10:00:00+08:00",
        "verified_at": "2026-09-02T11:00:00+08:00",
        "description": "SearchQuery策略离线测试。",
        "targets": [
            {
                "target_id": "longyanrou-test",
                "dataset_id": "query-policy-test",
                "standard_name": "龙眼肉（桂圆）",
                "target_type": "food_medicine",
                "source_name": "测试来源",
                "source_reference": "https://example.test/official",
                "source_date": "2026-09-01",
                "enabled": False,
                "queries": [
                    {
                        "query_id": "longyanrou-base",
                        "target_id": "longyanrou-test",
                        "query_text": "龙眼肉",
                        "query_type": "base",
                        "query_source": "standard_name",
                        "validation_status": "unvalidated",
                        "query_note": "待真实搜索验证。",
                        "order": 1,
                        "enabled": False,
                    },
                    {
                        "query_id": "guiyuan-alias",
                        "target_id": "longyanrou-test",
                        "query_text": "桂圆",
                        "query_type": "base",
                        "query_source": "official_alias",
                        "validation_status": "unvalidated",
                        "query_note": "来自官方名称括号。",
                        "order": 2,
                        "enabled": False,
                    },
                ],
            }
        ],
    }


class SearchQueryPolicyTest(unittest.TestCase):
    def test_standard_name_and_official_alias_are_accepted(self):
        normalized = validate_monitor_config(query_dataset())
        queries = normalized["targets"][0]["queries"]
        self.assertEqual(
            [(query["query_text"], query["query_source"]) for query in queries],
            [("龙眼肉", "standard_name"), ("桂圆", "official_alias")],
        )

    def test_official_alias_must_come_from_parenthesized_official_name(self):
        payload = query_dataset()
        payload["targets"][0]["queries"][1]["query_text"] = "龙眼"
        with self.assertRaisesRegex(MonitorConfigValidationError, "官方名称括号"):
            validate_monitor_config(payload)

    def test_query_source_and_validation_status_are_enumerated(self):
        invalid_source = query_dataset()
        invalid_source["targets"][0]["queries"][0]["query_source"] = "llm"
        invalid_status = query_dataset()
        invalid_status["targets"][0]["queries"][0]["validation_status"] = "maybe"
        for payload, message in (
            (invalid_source, "query_source"),
            (invalid_status, "validation_status"),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(
                MonitorConfigValidationError, message
            ):
                validate_monitor_config(payload)

    def test_observed_and_manual_queries_require_a_note(self):
        for source, query_type in (
            ("observed_product_form", "product_form"),
            ("manual", "base"),
        ):
            payload = query_dataset()
            query = payload["targets"][0]["queries"][0]
            query.update(
                {
                    "query_source": source,
                    "query_type": query_type,
                    "query_note": "",
                }
            )
            with self.subTest(source=source), self.assertRaisesRegex(
                MonitorConfigValidationError, "query_note"
            ):
                validate_monitor_config(payload)

    def test_unvalidated_query_cannot_be_enabled(self):
        payload = query_dataset()
        payload["targets"][0]["queries"][0]["enabled"] = True
        with self.assertRaisesRegex(MonitorConfigValidationError, "未经search_validated"):
            validate_monitor_config(payload)

    def test_enabled_target_requires_enabled_validated_query(self):
        payload = query_dataset()
        payload["targets"][0]["enabled"] = True
        with self.assertRaisesRegex(MonitorConfigValidationError, "已验证且启用"):
            validate_monitor_config(payload)

        validated = copy.deepcopy(payload)
        query = validated["targets"][0]["queries"][0]
        query["validation_status"] = "search_validated"
        query["query_note"] = "真实search-only输出：output/test/search_diagnostics.json"
        query["enabled"] = True
        self.assertTrue(validate_monitor_config(validated)["targets"][0]["enabled"])

    def test_sqlite_round_trip_and_reimport_preserve_query_metadata(self):
        payload = query_dataset()
        query = payload["targets"][0]["queries"][0]
        query.update(
            {
                "validation_status": "search_validated",
                "query_note": "真实search-only输出：output/test/search_diagnostics.json",
                "enabled": True,
            }
        )
        payload["targets"][0]["enabled"] = True
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path = root / "query-policy.json"
            write_json(config_path, payload)
            store = DataStore(root / "app.db", root / "output")
            store.initialize()
            first = store.import_monitor_config(config_path)
            store.import_monitor_config(config_path)
            target = store.get_monitor_target("longyanrou-test")
            self.assertEqual(first, {"datasets": 1, "targets": 1, "queries": 2})
            self.assertEqual(target["queries"][0]["query_source"], "standard_name")
            self.assertEqual(
                target["queries"][0]["validation_status"], "search_validated"
            )
            self.assertIn("search_diagnostics", target["queries"][0]["query_note"])
            self.assertEqual(store.table_counts()["search_queries"], 2)

    def test_schema_v3_database_upgrades_query_columns_without_data_loss(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            database = root / "legacy-v3.db"
            connection = sqlite3.connect(database)
            try:
                connection.executescript(
                    """
                    PRAGMA user_version = 3;
                    CREATE TABLE search_queries (
                        query_id TEXT PRIMARY KEY,
                        target_id TEXT NOT NULL,
                        query_text TEXT NOT NULL,
                        query_type TEXT NOT NULL,
                        query_order INTEGER NOT NULL,
                        enabled INTEGER NOT NULL DEFAULT 1,
                        updated_at TEXT NOT NULL,
                        UNIQUE(target_id, query_text)
                    );
                    INSERT INTO search_queries VALUES (
                        'legacy-query', 'legacy-target', '旧搜索词', 'base',
                        1, 1, '2026-09-01T00:00:00+08:00'
                    );
                    """
                )
            finally:
                connection.close()
            store = DataStore(database, root / "output")
            store.initialize()
            connection = sqlite3.connect(database)
            try:
                connection.row_factory = sqlite3.Row
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                row = connection.execute(
                    "SELECT * FROM search_queries WHERE query_id='legacy-query'"
                ).fetchone()
            finally:
                connection.close()
            self.assertEqual(version, 6)
            self.assertEqual(row["query_text"], "旧搜索词")
            self.assertEqual(row["query_source"], "manual")
            self.assertEqual(row["validation_status"], "unvalidated")


if __name__ == "__main__":
    unittest.main()
