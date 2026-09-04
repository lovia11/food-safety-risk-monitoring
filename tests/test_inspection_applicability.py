import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.data_store import DataStore
from src.inspection_applicability import (
    ProductApplicabilityResult,
    ProductInspectionContext,
    evaluate_signal_trace,
)
from src.inspection_signal_trace import InspectionSignalTraceResolver


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INSPECTION_REFERENCE_CONFIG = PROJECT_ROOT / "config" / "inspection_reference.json"
RISK_REFERENCE_CONFIG = PROJECT_ROOT / "config" / "risk_substance_reference.json"


def context(
    *,
    product_category: str | None = None,
    product_form: str | None = None,
    ingredients: list[str] | None = None,
    evidence: list[dict] | None = None,
) -> ProductInspectionContext:
    return ProductInspectionContext(
        product_category=product_category,
        product_form=product_form,
        confirmed_ingredient_contexts=ingredients or [],
        context_evidence=evidence or [],
    )


def applicability(
    applicability_id: str,
    scope_type: str,
    *,
    substance_id: str | None = None,
    product_category: str = "",
    product_form: str = "",
    ingredient_context: str = "",
) -> dict:
    return {
        "applicability_id": applicability_id,
        "method_id": "method-a",
        "substance_id": substance_id,
        "scope_type": scope_type,
        "product_category": product_category,
        "product_form": product_form,
        "ingredient_context": ingredient_context,
        "source_scope_text": "synthetic scope",
        "note": "synthetic test only",
    }


def method(
    method_id: str = "method-a",
    *,
    method_status: str = "current",
    method_level: list[dict] | None = None,
    substance_scoped: list[dict] | None = None,
) -> dict:
    rows = [] if method_level is None else method_level
    scoped_rows = [] if substance_scoped is None else substance_scoped
    for row in rows + scoped_rows:
        row["method_id"] = method_id
    return {
        "method_id": method_id,
        "method_no": method_id.upper(),
        "method_name": f"Synthetic {method_id}",
        "method_type": "supplementary_bjs",
        "method_status": method_status,
        "publisher": "synthetic publisher",
        "published_date": "2026-01-01",
        "effective_date": None,
        "determination_role": "qualitative",
        "source_label": "合成物质",
        "source_cas_no": "0000-00-0",
        "normalization_note": "",
        "source_name": "synthetic source",
        "source_reference": "synthetic reference",
        "source_date": "2026-01-01",
        "note": "synthetic test only",
        "method_level_applicabilities": rows,
        "substance_scoped_applicabilities": scoped_rows,
    }


def substance(
    substance_id: str = "substance-a",
    *,
    methods: list[dict] | None = None,
    regulatory_contexts: list[dict] | None = None,
) -> dict:
    return {
        "substance_id": substance_id,
        "canonical_name": f"Synthetic {substance_id}",
        "english_name": "Synthetic substance",
        "cas_no": "0000-00-0",
        "mapping_evidence": [],
        "inspection_methods": [] if methods is None else methods,
        "regulatory_contexts": (
            [] if regulatory_contexts is None else regulatory_contexts
        ),
    }


def signal(
    risk_category: str,
    *,
    substances: list[dict],
    knowledge_gaps: list[dict] | None = None,
) -> dict:
    return {
        "risk_category": risk_category,
        "bridge_mapping_ids": [],
        "reference_mapping_ids": [],
        "trigger_evidence": [],
        "knowledge_trace": {
            "risk_category": risk_category,
            "risk_labels": [],
            "group_targets": [],
            "substance_targets": substances,
            "unresolved_groups": [],
            "knowledge_gaps": [] if knowledge_gaps is None else knowledge_gaps,
        },
    }


def trace(
    *signals: dict,
    composition_gaps: list[dict] | None = None,
) -> dict:
    return {
        "bridge_id": "synthetic-bridge",
        "bridge_version": "synthetic-1",
        "risk_knowledge_signals": list(signals),
        "unmapped_evidence": [],
        "composition_gaps": [] if composition_gaps is None else composition_gaps,
    }


