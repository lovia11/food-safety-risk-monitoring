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
    def test_approved_candidates_remain_non_runtime_discovery_records(self):
        payload = validate_inspection_candidate_manifest(read_json(CANDIDATE_CONFIG))

        self.assertFalse(payload["runtime_consumed"])
        self.assertEqual(
            [item["candidate_id"] for item in payload["candidates"]],
            ["candidate-bjs-202405", "candidate-gbt-5009-170-2003"],
        )
        bjs = payload["candidates"][0]
        self.assertEqual(bjs["method_no"], "BJS 202405")
        self.assertIsNone(bjs["title"])
        self.assertEqual(bjs["status"], "candidate")

    def test_candidate_status_cannot_self_promote(self):
        payload = read_json(CANDIDATE_CONFIG)
        promoted = copy.deepcopy(payload)
        promoted["candidates"][0]["status"] = "verified_reference"
        with self.assertRaisesRegex(
            InspectionCandidateValidationError, "status必须为candidate"
        ):
            validate_inspection_candidate_manifest(promoted)

        runtime = copy.deepcopy(payload)
        runtime["runtime_consumed"] = True
        with self.assertRaisesRegex(
            InspectionCandidateValidationError, "runtime_consumed"
        ):
            validate_inspection_candidate_manifest(runtime)

    def test_candidates_never_enter_operational_sqlite_or_coverage_denominator(self):
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

        self.assertEqual(len(operational_method_numbers), 5)
        self.assertTrue(
            operational_method_numbers.isdisjoint(
                {item["method_no"] for item in candidates}
            )
        )
        report = load_and_build_audit()
        self.assertEqual(report["inventory"]["indexed_methods"], 5)
        self.assertEqual(report["inventory"]["candidate_methods"], 2)
        self.assertEqual(
            report["metrics"]["method_reference_coverage"]["denominator"], 5
        )
        self.assertTrue(
            report["candidate_manifest"]["excluded_from_coverage_denominator"]
        )


if __name__ == "__main__":
    unittest.main()
