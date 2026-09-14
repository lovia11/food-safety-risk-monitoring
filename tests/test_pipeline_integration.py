import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.claim_analysis import CLAIM_ANALYSIS_ERROR_FILE, CLAIM_ANALYSIS_FILE
from src.data_store import DataStore, ReviewEligibilityError
from src.local_api import task_business_dto
from src.main import PipelineOptions, ProductStatus, StandalonePipeline, initial_state
from src.review_decision import ReviewDecisionService
from src.runtime import read_json, write_json
from src.sampling_store import SamplingStore
from src.web_contract import write_web_snapshot


def _record(product_id: str, status: str, original: int = 0, ocr: int = 0):
    return {
        "keyword": "离线契约测试",
        "product_id": product_id,
        "product_name": f"商品 {product_id}",
        "shop_name": "离线店铺",
        "region": "浙江",
        "product_url": f"https://item.example/{product_id}",
        "original_image_count": original,
        "ocr_image_count": ocr,
        "detected_effects": [],
        "review_required": None,
        "risk_reason": "",
        "evidence_details": [],
        "crawl_status": status,
        "errors": [],
    }


def _write_analysis_ready_product(
    run_root: Path,
    product_id: str,
    *,
    evidence: list[dict] | None = None,
) -> None:
    product_root = run_root / "products" / product_id
    image_path = product_root / "images" / "original" / "original_002.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(b"offline-image")
    write_json(
        product_root / "meta.json",
        {
            "productId": product_id,
            "imageCount": 1,
            "ocrImageNumbers": [2],
            "images": [
                {
                    "index": 2,
                    "localPath": "images/original/original_002.png",
                    "ocrCandidate": True,
                }
            ],
            "screenshots": [],
        },
    )
    text_path = product_root / "ocr" / "original_002.txt"
    text_path.parent.mkdir(parents=True, exist_ok=True)
    text_path.write_text("未发现明确功效表达", encoding="utf-8")
    write_json(product_root / "ocr" / "original_002.json", {"lines": []})
    write_json(
        product_root / "ocr" / "manifest.json",
        [
            {
                "image": "original_002.png",
                "sourcePath": "images/original/original_002.png",
                "status": "success",
                "textPath": "ocr/original_002.txt",
                "jsonPath": "ocr/original_002.json",
            }
        ],
    )
    (product_root / "ocr" / "combined_text.txt").write_text(
        "未发现明确功效表达\n", encoding="utf-8"
    )
    write_json(
        product_root / "analysis.json",
        {
            "product_id": product_id,
            "detected_effects": [],
            "review_required": False,
            "risk_reason": "未发现明确功效表达",
            "evidence_details": evidence or [],
        },
    )


class MixedPipelineIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.output_root = self.root / "output"
        self.run_root = self.output_root / "mixed-run"
        _write_analysis_ready_product(self.run_root, "A")
        write_json(
            self.run_root / "products" / "C" / "meta.json",
            {
                "productId": "C",
                "imageCount": 1,
                "ocrImageNumbers": [2],
                "images": [],
                "screenshots": [],
            },
        )
        write_json(
            self.run_root / "task_request.json",
            {
                "task_id": "mixed-run",
                "task_type": "quick",
                "keyword": "离线契约测试",
                "candidate_limit": 4,
                "detail_limit": 3,
            },
        )
        records = [
            _record("A", "success", original=1, ocr=1),
            _record("B", "failed_collection"),
            _record("C", "failed_processing", original=1, ocr=0),
            _record("D", "pending_detail_collection"),
        ]
        write_web_snapshot(
            self.run_root,
            {
                "keyword": "离线契约测试",
                "search_raw_count": 4,
                "search_deduplicated_count": 4,
                "candidates": [
                    {"product_id": item, "rank": rank}
                    for rank, item in enumerate(("A", "B", "C", "D"), start=1)
                ],
            },
            records,
            "completed_with_errors",
            "离线混合结果",
        )
        self.store = DataStore(self.root / "data" / "app.db", self.output_root)
        self.store.initialize()
        self.store.import_run(self.run_root)
        self.sampling = SamplingStore(self.store.database_path)
        self.decisions = ReviewDecisionService(self.store, self.sampling)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_mixed_results_preserve_facts_and_enforce_review_boundary(self) -> None:
        snapshots = {
            item["productId"]: item
            for item in self.store.list_products(task_id="mixed-run", page_size=10)
        }
        self.assertEqual(set(snapshots), {"A", "B", "C", "D"})
        self.assertTrue(snapshots["A"]["readiness"]["reviewEligible"])
        for product_id in ("B", "C", "D"):
            with self.subTest(product_id=product_id):
                self.assertFalse(
                    snapshots[product_id]["readiness"]["reviewEligible"]
                )
                self.assertEqual(
                    snapshots[product_id]["sampling"]["decisionStatus"],
                    "not_eligible",
                )

        pending = self.store.list_products(
            task_id="mixed-run", review_status="pending", page_size=10
        )
        self.assertEqual([item["productId"] for item in pending], ["A"])

        summary = self.store.get_task_business_summary("mixed-run")
        self.assertEqual(
            {
                key: summary["archiveSummary"][key]
                for key in (
                    "detailCompleted",
                    "detailTarget",
                    "detailFailed",
                    "analysisCompleted",
                    "analysisTarget",
                    "analysisFailed",
                    "pendingReview",
                    "completedReview",
                )
            },
            {
                "detailCompleted": 2,
                "detailTarget": 3,
                "detailFailed": 1,
                "analysisCompleted": 1,
                "analysisTarget": 2,
                "analysisFailed": 1,
                "pendingReview": 1,
                "completedReview": 0,
            },
        )
        task = task_business_dto(
            {
                "task": {"stage": "completed_with_errors"},
                "runtime": {"active": False, "resumable": False},
            },
            summary,
        )
        self.assertEqual(
            {item["key"]: item["state"] for item in task["flow"]},
            {
                "search": "done",
                "detail": "partial",
                "analysis": "partial",
                "review": "active",
            },
        )

        for product_id in ("B", "C", "D"):
            with self.subTest(rejected_product=product_id):
                with self.assertRaises(ReviewEligibilityError):
                    self.decisions.decide(
                        snapshots[product_id]["snapshotId"],
                        "no_further_action",
                        "inspection_workspace",
                    )
        with sqlite3.connect(self.store.database_path) as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM reviews WHERE review_status = 'pending'"
                ).fetchone()[0],
                4,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM sampling_list_memberships"
                ).fetchone()[0],
                0,
            )

    def test_analysis_without_evidence_is_still_completed_and_review_eligible(self):
        self.assertEqual(self.store.table_counts()["evidence"], 0)
        snapshot = self.store.list_products(task_id="mixed-run", page_size=10)[0]
        self.assertEqual(snapshot["productId"], "A")
        self.assertTrue(snapshot["readiness"]["analysisReady"])
        summary = self.store.get_task_business_summary("mixed-run")["archiveSummary"]
        self.assertEqual(summary["analysisCompleted"], 1)
        self.assertEqual(summary["clueProducts"], 0)