def one_assessment(
    applicability_rows: list[dict],
    product_context: ProductInspectionContext,
    *,
    substance_scoped: bool = False,
    method_status: str = "current",
) -> dict:
    inspection_method = method(
        method_status=method_status,
        method_level=[] if substance_scoped else applicability_rows,
        substance_scoped=applicability_rows if substance_scoped else [],
    )
    result = evaluate_signal_trace(
        trace(signal("risk-a", substances=[substance(methods=[inspection_method])])),
        product_context,
    )
    return result.method_assessments[0]


class ProductInspectionContextTest(unittest.TestCase):
    def test_context_contract_accepts_explicitly_unknown_values(self):
        product_context = context()

        self.assertEqual(
            product_context.to_dict(),
            {
                "product_category": None,
                "product_form": None,
                "confirmed_ingredient_contexts": [],
                "context_evidence": [],
            },
        )
        self.assertEqual(dict(product_context), product_context.to_dict())

    def test_context_evidence_is_preserved_without_source_qualification(self):
        context_evidence = [
            {
                "field": "product_form",
                "value": "片剂",
                "source_type": "user_generated",
                "source_path": "dom_text.txt",
                "text": "用户称为片剂",
            }
        ]
        row = applicability(
            "include-tablet",
            "include",
            product_category="保健食品",
            product_form="片剂",
        )
        product_context = context(
            product_category="保健食品",
            product_form="片剂",
            evidence=context_evidence,
        )
        result = evaluate_signal_trace(
            trace(signal("risk-a", substances=[substance(methods=[method(method_level=[row])])])),
            product_context,
        )

        self.assertEqual(result.product_context["context_evidence"], context_evidence)
        self.assertEqual(
            result.method_assessments[0]["applicability_status"], "applicable"
        )


class FormalReferenceApplicabilityTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.store = DataStore(root / "data" / "app.db", root / "output")
        self.store.initialize()
        self.store.import_inspection_config(INSPECTION_REFERENCE_CONFIG)
        self.store.import_risk_substance_config(RISK_REFERENCE_CONFIG)
        self.signal_trace = InspectionSignalTraceResolver(self.store).resolve_analysis(
            {
                "detected_effects": ["减脂"],
                "evidence_details": [
                    {
                        "effect": "减脂",
                        "text": "帮助减肥",
                        "matched_keywords": ["减肥"],
                        "source_type": "dom_product",
                        "source_label": "当前商品 DOM",
                        "content_origin": "seller_managed",
                        "source_path": "dom_text.txt",
                        "line_number": 1,
                    }
                ],
            }
        )

    def tearDown(self):
        self.temporary.cleanup()

    def _assessment(self, method_id: str, product_context: ProductInspectionContext):
        result = evaluate_signal_trace(self.signal_trace, product_context)
        return next(
            item for item in result.method_assessments if item["method_id"] == method_id
        )

    def test_exact_category_match_uses_real_bjs_201701_include_scope(self):
        assessment = self._assessment(
            "bjs-201701",
            context(product_category="饼干", product_form="饼干"),
        )

        self.assertEqual(assessment["applicability_status"], "applicable")
        self.assertEqual(
            assessment["matched_applicability_ids"], ["bjs-201701-scope-02"]
        )

    def test_category_mismatch_is_not_applicable(self):
        assessment = self._assessment(
            "bjs-201701",
            context(product_category="糖果", product_form="片剂"),
        )

        self.assertEqual(assessment["applicability_status"], "not_applicable")
        self.assertIn("does not establish", assessment["reason"])

    def test_category_missing_is_insufficient_context(self):
        assessment = self._assessment(
            "bjs-201701",
            context(product_form="饼干"),
        )

        self.assertEqual(assessment["applicability_status"], "insufficient_context")
        self.assertEqual(
            assessment["unresolved_applicability_ids"],
            [
                "bjs-201701-scope-01",
                "bjs-201701-scope-02",
                "bjs-201701-scope-03",
                "bjs-201701-scope-04",
            ],
        )

    def test_exact_form_match_uses_real_bjs_201710_include_scope(self):
        assessment = self._assessment(
            "bjs-201710",
            context(product_category="保健食品", product_form="片剂"),
        )

        self.assertEqual(assessment["applicability_status"], "applicable")
        self.assertEqual(
            assessment["matched_applicability_ids"], ["bjs-201710-scope-01"]
        )

    def test_form_mismatch_is_not_applicable_without_fuzzy_matching(self):
        assessment = self._assessment(
            "bjs-201710",
            context(product_category="保健食品", product_form="片"),
        )

        self.assertEqual(assessment["applicability_status"], "not_applicable")

    def test_form_missing_is_insufficient_context(self):
        assessment = self._assessment(
            "bjs-201710",
            context(product_category="保健食品"),
        )

        self.assertEqual(assessment["applicability_status"], "insufficient_context")
        self.assertEqual(
            assessment["unresolved_applicability_ids"],
            [
                "bjs-201710-scope-01",
                "bjs-201710-scope-02",
                "bjs-201710-scope-03",
                "bjs-201710-scope-04",
            ],
        )

    def test_schema_version_remains_seven(self):
        with sqlite3.connect(self.store.database_path) as connection:
            schema_version = connection.execute("PRAGMA user_version").fetchone()[0]

        self.assertEqual(schema_version, 7)


