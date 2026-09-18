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
    "inspection_regulatory_documents",
    "inspection_methods",
    "inspection_substances",
    "inspection_method_substances",
    "inspection_method_applicabilities",
    "substance_regulatory_contexts",
    "substance_group_memberships",
}


def inspection_dataset(
    *,
    dataset_id: str = "inspection-test-dataset",
    status: str = "development_seed",
    include_records: bool = True,
) -> dict:
    payload = {
        "schema_version": 2,
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
        "regulatory_documents": [],
        "methods": [],
        "substances": [],
        "method_substances": [],
        "method_applicabilities": [],
        "substance_regulatory_contexts": [],
        "substance_group_memberships": [],
    }
    if not include_records:
        return payload
    payload["regulatory_documents"] = [
        {
            "document_id": "test-document-1",
            "document_type": "official_method_page",
            "document_no": "TEST 0001",
            "title": "测试检验方法",
            "publisher": "测试发布方",
            "published_date": "2026-08-01",
            "effective_date": "2026-09-01",
            "status": "current",
            "source_reference": "test://method-1",
            "jurisdiction": "CN",
            "supersedes": [],
            "superseded_by": [],
            "dataset_id": dataset_id,
            "dataset_version": "test-1",
        }
    ]
    payload["methods"] = [
        {
            "method_id": "test-method-1",
            "dataset_id": dataset_id,
            "method_no": "TEST 0001",
            "method_name": "测试检验方法",
            "method_type": "supplementary_bjs",
            "method_status": "current",
            "knowledge_depth": "recommendation_ready",
            "regulatory_document_id": "test-document-1",
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
            "substance_id": None,
            "scope_type": "include",
            "product_category": "测试食品",
            "product_form": "测试剂型",
            "ingredient_context": "",
            "source_scope_text": "测试适用范围原文",
            "note": "synthetic test only",
        },
        {
            "applicability_id": "test-applicability-substance-1",
            "method_id": "test-method-1",
            "substance_id": "test-substance-1",
            "scope_type": "conditional",
            "product_category": "测试食品",
            "product_form": "测试特殊基质",
            "ingredient_context": "",
            "source_scope_text": "测试物质在特殊基质中的条件适用原文",
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
        with self.assertRaisesRegex(InspectionConfigValidationError, "一个Method"):
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

    def test_cas_normalization_requires_an_explicit_note_only_when_values_differ(self):
        matching = inspection_dataset()
        matching["substances"][0]["cas_no"] = "TEST-CAS-1"
        matching["method_substances"][0].update(
            {
                "source_label": "测试物质",
                "source_cas_no": "TEST-CAS-1",
                "normalization_note": "",
            }
        )
        self.assertEqual(
            validate_inspection_config(matching)["method_substances"][0][
                "source_cas_no"
            ],
            "TEST-CAS-1",
        )

        mismatching = copy.deepcopy(matching)
        mismatching["method_substances"][0]["source_cas_no"] = "TEST-CAS-2"
        with self.assertRaisesRegex(
            InspectionConfigValidationError, "normalization_note"
        ):
            validate_inspection_config(mismatching)

        explained = copy.deepcopy(mismatching)
        explained["method_substances"][0]["normalization_note"] = (
            "测试中明确记录两个CAS值不同，未自动选择其一。"
        )
        self.assertTrue(
            validate_inspection_config(explained)["method_substances"][0][
                "normalization_note"
            ]
        )

    def test_verified_reference_rejects_pending_regulatory_context(self):
        development = inspection_dataset()
        development["substance_regulatory_contexts"][0]["context_status"] = (
            "verification_pending"
        )
        self.assertEqual(
            validate_inspection_config(development)[
                "substance_regulatory_contexts"
            ][0]["context_status"],
            "verification_pending",
        )

        payload = inspection_dataset(status="verified_reference")
        payload["substance_regulatory_contexts"][0]["context_status"] = (
            "verification_pending"
        )
        with self.assertRaisesRegex(
            InspectionConfigValidationError, "verification_pending"
        ):
            validate_inspection_config(payload)

    def test_verified_reference_requires_applicability_source_scope_text(self):
        development = inspection_dataset()
        development["methods"][0]["knowledge_depth"] = "analyte_verified"
        development["method_applicabilities"][0]["source_scope_text"] = ""
        self.assertEqual(
            validate_inspection_config(development)["method_applicabilities"][0][
                "source_scope_text"
            ],
            "",
        )

        payload = inspection_dataset(status="verified_reference")
        payload["method_applicabilities"][0]["source_scope_text"] = ""
        with self.assertRaisesRegex(
            InspectionConfigValidationError, "source_scope_text"
        ):
            validate_inspection_config(payload)

    def test_applicability_substance_scope_requires_an_explicit_valid_relationship(self):
        normalized = validate_inspection_config(inspection_dataset())
        self.assertEqual(
            [
                item["substance_id"]
                for item in normalized["method_applicabilities"]
            ],
            [None, "test-substance-1"],
        )

        missing_field = inspection_dataset()
        del missing_field["method_applicabilities"][0]["substance_id"]
        with self.assertRaisesRegex(
            InspectionConfigValidationError, "显式包含substance_id"
        ):
            validate_inspection_config(missing_field)

        missing_substance = inspection_dataset()
        missing_substance["method_applicabilities"][1]["substance_id"] = (
            "missing-substance"
        )
        with self.assertRaisesRegex(
            InspectionConfigValidationError, "substance_id不存在"
        ):
            validate_inspection_config(missing_substance)

        unrelated_substance = inspection_dataset()
        second_substance = copy.deepcopy(unrelated_substance["substances"][0])
        second_substance.update(
            {"substance_id": "test-substance-2", "canonical_name": "测试物质二"}
        )
        unrelated_substance["substances"].append(second_substance)
        unrelated_substance["method_applicabilities"][1]["substance_id"] = (
            "test-substance-2"
        )
        with self.assertRaisesRegex(InspectionConfigValidationError, "不检测Substance"):
            validate_inspection_config(unrelated_substance)

    def test_verified_method_requires_a_method_level_applicability(self):
        payload = inspection_dataset(status="verified_reference")
        payload["method_applicabilities"] = [
            item
            for item in payload["method_applicabilities"]
            if item["substance_id"] is not None
        ]
        with self.assertRaisesRegex(
            InspectionConfigValidationError, "Method级Applicability"
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
        cases.append(("method_status.*current", pending_method))
        no_method_relation = inspection_dataset(status="verified_reference")
        no_method_relation["method_substances"] = []
        no_method_relation["method_applicabilities"] = [
            item
            for item in no_method_relation["method_applicabilities"]
            if item["substance_id"] is None
        ]
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

    def test_knowledge_depth_gates_are_enforced_without_global_relaxation(self):
        reference_only = inspection_dataset(status="verified_reference")
        reference_only["methods"][0]["knowledge_depth"] = "reference_only"
        reference_only["method_substances"] = []
        reference_only["method_applicabilities"] = []
        normalized = validate_inspection_config(reference_only)
        self.assertEqual(
            normalized["methods"][0]["knowledge_depth"], "reference_only"
        )

        analyte_without_relation = inspection_dataset(status="verified_reference")
        analyte_without_relation["methods"][0]["knowledge_depth"] = (
            "analyte_verified"
        )
        analyte_without_relation["method_substances"] = []
        analyte_without_relation["method_applicabilities"] = []
        with self.assertRaisesRegex(
            InspectionConfigValidationError, "analyte_verified.*MethodSubstance"
        ):
            validate_inspection_config(analyte_without_relation)

        applicability_without_scope = inspection_dataset(
            status="verified_reference"
        )
        applicability_without_scope["methods"][0]["knowledge_depth"] = (
            "applicability_verified"
        )
        applicability_without_scope["method_applicabilities"] = []
        with self.assertRaisesRegex(
            InspectionConfigValidationError,
            "applicability_verified.*MethodApplicability",
        ):
            validate_inspection_config(applicability_without_scope)

        ready_without_scope = inspection_dataset(status="verified_reference")
        ready_without_scope["method_applicabilities"] = []
        with self.assertRaisesRegex(
            InspectionConfigValidationError,
            "recommendation_ready.*MethodApplicability",
        ):
            validate_inspection_config(ready_without_scope)

        ready_without_relation = inspection_dataset(status="verified_reference")
        ready_without_relation["method_substances"] = []
        ready_without_relation["method_applicabilities"] = []
        with self.assertRaisesRegex(
            InspectionConfigValidationError,
            "recommendation_ready.*MethodSubstance",
        ):
            validate_inspection_config(ready_without_relation)

    def test_lifecycle_and_knowledge_depth_are_independent(self):
        current_reference = inspection_dataset(status="verified_reference")
        current_reference["methods"][0]["knowledge_depth"] = "reference_only"
        current_reference["method_substances"] = []
        current_reference["method_applicabilities"] = []
        self.assertEqual(
            validate_inspection_config(current_reference)["methods"][0][
                "method_status"
            ],
            "current",
        )

        superseded_deep = inspection_dataset(status="verified_reference")
        superseded_deep["methods"][0].update(
            {
                "method_status": "superseded",
                "knowledge_depth": "applicability_verified",
                "replaced_by_method_no": "TEST 0002",
            }
        )
        normalized = validate_inspection_config(superseded_deep)
        self.assertEqual(
            (
                normalized["methods"][0]["method_status"],
                normalized["methods"][0]["knowledge_depth"],
            ),
            ("superseded", "applicability_verified"),
        )

    def test_regulatory_document_links_and_lifecycle_direction_are_validated(self):
        normalized = validate_inspection_config(
            inspection_dataset(status="verified_reference")
        )
        self.assertEqual(len(normalized["regulatory_documents"]), 1)
        self.assertEqual(
            normalized["methods"][0]["regulatory_document_id"],
            "test-document-1",
        )

        missing = inspection_dataset()
        missing["methods"][0]["regulatory_document_id"] = "missing-document"
        with self.assertRaisesRegex(
            InspectionConfigValidationError, "RegulatoryDocument不存在"
        ):
            validate_inspection_config(missing)

        one_way = inspection_dataset()
        predecessor = copy.deepcopy(one_way["regulatory_documents"][0])
        predecessor.update(
            {
                "document_id": "test-document-predecessor",
                "document_no": "TEST 0000",
                "superseded_by": [],
            }
        )
        one_way["regulatory_documents"].append(predecessor)
        one_way["regulatory_documents"][0]["supersedes"] = [
            "test-document-predecessor"
        ]
        with self.assertRaisesRegex(InspectionConfigValidationError, "双向一致"):
            validate_inspection_config(one_way)

        wrong_version = inspection_dataset()
        wrong_version["regulatory_documents"][0]["dataset_version"] = "other"
        with self.assertRaisesRegex(
            InspectionConfigValidationError, "dataset_version必须等于"
        ):
            validate_inspection_config(wrong_version)

    def test_group_membership_contract_accepts_zero_and_rejects_inference(self):
        baseline = validate_inspection_config(
            inspection_dataset(status="verified_reference")
        )
        self.assertEqual(baseline["substance_group_memberships"], [])

        explicit = inspection_dataset(status="verified_reference")
        explicit["substance_group_memberships"] = [
            {
                "membership_id": "test-group-member-1",
                "group_identity": "test-group-1",
                "group_label": "测试来源组",
                "substance_id": "test-substance-1",
                "membership_scope": "来源明确列名成员",
                "completeness_context": "partial",
                "source_basis": "synthetic explicit membership only",
                "source_reference": "test://group-membership",
                "status": "current",
                "dataset_id": "inspection-test-dataset",
                "dataset_version": "test-1",
            }
        ]
        normalized = validate_inspection_config(explicit)
        self.assertEqual(
            normalized["substance_group_memberships"][0][
                "completeness_context"
            ],
            "partial",
        )

        wrong_version = copy.deepcopy(explicit)
        wrong_version["substance_group_memberships"][0]["dataset_version"] = (
            "other"
        )
        with self.assertRaisesRegex(
            InspectionConfigValidationError, "dataset_version必须匹配"
        ):
            validate_inspection_config(wrong_version)


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

    def test_schema_version_seven_preserves_inspection_foundation_tables(self):
        with sqlite3.connect(self.store.database_path) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            all_tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            applicability_columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(inspection_method_applicabilities)"
                )
            }
        self.assertEqual(version, 14)
        self.assertTrue(INSPECTION_TABLES <= all_tables)
        self.assertIn("substance_id", applicability_columns)
        self.assertIn("risk_mapping_datasets", all_tables)
        self.assertIn("risk_substance_mappings", all_tables)
        self.assertNotIn("inspection_recommendations", all_tables)

    def test_schema_twelve_upgrades_depth_safely_and_preserves_method_row(self):
        database = self.root / "legacy-v12.db"
        with sqlite3.connect(database) as connection:
            connection.executescript(
                """
                CREATE TABLE inspection_datasets (
                    dataset_id TEXT PRIMARY KEY,
                    dataset_version TEXT NOT NULL,
                    dataset_status TEXT NOT NULL,
                    source_name TEXT,
                    source_reference TEXT,
                    source_date TEXT,
                    collected_at TEXT,
                    verified_at TEXT,
                    description TEXT NOT NULL DEFAULT '',
                    imported_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE inspection_methods (
                    method_id TEXT PRIMARY KEY,
                    dataset_id TEXT NOT NULL REFERENCES inspection_datasets(dataset_id),
                    method_no TEXT NOT NULL,
                    method_name TEXT NOT NULL,
                    method_type TEXT NOT NULL,
                    method_status TEXT NOT NULL,
                    publisher TEXT NOT NULL DEFAULT '',
                    published_date TEXT,
                    effective_date TEXT,
                    replaces_method_no TEXT,
                    replaced_by_method_no TEXT,
                    source_name TEXT NOT NULL,
                    source_reference TEXT NOT NULL,
                    source_date TEXT,
                    note TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL,
                    UNIQUE(dataset_id, method_no)
                );
                INSERT INTO inspection_datasets VALUES (
                    'legacy-inspection', 'legacy-v12', 'verified_reference',
                    'legacy source', 'legacy reference', '2026-01-01', NULL,
                    '2026-01-01T00:00:00+08:00', '',
                    '2026-01-01T00:00:00+08:00',
                    '2026-01-01T00:00:00+08:00'
                );
                INSERT INTO inspection_methods VALUES (
                    'legacy-method', 'legacy-inspection', 'LEGACY 1',
                    '旧方法', 'supplementary_bjs', 'current', '旧发布方',
                    '2026-01-01', NULL, NULL, NULL, '旧来源', 'legacy reference',
                    '2026-01-01', 'must survive',
                    '2026-01-01T00:00:00+08:00'
                );
                PRAGMA user_version = 12;
                """
            )

        DataStore(database, self.root / "legacy-v12-output").initialize()
        with sqlite3.connect(database) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            method = connection.execute(
                "SELECT method_no, note, knowledge_depth, regulatory_document_id "
                "FROM inspection_methods WHERE method_id='legacy-method'"
            ).fetchone()
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }

        self.assertEqual(version, 14)
        self.assertEqual(
            method,
            ("LEGACY 1", "must survive", "reference_only", None),
        )
        self.assertIn("inspection_regulatory_documents", tables)
        self.assertIn("substance_group_memberships", tables)

    def test_import_is_idempotent_and_preserves_distinct_names_and_context(self):
        path = self._write(inspection_dataset(status="verified_reference"))
        expected = {
            "dataset": 1,
            "regulatory_documents": 1,
            "methods": 1,
            "substances": 1,
            "method_substances": 1,
            "applicabilities": 2,
            "regulatory_contexts": 1,
            "group_memberships": 0,
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

    def test_explicit_group_membership_rebuilds_without_method_inference(self):
        payload = inspection_dataset(dataset_id="group-contract")
        payload["substance_group_memberships"] = [
            {
                "membership_id": "group-contract-member-1",
                "group_identity": "source-group-1",
                "group_label": "来源明确测试组",
                "substance_id": "test-substance-1",
                "membership_scope": "来源明确列名成员",
                "completeness_context": "partial",
                "source_basis": "synthetic explicit membership only",
                "source_reference": "test://group-contract",
                "status": "current",
                "dataset_id": "group-contract",
                "dataset_version": "test-1",
            }
        ]
        result = self.store.import_inspection_config(
            self._write(payload, "group-contract.json")
        )

        self.assertEqual(result["group_memberships"], 1)
        with sqlite3.connect(self.store.database_path) as connection:
            row = connection.execute(
                "SELECT group_identity, substance_id, completeness_context "
                "FROM substance_group_memberships"
            ).fetchone()
        self.assertEqual(
            row,
            ("source-group-1", "test-substance-1", "partial"),
        )

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
        self.assertEqual(counts["inspection_method_applicabilities"], 2)
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
        development["methods"][0]["regulatory_document_id"] = (
            "development-document"
        )
        development["regulatory_documents"][0]["document_id"] = (
            "development-document"
        )
        development["method_substances"][0]["method_id"] = "development-method"
        for applicability in development["method_applicabilities"]:
            applicability["method_id"] = "development-method"
            if applicability["substance_id"] is not None:
                applicability["substance_id"] = "development-substance"
        development["substances"][0]["substance_id"] = "development-substance"
        development["method_substances"][0]["substance_id"] = "development-substance"
        development["substance_regulatory_contexts"][0]["substance_id"] = (
            "development-substance"
        )
        development["method_applicabilities"][0]["applicability_id"] = (
            "development-applicability"
        )
        development["method_applicabilities"][1]["applicability_id"] = (
            "development-substance-applicability"
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
        method["knowledge_depth"] = "reference_only"
        method["regulatory_document_id"] = "owner-b-document"
        method_takeover["methods"] = [method]
        document = copy.deepcopy(first["regulatory_documents"][0])
        document["dataset_id"] = "owner-b"
        document["document_id"] = "owner-b-document"
        method_takeover["regulatory_documents"] = [document]
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

    def test_applicability_id_cannot_change_method_or_substance_parent(self):
        initial = inspection_dataset(dataset_id="applicability-owner")
        second_substance = copy.deepcopy(initial["substances"][0])
        second_substance.update(
            {"substance_id": "test-substance-2", "canonical_name": "测试物质二"}
        )
        initial["substances"].append(second_substance)
        second_relation = copy.deepcopy(initial["method_substances"][0])
        second_relation.update(
            {
                "substance_id": "test-substance-2",
                "source_label": "测试物质二",
                "normalization_note": "",
                "ordinal": 2,
            }
        )
        initial["method_substances"].append(second_relation)
        self.store.import_inspection_config(self._write(initial, "parents.json"))

        null_to_substance = copy.deepcopy(initial)
        null_to_substance["methods"][0]["knowledge_depth"] = "analyte_verified"
        null_to_substance["method_applicabilities"][0]["substance_id"] = (
            "test-substance-1"
        )
        with self.assertRaisesRegex(DataStoreError, "不能改绑"):
            self.store.import_inspection_config(
                self._write(null_to_substance, "null-to-substance.json")
            )

        substance_to_other = copy.deepcopy(initial)
        substance_to_other["methods"][0]["knowledge_depth"] = "analyte_verified"
        substance_to_other["method_applicabilities"][1]["substance_id"] = (
            "test-substance-2"
        )
        with self.assertRaisesRegex(DataStoreError, "不能改绑"):
            self.store.import_inspection_config(
                self._write(substance_to_other, "substance-to-other.json")
            )

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
                "knowledge_depth": "reference_only",
            }
        )
        initial["methods"] = [old_method]
        initial_document = copy.deepcopy(
            inspection_dataset()["regulatory_documents"][0]
        )
        initial_document["dataset_id"] = "rollback-dataset"
        initial["regulatory_documents"] = [initial_document]
        self.store.import_inspection_config(self._write(initial, "initial.json"))

        failing = inspection_dataset(
            dataset_id="rollback-dataset", include_records=False
        )
        failing["dataset_version"] = "must-rollback"
        failing["regulatory_documents"] = copy.deepcopy(
            initial["regulatory_documents"]
        )
        failing["regulatory_documents"][0]["dataset_version"] = "must-rollback"
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
        self.assertEqual(version, 14)
        self.assertTrue(INSPECTION_TABLES <= tables)
        self.assertEqual(set(preserved.values()), {1})
        self.assertEqual(review, ("recommend_follow_up", "必须保留的人工备注"))

    def test_v5_upgrade_adds_nullable_substance_scope_without_data_loss(self):
        database = self.root / "legacy-v5.db"
        legacy = DataStore(database, self.root / "legacy-v5-output")
        legacy.initialize()
        legacy.import_inspection_config(
            self._write(
                inspection_dataset(dataset_id="legacy-inspection"),
                "legacy-inspection.json",
            )
        )
        with sqlite3.connect(database) as connection:
            connection.executescript(
                """
                INSERT INTO tasks (
                    task_id, keyword, stage, run_path, updated_at
                ) VALUES (
                    'v5-task', '测试', 'completed', 'v5-task',
                    '2026-09-01T00:00:00+08:00'
                );
                INSERT INTO products VALUES (
                    'v5-product', '2026-09-01T00:00:00+08:00',
                    '2026-09-01T00:00:00+08:00'
                );
                INSERT INTO product_snapshots (
                    snapshot_id, product_id, task_id, product_name, product_path,
                    updated_at
                ) VALUES (
                    'v5-snapshot', 'v5-product', 'v5-task', '旧商品',
                    'products/v5-product', '2026-09-01T00:00:00+08:00'
                );
                INSERT INTO reviews VALUES (
                    'v5-snapshot', 'recommend_follow_up', 'v5人工备注',
                    '2026-09-01T01:00:00+08:00'
                );
                INSERT INTO monitor_datasets VALUES (
                    'v5-monitor-dataset', '1', 'development_seed', '旧来源',
                    '旧引用', NULL, NULL, NULL, '',
                    '2026-09-01T00:00:00+08:00', '2026-09-01T00:00:00+08:00'
                );
                INSERT INTO monitor_targets (
                    target_id, dataset_id, standard_name, target_type, source_name,
                    source_reference, enabled, updated_at
                ) VALUES (
                    'v5-target', 'v5-monitor-dataset', '旧对象', 'food_medicine',
                    '旧来源', '旧引用', 1, '2026-09-01T00:00:00+08:00'
                );
                """
            )
            connection.executescript(
                """
                PRAGMA foreign_keys = OFF;
                ALTER TABLE inspection_method_applicabilities
                    RENAME TO inspection_method_applicabilities_v6;
                CREATE TABLE inspection_method_applicabilities (
                    applicability_id TEXT PRIMARY KEY,
                    method_id TEXT NOT NULL REFERENCES inspection_methods(method_id),
                    scope_type TEXT NOT NULL,
                    product_category TEXT NOT NULL DEFAULT '',
                    product_form TEXT NOT NULL DEFAULT '',
                    ingredient_context TEXT NOT NULL DEFAULT '',
                    source_scope_text TEXT NOT NULL DEFAULT '',
                    note TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                );
                INSERT INTO inspection_method_applicabilities (
                    applicability_id, method_id, scope_type, product_category,
                    product_form, ingredient_context, source_scope_text, note,
                    updated_at
                )
                SELECT applicability_id, method_id, scope_type, product_category,
                       product_form, ingredient_context, source_scope_text, note,
                       updated_at
                FROM inspection_method_applicabilities_v6;
                DROP TABLE inspection_method_applicabilities_v6;
                PRAGMA user_version = 5;
                """
            )

        upgraded = DataStore(database, self.root / "legacy-v5-output")
        upgraded.initialize()
        with sqlite3.connect(database) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            applicability_scopes = connection.execute(
                "SELECT substance_id FROM inspection_method_applicabilities "
                "ORDER BY applicability_id"
            ).fetchall()
            review_note = connection.execute(
                "SELECT review_note FROM reviews WHERE snapshot_id='v5-snapshot'"
            ).fetchone()[0]
            monitor_name = connection.execute(
                "SELECT standard_name FROM monitor_targets WHERE target_id='v5-target'"
            ).fetchone()[0]
            inspection_counts = {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in INSPECTION_TABLES
            }
        self.assertEqual(version, 14)
        self.assertEqual(applicability_scopes, [(None,), (None,)])
        self.assertEqual(review_note, "v5人工备注")
        self.assertEqual(monitor_name, "旧对象")
        self.assertEqual(inspection_counts["substance_group_memberships"], 0)
        self.assertTrue(
            all(
                count > 0
                for table, count in inspection_counts.items()
                if table != "substance_group_memberships"
            )
        )


if __name__ == "__main__":
    unittest.main()
