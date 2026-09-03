import copy
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.data_store import DataStore, DataStoreError
from src.inspection_reference import (
    InspectionConfigValidationError,
    validate_inspection_config,
)
from src.runtime import write_json


INSPECTION_TABLES = {
    "inspection_datasets",
    "inspection_methods",
    "inspection_substances",
    "inspection_method_substances",
    "inspection_method_applicabilities",
    "substance_regulatory_contexts",
}


def inspection_dataset(
    *,
    dataset_id: str = "inspection-test-dataset",
    status: str = "development_seed",
    include_records: bool = True,
) -> dict:
    payload = {
        "schema_version": 1,
        "dataset_id": dataset_id,
        "dataset_version": "test-1",
        "dataset_status": status,
        "source_name": "测试数据集来源",
        "source_reference": "test://inspection-dataset",
        "source_date": "2026-09-01",
        "collected_at": "2026-09-03T10:00:00+08:00",
        "verified_at": (
            "2026-09-03T11:00:00+08:00"
            if status == "verified_reference"
            else None
        ),
        "description": "仅用于自动化测试，不是正式监管知识。",
        "methods": [],
        "substances": [],
        "method_substances": [],
        "method_applicabilities": [],
        "substance_regulatory_contexts": [],
    }
    if not include_records:
        return payload
    payload["methods"] = [
        {
            "method_id": "test-method-1",
            "dataset_id": dataset_id,
            "method_no": "TEST 0001",
            "method_name": "测试检验方法",
            "method_type": "supplementary_bjs",
            "method_status": "current",
            "publisher": "测试发布方",
            "published_date": "2026-08-01",
            "effective_date": "2026-09-01",
            "replaces_method_no": None,
            "replaced_by_method_no": None,
            "source_name": "测试方法来源",
            "source_reference": "test://method-1",
            "source_date": "2026-08-01",
            "note": "synthetic test only",
        }
    ]
    payload["substances"] = [
        {
            "substance_id": "test-substance-1",
            "dataset_id": dataset_id,
            "canonical_name": "测试物质",
            "english_name": "Test substance",
            "cas_no": "",
            "substance_group": "test-only",
            "note": "synthetic test only",
        }
    ]
    payload["method_substances"] = [
        {
            "method_id": "test-method-1",
            "substance_id": "test-substance-1",
            "source_label": "测试物质原文名",
            "source_cas_no": "",
            "determination_role": "qualitative",
            "normalization_note": "测试中显式记录原文名到规范名的映射。",
            "ordinal": 1,
        }
    ]
    payload["method_applicabilities"] = [
        {
            "applicability_id": "test-applicability-1",
            "method_id": "test-method-1",
            "scope_type": "include",
            "product_category": "测试食品",
            "product_form": "测试剂型",
            "ingredient_context": "",
            "source_scope_text": "测试适用范围原文",
            "note": "synthetic test only",
        }
    ]
    payload["substance_regulatory_contexts"] = [
        {
            "context_id": "test-context-1",
            "substance_id": "test-substance-1",
            "context_status": "context_dependent",
            "product_scope": "测试产品范围",
            "jurisdiction": "CN",
            "valid_from": "2026-01-01",
            "valid_to": "2026-12-31",
            "source_label": "测试法规原文标签",
            "source_name": "测试法规来源",
            "source_reference": "test://regulatory-context-1",
            "source_date": "2026-07-01",
            "note": "synthetic test only",
        }
    ]
    return payload


