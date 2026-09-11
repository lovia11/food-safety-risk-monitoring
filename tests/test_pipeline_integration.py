import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