class OCRRuntimeInitializationIntegrationTest(unittest.TestCase):
    def test_pipeline_derives_claim_sidecar_from_phase3_evidence_and_projects_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_root = root / "output"
            pipeline = StandalonePipeline(
                PipelineOptions(
                    keyword="发现策略词不进入 Claim",
                    output_root=output_root,
                    run_id="claim-pipeline",
                )
            )
            product_id = "A"
            candidate = {
                "product_id": product_id,
                "product_name": "商品 A",
                "product_url": "https://item.example/A",
                "rank": 1,
            }
            _write_analysis_ready_product(pipeline.run_root, product_id)
            product_root = pipeline.products_root / product_id
            (product_root / "analysis.json").unlink()
            pipeline.prepared_roots[product_id] = product_root
            pipeline.state_by_id[product_id] = initial_state(candidate)
            pipeline.search_payload = {
                "keyword": "减肥",
                "candidates": [candidate],
            }

            def write_analysis(target, *_args, **_kwargs):
                write_json(
                    target / "analysis.json",
                    {
                        "detected_effects": ["助眠"],
                        "review_required": True,
                        "risk_reason": "legacy output",
                        "evidence_details": [
                            {
                                "effect": "助眠",
                                "text": "本品帮助安睡",
                                "matched_keywords": ["安睡"],
                                "source_type": "ocr",
                                "source_label": "详情图 OCR",
                                "content_origin": "seller_managed",
                                "source_path": "ocr/original_002.txt",
                                "line_number": 1,
                            }
                        ],
                    },
                )

            with (
                patch("src.main.create_ocr_runtime", return_value=object()),
                patch("src.main.run_ocr"),
                patch("src.main.run_analysis", side_effect=write_analysis),
            ):
                pipeline._process_products()

            artifact = read_json(product_root / CLAIM_ANALYSIS_FILE)
            self.assertEqual(artifact["status"], "complete")
            self.assertEqual(
                [item["matchedExpression"] for item in artifact["claimMentions"]],
                ["安睡"],
            )
            self.assertEqual(artifact["claimSignals"][0]["claimType"], "sleep_related")
            self.assertEqual(
                pipeline.state_by_id[product_id]["status"], ProductStatus.SUCCESS
            )

            pipeline.web_stage = "completed"
            pipeline._write_outputs(pipeline.search_payload)
            write_json(
                pipeline.run_root / "task_request.json",
                {
                    "task_id": pipeline.run_root.name,
                    "keyword": "减肥",
                    "candidate_limit": 1,
                    "detail_limit": 1,
                },
            )
            store = DataStore(root / "data" / "app.db", output_root)
            store.initialize()
            store.import_run(pipeline.run_root)
            detail = store.get_snapshot(store.list_products()[0]["snapshotId"])
            self.assertTrue(detail["readiness"]["reviewEligible"])
            self.assertEqual(detail["review"]["status"], "pending")
            self.assertEqual(detail["claimAnalysisStatus"], "complete")
            self.assertEqual(detail["claimSignals"][0]["claimType"], "sleep_related")
            for handler in list(pipeline.logger.handlers):
                handler.close()
                pipeline.logger.removeHandler(handler)

    def test_claim_sidecar_failure_is_degradable_and_does_not_change_review_readiness(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_root = root / "output"
            pipeline = StandalonePipeline(
                PipelineOptions(
                    keyword="Claim 降级",
                    output_root=output_root,
                    run_id="claim-failure",
                )
            )
            product_id = "A"
            candidate = {
                "product_id": product_id,
                "product_name": "商品 A",
                "product_url": "https://item.example/A",
                "rank": 1,
            }
            _write_analysis_ready_product(pipeline.run_root, product_id)
            product_root = pipeline.products_root / product_id
            (product_root / "analysis.json").unlink()
            pipeline.prepared_roots[product_id] = product_root
            pipeline.state_by_id[product_id] = initial_state(candidate)
            pipeline.search_payload = {"keyword": "Claim 降级", "candidates": [candidate]}

            def write_analysis(target, *_args, **_kwargs):
                write_json(
                    target / "analysis.json",
                    {
                        "detected_effects": [],
                        "review_required": False,
                        "risk_reason": "分析完成",
                        "evidence_details": [],
                    },
                )

            with (
                patch("src.main.create_ocr_runtime", return_value=object()),
                patch("src.main.run_ocr"),
                patch("src.main.run_analysis", side_effect=write_analysis),
                patch(
                    "src.main.write_claim_analysis",
                    side_effect=RuntimeError("claim sidecar unavailable"),
                ),
            ):
                pipeline._process_products()

            self.assertEqual(
                pipeline.state_by_id[product_id]["status"], ProductStatus.SUCCESS
            )
            self.assertTrue((product_root / "analysis.json").is_file())
            self.assertFalse((product_root / CLAIM_ANALYSIS_FILE).exists())
            error = read_json(product_root / CLAIM_ANALYSIS_ERROR_FILE)
            self.assertEqual(error["errorType"], "RuntimeError")
            pipeline.web_stage = "completed"
            pipeline._write_outputs(pipeline.search_payload)
            write_json(
                pipeline.run_root / "task_request.json",
                {
                    "task_id": pipeline.run_root.name,
                    "keyword": "Claim 降级",
                    "candidate_limit": 1,
                    "detail_limit": 1,
                },
            )
            store = DataStore(root / "data" / "app.db", output_root)
            store.initialize()
            store.import_run(pipeline.run_root)
            detail = store.get_snapshot(store.list_products()[0]["snapshotId"])
            self.assertTrue(detail["readiness"]["reviewEligible"])
            self.assertEqual(detail["review"]["status"], "pending")
            self.assertEqual(detail["claimAnalysisStatus"], "error")
            for handler in list(pipeline.logger.handlers):
                handler.close()
                pipeline.logger.removeHandler(handler)

    def test_shared_runtime_failure_records_each_product_and_blocks_review(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_root = root / "output"
            pipeline = StandalonePipeline(
                PipelineOptions(
                    keyword="离线 OCR 初始化失败",
                    output_root=output_root,
                    run_id="ocr-runtime-failure",
                )
            )
            candidates = []
            for rank, product_id in enumerate(("A", "B"), start=1):
                candidate = {
                    "product_id": product_id,
                    "product_name": f"商品 {product_id}",
                    "product_url": f"https://item.example/{product_id}",
                    "rank": rank,
                }
                candidates.append(candidate)
                product_root = pipeline.products_root / product_id
                image_path = (
                    product_root / "images" / "original" / "original_002.png"
                )
                image_path.parent.mkdir(parents=True, exist_ok=True)
                image_path.write_bytes(b"offline-image")
                write_json(
                    product_root / "meta.json",
                    {
                        "productId": product_id,
                        "productName": candidate["product_name"],
                        "imageCount": 1,
                        "savedOriginalCount": 1,
                        "ocrCandidateCount": 1,
                        "ocrImageNumbers": [2],
                        "images": [
                            {
                                "index": 2,
                                "localPath": "images/original/original_002.png",
                                "ocrCandidate": True,
                            }
                        ],
                        "screenshots": [],
                    },
                )
                pipeline.prepared_roots[product_id] = product_root
                pipeline.state_by_id[product_id] = initial_state(candidate)
                pipeline.state_by_id[product_id]["status"] = (
                    ProductStatus.DETAIL_COLLECTED
                )
            pipeline.search_payload = {
                "keyword": "离线 OCR 初始化失败",
                "raw_card_count": 2,
                "deduplicated_count": 2,
                "candidates": candidates,
            }

            failure = RuntimeError("incompatible shared OCR runtime")
            with patch(
                "src.main.create_ocr_runtime", side_effect=failure
            ) as create_runtime:
                pipeline._process_products()

            self.assertEqual(create_runtime.call_count, 1)
            for product_id in ("A", "B"):
                with self.subTest(product_id=product_id):
                    product_root = pipeline.products_root / product_id
                    self.assertEqual(
                        pipeline.state_by_id[product_id]["status"],
                        ProductStatus.FAILED_PROCESSING,
                    )
                    run_info = read_json(product_root / "ocr" / "run_info.json")
                    self.assertEqual(
                        set(
                            (
                                "pythonVersion",
                                "paddlepaddleVersion",
                                "paddleocrVersion",
                                "paddlexVersion",
                                "ocrVersion",
                                "modelSource",
                                "device",
                                "scoreThreshold",
                            )
                        )
                        - set(run_info),
                        set(),
                    )
                    stage_error = read_json(
                        product_root / "ocr" / "stage_error.json"
                    )
                    self.assertEqual(stage_error["errorType"], "RuntimeError")
                    self.assertEqual(
                        stage_error["message"], "incompatible shared OCR runtime"
                    )
                    self.assertTrue(stage_error["failedAt"])
                    self.assertFalse((product_root / "analysis.json").exists())

            pipeline.web_stage = "completed_with_errors"
            pipeline.web_message = "OCR Runtime 初始化失败"
            pipeline._write_outputs(pipeline.search_payload)
            write_json(
                pipeline.run_root / "task_request.json",
                {
                    "task_id": pipeline.run_root.name,
                    "task_type": "quick",
                    "keyword": pipeline.options.keyword,
                    "candidate_limit": 2,
                    "detail_limit": 2,
                },
            )
            store = DataStore(root / "data" / "app.db", output_root)
            store.initialize()
            store.import_run(pipeline.run_root)
            products = store.list_products(
                task_id=pipeline.run_root.name,
                page_size=10,
            )
            self.assertEqual(len(products), 2)
            self.assertTrue(
                all(not item["readiness"]["reviewEligible"] for item in products)
            )
            self.assertEqual(
                store.list_products(
                    task_id=pipeline.run_root.name,
                    review_status="pending",
                    page_size=10,
                ),
                [],
            )
            for handler in list(pipeline.logger.handlers):
                handler.close()
                pipeline.logger.removeHandler(handler)

    def test_product_fact_extractor_failure_is_degradable_after_ocr(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_root = root / "output"
            pipeline = StandalonePipeline(
                PipelineOptions(
                    keyword="离线 ProductFact 降级",
                    output_root=output_root,
                    run_id="product-fact-degraded",
                )
            )
            product_id = "A"
            candidate = {
                "product_id": product_id,
                "product_name": "商品 A",
                "product_url": "https://item.example/A",
                "rank": 1,
            }
            product_root = pipeline.products_root / product_id
            _write_analysis_ready_product(pipeline.run_root, product_id)
            (product_root / "analysis.json").unlink()
            pipeline.prepared_roots[product_id] = product_root
            pipeline.state_by_id[product_id] = initial_state(candidate)
            pipeline.state_by_id[product_id]["status"] = ProductStatus.DETAIL_COLLECTED
            pipeline.search_payload = {
                "keyword": pipeline.options.keyword,
                "raw_card_count": 1,
                "deduplicated_count": 1,
                "candidates": [candidate],
            }

            def write_analysis(target: Path, *_args, **_kwargs):
                write_json(
                    target / "analysis.json",
                    {
                        "product_id": product_id,
                        "detected_effects": [],
                        "review_required": False,
                        "risk_reason": "分析已完成",
                        "evidence_details": [],
                    },
                )

            with (
                patch("src.main.create_ocr_runtime", return_value=object()),
                patch("src.main.run_ocr", return_value=product_root / "phase2_ocr_report.md"),
                patch("src.main.extract_product_facts", side_effect=RuntimeError("fact writer failed")),
                patch("src.main.run_analysis", side_effect=write_analysis),
            ):
                pipeline._process_products()

            self.assertEqual(
                pipeline.state_by_id[product_id]["status"], ProductStatus.SUCCESS
            )
            self.assertTrue((product_root / "analysis.json").is_file())
            self.assertFalse((product_root / "product_facts.json").exists())
            pipeline.web_stage = "completed"
            pipeline.web_message = "完成"
            pipeline._write_outputs(pipeline.search_payload)
            write_json(
                pipeline.run_root / "task_request.json",
                {
                    "task_id": pipeline.run_root.name,
                    "task_type": "quick",
                    "keyword": pipeline.options.keyword,
                    "candidate_limit": 1,
                    "detail_limit": 1,
                },
            )
            store = DataStore(root / "data" / "app.db", output_root)
            store.initialize()
            store.import_run(pipeline.run_root)
            snapshot = store.list_products(task_id=pipeline.run_root.name)[0]
            self.assertTrue(snapshot["readiness"]["reviewEligible"])
            detail = store.get_snapshot(snapshot["snapshotId"])
            self.assertEqual(detail["declaredOrigin"]["state"], "none")

            for handler in list(pipeline.logger.handlers):
                handler.close()
                pipeline.logger.removeHandler(handler)

    def test_health_food_identity_extraction_failure_does_not_break_analysis(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pipeline = StandalonePipeline(
                PipelineOptions(keyword="身份抽取降级", output_root=root / "output", run_id="identity-failure")
            )
            product_id = "A"
            candidate = {"product_id": product_id, "product_name": "商品 A", "product_url": "https://item.example/A", "rank": 1}
            _write_analysis_ready_product(pipeline.run_root, product_id)
            product_root = pipeline.products_root / product_id
            (product_root / "analysis.json").unlink()
            pipeline.prepared_roots[product_id] = product_root
            pipeline.state_by_id[product_id] = initial_state(candidate)
            pipeline.search_payload = {"keyword": "身份抽取降级", "candidates": [candidate]}

            def write_analysis(target, *_args, **_kwargs):
                write_json(target / "analysis.json", {"detected_effects": [], "review_required": False, "evidence_details": []})

            with (
                patch("src.main.create_ocr_runtime", return_value=object()),
                patch("src.main.run_ocr"),
                patch("src.main.extract_health_food_identity", side_effect=RuntimeError("identity extractor failed")),
                patch("src.main.run_analysis", side_effect=write_analysis),
            ):
                pipeline._process_products()
            self.assertEqual(pipeline.state_by_id[product_id]["status"], ProductStatus.SUCCESS)
            self.assertTrue((product_root / "analysis.json").is_file())
            for handler in list(pipeline.logger.handlers):
                handler.close()
                pipeline.logger.removeHandler(handler)

    def test_registry_unavailable_is_persisted_without_review_or_sampling_side_effects(self):
        class UnavailableProvider:
            def lookup(self, identifier):
                return {
                    "status": "unavailable",
                    "queriedIdentifier": identifier,
                    "sourceName": "official",
                    "sourceReference": "https://example.invalid",
                    "queriedAt": "2026-09-13T10:00:00+08:00",
                    "record": None,
                    "rawArtifactPath": None,
                    "rawArtifactSha256": None,
                    "error": "offline",
                }

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_root = root / "output"
            pipeline = StandalonePipeline(
                PipelineOptions(keyword="身份查询降级", output_root=output_root, run_id="registry-unavailable")
            )
            pipeline.set_health_food_registry_provider(UnavailableProvider())
            product_id = "A"
            candidate = {"product_id": product_id, "product_name": "商品 A", "product_url": "https://item.example/A", "rank": 1}
            _write_analysis_ready_product(pipeline.run_root, product_id)
            product_root = pipeline.products_root / product_id
            (product_root / "analysis.json").unlink()
            (product_root / "dom_text.txt").write_text(
                "参数信息\n批准文号：国食健注G20190188\n图文详情", encoding="utf-8"
            )
            pipeline.prepared_roots[product_id] = product_root
            pipeline.state_by_id[product_id] = initial_state(candidate)
            pipeline.search_payload = {"keyword": "身份查询降级", "candidates": [candidate]}

            def write_analysis(target, *_args, **_kwargs):
                write_json(target / "analysis.json", {"detected_effects": [], "review_required": False, "evidence_details": []})

            with (
                patch("src.main.create_ocr_runtime", return_value=object()),
                patch("src.main.run_ocr"),
                patch("src.main.run_analysis", side_effect=write_analysis),
            ):
                pipeline._process_products()
            self.assertEqual(pipeline.state_by_id[product_id]["status"], ProductStatus.SUCCESS)
            self.assertEqual(
                read_json(product_root / "health_food_identity.json")["identityAssessment"]["state"],
                "registry_lookup_unavailable",
            )
            pipeline.web_stage = "completed"
            pipeline._write_outputs(pipeline.search_payload)
            write_json(pipeline.run_root / "task_request.json", {"task_id": pipeline.run_root.name, "keyword": "身份查询降级", "detail_limit": 1})
            store = DataStore(root / "data/app.db", output_root)
            store.initialize()
            store.import_run(pipeline.run_root)
            snapshot = store.list_products(task_id=pipeline.run_root.name)[0]
            self.assertTrue(snapshot["readiness"]["reviewEligible"])
            self.assertEqual(store.get_snapshot(snapshot["snapshotId"])["healthFoodIdentity"]["state"], "registry_lookup_unavailable")
            with sqlite3.connect(store.database_path) as connection:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM sampling_list_memberships").fetchone()[0], 0)
                self.assertEqual(connection.execute("SELECT review_status FROM reviews").fetchone()[0], "pending")
            connection.close()
            for handler in list(pipeline.logger.handlers):
                handler.close()
                pipeline.logger.removeHandler(handler)


if __name__ == "__main__":
    unittest.main()