class SyntheticApplicabilityEvaluationTest(unittest.TestCase):
    def test_ingredient_context_requires_exact_confirmed_value(self):
        row = applicability(
            "ingredient-include",
            "include",
            ingredient_context="含红曲的基质",
        )
        assessment = one_assessment(
            [row], context(ingredients=["含红曲的基质"])
        )

        self.assertEqual(assessment["applicability_status"], "applicable")
        self.assertEqual(
            assessment["matched_applicability_ids"], ["ingredient-include"]
        )

    def test_ingredient_substring_is_unresolved_not_a_match(self):
        row = applicability(
            "ingredient-include",
            "include",
            ingredient_context="含红曲的基质",
        )
        assessment = one_assessment([row], context(ingredients=["含红曲"]))

        self.assertEqual(assessment["applicability_status"], "insufficient_context")
        self.assertEqual(
            assessment["unresolved_applicability_ids"], ["ingredient-include"]
        )

    def test_unknown_ingredient_context_is_unresolved_not_not_applicable(self):
        row = applicability(
            "ingredient-include",
            "include",
            ingredient_context="含红曲的基质",
        )
        assessment = one_assessment([row], context())

        self.assertEqual(assessment["applicability_status"], "insufficient_context")

    def test_confirmed_include_is_applicable(self):
        row = applicability(
            "include-a",
            "include",
            product_category="保健食品",
            product_form="片剂",
        )
        assessment = one_assessment(
            [row], context(product_category="保健食品", product_form="片剂")
        )

        self.assertEqual(assessment["applicability_status"], "applicable")

    def test_confirmed_conditional_remains_conditional(self):
        row = applicability(
            "conditional-a",
            "conditional",
            product_category="其他低糖、低脂、低蛋白类基质",
        )
        assessment = one_assessment(
            [row], context(product_category="其他低糖、低脂、低蛋白类基质")
        )

        self.assertEqual(assessment["applicability_status"], "conditional")
        self.assertEqual(
            assessment["conditional_applicability_ids"], ["conditional-a"]
        )

    def test_confirmed_exclude_is_not_applicable(self):
        row = applicability(
            "exclude-a",
            "exclude",
            substance_id="substance-a",
            ingredient_context="含红曲的基质",
        )
        assessment = one_assessment(
            [row],
            context(ingredients=["含红曲的基质"]),
            substance_scoped=True,
        )

        self.assertEqual(assessment["applicability_status"], "not_applicable")
        self.assertEqual(assessment["blocking_applicability_ids"], ["exclude-a"])

    def test_confirmed_exclude_overrides_confirmed_include(self):
        rows = [
            applicability("include-a", "include", product_category="保健食品"),
            applicability(
                "exclude-a",
                "exclude",
                product_category="保健食品",
            ),
        ]
        assessment = one_assessment(rows, context(product_category="保健食品"))

        self.assertEqual(assessment["applicability_status"], "not_applicable")
        self.assertEqual(assessment["matched_applicability_ids"], ["include-a"])
        self.assertEqual(assessment["blocking_applicability_ids"], ["exclude-a"])

    def test_unresolved_special_constraint_prevents_applicable_status(self):
        rows = [
            applicability("include-a", "include", product_category="保健食品"),
            applicability(
                "exclude-ingredient",
                "exclude",
                product_category="保健食品",
                ingredient_context="含红曲的基质",
            ),
        ]
        assessment = one_assessment(rows, context(product_category="保健食品"))

        self.assertEqual(assessment["applicability_status"], "insufficient_context")
        self.assertEqual(
            assessment["unresolved_applicability_ids"], ["exclude-ingredient"]
        )

    def test_substance_scoped_exclude_is_isolated_to_its_substance(self):
        shared_include = applicability(
            "include-a", "include", product_category="保健食品"
        )
        scoped_exclude = applicability(
            "exclude-substance-a",
            "exclude",
            substance_id="substance-a",
            ingredient_context="confirmed matrix",
        )
        method_a = method(
            method_level=[shared_include.copy()],
            substance_scoped=[scoped_exclude],
        )
        method_b = method(
            method_level=[shared_include.copy()],
            substance_scoped=[scoped_exclude.copy()],
        )
        result = evaluate_signal_trace(
            trace(
                signal(
                    "risk-a",
                    substances=[
                        substance("substance-a", methods=[method_a]),
                        substance("substance-b", methods=[method_b]),
                    ],
                )
            ),
            context(
                product_category="保健食品",
                ingredients=["confirmed matrix"],
            ),
        )
        by_substance = {
            item["substance_id"]: item for item in result.method_assessments
        }

        self.assertEqual(
            by_substance["substance-a"]["applicability_status"], "not_applicable"
        )
        self.assertEqual(
            by_substance["substance-b"]["applicability_status"], "applicable"
        )
        self.assertEqual(
            by_substance["substance-b"]["blocking_applicability_ids"], []
        )

    def test_method_status_is_preserved_but_does_not_set_applicability(self):
        row = applicability("include-a", "include", product_category="保健食品")
        assessment = one_assessment(
            [row],
            context(product_category="保健食品"),
            method_status="superseded",
        )

        self.assertEqual(assessment["method_status"], "superseded")
        self.assertEqual(assessment["applicability_status"], "applicable")

    def test_regulatory_context_does_not_change_applicability(self):
        row = applicability("include-a", "include", product_category="保健食品")
        inspection_method = method(method_level=[row])
        base = substance(methods=[inspection_method], regulatory_contexts=[])
        with_context = substance(
            methods=[inspection_method],
            regulatory_contexts=[
                {
                    "context_id": "legal-context",
                    "context_status": "legal_health_food_raw_material",
                }
            ],
        )
        product_context = context(product_category="保健食品")

        without_status = evaluate_signal_trace(
            trace(signal("risk-a", substances=[base])), product_context
        ).method_assessments[0]["applicability_status"]
        with_status = evaluate_signal_trace(
            trace(signal("risk-a", substances=[with_context])), product_context
        ).method_assessments[0]["applicability_status"]
        self.assertEqual(without_status, "applicable")
        self.assertEqual(with_status, without_status)

    def test_d3_composition_gaps_are_preserved(self):
        gap = {
            "type": "bridge_reference_not_in_knowledge_trace",
            "risk_category": "risk-a",
            "bridge_mapping_ids": ["bridge-a"],
            "reference_mapping_id": "reference-a",
            "message": "synthetic gap",
        }
        result = evaluate_signal_trace(
            trace(
                signal("risk-a", substances=[]),
                composition_gaps=[gap],
            ),
            context(),
        )

        self.assertEqual(result.composition_gaps, [gap])

    def test_d1_knowledge_gap_is_preserved_without_fake_assessment(self):
        gap = {
            "type": "no_verified_method",
            "substance_id": "substance-a",
            "message": "No persisted MethodSubstance relation was found.",
        }
        result = evaluate_signal_trace(
            trace(
                signal(
                    "risk-a",
                    substances=[substance(methods=[])],
                    knowledge_gaps=[gap],
                )
            ),
            context(),
        )

        self.assertEqual(result.method_assessments, [])
        self.assertEqual(
            result.knowledge_gaps,
            [{"risk_category": "risk-a", **gap}],
        )

    def test_multiple_methods_are_assessed_independently(self):
        include_method = method(
            "method-include",
            method_level=[
                applicability("include-a", "include", product_category="保健食品")
            ],
        )
        conditional_method = method(
            "method-conditional",
            method_level=[
                applicability(
                    "conditional-a", "conditional", product_category="保健食品"
                )
            ],
        )
        result = evaluate_signal_trace(
            trace(
                signal(
                    "risk-a",
                    substances=[
                        substance(methods=[include_method, conditional_method])
                    ],
                )
            ),
            context(product_category="保健食品"),
        )
        by_method = {item["method_id"]: item for item in result.method_assessments}

        self.assertEqual(
            by_method["method-include"]["applicability_status"], "applicable"
        )
        self.assertEqual(
            by_method["method-conditional"]["applicability_status"], "conditional"
        )

    def test_assessment_and_applicability_id_ordering_is_deterministic(self):
        method_z = method(
            "method-z",
            method_level=[
                applicability("include-z", "include", product_category="保健食品"),
                applicability("include-a", "include", product_category="保健食品"),
            ],
        )
        method_a = method(
            "method-a",
            method_level=[
                applicability("include-b", "include", product_category="保健食品")
            ],
        )
        result = evaluate_signal_trace(
            trace(
                signal(
                    "risk-z",
                    substances=[substance("substance-z", methods=[method_z])],
                ),
                signal(
                    "risk-a",
                    substances=[substance("substance-a", methods=[method_a])],
                ),
            ),
            context(product_category="保健食品"),
        )

        self.assertEqual(
            [
                (item["risk_category"], item["substance_id"], item["method_id"])
                for item in result.method_assessments
            ],
            [
                ("risk-a", "substance-a", "method-a"),
                ("risk-z", "substance-z", "method-z"),
            ],
        )
        self.assertEqual(
            result.method_assessments[1]["matched_applicability_ids"],
            ["include-a", "include-z"],
        )

    def test_output_has_no_recommendation_or_scoring_fields(self):
        row = applicability("include-a", "include", product_category="保健食品")
        result = evaluate_signal_trace(
            trace(
                signal(
                    "risk-a",
                    substances=[substance(methods=[method(method_level=[row])])],
                )
            ),
            context(product_category="保健食品"),
        ).to_dict()
        forbidden = {
            "recommended",
            "recommendation",
            "preferred",
            "best",
            "priority",
            "risk_score",
            "confidence",
            "illegal",
            "selected_method",
        }

        def assert_no_forbidden_fields(value):
            if isinstance(value, dict):
                self.assertTrue(forbidden.isdisjoint(value))
                for nested in value.values():
                    assert_no_forbidden_fields(nested)
            elif isinstance(value, list):
                for nested in value:
                    assert_no_forbidden_fields(nested)

        assert_no_forbidden_fields(result)

    def test_result_contract_is_json_compatible_mapping(self):
        row = applicability("include-a", "include", product_category="保健食品")
        result = evaluate_signal_trace(
            trace(
                signal(
                    "risk-a",
                    substances=[substance(methods=[method(method_level=[row])])],
                )
            ),
            context(product_category="保健食品"),
        )

        self.assertIsInstance(result, ProductApplicabilityResult)
        self.assertEqual(
            set(result.to_dict()),
            {
                "product_context",
                "method_assessments",
                "composition_gaps",
                "knowledge_gaps",
            },
        )


if __name__ == "__main__":
    unittest.main()
