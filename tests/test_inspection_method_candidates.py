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
    def test_approved_candidates_retain_non_runtime_promotion_trace(self):
        payload = validate_inspection_candidate_manifest(read_json(CANDIDATE_CONFIG))

        self.assertFalse(payload["runtime_consumed"])
        self.assertEqual(
            [item["candidate_id"] for item in payload["candidates"]],
            ["candidate-bjs-202405", "candidate-gbt-5009-170-2003"],
        )
        bjs = payload["candidates"][0]
        self.assertEqual(bjs["method_no"], "BJS 202405")
        self.assertEqual(
            bjs["title"], "食品中西地那非、他达拉非等化合物的测定"
        )
        self.assertEqual(bjs["status"], "promoted")
        self.assertEqual(bjs["expected_depth"], "reference_only")
        self.assertEqual(bjs["promoted_method_id"], "bjs-202405")
        self.assertEqual(bjs["promoted_dataset_version"], "2026.09-b7")
        self.assertEqual(len(bjs["verification_sources"]), 2)
        self.assertNotIn("weight_loss", bjs["reason"])
        self.assertNotIn("西布曲明", bjs["reason"])
        self.assertIn("旧关联作废", bjs["correction_note"])

        predecessor = payload["candidates"][1]
        self.assertEqual(predecessor["status"], "promoted")
        self.assertEqual(
            predecessor["title"], "保健食品中褪黑素含量的测定"
        )
        self.assertEqual(
            predecessor["promoted_method_id"], "gbt-5009-170-2003"
        )
        self.assertEqual(predecessor["promoted_dataset_version"], "2026.09-b7")
        self.assertIn("两者保持独立身份", predecessor["correction_note"])

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

        self.assertEqual(len(operational_method_numbers), 7)
        self.assertTrue(
            {item["method_no"] for item in candidates}.issubset(
                operational_method_numbers
            )
        )
        report = load_and_build_audit()
        self.assertEqual(report["inventory"]["indexed_methods"], 7)
        self.assertEqual(report["inventory"]["candidate_records"], 2)
        self.assertEqual(report["inventory"]["candidate_methods"], 0)
        self.assertEqual(report["inventory"]["promoted_candidate_methods"], 2)
        self.assertEqual(
            report["metrics"]["method_reference_coverage"]["denominator"], 7
        )
        self.assertEqual(report["candidate_manifest"]["pending_candidate_ids"], [])
        self.assertEqual(len(report["candidate_manifest"]["promoted_candidates"]), 2)
        self.assertTrue(
            report["candidate_manifest"]["excluded_from_coverage_denominator"]
        )


if __name__ == "__main__":
    unittest.main()
