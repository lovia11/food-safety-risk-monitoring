import json
import sqlite3
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

from src.claim_consistency import DEFAULT_HEALTH_FUNCTIONS_PATH
from src.data_store import DataStore
from src.inspection_runtime import (
    DEFAULT_INSPECTION_CONFIG_PATH,
    DEFAULT_RISK_SUBSTANCE_CONFIG_PATH,
)
from src.knowledge_read import KnowledgeQueryValidationError, KnowledgeReadService
from src.local_api import create_handler
from src.task_runtime import TaskManager


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MONITOR_REFERENCE = PROJECT_ROOT / "config" / "monitor_targets.reference.json"


class KnowledgeReadServiceTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.output_root = root / "output"
        self.store = DataStore(root / "data" / "app.db", self.output_root)
        self.store.initialize()
        self.store.import_monitor_config(MONITOR_REFERENCE)
        self.store.import_inspection_config(DEFAULT_INSPECTION_CONFIG_PATH)
        self.store.import_risk_substance_config(DEFAULT_RISK_SUBSTANCE_CONFIG_PATH)
        self.service = KnowledgeReadService(
            self.store, DEFAULT_HEALTH_FUNCTIONS_PATH
        )

    def tearDown(self):
        self.temporary.cleanup()

    def test_summary_uses_separate_governed_denominators(self):
        summary = self.service.summary()

        self.assertEqual(
            summary["counts"],
            {
                "referenceMonitorTargets": 106,
                "operationalMonitorTargets": 16,
                "queryPendingMonitorTargets": 88,
                "pausedMonitorTargets": 2,
                "healthFunctions": 25,
                "inspectionMethods": 10,
                "recommendationReadyMethods": 9,
                "referenceOnlyMethods": 1,
                "substances": 205,
                "riskMappings": 83,
                "groupMappings": 12,
                "regulatoryDocuments": 8,
            },
        )
        self.assertEqual(
            summary["authorities"]["inspection"]["datasetVersion"],
            "2026.09-b10",
        )
        self.assertEqual(
            summary["authorities"]["healthFunctions"]["datasetVersion"],
            "health-functions-v2.0",
        )
        self.assertNotIn("completeness", summary["counts"])

    def test_monitor_reference_availability_is_not_operational_readiness(self):
        pending = self.service.monitor_targets(
            availability="query_pending", limit=100, offset=0
        )
        paused = self.service.monitor_targets(
            availability="paused", limit=100, offset=0
        )

        self.assertEqual(pending["total"], 88)
        self.assertTrue(
            all(not item["hasValidatedSearchQuery"] for item in pending["items"])
        )
        self.assertTrue(
            all(
                "validated_search_query_not_available" in item["knowledgeGaps"]
                for item in pending["items"]
            )
        )
        self.assertEqual(paused["total"], 2)
        self.assertTrue(
            all(item["source"]["datasetVersion"] == "2024.08" for item in paused["items"])
        )

    def test_health_function_filter_alias_and_framework_gap_are_traceable(self):
        page = self.service.health_functions(query="改善睡眠", limit=10, offset=0)
        self.assertEqual(page["total"], 1)
        function = page["items"][0]
        self.assertEqual(function["officialName"], "有助于改善睡眠")
        self.assertEqual(
            [item["aliasText"] for item in function["transitionAliases"]],
            ["改善睡眠"],
        )
        self.assertEqual(
            function["source"]["datasetVersion"], "health-functions-v2.0"
        )
        self.assertIn("HealthFunction", function["interpretation"])

        nutrient = self.service.health_functions(
            framework="hf-framework-nutrient-supplement-cn-2023",
            limit=10,
            offset=0,
        )
        self.assertEqual(nutrient["total"], 1)
        self.assertIn(
            "framework_catalog_detail_not_governed",
            nutrient["items"][0]["knowledgeGaps"],
        )

    def test_substances_preserve_missing_context_and_method_count_boundary(self):
        melatonin = self.service.substances(query="褪黑素", limit=10, offset=0)
        self.assertEqual(melatonin["total"], 1)
        self.assertEqual(
            melatonin["items"][0]["regulatoryContext"]["availability"],
            "recorded",
        )
        self.assertGreaterEqual(melatonin["items"][0]["methodCoverageCount"], 1)

        sildenafil = self.service.substances(query="139755-83-2", limit=10, offset=0)
        self.assertEqual(sildenafil["total"], 1)
        record = sildenafil["items"][0]
        self.assertEqual(record["regulatoryContext"]["availability"], "not_recorded")
        self.assertIn("regulatory_context_not_recorded", record["knowledgeGaps"])
        self.assertIn("does not mean", record["interpretation"])

    def test_risk_group_mapping_stays_unresolved_and_method_analytes_add_none(self):
        groups = self.service.risk_mappings(
            target_type="substance_group", limit=100, offset=0
        )
        self.assertEqual(groups["total"], 12)
        self.assertTrue(
            all(
                item["groupResolution"] == {"status": "unresolved", "memberCount": 0}
                for item in groups["items"]
            )
        )
        self.assertTrue(
            all(
                "substance_group_membership_unresolved" in item["knowledgeGaps"]
                for item in groups["items"]
            )
        )
        all_mappings = self.service.risk_mappings(limit=100, offset=0)
        self.assertEqual(all_mappings["total"], 83)
        current = self.service.risk_mappings(status="current", limit=100, offset=0)
        historical = self.service.risk_mappings(status="historical", limit=100, offset=0)
        self.assertEqual(current["total"], 13)
        self.assertEqual(historical["total"], 70)
        self.assertEqual(
            {item["riskCategory"] for item in historical["items"]},
            {"sleep_aid", "blood_pressure", "blood_lipid", "blood_glucose", "weight_loss", "anti_fatigue"},
        )
        self.assertNotIn(
            "substance-cas-139755-95-6",
            {
                item["target"]["substanceId"]
                for item in all_mappings["items"]
                if item["targetType"] == "substance"
            },
        )

    def test_method_depth_lifecycle_pagination_and_recommendation_boundary(self):
        first = self.service.inspection_methods(limit=3, offset=0)
        second = self.service.inspection_methods(limit=3, offset=3)
        self.assertEqual(first["total"], 10)
        self.assertEqual(first["count"], 3)
        self.assertTrue(first["hasMore"])
        self.assertEqual(second["offset"], 3)

        shallow = self.service.inspection_methods(
            knowledge_depth="reference_only", limit=10, offset=0
        )
        self.assertEqual(shallow["total"], 1)
        old = shallow["items"][0]
        self.assertEqual(old["methodNo"], "GB/T 5009.170-2003")
        self.assertEqual(old["methodStatus"], "revoked")
        self.assertEqual(old["knowledgeDepth"], "reference_only")
        self.assertEqual(old["applicability"]["availability"], "not_recorded")
        self.assertIn("analyte_depth_not_verified", old["knowledgeGaps"])
        self.assertEqual(old["source"]["datasetVersion"], "2026.09-b10")

        recommendation_methods = self.store.list_substance_methods(
            "substance-cas-73-31-4", recommendation_ready_only=True
        )
        self.assertNotIn(
            "gbt-5009-170-2003",
            {item["method_id"] for item in recommendation_methods},
        )

    def test_regulatory_document_supersession_and_source_are_preserved(self):
        page = self.service.regulatory_documents(
            query="5009.170", limit=10, offset=0
        )
        self.assertEqual(page["total"], 1)
        document = page["items"][0]
        self.assertEqual(document["status"], "revoked")
        self.assertEqual(document["supersededBy"], ["regdoc-gbt-45443-2025"])
        self.assertTrue(document["sourceReference"].startswith("https://"))
        self.assertEqual(document["source"]["datasetVersion"], "2026.09-b10")

    def test_invalid_filters_and_pagination_are_rejected(self):
        with self.assertRaises(KnowledgeQueryValidationError):
            self.service.inspection_methods(
                knowledge_depth="current", limit=10, offset=0
            )
        with self.assertRaises(KnowledgeQueryValidationError):
            self.service.health_functions(status="unknown", limit=10, offset=0)
        with self.assertRaises(KnowledgeQueryValidationError):
            self.service.substances(limit=101, offset=0)


