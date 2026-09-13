import json
import io
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from src.data_store import DataStore, validate_monitor_config
from src.local_api import create_handler
from src.monitor_coverage import is_operational_query, reference_coverage
from src.monitor_query_validation import (
    select_validation_queries,
    validate_validation_ledger,
    validation_dry_run,
)
from src.runtime import read_json
from src.task_runtime import MonitorTargetNotOperationalError, TaskManager
from tools.validate_monitor_queries import main as validation_tool_main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_CONFIG = PROJECT_ROOT / "config" / "monitor_targets.reference.json"
DEVELOPMENT_CONFIG = PROJECT_ROOT / "config" / "monitor_targets.development.json"
LEDGER = PROJECT_ROOT / "config" / "monitor_query_validation.json"


class MonitorCoverageV2Test(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.store = DataStore(self.root / "data" / "app.db", self.root / "output")
        self.store.initialize()
        self.store.import_monitor_config(DEVELOPMENT_CONFIG)
        self.store.import_monitor_config(REFERENCE_CONFIG)

    def tearDown(self):
        self.temporary.cleanup()

    def test_reference_coverage_is_derived_from_governed_configuration(self):
        coverage = self.store.monitor_coverage()
        self.assertEqual(
            coverage,
            {
                "reference_target_count": 106,
                "targets_with_query_count": 18,
                "operational_target_count": 15,
                "enabled_query_count": 18,
                "validated_query_count": 18,
                "disabled_query_count": 4,
                "candidate_query_count": 1,
                "paused_target_count": 3,
            },
        )
        self.assertEqual(
            coverage,
            reference_coverage(self.store.list_monitor_targets()),
        )

    def test_reference_and_operational_scopes_have_distinct_semantics(self):
        reference = self.store.list_monitor_targets(scope="reference")
        operational = self.store.list_monitor_targets(scope="operational")
        formal_operational = [
            target
            for target in operational
            if target["dataset_status"] == "verified_reference"
        ]
        self.assertEqual(len(reference), 106)
        self.assertEqual(len(formal_operational), 15)
        self.assertEqual(len(operational), 16)  # includes the independent development seed
        self.assertTrue(
            all(target["availability"] == "operational" for target in operational)
        )

    def test_availability_and_query_dto_do_not_expose_unvalidated_as_runnable(self):
        reference = self.store.list_monitor_targets(scope="reference")
        acid = next(item for item in reference if item["standard_name"] == "酸枣仁")
        mountain_yam = next(item for item in reference if item["standard_name"] == "山药")
        lily = next(item for item in reference if item["standard_name"] == "百合")
        angelica = next(item for item in reference if item["standard_name"] == "当归")
        self.assertEqual(acid["availability"], "operational")
        self.assertEqual([item["query_text"] for item in acid["validated_queries"]], ["酸枣仁", "酸枣仁茶"])
        self.assertEqual(acid["targetId"], acid["target_id"])
        self.assertEqual(acid["standardName"], "酸枣仁")
        self.assertEqual(acid["validatedQueryCount"], 2)
        self.assertEqual(acid["validatedQueries"], acid["validated_queries"])
        self.assertEqual(mountain_yam["availability"], "operational")
        self.assertEqual(mountain_yam["validated_query_count"], 1)
        self.assertEqual(mountain_yam["validated_queries"][0]["query_text"], "山药")
        self.assertEqual(lily["availability"], "paused")
        self.assertEqual(lily["candidate_query_count"], 1)
        self.assertEqual(lily["validated_queries"], [])
        self.assertEqual(lily["queries"][0]["validation_status"], "rejected_low_relevance")
        self.assertEqual(lily["queries"][1]["query_text"], "食用百合")
        self.assertEqual(lily["queries"][1]["query_source"], "manually_curated")
        self.assertEqual(lily["queries"][1]["validation_status"], "candidate_unvalidated")
        self.assertFalse(lily["queries"][1]["enabled"])
        self.assertIn("v2-4b-batch-02b", lily["queries"][1]["query_note"])
        self.assertIn("观察相关率50%", lily["availability_reason"])
        self.assertEqual(angelica["availability"], "paused")
        self.assertIn("中药材/饮片", angelica["availability_reason"])
        self.assertEqual(angelica["validated_queries"], [])

    def test_candidate_rejected_and_paused_queries_are_never_operational(self):
        reference = self.store.list_monitor_targets(scope="reference")
        lily_queries = next(item for item in reference if item["standard_name"] == "百合")["queries"]
        rejected, candidate = lily_queries
        paused = next(item for item in reference if item["standard_name"] == "当归")["queries"][0]
        self.assertFalse(is_operational_query(rejected))
        self.assertFalse(is_operational_query(candidate))
        self.assertFalse(is_operational_query(paused))

    def test_reference_only_target_is_rejected_by_server_business_guard(self):
        manager = TaskManager(
            self.root / "output",
            monitor_target_provider=self.store.get_monitor_target,
        )
        with self.assertRaisesRegex(
            MonitorTargetNotOperationalError,
            "没有已验证并启用",
        ):
            manager.create_task(
                {
                    "task_type": "monitor",
                    "target_id": "food-medicine-2002-022",
                    "per_query_candidate_limit": 10,
                    "detail_limit": 10,
                }
            )
        self.assertEqual(list((self.root / "output").iterdir()), [])

    def test_api_returns_specific_non_operational_error_code(self):
        web_root = self.root / "web"
        web_root.mkdir()
        (web_root / "index.html").write_text("ok", encoding="utf-8")
        manager = TaskManager(
            self.root / "output",
            monitor_target_provider=self.store.get_monitor_target,
        )
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            create_handler(
                self.root / "output",
                web_root,
                manager,
                data_store=self.store,
                monitor_config=None,
            ),
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            request = Request(
                f"http://127.0.0.1:{server.server_port}/api/tasks",
                method="POST",
                headers={"Content-Type": "application/json"},
                data=json.dumps(
                    {
                        "task_type": "monitor",
                        "target_id": "food-medicine-2002-022",
                        "per_query_candidate_limit": 10,
                        "detail_limit": 10,
                    }
                ).encode("utf-8"),
            )
            with self.assertRaises(HTTPError) as raised:
                urlopen(request)
            self.assertEqual(raised.exception.code, 409)
            body = json.loads(raised.exception.read().decode("utf-8"))
            self.assertEqual(body["error"]["code"], "monitor_target_not_operational")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(2)

    def test_validation_ledger_covers_every_governed_final_query(self):
        config = validate_monitor_config(read_json(REFERENCE_CONFIG))
        ledger = validate_validation_ledger(config, read_json(LEDGER))
        self.assertEqual(len(ledger["records"]), 21)
        wave_one = {
            item["query_text"]: item
            for item in ledger["records"]
            if item["batch_id"] == "v2-4b-batch-01a"
        }
        self.assertEqual(set(wave_one), {"山楂", "乌梅", "沙棘", "罗汉果", "黑芝麻", "蜂蜜"})
        self.assertEqual(wave_one["乌梅"]["decision"], "hold")
        self.assertTrue(wave_one["乌梅"]["systematic_scope_issue"])
        self.assertEqual(wave_one["山楂"]["relevant_count"], 9)
        self.assertIn("未发现系统性范围问题", wave_one["山楂"]["decision_note"])
        wave_two_a = {
            item["query_text"]: item
            for item in ledger["records"]
            if item["batch_id"] == "v2-4b-batch-02a"
        }
        self.assertEqual(set(wave_two_a), {"山药", "赤小豆", "枸杞子", "莲子"})
        self.assertTrue(all(item["decision"] == "promote" for item in wave_two_a.values()))
        self.assertEqual(wave_two_a["莲子"]["ambiguous_skipped"], 1)
        self.assertEqual(
            wave_two_a["莲子"]["artifact_manifest_sha256"],
            "b5acfc84635c4f5103ac2a10e0524b90bd065f68d26830f8b07464c25094fe54",
        )
        wave_two_b = {
            item["query_text"]: item
            for item in ledger["records"]
            if item["batch_id"] == "v2-4b-batch-02b"
        }
        self.assertEqual(set(wave_two_b), {"百合", "菊花"})
        self.assertEqual(wave_two_b["百合"]["decision"], "reject")
        self.assertEqual(wave_two_b["百合"]["relevance_rate"], 0.5)
        self.assertEqual(wave_two_b["菊花"]["decision"], "promote")
        self.assertEqual(wave_two_b["菊花"]["relevance_rate"], 1.0)
        self.assertEqual(
            wave_two_b["百合"]["artifact_manifest_sha256"],
            "c130bb453df91397bab926a722ef759d56fee038def2bdeb12dcfc145cb3b16e",
        )

    def test_unfiltered_dry_run_selects_only_refined_lily_candidate(self):
        config = validate_monitor_config(read_json(REFERENCE_CONFIG))
        selected = select_validation_queries(config)
        plan = validation_dry_run(
            batch_id="v2-4b-batch-02c",
            output_root=self.root / "query-validation",
            max_results=15,
            selected=selected,
        )
        self.assertEqual(plan["queryCount"], 1)
        self.assertEqual(plan["queries"][0]["standardName"], "百合")
        self.assertEqual(plan["queries"][0]["queryText"], "食用百合")
        self.assertEqual(plan["queries"][0]["queryId"], "food-medicine-2002-022-edible-candidate")
        self.assertEqual(plan["queries"][0]["validationStatus"], "candidate_unvalidated")

    def test_validation_tool_dry_run_prints_plan_without_creating_runtime_output(self):
        destination = self.root / "validation-output"
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            result = validation_tool_main(
                [
                    "--batch",
                    "offline-dry-run",
                    "--dry-run",
                    "--max-results",
                    "10",
                    "--output",
                    str(destination),
                    "--config",
                    str(REFERENCE_CONFIG),
                ]
            )
        plan = json.loads(stdout.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(plan["queryCount"], 1)
        self.assertEqual(plan["queries"][0]["queryText"], "食用百合")
        self.assertFalse(destination.exists())

    def test_wave_one_dry_run_separates_collection_ceiling_from_review_sample(self):
        config = validate_monitor_config(read_json(REFERENCE_CONFIG))
        target_ids = {
            "food-medicine-2002-007",
            "food-medicine-2002-010",
            "food-medicine-2002-028",
            "food-medicine-2002-038",
            "food-medicine-2002-071",
            "food-medicine-2002-076",
        }
        query_ids = {
            "food-medicine-2002-007-base-candidate",
            "food-medicine-2002-010-base-candidate",
            "food-medicine-2002-028-base-candidate",
            "food-medicine-2002-038-base-candidate",
            "food-medicine-2002-071-base-candidate",
            "food-medicine-2002-076-base-candidate",
        }
        selected = select_validation_queries(
            config, target_ids=target_ids, query_ids=query_ids
        )
        plan = validation_dry_run(
            batch_id="v2-4b-batch-01a",
            output_root=self.root / "query-validation",
            max_results=15,
            selected=selected,
        )
        self.assertEqual(plan["queryCount"], 6)
        self.assertEqual(plan["collectionRawLimit"], 15)
        self.assertEqual(plan["evaluationSampleSize"], 10)
        self.assertEqual(plan["plannedResultSampleSize"], 10)
        self.assertEqual(
            [item["targetId"] for item in plan["queries"]],
            [
                "food-medicine-2002-007",
                "food-medicine-2002-010",
                "food-medicine-2002-028",
                "food-medicine-2002-038",
                "food-medicine-2002-071",
                "food-medicine-2002-076",
            ],
        )

    def test_reviewed_promotions_pass_server_guard_without_running_network(self):
        captured = []

        class NoNetworkPipeline:
            def __init__(self, options):
                captured.append(options)

            def run(self):
                return None

        manager = TaskManager(
            self.root / "task-output",
            pipeline_factory=NoNetworkPipeline,
            monitor_target_provider=self.store.get_monitor_target,
        )
        promoted_ids = [
            "food-medicine-2002-007",
            "food-medicine-2002-028",
            "food-medicine-2002-038",
            "food-medicine-2002-071",
            "food-medicine-2002-076",
            "food-medicine-2002-006",
            "food-medicine-2002-032",
            "food-medicine-2002-045",
            "food-medicine-2002-060",
            "food-medicine-2002-064",
        ]
        for target_id in promoted_ids:
            created = manager.create_task(
                {
                    "task_type": "monitor",
                    "target_id": target_id,
                    "per_query_candidate_limit": 1,
                    "detail_limit": 1,
                }
            )
            self.assertEqual(created["runtime"]["request"]["targetId"], target_id)
            self.assertTrue(manager.wait_for_idle())
        self.assertEqual(len(captured), 10)
        self.assertTrue(
            all(
                options.search_queries[0]["query_source"] == "standard_name"
                and options.search_queries[0]["validation_status"] == "search_validated"
                for options in captured
            )
        )
        with self.assertRaises(MonitorTargetNotOperationalError):
            manager.create_task(
                {
                    "task_type": "monitor",
                    "target_id": "food-medicine-2002-010",
                    "per_query_candidate_limit": 1,
                    "detail_limit": 1,
                }
            )


if __name__ == "__main__":
    unittest.main()