class InspectionReferenceValidationTest(unittest.TestCase):
    def test_development_dataset_is_normalized_without_losing_source_label(self):
        normalized = validate_inspection_config(inspection_dataset())
        self.assertEqual(normalized["dataset_status"], "development_seed")
        self.assertEqual(
            normalized["method_substances"][0]["source_label"],
            "测试物质原文名",
        )
        self.assertEqual(
            normalized["substances"][0]["canonical_name"], "测试物质"
        )

    def test_reference_pending_accepts_only_empty_collections(self):
        pending = inspection_dataset(status="reference_pending", include_records=False)
        self.assertEqual(
            validate_inspection_config(pending)["dataset_status"],
            "reference_pending",
        )
        pending["methods"] = inspection_dataset()["methods"]
        with self.assertRaisesRegex(
            InspectionConfigValidationError, "reference_pending"
        ):
            validate_inspection_config(pending)

    def test_verified_reference_requires_timestamp_and_nonempty_entities(self):
        missing_time = inspection_dataset(status="verified_reference")
        missing_time["verified_at"] = None
        with self.assertRaisesRegex(InspectionConfigValidationError, "verified_at"):
            validate_inspection_config(missing_time)

        empty = inspection_dataset(status="verified_reference", include_records=False)
        with self.assertRaisesRegex(InspectionConfigValidationError, "Method和一个Substance"):
            validate_inspection_config(empty)

    def test_duplicate_primary_and_business_identifiers_are_rejected(self):
        mutations = []
        for collection, label in (
            ("methods", "method_id"),
            ("substances", "substance_id"),
            ("method_applicabilities", "applicability_id"),
            ("substance_regulatory_contexts", "context_id"),
        ):
            payload = inspection_dataset()
            payload[collection].append(copy.deepcopy(payload[collection][0]))
            mutations.append((label, payload))

        duplicate_method_no = inspection_dataset()
        second_method = copy.deepcopy(duplicate_method_no["methods"][0])
        second_method["method_id"] = "test-method-2"
        duplicate_method_no["methods"].append(second_method)
        mutations.append(("method_no", duplicate_method_no))

        duplicate_name = inspection_dataset()
        second_substance = copy.deepcopy(duplicate_name["substances"][0])
        second_substance["substance_id"] = "test-substance-2"
        duplicate_name["substances"].append(second_substance)
        mutations.append(("canonical_name", duplicate_name))

        duplicate_relation = inspection_dataset()
        duplicate_relation["method_substances"].append(
            copy.deepcopy(duplicate_relation["method_substances"][0])
        )
        mutations.append(("MethodSubstance", duplicate_relation))

        for label, payload in mutations:
            with self.subTest(label=label), self.assertRaisesRegex(
                InspectionConfigValidationError, label
            ):
                validate_inspection_config(payload)

    def test_orphan_relationships_are_rejected_before_sqlite(self):
        mutations = []
        method_substance = inspection_dataset()
        method_substance["method_substances"][0]["method_id"] = "missing-method"
        mutations.append(("MethodSubstance", "method_id不存在", method_substance))

        method_substance_target = inspection_dataset()
        method_substance_target["method_substances"][0]["substance_id"] = (
            "missing-substance"
        )
        mutations.append(
            ("MethodSubstance substance", "substance_id不存在", method_substance_target)
        )

        applicability = inspection_dataset()
        applicability["method_applicabilities"][0]["method_id"] = "missing-method"
        mutations.append(("Applicability", "method_id不存在", applicability))

        context = inspection_dataset()
        context["substance_regulatory_contexts"][0]["substance_id"] = (
            "missing-substance"
        )
        mutations.append(("RegulatoryContext", "substance_id不存在", context))

        for label, message, payload in mutations:
            with self.subTest(label=label), self.assertRaisesRegex(
                InspectionConfigValidationError, message
            ):
                validate_inspection_config(payload)

    def test_silent_name_normalization_is_rejected(self):
        payload = inspection_dataset()
        payload["method_substances"][0]["normalization_note"] = ""
        with self.assertRaisesRegex(
            InspectionConfigValidationError, "normalization_note"
        ):
            validate_inspection_config(payload)

    def test_enum_like_fields_are_rejected_independently(self):
        cases = []
        method_type = inspection_dataset()
        method_type["methods"][0]["method_type"] = "official"
        cases.append(("method_type", method_type))
        method_status = inspection_dataset()
        method_status["methods"][0]["method_status"] = "active"
        cases.append(("method_status", method_status))
        context_status = inspection_dataset()
        context_status["substance_regulatory_contexts"][0]["context_status"] = (
            "illegal"
        )
        cases.append(("context_status", context_status))
        scope_type = inspection_dataset()
        scope_type["method_applicabilities"][0]["scope_type"] = "all"
        cases.append(("scope_type", scope_type))
        determination_role = inspection_dataset()
        determination_role["method_substances"][0]["determination_role"] = "detected"
        cases.append(("determination_role", determination_role))

        for field, payload in cases:
            with self.subTest(field=field), self.assertRaisesRegex(
                InspectionConfigValidationError, field
            ):
                validate_inspection_config(payload)

    def test_dates_intervals_and_ordinals_are_validated(self):
        invalid_date = inspection_dataset()
        invalid_date["methods"][0]["published_date"] = "2026-02-30"
        reversed_interval = inspection_dataset()
        reversed_interval["substance_regulatory_contexts"][0].update(
            {"valid_from": "2026-12-31", "valid_to": "2026-01-01"}
        )
        invalid_ordinal = inspection_dataset()
        invalid_ordinal["method_substances"][0]["ordinal"] = 0
        for label, payload in (
            ("有效日期", invalid_date),
            ("valid_from", reversed_interval),
            ("正整数", invalid_ordinal),
        ):
            with self.subTest(label=label), self.assertRaisesRegex(
                InspectionConfigValidationError, label
            ):
                validate_inspection_config(payload)

    def test_verified_reference_requires_complete_relations_and_provenance(self):
        cases = []
        pending_method = inspection_dataset(status="verified_reference")
        pending_method["methods"][0]["method_status"] = "verification_pending"
        cases.append(("verification_pending", pending_method))
        no_method_relation = inspection_dataset(status="verified_reference")
        no_method_relation["method_substances"] = []
        cases.append(("MethodSubstance", no_method_relation))
        no_applicability = inspection_dataset(status="verified_reference")
        no_applicability["method_applicabilities"] = []
        cases.append(("MethodApplicability", no_applicability))
        no_method_source_date = inspection_dataset(status="verified_reference")
        no_method_source_date["methods"][0]["source_date"] = None
        cases.append(("source_date", no_method_source_date))
        no_context_source_date = inspection_dataset(status="verified_reference")
        no_context_source_date["substance_regulatory_contexts"][0]["source_date"] = None
        cases.append(("source_date", no_context_source_date))
        no_context_source_reference = inspection_dataset(status="verified_reference")
        no_context_source_reference["substance_regulatory_contexts"][0][
            "source_reference"
        ] = ""
        cases.append(("source_reference", no_context_source_reference))
        no_dataset_source = inspection_dataset(status="verified_reference")
        no_dataset_source["source_name"] = None
        cases.append(("source_name", no_dataset_source))

        orphan_substance = inspection_dataset(status="verified_reference")
        extra = copy.deepcopy(orphan_substance["substances"][0])
        extra.update(
            {"substance_id": "test-substance-2", "canonical_name": "孤立测试物质"}
        )
        orphan_substance["substances"].append(extra)
        cases.append(("孤立实体", orphan_substance))

        for message, payload in cases:
            with self.subTest(message=message), self.assertRaisesRegex(
                InspectionConfigValidationError, message
            ):
                validate_inspection_config(payload)


class InspectionReferencePersistenceTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.store = DataStore(self.root / "data" / "app.db", self.root / "output")
        self.store.initialize()

    def tearDown(self):
        self.temporary.cleanup()

    def _write(self, payload: dict, name: str = "inspection.json") -> Path:
        path = self.root / name
        write_json(path, payload)
        return path

    def test_schema_version_five_contains_exact_inspection_foundation_tables(self):
        with sqlite3.connect(self.store.database_path) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            all_tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        self.assertEqual(version, 5)
        self.assertTrue(INSPECTION_TABLES <= all_tables)
        self.assertNotIn("risk_substance_mappings", all_tables)
        self.assertNotIn("inspection_recommendations", all_tables)

    def test_import_is_idempotent_and_preserves_distinct_names_and_context(self):
        path = self._write(inspection_dataset(status="verified_reference"))
        expected = {
            "dataset": 1,
            "methods": 1,
            "substances": 1,
            "method_substances": 1,
            "applicabilities": 1,
            "regulatory_contexts": 1,
        }
        self.assertEqual(self.store.import_inspection_config(path), expected)
        first = self.store.table_counts()
        self.assertEqual(self.store.import_inspection_config(path), expected)
        self.assertEqual(first, self.store.table_counts())
        with sqlite3.connect(self.store.database_path) as connection:
            names = connection.execute(
                """
                SELECT ms.source_label, s.canonical_name, ms.normalization_note
                FROM inspection_method_substances ms
                JOIN inspection_substances s ON s.substance_id = ms.substance_id
                """
            ).fetchone()
            context = connection.execute(
                "SELECT context_status, product_scope FROM substance_regulatory_contexts"
            ).fetchone()
        self.assertEqual(names[:2], ("测试物质原文名", "测试物质"))
        self.assertTrue(names[2])
        self.assertEqual(context, ("context_dependent", "测试产品范围"))

    def test_upsert_does_not_delete_records_omitted_from_later_payload(self):
        initial = inspection_dataset(dataset_id="nondeleting-dataset")
        self.store.import_inspection_config(self._write(initial, "full.json"))
        later = inspection_dataset(
            dataset_id="nondeleting-dataset", include_records=False
        )
        later["dataset_version"] = "test-2"
        self.store.import_inspection_config(self._write(later, "partial.json"))
        counts = self.store.table_counts()
        self.assertEqual(counts["inspection_methods"], 1)
        self.assertEqual(counts["inspection_substances"], 1)
        self.assertEqual(counts["inspection_method_substances"], 1)
        self.assertEqual(counts["inspection_method_applicabilities"], 1)
        self.assertEqual(counts["substance_regulatory_contexts"], 1)

    def test_only_pending_to_verified_transition_is_allowed(self):
        pending = inspection_dataset(
            dataset_id="transition-dataset",
            status="reference_pending",
            include_records=False,
        )
        self.store.import_inspection_config(self._write(pending, "pending.json"))
        verified = inspection_dataset(
            dataset_id="transition-dataset", status="verified_reference"
        )
        self.store.import_inspection_config(self._write(verified, "verified.json"))

        downgrade = inspection_dataset(
            dataset_id="transition-dataset",
            status="reference_pending",
            include_records=False,
        )
        with self.assertRaisesRegex(InspectionConfigValidationError, "不能从"):
            self.store.import_inspection_config(self._write(downgrade, "downgrade.json"))

        development = inspection_dataset(dataset_id="development-transition")
        development["methods"][0]["method_id"] = "development-method"
        development["method_substances"][0]["method_id"] = "development-method"
        development["method_applicabilities"][0]["method_id"] = "development-method"
        development["substances"][0]["substance_id"] = "development-substance"
        development["method_substances"][0]["substance_id"] = "development-substance"
        development["substance_regulatory_contexts"][0]["substance_id"] = (
            "development-substance"
        )
        development["method_applicabilities"][0]["applicability_id"] = (
            "development-applicability"
        )
        development["substance_regulatory_contexts"][0]["context_id"] = (
            "development-context"
        )
        self.store.import_inspection_config(self._write(development, "development.json"))
        promoted = copy.deepcopy(development)
        promoted["dataset_status"] = "verified_reference"
        promoted["verified_at"] = "2026-09-03T11:00:00+08:00"
        with self.assertRaisesRegex(InspectionConfigValidationError, "不能从"):
            self.store.import_inspection_config(self._write(promoted, "promoted.json"))

    def test_method_and_substance_ids_cannot_change_dataset_owner(self):
        first = inspection_dataset(dataset_id="owner-a")
        self.store.import_inspection_config(self._write(first, "owner-a.json"))

        method_takeover = inspection_dataset(
            dataset_id="owner-b", include_records=False
        )
        method = copy.deepcopy(first["methods"][0])
        method["dataset_id"] = "owner-b"
        method_takeover["methods"] = [method]
        with self.assertRaisesRegex(DataStoreError, "method_id"):
            self.store.import_inspection_config(
                self._write(method_takeover, "method-takeover.json")
            )

        substance_takeover = inspection_dataset(
            dataset_id="owner-c", include_records=False
        )
        substance = copy.deepcopy(first["substances"][0])
        substance["dataset_id"] = "owner-c"
        substance_takeover["substances"] = [substance]
        with self.assertRaisesRegex(DataStoreError, "substance_id"):
            self.store.import_inspection_config(
                self._write(substance_takeover, "substance-takeover.json")
            )
        counts = self.store.table_counts()
        self.assertEqual(counts["inspection_datasets"], 1)

    def test_database_failure_rolls_back_entire_import(self):
        initial = inspection_dataset(
            dataset_id="rollback-dataset", include_records=False
        )
        old_method = copy.deepcopy(inspection_dataset()["methods"][0])
        old_method.update(
            {
                "method_id": "existing-method",
                "dataset_id": "rollback-dataset",
                "method_no": "TEST 0002",
            }
        )
        initial["methods"] = [old_method]
        self.store.import_inspection_config(self._write(initial, "initial.json"))

        failing = inspection_dataset(
            dataset_id="rollback-dataset", include_records=False
        )
        failing["dataset_version"] = "must-rollback"
        first_new = copy.deepcopy(old_method)
        first_new.update({"method_id": "new-method", "method_no": "TEST 0001"})
        conflicting = copy.deepcopy(old_method)
        conflicting["method_id"] = "conflicting-method"
        failing["methods"] = [first_new, conflicting]

        with self.assertRaises(sqlite3.IntegrityError):
            self.store.import_inspection_config(self._write(failing, "failing.json"))
        with sqlite3.connect(self.store.database_path) as connection:
            method_ids = {
                row[0]
                for row in connection.execute("SELECT method_id FROM inspection_methods")
            }
            version = connection.execute(
                "SELECT dataset_version FROM inspection_datasets "
                "WHERE dataset_id='rollback-dataset'"
            ).fetchone()[0]
        self.assertEqual(method_ids, {"existing-method"})
        self.assertEqual(version, "test-1")

    def test_v4_upgrade_preserves_product_review_and_monitor_records(self):
        database = self.root / "legacy-v4.db"
        legacy = DataStore(database, self.root / "legacy-output")
        legacy.initialize()
        with sqlite3.connect(database) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(
                """
                INSERT INTO tasks (
                    task_id, keyword, stage, run_path, updated_at,
                    task_type, target_id
                ) VALUES (
                    'legacy-task', '测试', 'completed', 'legacy-task',
                    '2026-09-01T00:00:00+08:00', 'monitor', 'legacy-target'
                );
                INSERT INTO products VALUES (
                    'legacy-product', '2026-09-01T00:00:00+08:00',
                    '2026-09-01T00:00:00+08:00'
                );
                INSERT INTO product_snapshots (
                    snapshot_id, product_id, task_id, product_name, product_path,
                    updated_at
                ) VALUES (
                    'legacy-snapshot', 'legacy-product', 'legacy-task', '旧商品',
                    'products/legacy-product', '2026-09-01T00:00:00+08:00'
                );
                INSERT INTO evidence (
                    evidence_id, snapshot_id, ordinal, text
                ) VALUES ('legacy-evidence', 'legacy-snapshot', 1, '旧证据');
                INSERT INTO reviews VALUES (
                    'legacy-snapshot', 'recommend_follow_up', '必须保留的人工备注',
                    '2026-09-01T01:00:00+08:00'
                );
                INSERT INTO monitor_datasets VALUES (
                    'legacy-monitor-dataset', '1', 'development_seed', '旧来源',
                    '旧引用', NULL, NULL, NULL, '',
                    '2026-09-01T00:00:00+08:00', '2026-09-01T00:00:00+08:00'
                );
                INSERT INTO monitor_targets (
                    target_id, dataset_id, standard_name, target_type, source_name,
                    source_reference, enabled, updated_at
                ) VALUES (
                    'legacy-target', 'legacy-monitor-dataset', '旧对象',
                    'food_medicine', '旧来源', '旧引用', 1,
                    '2026-09-01T00:00:00+08:00'
                );
                INSERT INTO search_queries (
                    query_id, target_id, query_text, query_type, query_order,
                    enabled, updated_at, query_source, validation_status, query_note
                ) VALUES (
                    'legacy-query', 'legacy-target', '旧对象', 'base', 1, 1,
                    '2026-09-01T00:00:00+08:00', 'standard_name',
                    'search_validated', '旧验证记录'
                );
                INSERT INTO candidate_hits VALUES (
                    'legacy-hit', 'legacy-task', 'legacy-product', 'legacy-query',
                    '旧对象', 1, '2026-09-01T00:00:00+08:00'
                );
                """
            )
            connection.execute("PRAGMA foreign_keys = OFF")
            connection.executescript(
                """
                DROP TABLE substance_regulatory_contexts;
                DROP TABLE inspection_method_applicabilities;
                DROP TABLE inspection_method_substances;
                DROP TABLE inspection_substances;
                DROP TABLE inspection_methods;
                DROP TABLE inspection_datasets;
                PRAGMA user_version = 4;
                """
            )

        upgraded = DataStore(database, self.root / "legacy-output")
        upgraded.initialize()
        with sqlite3.connect(database) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            review = connection.execute(
                "SELECT review_status, review_note FROM reviews"
            ).fetchone()
            preserved = {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in (
                    "tasks",
                    "products",
                    "product_snapshots",
                    "evidence",
                    "reviews",
                    "monitor_datasets",
                    "monitor_targets",
                    "search_queries",
                    "candidate_hits",
                )
            }
        self.assertEqual(version, 5)
        self.assertTrue(INSPECTION_TABLES <= tables)
        self.assertEqual(set(preserved.values()), {1})
        self.assertEqual(review, ("recommend_follow_up", "必须保留的人工备注"))


if __name__ == "__main__":
    unittest.main()
