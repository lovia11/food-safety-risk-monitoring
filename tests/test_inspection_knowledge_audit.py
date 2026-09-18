import copy
import unittest

from scripts.audit_inspection_knowledge import (
    DEFAULT_BRIDGE_CONFIG,
    DEFAULT_INSPECTION_CONFIG,
    DEFAULT_RISK_CONFIG,
    InspectionKnowledgeAuditError,
    build_audit,
    load_and_build_audit,
)
from src.claim_inspection_bridge import validate_claim_inspection_bridge_config
from src.inspection_reference import validate_inspection_config
from src.risk_substance_reference import validate_risk_substance_config
from src.runtime import read_json


class InspectionKnowledgeAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inspection_raw = read_json(DEFAULT_INSPECTION_CONFIG)
        cls.risk_raw = read_json(DEFAULT_RISK_CONFIG)
        cls.bridge_raw = read_json(DEFAULT_BRIDGE_CONFIG)
        cls.inspection = validate_inspection_config(cls.inspection_raw)
        cls.risk = validate_risk_substance_config(cls.risk_raw)
        cls.bridge = validate_claim_inspection_bridge_config(
            cls.bridge_raw,
            risk_reference_config=cls.risk_raw,
        )

    def test_current_governed_inventory_and_coverage_are_stable(self):
        report = load_and_build_audit()
        inventory = report["inventory"]

        self.assertEqual(inventory["governed_dataset_count"], 3)
        self.assertEqual(inventory["methods"], 9)
        self.assertEqual(inventory["indexed_methods"], 9)
        self.assertEqual(inventory["candidate_records"], 12)
        self.assertEqual(inventory["candidate_methods"], 8)
        self.assertEqual(inventory["promoted_candidate_methods"], 4)
        self.assertEqual(
            inventory["knowledge_depth_counts"],
            {
                "reference_only": 1,
                "analyte_verified": 0,
                "applicability_verified": 0,
                "recommendation_ready": 8,
            },
        )
        self.assertEqual(
            inventory["method_type_counts"],
            {
                "supplementary_bjs": 4,
                "rapid_kj": 3,
                "national_standard_gbt": 2,
            },
        )
        self.assertEqual(inventory["method_status_counts"]["current"], 8)
        self.assertEqual(inventory["method_status_counts"]["revoked"], 1)
        self.assertEqual(inventory["substances"], 201)
        self.assertEqual(inventory["method_substance_relations"], 231)
        self.assertEqual(inventory["method_applicabilities"], 46)
        self.assertEqual(inventory["substance_regulatory_contexts"], 1)
        self.assertEqual(inventory["regulatory_documents"], 7)
        self.assertEqual(inventory["method_regulatory_document_links"], 9)
        self.assertEqual(inventory["unresolved_lifecycle_document_edges"], 0)
        self.assertEqual(inventory["risk_substance_mappings"], 7)
        self.assertEqual(inventory["risk_substance_group_mappings"], 6)
        self.assertEqual(inventory["risk_mappings_total"], 81)
        self.assertEqual(inventory["risk_mappings_current"], 13)
        self.assertEqual(inventory["risk_mappings_historical"], 68)
        self.assertEqual(inventory["historical_risk_categories"], 6)
        self.assertEqual(inventory["historical_risk_group_labels"], 6)
        self.assertEqual(inventory["evidence_risk_bridge_mappings"], 25)
        self.assertEqual(inventory["group_membership_relations"], 0)
        self.assertTrue(
            report["integrity"]["depth_declarations_match_static_gate"]
        )
        self.assertEqual(
            report["metrics"]["method_reference_coverage"],
            {
                "numerator": 9,
                "denominator": 9,
                "ratio": 1.0,
                "denominator_definition": (
                    "methods in the committed Inspection Reference Index"
                ),
            },
        )
        self.assertEqual(
            report["metrics"]["method_deep_verification_coverage"]["numerator"],
            8,
        )
        self.assertEqual(
            report["metrics"]["method_deep_verification_coverage"]["denominator"],
            9,
        )
        self.assertEqual(
            report["metrics"]["recommendation_end_to_end_reachability"],
            {
                "numerator": 7,
                "denominator": 7,
                "ratio": 1.0,
                "denominator_definition": (
                    "current explicit governed Risk-to-Substance mappings; requires an "
                    "existing Evidence-to-Risk category bridge and a structurally ready "
                    "method path"
                ),
            },
        )

    def test_historical_inventory_does_not_pollute_current_coverage(self):
        report = load_and_build_audit()

        self.assertEqual(report["inventory"]["risk_mappings_historical"], 68)
        current_reachability_categories = {
            item["risk_category"] for item in report["risk_reachability"]
        }
        for historical_only_category in {
            "sleep_aid", "blood_pressure", "blood_lipid", "blood_glucose"
        }:
            self.assertNotIn(
                historical_only_category,
                current_reachability_categories,
            )
        self.assertIn("weight_loss", current_reachability_categories)
        self.assertIn("anti_fatigue", current_reachability_categories)
        self.assertEqual(
            report["metrics"]["recommendation_end_to_end_reachability"]["denominator"],
            7,
        )
        self.assertEqual(
            report["inventory"]["runtime_recommendation_usage"]["risk_category_ids"],
            ["anti_fatigue", "male_function", "weight_loss"],
        )

    def test_no_dangling_governed_identities(self):
        report = load_and_build_audit()

        self.assertTrue(
            all(not values for values in report["integrity"]["dangling_identities"].values())
        )

    def test_dangling_risk_or_applicability_identity_fails_the_audit(self):
        risk = copy.deepcopy(self.risk)
        risk["mappings"][0]["target_type"] = "substance"
        risk["mappings"][0]["substance_id"] = "substance-missing"
        risk["mappings"][0]["target_group_label"] = None
        with self.assertRaisesRegex(
            InspectionKnowledgeAuditError, "substance-missing"
        ):
            build_audit(self.inspection, risk, self.bridge)

        inspection = copy.deepcopy(self.inspection)
        inspection["method_applicabilities"][0]["method_id"] = "method-missing"
        with self.assertRaisesRegex(
            InspectionKnowledgeAuditError, "method-missing"
        ):
            build_audit(inspection, self.risk, self.bridge)

    def test_group_mapping_is_not_expanded_from_substance_group_labels(self):
        inspection = copy.deepcopy(self.inspection)
        inspection["substances"][0]["substance_group"] = "西布曲明及其系列衍生物"

        report = build_audit(inspection, self.risk, self.bridge)
        group_rows = [
            item
            for item in report["risk_reachability"]
            if item["target_type"] == "substance_group"
        ]

        self.assertEqual(len(group_rows), 6)
        self.assertTrue(all(not item["has_explicit_substance"] for item in group_rows))
        self.assertTrue(all(item["method_ids"] == [] for item in group_rows))
        self.assertTrue(all(item["gap_reason"] == "group_not_expanded" for item in group_rows))
        self.assertFalse(report["integrity"]["groups_expanded"])

    def test_method_relation_never_creates_a_risk_mapping(self):
        inspection = copy.deepcopy(self.inspection)
        unrelated = next(
            item
            for item in inspection["substances"]
            if item["substance_id"]
            not in {
                mapping["substance_id"]
                for mapping in self.risk["mappings"]
                if mapping["target_type"] == "substance"
            }
        )
        inspection["method_substances"].append(
            {
                "method_id": "bjs-202209",
                "substance_id": unrelated["substance_id"],
                "source_label": unrelated["canonical_name"],
                "source_cas_no": unrelated["cas_no"],
                "determination_role": "quantitative",
                "normalization_note": "test-only relation",
                "ordinal": 999,
            }
        )

        report = build_audit(inspection, self.risk, self.bridge)

        self.assertEqual(report["inventory"]["risk_mappings_total"], 81)
        self.assertEqual(report["inventory"]["risk_mappings_current"], 13)
        self.assertEqual(report["inventory"]["risk_mappings_historical"], 68)
        self.assertNotIn(
            unrelated["substance_id"],
            {item["target"] for item in report["risk_reachability"]},
        )
        self.assertFalse(report["integrity"]["risk_mappings_derived_from_methods"])

    def test_missing_applicability_remains_an_explicit_gap(self):
        inspection = copy.deepcopy(self.inspection)
        inspection["method_applicabilities"] = [
            item
            for item in inspection["method_applicabilities"]
            if item["method_id"] != "gbt-45443-2025"
        ]

        report = build_audit(inspection, self.risk, self.bridge)
        method = next(
            item
            for item in report["method_matrix"]
            if item["method_id"] == "gbt-45443-2025"
        )

        self.assertFalse(method["applicability_verified"])
        self.assertEqual(method["knowledge_depth"], "analyte_verified")
        self.assertIn(
            {
                "method_id": "gbt-45443-2025",
                "substance_id": "substance-cas-73-31-4",
            },
            report["applicability_quality"]["missing_relation_paths"],
        )

    def test_superseded_lifecycle_is_preserved_and_not_recommendation_ready(self):
        inspection = copy.deepcopy(self.inspection)
        method = next(
            item
            for item in inspection["methods"]
            if item["method_id"] == "bjs-201701"
        )
        method["method_status"] = "superseded"
        method["replaced_by_method_no"] = "TEST 000001"

        report = build_audit(inspection, self.risk, self.bridge)
        audited = next(
            item
            for item in report["method_matrix"]
            if item["method_id"] == "bjs-201701"
        )

        self.assertEqual(audited["method_status"], "superseded")
        self.assertEqual(audited["knowledge_depth"], "applicability_verified")
        self.assertFalse(audited["recommendation_ready"])

    def test_all_current_method_and_risk_records_retain_official_provenance(self):
        report = load_and_build_audit()

        self.assertTrue(
            all(
                item["reference_complete"] and item["official_source_reference"]
                for item in report["method_matrix"]
            )
        )
        for mapping in self.risk["mappings"]:
            self.assertTrue(mapping["source_name"])
            self.assertTrue(mapping["source_reference"].startswith("https://www.samr.gov.cn/"))
            self.assertTrue(mapping["source_date"])
            self.assertTrue(mapping["source_basis_text"])

    def test_risk_scoped_applicability_does_not_leak_across_risk_categories(self):
        inspection = copy.deepcopy(self.inspection)
        for item in inspection["method_applicabilities"]:
            if item["method_id"] == "bjs-202405":
                item["risk_category"] = "anti_fatigue"

        report = build_audit(inspection, self.risk, self.bridge)
        by_key = {
            (item["risk_category"], item["target"]): item
            for item in report["risk_reachability"]
            if item["target_type"] == "substance"
        }
        sildenafil_id = "substance-cas-139755-83-2"

        anti = by_key[("anti_fatigue", sildenafil_id)]
        male = by_key[("male_function", sildenafil_id)]
        self.assertIn("bjs-202405", anti["recommendation_ready_method_ids"])
        self.assertNotIn("bjs-202405", male["recommendation_ready_method_ids"])
        self.assertIn("bjs-201710", male["recommendation_ready_method_ids"])

    def test_current_runtime_usage_is_computed_from_bridge_categories_only(self):
        usage = load_and_build_audit()["inventory"]["runtime_recommendation_usage"]

        self.assertEqual(
            usage["risk_category_ids"],
            ["anti_fatigue", "male_function", "weight_loss"],
        )
        self.assertEqual(usage["risk_mapping_rows"], 13)
        self.assertEqual(usage["explicit_substances"], 5)
        self.assertEqual(
            usage["method_ids"],
            ["bjs-201701", "bjs-201710", "bjs-202405", "kj-201901"],
        )
        self.assertEqual(usage["applicability_records"], 20)

    def test_bjs_202405_enters_deep_subset_while_old_gbt_stays_reference_only(self):
        report = load_and_build_audit()
        methods = {item["method_id"]: item for item in report["method_matrix"]}

        self.assertEqual(
            methods["bjs-202405"]["knowledge_depth"], "recommendation_ready"
        )
        self.assertEqual(methods["bjs-202405"]["method_status"], "current")
        self.assertTrue(methods["bjs-202405"]["recommendation_ready"])
        self.assertEqual(methods["bjs-202405"]["analyte_relation_count"], 95)
        self.assertEqual(methods["bjs-202405"]["applicability_count"], 7)
        self.assertEqual(
            methods["gbt-5009-170-2003"]["knowledge_depth"],
            "reference_only",
        )
        self.assertEqual(methods["gbt-5009-170-2003"]["method_status"], "revoked")
        self.assertFalse(methods["gbt-5009-170-2003"]["recommendation_ready"])
        self.assertEqual(
            report["inventory"]["runtime_recommendation_usage"]["method_ids"],
            ["bjs-201701", "bjs-201710", "bjs-202405", "kj-201901"],
        )

    def test_kj_promotions_are_deep_but_preserve_risk_scopes(self):
        report = load_and_build_audit()
        methods = {item["method_id"]: item for item in report["method_matrix"]}

        for method_id in ("kj-201901", "kj-201902"):
            self.assertEqual(
                methods[method_id]["knowledge_depth"],
                "recommendation_ready",
            )
            self.assertTrue(methods[method_id]["recommendation_ready"])
            self.assertEqual(methods[method_id]["analyte_relation_count"], 2)
            self.assertEqual(methods[method_id]["applicability_count"], 1)

        by_key = {
            (item["risk_category"], item["target"]): item
            for item in report["risk_reachability"]
            if item["target_type"] == "substance"
        }
        sildenafil_id = "substance-cas-139755-83-2"
        self.assertIn(
            "kj-201901",
            by_key[("anti_fatigue", sildenafil_id)][
                "recommendation_ready_method_ids"
            ],
        )
        self.assertNotIn(
            "kj-201901",
            by_key[("male_function", sildenafil_id)][
                "recommendation_ready_method_ids"
            ],
        )

    def test_context_corpus_is_reproducible_and_denominator_defined(self):
        report = load_and_build_audit()
        corpus = report["context_corpus"]

        self.assertTrue(corpus["all_expectations_match"])
        self.assertEqual(len(corpus["case_results"]), 6)
        self.assertEqual(
            report["metrics"]["context_corpus_recommendation_reachability"],
            {
                "numerator": 3,
                "denominator": 6,
                "ratio": 0.5,
                "denominator_definition": (
                    "本文件cases数组中的6个预定义Product Context案例；仅actual "
                    "applicability为applicable或conditional且方法进入suggested_methods"
                    "的案例计入分子"
                ),
            },
        )
        by_id = {item["case_id"]: item for item in corpus["case_results"]}
        self.assertEqual(
            by_id["male-function-sildenafil-alcohol-applicable"][
                "actual_method_id"
            ],
            "bjs-202405",
        )
        self.assertEqual(
            by_id["male-function-tadalafil-insufficient-context"][
                "actual_applicability"
            ],
            "insufficient_context",
        )
        self.assertEqual(
            by_id["male-function-group-remains-unresolved"]["actual_bucket"],
            "no_group_expansion",
        )


if __name__ == "__main__":
    unittest.main()
