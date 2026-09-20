import copy
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.audit_inspection_knowledge import load_and_build_audit
from src.data_store import DataStore
from src.inspection_method_candidates import (
    InspectionCandidateValidationError,
    validate_inspection_candidate_manifest,
)
from src.runtime import read_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_CONFIG = (
    PROJECT_ROOT / "config" / "inspection_method_candidates_v2.json"
)
INSPECTION_CONFIG = PROJECT_ROOT / "config" / "inspection_reference.json"


class InspectionMethodCandidateManifestTest(unittest.TestCase):
    def test_manifest_separates_promoted_traces_from_verification_queue(self):
        payload = validate_inspection_candidate_manifest(read_json(CANDIDATE_CONFIG))

        self.assertFalse(payload["runtime_consumed"])
        promoted = [
            item for item in payload["candidates"]
            if item["status"] == "promoted"
        ]
        verification = [
            item for item in payload["candidates"]
            if item["status"] == "verification"
        ]
        self.assertEqual(
            {item["candidate_id"] for item in promoted},
            {
                "candidate-bjs-201901",
                "candidate-bjs-202405",
                "candidate-gbt-5009-170-2003",
                "candidate-kj201901",
                "candidate-kj201902",
                "candidate-bjs-201808",
            },
        )
        self.assertEqual(
            {item["method_no"] for item in verification},
            {
                "BJS 202409",
                "BJS 202501",
                "BJS 202502",
                "BJS 202504",
                "BJS 202601",
                "BJS 202602",
            },
        )
        self.assertTrue(
            all(item["expected_depth"] == "reference_only" for item in verification)
        )
        self.assertTrue(
            all(item["verification_sources"] for item in verification)
        )
        self.assertTrue(
            all(item["promoted_method_id"] is None for item in verification)
        )
        self.assertTrue(
            all(item["promoted_dataset_version"] is None for item in verification)
        )

        bjs = next(item for item in promoted if item["method_no"] == "BJS 202405")
        self.assertEqual(bjs["method_no"], "BJS 202405")
        self.assertEqual(
            bjs["title"], "食品中西地那非、他达拉非等化合物的测定"
        )
        self.assertEqual(bjs["expected_depth"], "reference_only")
        self.assertEqual(bjs["promoted_method_id"], "bjs-202405")
        self.assertEqual(bjs["promoted_dataset_version"], "2026.09-b7")
        self.assertEqual(len(bjs["verification_sources"]), 2)
        self.assertNotIn("weight_loss", bjs["reason"])
        self.assertNotIn("西布曲明", bjs["reason"])
        self.assertIn("旧关联作废", bjs["correction_note"])

        predecessor = next(
            item for item in promoted if item["method_no"] == "GB/T 5009.170-2003"
        )
        self.assertEqual(
            predecessor["title"], "保健食品中褪黑素含量的测定"
        )
        self.assertEqual(
            predecessor["promoted_method_id"], "gbt-5009-170-2003"
        )
        self.assertEqual(predecessor["promoted_dataset_version"], "2026.09-b7")
        self.assertIn("两者保持独立身份", predecessor["correction_note"])

        bjs_201901 = next(
            item for item in promoted if item["method_no"] == "BJS 201901"
        )
        self.assertEqual(bjs_201901["expected_depth"], "recommendation_ready")
        self.assertEqual(bjs_201901["promoted_method_id"], "bjs-201901")
        self.assertEqual(bjs_201901["promoted_dataset_version"], "2026.09-b11")
        self.assertIn("C4A697A35F4171516C06947C937F0C10D01FDC3AFC671D7780154A5AD9936EE9", bjs_201901["reason"])
        self.assertIn("antiword", bjs_201901["reason"])
        self.assertIn("27种", bjs_201901["reason"])
        self.assertIn("14个新Substance", bjs_201901["correction_note"])
        self.assertIn("格列本脲", bjs_201901["correction_note"])
        self.assertIn("格列苯脲", bjs_201901["correction_note"])
        self.assertIn("吡格列酮", bjs_201901["correction_note"])
        self.assertIn("无需额外normalization", bjs_201901["correction_note"])
        self.assertTrue(any(
            "official_fulltext_parsed" in source["verified_facts"]
            for source in bjs_201901["verification_sources"]
        ))

        bjs_202409 = next(
            item for item in verification if item["method_no"] == "BJS 202409"
        )
        self.assertEqual(bjs_202409["expected_depth"], "reference_only")
        self.assertIsNone(bjs_202409["promoted_method_id"])
        self.assertIsNone(bjs_202409["promoted_dataset_version"])
        self.assertIn("1889293DAE36340D05FECE79C96ACFC3AC4C7D5E8EB4571DB201D98D8D0CD4DF", bjs_202409["reason"])
        self.assertIn("success=false/data={}", bjs_202409["reason"])
        self.assertIn("仅已有氯噻嗪58-94-6、氢氯噻嗪58-93-5、呋塞米54-31-9", bjs_202409["correction_note"])
        self.assertIn("依善利酮/依普利酮", bjs_202409["correction_note"])
        self.assertIn("B5-9B provenance decision", bjs_202409["reason"])
        self.assertIn("明确deferred", bjs_202409["reason"])
        self.assertIn("第三方上传PDF", bjs_202409["reason"])
        self.assertIn("不新增MethodSubstance或MethodApplicability", bjs_202409["correction_note"])
        self.assertIn("不新增任何Claim→Risk、Risk→Substance", bjs_202409["correction_note"])
        self.assertIn("继续保持unresolved", bjs_202409["correction_note"])
        self.assertTrue(any(
            "secondary_19_analyte_cas_crosscheck" in source["verified_facts"]
            for source in bjs_202409["verification_sources"]
        ))

        bjs_202501 = next(
            item for item in verification if item["method_no"] == "BJS 202501"
        )
        self.assertEqual(payload["manifest_version"], "2026.09-b17")
        self.assertEqual(bjs_202501["expected_depth"], "reference_only")
        self.assertIsNone(bjs_202501["promoted_method_id"])
        self.assertIsNone(bjs_202501["promoted_dataset_version"])
        self.assertIn("AuthorizedRead", bjs_202501["reason"])
        self.assertIn("禁止孤立Substance", bjs_202501["reason"])
        self.assertIn("不得由Method存在或药理用途反推Risk", bjs_202501["correction_note"])

        bjs_202601 = next(
            item for item in verification if item["method_no"] == "BJS 202601"
        )
        self.assertEqual(bjs_202601["expected_depth"], "reference_only")
        self.assertIsNone(bjs_202601["promoted_method_id"])
        self.assertIsNone(bjs_202601["promoted_dataset_version"])
        self.assertIn("2043-38-1", bjs_202601["reason"])
        self.assertIn("3568-00-1", bjs_202601["reason"])
        self.assertIn("AuthorizedRead", bjs_202601["reason"])
        self.assertIn("独立Risk-governance backlog", bjs_202601["correction_note"])
        self.assertIn("不能作为Method promotion副作用", bjs_202601["correction_note"])
        self.assertIn("deferred", bjs_202601["reason"])

        bjs_202602 = next(
            item for item in verification if item["method_no"] == "BJS 202602"
        )
        self.assertEqual(bjs_202602["expected_depth"], "reference_only")
        self.assertIsNone(bjs_202602["promoted_method_id"])
        self.assertIsNone(bjs_202602["promoted_dataset_version"])
        self.assertIn("AuthorizedRead", bjs_202602["reason"])
        self.assertIn("UPLC-MS/MS", bjs_202602["reason"])
        self.assertIn("不得把商业供应商的“Vardenafil Impurity 30”编号当作稳定化学身份", bjs_202602["correction_note"])
        self.assertIn("不得把官方O-丙基伐地那非标准样品项目自动解释", bjs_202602["correction_note"])
        self.assertIn("substance_group_membership", bjs_202602["correction_note"])
        self.assertIn("明确deferred", bjs_202602["reason"])
        self.assertTrue(any(
            "identity_clue_only_not_bjs202602_equivalence" in source["verified_facts"]
            for source in bjs_202602["verification_sources"]
        ))

        promoted_by_no = {item["method_no"]: item for item in promoted}
        for method_no, method_id, dataset_version in (
            ("KJ201901", "kj-201901", "2026.09-b9"),
            ("KJ201902", "kj-201902", "2026.09-b9"),
            ("BJS 201808", "bjs-201808", "2026.09-b10"),
            ("BJS 201901", "bjs-201901", "2026.09-b11"),
        ):
            item = promoted_by_no[method_no]
            self.assertEqual(item["expected_depth"], "recommendation_ready")
            self.assertEqual(item["promoted_method_id"], method_id)
            self.assertEqual(item["promoted_dataset_version"], dataset_version)
            self.assertIn("正式", item["reason"])

    def test_candidate_lifecycle_requires_governed_verification_trace(self):
        payload = read_json(CANDIDATE_CONFIG)
        unknown_status = copy.deepcopy(payload)
        unknown_status["candidates"][0]["status"] = "verified_reference"
        with self.assertRaisesRegex(
            InspectionCandidateValidationError, "status不受支持"
        ):
            validate_inspection_candidate_manifest(unknown_status)

        missing_trace = copy.deepcopy(payload)
        missing_trace["candidates"][0].pop("verification_sources")
        with self.assertRaisesRegex(
            InspectionCandidateValidationError, "verification_sources"
        ):
            validate_inspection_candidate_manifest(missing_trace)

        missing_target = copy.deepcopy(payload)
        missing_target["candidates"][0].pop("promoted_method_id")
        with self.assertRaisesRegex(
            InspectionCandidateValidationError, "promoted_method_id"
        ):
            validate_inspection_candidate_manifest(missing_target)

        runtime = copy.deepcopy(payload)
        runtime["runtime_consumed"] = True
        with self.assertRaisesRegex(
            InspectionCandidateValidationError, "runtime_consumed"
        ):
            validate_inspection_candidate_manifest(runtime)

    def test_promoted_methods_enter_index_once_without_double_counting_manifest(self):
        candidates = validate_inspection_candidate_manifest(
            read_json(CANDIDATE_CONFIG)
        )["candidates"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = DataStore(root / "data" / "app.db", root / "output")
            store.initialize()
            store.import_inspection_config(INSPECTION_CONFIG)
            with sqlite3.connect(store.database_path) as connection:
                operational_method_numbers = {
                    row[0]
                    for row in connection.execute(
                        "SELECT method_no FROM inspection_methods"
                    )
                }
            connection.close()

        self.assertEqual(len(operational_method_numbers), 11)
        promoted = [
            item for item in candidates if item["status"] == "promoted"
        ]
        verification = [
            item for item in candidates if item["status"] == "verification"
        ]
        self.assertTrue(
            {item["method_no"] for item in promoted}.issubset(
                operational_method_numbers
            )
        )
        self.assertTrue(
            {item["method_no"] for item in verification}.isdisjoint(
                operational_method_numbers
            )
        )

        report = load_and_build_audit()
        self.assertEqual(report["inventory"]["indexed_methods"], 11)
        self.assertEqual(report["inventory"]["candidate_records"], 12)
        self.assertEqual(report["inventory"]["candidate_methods"], 6)
        self.assertEqual(report["inventory"]["promoted_candidate_methods"], 6)
        self.assertEqual(
            report["metrics"]["method_reference_coverage"]["denominator"], 11
        )
        self.assertEqual(
            set(report["candidate_manifest"]["pending_candidate_ids"]),
            {item["candidate_id"] for item in verification},
        )
        self.assertEqual(len(report["candidate_manifest"]["promoted_candidates"]), 6)
        self.assertTrue(
            report["candidate_manifest"]["excluded_from_coverage_denominator"]
        )


if __name__ == "__main__":
    unittest.main()
