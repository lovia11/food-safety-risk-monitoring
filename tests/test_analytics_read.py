import json
import sqlite3
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from scripts.audit_inspection_knowledge import load_and_build_audit
from src.analytics_read import (
    AnalyticsMetricDictionaryError,
    AnalyticsQueryValidationError,
    AnalyticsReadService,
    load_metric_dictionary,
)
from src.data_store import DataStore
from src.inspection_runtime import (
    DEFAULT_INSPECTION_CONFIG_PATH,
    DEFAULT_RISK_SUBSTANCE_CONFIG_PATH,
)
from src.local_api import create_handler
from src.task_runtime import TaskManager


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MONITOR_REFERENCE = PROJECT_ROOT / "config" / "monitor_targets.reference.json"
METRIC_DICTIONARY = PROJECT_ROOT / "config" / "analytics_metrics_v2.json"


def _metric(payload, metric_id):
    return next(item for item in payload["metrics"] if item["metricId"] == metric_id)


def _bucket(metric, key):
    return next(item for item in metric["buckets"] if item["key"] == key)


class AnalyticsFixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.output_root = self.root / "output"
        self.store = DataStore(self.root / "data" / "app.db", self.output_root)
        self.store.initialize()
        self.store.import_monitor_config(MONITOR_REFERENCE)
        self.store.import_inspection_config(DEFAULT_INSPECTION_CONFIG_PATH)
        self.store.import_risk_substance_config(DEFAULT_RISK_SUBSTANCE_CONFIG_PATH)
        self._insert_runtime_fixture()
        self.service = AnalyticsReadService(self.store)

    def tearDown(self):
        self.temporary.cleanup()

    def _insert_runtime_fixture(self):
        with self.store._connect() as connection:
            for task_id in ("task-one", "task-two"):
                connection.execute(
                    """
                    INSERT INTO tasks (
                        task_id, display_name, keyword, stage, created_at,
                        run_path, updated_at
                    ) VALUES (?, ?, 'fixture', 'completed_with_errors', ?, ?, ?)
                    """,
                    (
                        task_id,
                        task_id,
                        "2026-01-01T00:00:00+08:00"
                        if task_id == "task-one"
                        else "2026-02-01T00:00:00+08:00",
                        task_id,
                        "2026-02-02T00:00:00+08:00",
                    ),
                )
            for product_id in ("P1", "P2", "P3", "P4"):
                connection.execute(
                    """
                    INSERT INTO products (taobao_product_id, first_seen_at, updated_at)
                    VALUES (?, '2026-01-01T00:00:00+08:00', '2026-02-02T00:00:00+08:00')
                    """,
                    (product_id,),
                )
            snapshots = (
                (
                    "S1", "P1", "task-one", "山东", "2026-01-01T10:00:00+08:00",
                    "success", '["助眠"]', "products/P1/meta.json",
                    "products/P1/analysis.json", 1, 1, "complete",
                ),
                (
                    "S2", "P1", "task-two", "云南", "2026-02-01T10:00:00+08:00",
                    "failed_collection", '["助眠"]', None, None, 0, 0,
                    "not_generated",
                ),
                (
                    "S3", "P2", "task-one", "", "2026-01-02T10:00:00+08:00",
                    "success", "[]", "products/P2/meta.json",
                    "products/P2/analysis.json", 1, 1, "complete",
                ),
                (
                    "S4", "P3", "task-one", "山东", "2026-01-03T10:00:00+08:00",
                    "failed_processing", "[]", "products/P3/meta.json", None,
                    1, 0, "error",
                ),
                (
                    "S5", "P4", "task-one", "福建", "2026-01-04T10:00:00+08:00",
                    "pending_detail_collection", "[]", None, None, 0, 0,
                    "not_generated",
                ),
            )
            for ordinal, item in enumerate(snapshots, start=1):
                connection.execute(
                    """
                    INSERT INTO product_snapshots (
                        snapshot_id, product_id, task_id, rank, product_name,
                        region, collected_at, status, detected_effects_json,
                        product_path, meta_path, analysis_path,
                        original_image_count, ocr_image_count,
                        claim_analysis_status, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item[0], item[1], item[2], ordinal, f"商品 {item[1]}",
                        item[3], item[4], item[5], item[6], f"products/{item[1]}",
                        item[7], item[8], item[9], item[10], item[11],
                        "2026-02-02T00:00:00+08:00",
                    ),
                )
            reviews = {
                "S1": "pending",
                "S2": "pending",
                "S3": "recommend_follow_up",
                "S4": "pending",
                "S5": "pending",
            }
            for snapshot_id, status in reviews.items():
                connection.execute(
                    "INSERT INTO reviews (snapshot_id, review_status) VALUES (?, ?)",
                    (snapshot_id, status),
                )
            connection.execute(
                """
                INSERT INTO sampling_list_memberships (
                    product_id, source_snapshot_id, source_task_id, added_from,
                    added_at, updated_at
                ) VALUES (
                    'P1', 'S1', 'task-one', 'product_overview',
                    '2026-01-05T00:00:00+08:00', '2026-01-05T00:00:00+08:00'
                )
                """
            )
            connection.execute(
                """
                INSERT INTO claim_signals (
                    claim_signal_id, snapshot_id, ordinal, claim_type,
                    display_label, taxonomy_version, status, created_at
                ) VALUES (
                    'CS1', 'S1', 1, 'sleep_related', '睡眠相关宣传',
                    'claim-taxonomy-v2.0', 'normalized',
                    '2026-01-01T12:00:00+08:00'
                )
                """
            )
            connection.execute(
                """
                INSERT INTO evidence (
                    evidence_id, snapshot_id, ordinal, text, source_type,
                    source_label, content_origin, source_path
                ) VALUES (
                    'E1', 'S2', 1, '用户说安睡', 'comment', '用户评价',
                    'user_generated', 'ugc/comment-1'
                )
                """
            )
            fact_rows = (
                ("F1", "S1", "云南省", "云南省", "dom_parameter", "dom#1"),
                ("F2", "S3", "河北省", "河北省", "dom_parameter", "dom#2"),
                ("F3", "S3", "安徽省", "安徽省", "ocr_detail_image", "ocr#3"),
            )
            for fact_id, snapshot_id, normalized, raw, source_type, source_path in fact_rows:
                connection.execute(
                    """
                    INSERT INTO product_facts (
                        fact_id, snapshot_id, fact_type, normalized_value,
                        raw_value, source_type, content_origin, source_path,
                        source_text, extraction_method, verification_state,
                        created_at
                    ) VALUES (
                        ?, ?, 'declared_origin', ?, ?, ?, 'seller_managed', ?,
                        ?, 'fixture', 'extracted', '2026-01-05T00:00:00+08:00'
                    )
                    """,
                    (
                        fact_id, snapshot_id, normalized, raw, source_type,
                        source_path, f"商品产地：{raw}",
                    ),
                )


class AnalyticsMetricDictionaryTest(unittest.TestCase):
    def test_dictionary_has_complete_governed_definitions_and_explicit_gaps(self):
        payload = load_metric_dictionary(METRIC_DICTIONARY)
        self.assertEqual(len(payload["metrics"]), 32)
        self.assertEqual(
            {item["metric_type"] for item in payload["metrics"]},
            {"count", "ratio", "distribution", "coverage"},
        )
        self.assertEqual(
            {item["domain"] for item in payload["metrics"]},
            {"pipeline", "claims", "geography", "knowledge"},
        )
        unavailable = {item["metric_id"]: item for item in payload["unavailable_metrics"]}
        self.assertEqual(unavailable["search_discovery_recall"]["status"], "not_available")
        self.assertIn("denominator", unavailable["search_discovery_recall"]["reason"])
        self.assertIn("全国", unavailable["national_inspection_method_coverage"]["reason"])

    def test_dictionary_rejects_duplicate_identity(self):
        payload = json.loads(METRIC_DICTIONARY.read_text(encoding="utf-8"))
        payload["metrics"].append(dict(payload["metrics"][0]))
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(AnalyticsMetricDictionaryError):
                load_metric_dictionary(path)


class AnalyticsReadModelTest(AnalyticsFixture):
    def test_pipeline_uses_real_attempt_denominators_and_product_snapshot_grains(self):
        payload = self.service.pipeline()
        self.assertEqual(_metric(payload, "search_candidate_observation_count")["value"], 5)
        self.assertEqual(_metric(payload, "unique_product_count")["value"], 4)
        detail_rate = _metric(payload, "detail_collection_success_rate")
        self.assertEqual((detail_rate["numerator"], detail_rate["denominator"]), (3, 4))
        self.assertEqual(detail_rate["rate"], 0.75)
        ocr_rate = _metric(payload, "ocr_success_rate")
        self.assertEqual((ocr_rate["numerator"], ocr_rate["denominator"]), (2, 3))
        analysis_rate = _metric(payload, "analysis_readiness_rate")
        self.assertEqual((analysis_rate["numerator"], analysis_rate["denominator"]), (2, 2))
        review = _metric(payload, "review_status_distribution")
        self.assertEqual(_bucket(review, "pending")["count"], 1)
        self.assertEqual(_bucket(review, "recommend_follow_up")["count"], 1)
        self.assertEqual(review["denominator"], 2)
        self.assertEqual(_metric(payload, "current_sampling_membership_count")["value"], 1)

    def test_zero_denominator_is_null_not_zero(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = DataStore(root / "data" / "app.db", root / "output")
            store.initialize()
            service = AnalyticsReadService(store)
            metric = _metric(service.pipeline(), "detail_collection_success_rate")
            self.assertIsNone(metric["rate"])
            self.assertIsNone(metric["value"])
            self.assertEqual(metric["reason"], "zero_denominator")

    def test_time_and_stage_filters_are_snapshot_scoped_and_deterministic(self):
        february = self.service.pipeline(
            from_value="2026-02-01", to_value="2026-02-01"
        )
        self.assertEqual(_metric(february, "search_candidate_observation_count")["value"], 1)
        self.assertEqual(_metric(february, "unique_product_count")["value"], 1)
        failed = self.service.pipeline(stage="failed_processing")
        self.assertEqual(_metric(failed, "search_candidate_observation_count")["value"], 1)
        with self.assertRaises(AnalyticsQueryValidationError):
            self.service.pipeline(from_value="2026-02-02", to_value="2026-01-01")
        with self.assertRaises(AnalyticsQueryValidationError):
            self.service.pipeline(stage="completed")
        first = json.dumps(self.service.summary(), ensure_ascii=False, sort_keys=True)
        second = json.dumps(self.service.summary(), ensure_ascii=False, sort_keys=True)
        self.assertEqual(first, second)

    def test_claim_states_formal_only_and_ugc_boundary(self):
        payload = self.service.claims()
        statuses = _metric(payload, "claim_analysis_status_distribution")
        self.assertEqual(_bucket(statuses, "complete_with_claims")["count"], 1)
        self.assertEqual(_bucket(statuses, "complete_zero")["count"], 1)
        self.assertEqual(_bucket(statuses, "not_generated")["count"], 2)
        self.assertEqual(_bucket(statuses, "error")["count"], 1)
        self.assertEqual(_metric(payload, "formal_claim_signal_count")["value"], 1)
        claim_types = _metric(payload, "claim_type_snapshot_distribution")
        self.assertEqual(_bucket(claim_types, "sleep_related")["count"], 1)
        self.assertEqual(claim_types["denominator"], 2)
        evidence = _metric(payload, "evidence_source_scope_distribution")
        self.assertEqual(_bucket(evidence, "user_generated")["count"], 1)
        filtered = self.service.claims(claim_type="weight_management")
        self.assertEqual(_metric(filtered, "formal_claim_signal_count")["value"], 0)
        with self.assertRaises(AnalyticsQueryValidationError):
            self.service.claims(claim_type="助眠")

    def test_search_region_and_declared_origin_never_conflate_missing_or_conflict(self):
        payload = self.service.geography()
        search = _metric(payload, "collected_product_search_region_distribution")
        self.assertEqual(_bucket(search, "山东")["count"], 2)
        self.assertEqual(_bucket(search, "云南")["count"], 1)
        claim_region = _metric(payload, "claim_product_search_region_distribution")
        self.assertEqual(_bucket(claim_region, "山东")["count"], 1)
        origin = _metric(payload, "declared_origin_distribution")
        self.assertEqual(_bucket(origin, "云南省")["count"], 1)
        self.assertEqual(_bucket(origin, "conflict")["count"], 1)
        self.assertEqual(_bucket(origin, "unknown")["count"], 3)
        self.assertNotIn("山东", {item["key"] for item in origin["buckets"]})

    def test_knowledge_metrics_reuse_current_audit_values(self):
        payload = self.service.knowledge()
        audit = load_and_build_audit()
        mapping = {
            "inspection_method_reference_coverage": "method_reference_coverage",
            "group_resolution_coverage": "group_resolution_coverage",
            "recommendation_structural_reachability": "recommendation_structural_reachability",
            "recommendation_end_to_end_reachability": "recommendation_end_to_end_reachability",
            "context_corpus_recommendation_reachability": "context_corpus_recommendation_reachability",
        }
        for metric_id, audit_id in mapping.items():
            with self.subTest(metric_id=metric_id):
                metric = _metric(payload, metric_id)
                source = audit["metrics"][audit_id]
                self.assertEqual(metric["numerator"], source["numerator"])
                self.assertEqual(metric["denominator"], source["denominator"])
                self.assertEqual(metric["rate"], source["ratio"])
        self.assertEqual(_metric(payload, "reference_monitor_target_count")["value"], 106)
        self.assertEqual(_metric(payload, "inspection_indexed_method_count")["value"], 9)


class AnalyticsHttpApiTest(AnalyticsFixture):
    def test_get_endpoints_are_deterministic_and_do_not_change_business_state(self):
        web_root = self.root / "web"
        web_root.mkdir()
        (web_root / "index.html").write_text("ok", encoding="utf-8")
        manager = TaskManager(self.output_root)
        handler = create_handler(
            self.output_root,
            web_root,
            manager,
            self.store,
            monitor_config=MONITOR_REFERENCE,
        )
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"

        def business_state():
            with sqlite3.connect(self.store.database_path) as connection:
                return {
                    "reviews": connection.execute(
                        "SELECT snapshot_id, review_status, review_note, reviewed_at FROM reviews ORDER BY snapshot_id"
                    ).fetchall(),
                    "memberships": connection.execute(
                        "SELECT * FROM sampling_list_memberships ORDER BY product_id"
                    ).fetchall(),
                    "claims": connection.execute(
                        "SELECT * FROM claim_signals ORDER BY claim_signal_id"
                    ).fetchall(),
                    "facts": connection.execute(
                        "SELECT * FROM product_facts ORDER BY fact_id"
                    ).fetchall(),
                }

        before = business_state()
        try:
            endpoints = (
                "metrics",
                "summary?from=2026-01-01&to=2026-02-01",
                "pipeline?stage=success",
                "claims?claim_type=sleep_related",
                "geography?region=%E5%B1%B1%E4%B8%9C",
                "knowledge",
            )
            payloads = []
            for endpoint in endpoints:
                with urlopen(f"{base}/api/analytics/{endpoint}") as response:
                    self.assertEqual(response.status, 200)
                    payloads.append(json.load(response))
            self.assertEqual(payloads[0]["version"], "analytics-metrics-v2.0")
            self.assertEqual(
                _metric(payloads[2], "search_candidate_observation_count")["value"],
                2,
            )
            self.assertEqual(_metric(payloads[3], "formal_claim_signal_count")["value"], 1)
            self.assertEqual(_metric(payloads[4], "declared_origin_distribution")["denominator"], 2)
            self.assertEqual(_metric(payloads[5], "inspection_indexed_method_count")["value"], 9)
            with self.assertRaises(HTTPError) as raised:
                urlopen(f"{base}/api/analytics/claims?claim_type=legacy-effect")
            self.assertEqual(raised.exception.code, 400)
            request = Request(f"{base}/api/analytics/summary", method="POST")
            with self.assertRaises(HTTPError) as raised:
                urlopen(request)
            self.assertNotEqual(raised.exception.code, 200)
            self.assertEqual(before, business_state())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(2)


if __name__ == "__main__":
    unittest.main()
