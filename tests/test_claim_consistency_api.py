from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

from src.claim_consistency import write_claim_consistency_from_artifacts
from src.data_store import DataStore, make_snapshot_id
from src.local_api import create_handler
from src.runtime import read_json, write_json
from src.task_runtime import TaskManager
from tests.test_claim_data_store import write_claim_artifact
from tests.test_data_store import create_run, write_health_food_identity_artifact


FRAMEWORK_ID = "hf-framework-non-nutrient-cn-2023"
DESCRIPTIVE_UNRESOLVED = (
    "本品经动物实验评价，具有对化学性肝损伤有辅助保护作用的保健功能"
)


def prepare_case(
    output_root: Path,
    case_id: str,
    *,
    identity_state: str = "verified_match",
    claim_status: str = "complete",
    raw_functions: list[str] | None = None,
    framework_id: str | None | object = FRAMEWORK_ID,
    zero_claims: bool = False,
) -> tuple[Path, str]:
    product_id = case_id
    run_root = create_run(
        output_root,
        f"run-{case_id}",
        product_id=product_id,
        effect="" if zero_claims else "助眠",
    )
    snapshot_id = make_snapshot_id(run_root.name, product_id)
    write_health_food_identity_artifact(run_root, product_id)
    identity_path = run_root / "products" / product_id / "health_food_identity.json"
    identity = read_json(identity_path)
    identity["identityAssessment"]["state"] = identity_state
    record = identity["officialLookup"]["record"]
    record["officialHealthFunctions"] = raw_functions or ["有助于改善睡眠"]
    if framework_id is not ...:
        record["frameworkId"] = framework_id
    write_json(identity_path, identity)
    if claim_status == "complete":
        write_claim_artifact(run_root, product_id)
    elif claim_status == "error":
        write_json(
            run_root / "products" / product_id / "claim_analysis_error.json",
            {
                "schemaVersion": 1,
                "status": "error",
                "snapshotId": snapshot_id,
                "errorType": "FixtureError",
                "message": "offline fixture",
                "failedAt": "2026-09-15T00:00:00+08:00",
            },
        )
    write_claim_consistency_from_artifacts(
        run_root / "products" / product_id, snapshot_id
    )
    return run_root, snapshot_id


class ClaimConsistencyApiTests(unittest.TestCase):
    def test_snapshot_and_workspace_expose_every_operational_and_domain_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_root = root / "output"
            snapshots: dict[str, tuple[str, str]] = {}
            cases = (
                (
                    "identity-unverified",
                    {"identity_state": "candidate_identifier"},
                    "identity_not_verified",
                ),
                (
                    "claim-missing",
                    {"claim_status": "not_generated"},
                    "claim_not_generated",
                ),
                (
                    "claim-error",
                    {"claim_status": "error"},
                    "claim_analysis_error",
                ),
                (
                    "framework-unresolved",
                    {
                        "raw_functions": [DESCRIPTIVE_UNRESOLVED],
                        "framework_id": None,
                    },
                    "framework_unresolved",
                ),
                (
                    "function-unresolved",
                    {"raw_functions": [DESCRIPTIVE_UNRESOLVED]},
                    "official_function_unresolved",
                ),
                (
                    "zero-claims",
                    {"zero_claims": True},
                    "no_page_claims",
                ),
                ("assessed", {}, "assessed"),
            )
            for case_id, kwargs, expected_state in cases:
                _, snapshot_id = prepare_case(output_root, case_id, **kwargs)
                snapshots[case_id] = (snapshot_id, expected_state)

            missing_run = create_run(
                output_root, "run-not-generated", product_id="not-generated"
            )
            snapshots["not-generated"] = (
                make_snapshot_id(missing_run.name, "not-generated"),
                "not_generated",
            )
            error_run, error_snapshot = prepare_case(output_root, "sidecar-error")
            error_path = (
                error_run
                / "products"
                / "sidecar-error"
                / "claim_consistency.json"
            )
            invalid = read_json(error_path)
            invalid["state"] = "compliant"
            write_json(error_path, invalid)
            snapshots["sidecar-error"] = (error_snapshot, "error")

            web_root = root / "web"
            web_root.mkdir()
            (web_root / "index.html").write_text("ok", encoding="utf-8")
            store = DataStore(root / "data" / "app.db", output_root)
            manager = TaskManager(output_root)
            server = ThreadingHTTPServer(
                ("127.0.0.1", 0),
                create_handler(
                    output_root,
                    web_root,
                    manager,
                    store,
                    monitor_config=None,
                    inspection_config=None,
                    risk_substance_config=None,
                ),
            )
            server.daemon_threads = True
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                for case_id, (snapshot_id, expected) in snapshots.items():
                    with self.subTest(case=case_id):
                        with urlopen(f"{base}/api/snapshots/{snapshot_id}") as response:
                            detail = json.load(response)
                        with urlopen(
                            f"{base}/api/snapshots/{snapshot_id}/workspace"
                        ) as response:
                            workspace = json.load(response)
                        if expected in {"not_generated", "error"}:
                            self.assertEqual(detail["claimConsistencyStatus"], expected)
                            self.assertIsNone(detail["claimConsistency"])
                            self.assertIsNone(
                                detail["paths"]["claimConsistency"]
                            )
                        else:
                            self.assertEqual(
                                detail["claimConsistencyStatus"], "complete"
                            )
                            self.assertEqual(
                                detail["claimConsistency"]["state"], expected
                            )
                            self.assertEqual(
                                detail["paths"]["claimConsistency"],
                                f"products/{case_id}/claim_consistency.json",
                            )
                        self.assertEqual(
                            workspace["claimConsistencyStatus"],
                            detail["claimConsistencyStatus"],
                        )
                        self.assertEqual(
                            workspace["claimConsistency"],
                            detail["claimConsistency"],
                        )
            finally:
                server.shutdown()
                server.server_close()
                thread.join(2)


if __name__ == "__main__":
    unittest.main()