class KnowledgeReadHttpApiTest(unittest.TestCase):
    def test_get_endpoints_are_read_only_and_apply_server_side_filters(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_root = root / "output"
            web_root = root / "web"
            web_root.mkdir()
            (web_root / "index.html").write_text("ok", encoding="utf-8")
            store = DataStore(root / "data" / "app.db", output_root)
            manager = TaskManager(output_root)
            handler = create_handler(
                output_root,
                web_root,
                manager,
                store,
                monitor_config=MONITOR_REFERENCE,
            )
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"

            def business_counts():
                with sqlite3.connect(store.database_path) as connection:
                    return tuple(
                        connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                        for table in ("tasks", "reviews", "sampling_list_memberships")
                    )

            before = business_counts()
            try:
                endpoints = (
                    "summary",
                    "monitor-targets?availability=paused&limit=10&offset=0",
                    "health-functions?query=%E6%94%B9%E5%96%84%E7%9D%A1%E7%9C%A0",
                    "substances?query=%E8%A4%AA%E9%BB%91%E7%B4%A0",
                    "risk-mappings?target_type=substance_group",
                    "inspection-methods?knowledge_depth=reference_only",
                    "regulatory-documents?status=revoked",
                )
                payloads = []
                for endpoint in endpoints:
                    with urlopen(f"{base}/api/knowledge/{endpoint}") as response:
                        self.assertEqual(response.status, 200)
                        payloads.append(json.load(response))
                self.assertEqual(payloads[0]["counts"]["inspectionMethods"], 9)
                self.assertEqual(payloads[4]["total"], len(payloads[4]["items"]))
                self.assertGreater(payloads[4]["total"], 0)
                self.assertTrue(
                    all(
                        item["targetType"] == "substance_group"
                        for item in payloads[4]["items"]
                    )
                )
                self.assertEqual(payloads[5]["items"][0]["methodStatus"], "revoked")
                self.assertEqual(payloads[6]["items"][0]["status"], "revoked")

                with self.assertRaises(HTTPError) as raised:
                    urlopen(f"{base}/api/knowledge/substances?limit=0")
                self.assertEqual(raised.exception.code, 400)
                self.assertEqual(before, business_counts())
            finally:
                server.shutdown()
                server.server_close()
                thread.join(2)


if __name__ == "__main__":
    unittest.main()
