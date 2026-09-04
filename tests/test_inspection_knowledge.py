import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.data_store import DataStore
from src.inspection_knowledge import InspectionKnowledgeResolver, KnowledgeTrace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INSPECTION_REFERENCE_CONFIG = PROJECT_ROOT / "config" / "inspection_reference.json"
RISK_REFERENCE_CONFIG = PROJECT_ROOT / "config" / "risk_substance_reference.json"

SIBUTRAMINE_ID = "substance-cas-106650-56-0"
SILDENAFIL_ID = "substance-cas-139755-83-2"
TADALAFIL_ID = "substance-cas-171596-29-5"
MELATONIN_ID = "substance-cas-73-31-4"


class InspectionKnowledgeResolverTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.store = DataStore(root / "data" / "app.db", root / "output")
        self.store.initialize()
        self.store.import_inspection_config(INSPECTION_REFERENCE_CONFIG)
        self.store.import_risk_substance_config(RISK_REFERENCE_CONFIG)
        self.resolver = InspectionKnowledgeResolver(self.store)

    def tearDown(self):
        self.temporary.cleanup()

    def _execute(self, sql: str, parameters: tuple = ()) -> None:
        with sqlite3.connect(self.store.database_path) as connection:
            connection.execute(sql, parameters)

    def _insert_mapping(
        self,
        *,
        mapping_id: str,
        risk_category: str,
        target_type: str,
        substance_id: str | None = None,
        group_label: str | None = None,
        temporal_status: str = "current",
        dataset_id: str = "risk-substance-reference",
    ) -> None:
        evidence_grade = "A" if temporal_status == "current" else "B"
        basis_type = (
            "current_official_guidance"
            if temporal_status == "current"
            else "historical_sampling_plan"
        )
        self._execute(
            """
            INSERT INTO risk_substance_mappings (
                mapping_id, dataset_id, risk_category, risk_label, target_type,
                substance_id, target_group_label, evidence_grade, basis_type,
                temporal_status, product_scope, source_name, source_reference,
                source_date, source_basis_text, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                      'synthetic scope', 'synthetic source', 'synthetic reference',
                      '2026-01-01', 'synthetic basis', 'synthetic test only')
            """,
            (
                mapping_id,
                dataset_id,
                risk_category,
                f"{risk_category} label",
                target_type,
                substance_id,
                group_label,
                evidence_grade,
                basis_type,
                temporal_status,
            ),
        )

    def _insert_risk_dataset(
        self, dataset_id: str, dataset_status: str = "development_seed"
    ) -> None:
        self._execute(
            """
            INSERT INTO risk_mapping_datasets (
                dataset_id, dataset_version, dataset_status, source_name,
                source_reference, source_date, collected_at, verified_at,
                description, imported_at
            ) VALUES (?, 'synthetic-1', ?, 'synthetic source',
                      'synthetic reference', '2026-01-01',
                      '2026-01-01T00:00:00+08:00', NULL,
                      'synthetic test only', '2026-01-01T00:00:00+08:00')
            """,
            (dataset_id, dataset_status),
        )

    @staticmethod
    def _substances_by_id(trace: KnowledgeTrace) -> dict[str, dict]:
        return {item["substance_id"]: item for item in trace.substance_targets}

    def test_weight_loss_resolves_one_group_and_sibutramine_identity(self):
        trace = self.resolver.resolve("weight_loss")

        self.assertEqual(trace.risk_category, "weight_loss")
        self.assertEqual(trace.risk_labels, ["减肥/减重宣传"])
        self.assertEqual(len(trace.group_targets), 1)
        self.assertEqual(len(trace.substance_targets), 1)
        self.assertEqual(
            trace.group_targets[0]["target_group_label"],
            "西布曲明及其系列衍生物",
        )
        self.assertEqual(
            {
                key: trace.substance_targets[0][key]
                for key in ("substance_id", "canonical_name", "cas_no")
            },
            {
                "substance_id": SIBUTRAMINE_ID,
                "canonical_name": "西布曲明",
                "cas_no": "106650-56-0",
            },
        )

    def test_male_function_resolves_one_group_and_two_substances(self):
        trace = self.resolver.resolve("male_function")

        self.assertEqual(len(trace.group_targets), 1)
        self.assertEqual(
            {item["substance_id"] for item in trace.substance_targets},
            {SILDENAFIL_ID, TADALAFIL_ID},
        )

    def test_anti_fatigue_resolves_one_group_and_two_substances(self):
        trace = self.resolver.resolve("anti_fatigue")

        self.assertEqual(len(trace.group_targets), 1)
        self.assertEqual(
            {item["substance_id"] for item in trace.substance_targets},
            {SILDENAFIL_ID, TADALAFIL_ID},
        )

    def test_groups_remain_partial_and_do_not_expand_method_substance_members(self):
        weight_loss = self.resolver.resolve("weight_loss")
        male_function = self.resolver.resolve("male_function")

        self.assertEqual(weight_loss.group_targets[0]["resolution_status"], "partial")
        self.assertEqual(
            weight_loss.unresolved_groups[0]["resolution_status"], "partial"
        )
        self.assertEqual(
            weight_loss.unresolved_groups[0]["mapping_ids"],
            ["weight-loss-sibutramine-group-cn-2025"],
        )
        self.assertEqual(
            {item["substance_id"] for item in weight_loss.substance_targets},
            {SIBUTRAMINE_ID},
        )
        self.assertEqual(
            {item["substance_id"] for item in male_function.substance_targets},
            {SILDENAFIL_ID, TADALAFIL_ID},
        )
        self.assertIn(
            "unresolved_group",
            {gap["type"] for gap in weight_loss.knowledge_gaps},
        )

    def test_substance_mapping_provenance_is_preserved_completely(self):
        evidence_rows = [
            target["mapping_evidence"]
            for category in ("weight_loss", "male_function", "anti_fatigue")
            for target in self.resolver.resolve(category).substance_targets
        ]

        self.assertEqual(len(evidence_rows), 5)
        for evidence_list in evidence_rows:
            self.assertEqual(len(evidence_list), 1)
            evidence = evidence_list[0]
            self.assertEqual(
                set(evidence),
                {
                    "mapping_id",
                    "evidence_grade",
                    "basis_type",
                    "temporal_status",
                    "product_scope",
                    "source_name",
                    "source_reference",
                    "source_date",
                    "source_basis_text",
                    "note",
                },
            )
            self.assertTrue(all(evidence[field] for field in evidence))

    def test_methods_are_resolved_dynamically_through_method_substance(self):
        before = self.resolver.resolve("weight_loss").substance_targets[0]
        self.assertEqual(
            [method["method_id"] for method in before["inspection_methods"]],
            ["bjs-201701", "bjs-201710"],
        )

        self._execute(
            "DELETE FROM inspection_method_substances "
            "WHERE method_id = 'bjs-201710' AND substance_id = ?",
            (SIBUTRAMINE_ID,),
        )
        after = self.resolver.resolve("weight_loss").substance_targets[0]
        self.assertEqual(
            [method["method_id"] for method in after["inspection_methods"]],
            ["bjs-201701"],
        )
        self.assertEqual(
            after["inspection_methods"][0]["determination_role"], "qualitative"
        )

    def test_non_current_method_status_is_returned_without_recommendation_ranking(self):
        self._execute(
            "UPDATE inspection_methods SET method_status = 'superseded' "
            "WHERE method_id = 'bjs-201701'"
        )

        methods = self.resolver.resolve("weight_loss").substance_targets[0][
            "inspection_methods"
        ]
        self.assertEqual(methods[0]["method_id"], "bjs-201701")
        self.assertEqual(methods[0]["method_status"], "superseded")
        self.assertNotIn("priority", methods[0])
        self.assertNotIn("recommended", methods[0])

    def test_method_level_applicability_is_attached_to_each_matching_method(self):
        methods = self.resolver.resolve("weight_loss").substance_targets[0][
            "inspection_methods"
        ]
        bjs_201701 = next(item for item in methods if item["method_id"] == "bjs-201701")

        method_level = bjs_201701["method_level_applicabilities"]
        self.assertEqual(len(method_level), 4)
        self.assertTrue(all(item["substance_id"] is None for item in method_level))
        self.assertEqual(
            {item["scope_type"] for item in method_level}, {"include", "conditional"}
        )

    def test_other_substance_scoped_applicability_is_not_leaked(self):
        self._execute(
            """
            INSERT INTO inspection_method_applicabilities (
                applicability_id, method_id, substance_id, scope_type,
                product_category, product_form, ingredient_context,
                source_scope_text, note, updated_at
            ) VALUES (
                'synthetic-other-substance-scope', 'bjs-201710', ?, 'conditional',
                'synthetic category', '', 'synthetic context',
                'synthetic other-substance scope', 'synthetic test only',
                '2026-01-01T00:00:00+08:00'
            )
            """,
            (MELATONIN_ID,),
        )

        sildenafil = self._substances_by_id(
            self.resolver.resolve("male_function")
        )[SILDENAFIL_ID]
        bjs_201710 = next(
            item
            for item in sildenafil["inspection_methods"]
            if item["method_id"] == "bjs-201710"
        )
        self.assertEqual(bjs_201710["substance_scoped_applicabilities"], [])

    def test_regulatory_context_is_attached_only_to_its_substance(self):
        self._insert_mapping(
            mapping_id="synthetic-melatonin-context",
            risk_category="synthetic_context",
            target_type="substance",
            substance_id=MELATONIN_ID,
        )

        melatonin = self.resolver.resolve("synthetic_context").substance_targets[0]
        self.assertEqual(
            melatonin["regulatory_contexts"][0]["context_status"],
            "legal_health_food_raw_material",
        )
        self.assertEqual(
            melatonin["regulatory_contexts"][0]["context_id"],
            "melatonin-health-food-raw-material-cn-2021",
        )
        self.assertEqual(
            set(melatonin["regulatory_contexts"][0]),
            {
                "context_id",
                "context_status",
                "product_scope",
                "jurisdiction",
                "valid_from",
                "valid_to",
                "source_label",
                "source_name",
                "source_reference",
                "source_date",
                "note",
            },
        )
        self.assertNotIn("legal", melatonin["regulatory_contexts"][0])
        self.assertEqual(
            self.resolver.resolve("weight_loss").substance_targets[0][
                "regulatory_contexts"
            ],
            [],
        )

    def test_group_only_risk_exposes_no_concrete_substance_gap(self):
        self._insert_mapping(
            mapping_id="synthetic-group-only",
            risk_category="synthetic_group_only",
            target_type="substance_group",
            group_label="合成测试组",
        )

        trace = self.resolver.resolve("synthetic_group_only")
        self.assertEqual(len(trace.group_targets), 1)
        self.assertEqual(trace.substance_targets, [])
        self.assertEqual(
            {gap["type"] for gap in trace.knowledge_gaps},
            {"unresolved_group", "no_concrete_substance"},
        )

    def test_substance_without_method_exposes_no_verified_method_gap(self):
        self._execute(
            """
            INSERT INTO inspection_substances (
                substance_id, dataset_id, canonical_name, english_name,
                cas_no, substance_group, note, updated_at
            ) VALUES (
                'synthetic-substance-no-method', 'inspection-reference',
                '合成无方法物质', 'Synthetic no-method substance',
                '0000-00-0', '', 'synthetic test only',
                '2026-01-01T00:00:00+08:00'
            )
            """
        )
        self._insert_mapping(
            mapping_id="synthetic-no-method",
            risk_category="synthetic_no_method",
            target_type="substance",
            substance_id="synthetic-substance-no-method",
        )

        trace = self.resolver.resolve("synthetic_no_method")
        self.assertEqual(len(trace.substance_targets), 1)
        self.assertEqual(trace.substance_targets[0]["inspection_methods"], [])
        self.assertEqual(
            [gap["type"] for gap in trace.knowledge_gaps],
            ["no_verified_method"],
        )

    def test_unknown_risk_returns_empty_trace(self):
        trace = self.resolver.resolve("unknown_risk")

        self.assertEqual(
            trace.to_dict(),
            {
                "risk_category": "unknown_risk",
                "risk_labels": [],
                "group_targets": [],
                "substance_targets": [],
                "unresolved_groups": [],
                "knowledge_gaps": [],
            },
        )

    def test_non_verified_risk_datasets_are_excluded_in_both_temporal_modes(self):
        self._insert_risk_dataset("synthetic-development-risk")
        self._insert_mapping(
            mapping_id="synthetic-development-weight-loss-group",
            dataset_id="synthetic-development-risk",
            risk_category="weight_loss",
            target_type="substance_group",
            group_label="开发测试Group",
        )
        self._insert_risk_dataset(
            "synthetic-pending-risk", dataset_status="reference_pending"
        )
        self._insert_mapping(
            mapping_id="synthetic-pending-weight-loss-group",
            dataset_id="synthetic-pending-risk",
            risk_category="weight_loss",
            target_type="substance_group",
            group_label="待核验测试Group",
        )

        for include_historical in (False, True):
            with self.subTest(include_historical=include_historical):
                trace = self.resolver.resolve(
                    "weight_loss", include_historical=include_historical
                )
                self.assertEqual(len(trace.group_targets), 1)
                self.assertEqual(len(trace.substance_targets), 1)
                self.assertEqual(
                    trace.group_targets[0]["target_group_label"],
                    "西布曲明及其系列衍生物",
                )
                self.assertNotIn(
                    "开发测试Group",
                    {
                        item["target_group_label"]
                        for item in trace.group_targets
                    },
                )
                self.assertNotIn(
                    "待核验测试Group",
                    {
                        item["target_group_label"]
                        for item in trace.group_targets
                    },
                )

    def test_substance_identity_aggregates_current_and_historical_evidence(self):
        self._insert_mapping(
            mapping_id="synthetic-substance-a-current",
            risk_category="synthetic_multi_evidence",
            target_type="substance",
            substance_id=SIBUTRAMINE_ID,
        )
        self._insert_mapping(
            mapping_id="synthetic-substance-b-historical",
            risk_category="synthetic_multi_evidence",
            target_type="substance",
            substance_id=SIBUTRAMINE_ID,
            temporal_status="historical",
        )

        current = self.resolver.resolve("synthetic_multi_evidence")
        with (
            mock.patch.object(
                self.store,
                "get_inspection_substance",
                wraps=self.store.get_inspection_substance,
            ) as get_substance,
            mock.patch.object(
                self.store,
                "list_substance_methods",
                wraps=self.store.list_substance_methods,
            ) as list_methods,
            mock.patch.object(
                self.store,
                "list_method_applicabilities",
                wraps=self.store.list_method_applicabilities,
            ) as list_applicabilities,
            mock.patch.object(
                self.store,
                "list_substance_regulatory_contexts",
                wraps=self.store.list_substance_regulatory_contexts,
            ) as list_contexts,
        ):
            historical = self.resolver.resolve(
                "synthetic_multi_evidence", include_historical=True
            )
        self.assertEqual(get_substance.call_count, 1)
        self.assertEqual(list_methods.call_count, 1)
        self.assertEqual(list_applicabilities.call_count, 2)
        self.assertEqual(list_contexts.call_count, 1)
        self.assertEqual(len(current.substance_targets), 1)
        self.assertEqual(len(current.substance_targets[0]["mapping_evidence"]), 1)
        self.assertEqual(
            current.substance_targets[0]["mapping_evidence"][0]["mapping_id"],
            "synthetic-substance-a-current",
        )
        self.assertEqual(
            current.substance_targets[0]["mapping_evidence"][0]["temporal_status"],
            "current",
        )
        self.assertEqual(len(historical.substance_targets), 1)
        self.assertEqual(
            [
                evidence["mapping_id"]
                for evidence in historical.substance_targets[0]["mapping_evidence"]
            ],
            [
                "synthetic-substance-a-current",
                "synthetic-substance-b-historical",
            ],
        )

    def test_group_identity_aggregates_evidence_and_gap_once(self):
        for mapping_id, temporal_status in (
            ("synthetic-group-a-current", "current"),
            ("synthetic-group-b-historical", "historical"),
        ):
            self._insert_mapping(
                mapping_id=mapping_id,
                risk_category="synthetic_group_evidence",
                target_type="substance_group",
                group_label="同一测试Group",
                temporal_status=temporal_status,
            )

        trace = self.resolver.resolve(
            "synthetic_group_evidence", include_historical=True
        )
        unresolved_gaps = [
            gap for gap in trace.knowledge_gaps if gap["type"] == "unresolved_group"
        ]
        expected_mapping_ids = [
            "synthetic-group-a-current",
            "synthetic-group-b-historical",
        ]
        self.assertEqual(len(trace.group_targets), 1)
        self.assertEqual(len(trace.group_targets[0]["mapping_evidence"]), 2)
        self.assertEqual(len(trace.unresolved_groups), 1)
        self.assertEqual(
            trace.unresolved_groups[0]["mapping_ids"], expected_mapping_ids
        )
        self.assertEqual(len(unresolved_gaps), 1)
        self.assertEqual(unresolved_gaps[0]["mapping_ids"], expected_mapping_ids)

    def test_include_historical_defaults_to_false(self):
        for category in ("weight_loss", "male_function", "anti_fatigue"):
            self.assertEqual(
                self.resolver.resolve(category).to_dict(),
                self.resolver.resolve(
                    category, include_historical=True
                ).to_dict(),
            )

        self._insert_mapping(
            mapping_id="synthetic-history-current",
            risk_category="synthetic_history",
            target_type="substance_group",
            group_label="当前组",
        )
        self._insert_mapping(
            mapping_id="synthetic-history-old",
            risk_category="synthetic_history",
            target_type="substance_group",
            group_label="历史组",
            temporal_status="historical",
        )

        default_trace = self.resolver.resolve("synthetic_history")
        historical_trace = self.resolver.resolve(
            "synthetic_history", include_historical=True
        )
        self.assertEqual(
            [
                item["mapping_evidence"][0]["mapping_id"]
                for item in default_trace.group_targets
            ],
            ["synthetic-history-current"],
        )
        self.assertEqual(
            [
                item["mapping_evidence"][0]["mapping_id"]
                for item in historical_trace.group_targets
            ],
            ["synthetic-history-old", "synthetic-history-current"],
        )

    def test_trace_has_no_numeric_risk_score(self):
        trace = self.resolver.resolve("weight_loss").to_dict()

        def assert_no_score(value):
            if isinstance(value, dict):
                for key, nested in value.items():
                    self.assertNotIn("score", key.lower())
                    assert_no_score(nested)
            elif isinstance(value, list):
                for nested in value:
                    assert_no_score(nested)

        assert_no_score(trace)

    def test_schema_does_not_persist_a_risk_to_method_shortcut(self):
        with sqlite3.connect(self.store.database_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            schema_version = connection.execute("PRAGMA user_version").fetchone()[0]

        self.assertNotIn("risk_method_mapping", tables)
        self.assertNotIn("risk_method_mappings", tables)
        self.assertEqual(schema_version, 7)


if __name__ == "__main__":
    unittest.main()
