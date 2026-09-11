import hashlib
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

from src.local_api import create_handler
from src.runtime import read_json, write_json
from src.task_runtime import TaskManager
from tools.build_historical_validation_set import (
    ALLOW_LIST,
    DEFAULT_DISPLAY_NAME,
    DEFAULT_RUN_ID,
    HistoricalValidationError,
    archive_current_data,
    build_validation_set,
    initialize_validation_database,
)


def tree_hashes(root: Path) -> dict[str, str]:
    result = {}
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_file():
            result[path.relative_to(root).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    return result


class HistoricalValidationBuilderTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "historical-output"
        self.output = self.root / "output"
        self.collected_at = {}
        for index, item in enumerate(ALLOW_LIST, start=1):
            self._write_source(item.source_run_id, item.product_id, index)
        extra = self.source / "outside-run" / "products" / "999999999999"
        extra.mkdir(parents=True)
        (extra / "do-not-copy.txt").write_text("outside allow-list", encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def _write_source(self, run_id: str, product_id: str, index: int) -> None:
        product_root = self.source / run_id / "products" / product_id
        original = product_root / "images" / "original" / "original_001.webp"
        original.parent.mkdir(parents=True, exist_ok=True)
        original.write_bytes(f"historical-image-{product_id}".encode())
        collected_at = f"2026-08-{index:02d}T10:00:00+08:00"
        self.collected_at[product_id] = collected_at
        write_json(
            product_root / "meta.json",
            {
                "productId": product_id,
                "productName": f"历史商品 {product_id}",
                "productUrl": f"https://item.example/?id={product_id}",
                "sourceProductUrl": f"https://item.example/?id={product_id}",
                "shopName": "历史店铺",
                "region": "广东",
                "keyword": "减肥饼干" if index == 3 else "历史关键词",
                "crawlTime": collected_at,
                "imageCount": 1,
                "images": [
                    {
                        "index": 1,
                        "localPath": "images/original/original_001.webp",
                        "ocrCandidate": True,
                    }
                ],
                "screenshots": [],
            },
        )
        evidence = []
        effects = []
        if index == 1:
            effects = ["助眠"]
            evidence = [
                {
                    "effect": "助眠",
                    "text": "安睡整个夜晚",
                    "matched_keywords": ["安睡"],
                    "source_type": "ocr_product_image",
                    "source_label": "商品详情图 OCR",
                    "content_origin": "seller_managed",
                    "source_path": "ocr/original_001.txt",
                    "line_number": 1,
                }
            ]
        elif index == 3:
            effects = ["减脂"]
            evidence = [
                {
                    "effect": "减脂",
                    "text": "适用减脂人群",
                    "matched_keywords": ["减脂"],
                    "source_type": "dom_user_review",
                    "source_label": "用户评价",
                    "content_origin": "user_generated",
                    "source_path": "dom_text.txt",
                    "line_number": 1,
                }
            ]
        elif index in {4, 5}:
            effects = ["助眠"]
            evidence = [
                {
                    "effect": "助眠",
                    "text": "睡眠辅助线索",
                    "matched_keywords": ["睡眠"],
                    "source_type": "dom_product",
                    "source_label": "当前商品 DOM",
                    "content_origin": "seller_managed",
                    "source_path": "dom_text.txt",
                    "line_number": 1,
                }
            ]
        write_json(
            product_root / "analysis.json",
            {
                "product_id": product_id,
                "product_name": f"历史商品 {product_id}",
                "product_url": f"https://item.example/?id={product_id}",
                "keyword": "减肥饼干" if index == 3 else "历史关键词",
                "detected_effects": effects,
                "matched_keywords": {
                    effect: list(evidence[0]["matched_keywords"]) for effect in effects
                },
                "evidence": [item["text"] for item in evidence],
                "evidence_details": evidence,
                "evidence_source_counts": {},
                "evidence_origin_counts": {},
                "risk_reason": "历史 Phase3 已完成",
                "review_required": bool(evidence),
            },
        )
        write_json(
            product_root / "ocr" / "manifest.json",
            [
                {
                    "image": "original_001.webp",
                    "sourcePath": "images/original/original_001.webp",
                    "status": "success",
                    "lineCount": 1,
                    "characterCount": 4,
                    "textPath": "ocr/original_001.txt",
                    "jsonPath": "ocr/original_001.json",
                }
            ],
        )
        (product_root / "ocr" / "original_001.txt").write_text(
            "历史 OCR 文本", encoding="utf-8"
        )
        write_json(
            product_root / "ocr" / "original_001.json",
            {"image": "original_001.webp", "lines": []},
        )
        (product_root / "ocr" / "combined_text.txt").write_text(
            "历史 OCR 合并文本", encoding="utf-8"
        )
        write_json(
            product_root / "ocr" / "run_info.json",
            {"ocrVersion": "PP-OCRv6", "device": "cpu"},
        )
        (product_root / "dom_text.txt").write_text("历史 DOM", encoding="utf-8")
        if index == 3:
            write_json(
                product_root / "inspection_recommendation.json",
                {"historical": True, "mustNotBeCurrent": True},
            )

    def _build(self, **kwargs):
        return build_validation_set(
            self.source,
            self.output,
            created_at="2026-09-11T12:00:00+08:00",
            **kwargs,
        )

    def test_allow_list_copy_is_read_only_and_preserves_collected_at(self):
        source_before = tree_hashes(self.source)

        manifest = self._build()

        self.assertEqual(tree_hashes(self.source), source_before)
        self.assertEqual(len(manifest["items"]), 5)
        validation_root = self.output / DEFAULT_RUN_ID
        copied_products = {
            path.name for path in (validation_root / "products").iterdir() if path.is_dir()
        }
        self.assertEqual(copied_products, {item.product_id for item in ALLOW_LIST})
        self.assertFalse((validation_root / "products" / "999999999999").exists())
        for item in ALLOW_LIST:
            meta = read_json(validation_root / "products" / item.product_id / "meta.json")
            self.assertEqual(meta["crawlTime"], self.collected_at[item.product_id])
        negative_root = validation_root / "products" / ALLOW_LIST[2].product_id
        self.assertFalse((negative_root / "inspection_recommendation.json").read_text(encoding="utf-8").find('"historical": true') >= 0)
        self.assertTrue(
            (negative_root / "provenance" / "archive" / "source_inspection_recommendation.json").is_file()
        )

    def test_missing_core_artifact_rejects_before_destination_is_written(self):
        missing = (
            self.source
            / ALLOW_LIST[0].source_run_id
            / "products"
            / ALLOW_LIST[0].product_id
            / "ocr"
            / "combined_text.txt"
        )
        missing.unlink()

        with self.assertRaisesRegex(HistoricalValidationError, "combined_text"):
            self._build()

        self.assertFalse((self.output / DEFAULT_RUN_ID).exists())

    def test_existing_destination_requires_force_and_force_only_rebuilds_validation_run(self):
        self._build()
        sentinel = self.output / "unrelated-run" / "keep.txt"
        sentinel.parent.mkdir()
        sentinel.write_text("keep", encoding="utf-8")

        with self.assertRaisesRegex(HistoricalValidationError, "--force"):
            self._build()
        self._build(force=True)

        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_fresh_database_import_has_five_pending_eligible_snapshots_and_no_sampling(self):
        self._build()
        database = self.root / "data" / "app.db"
        store, imported = initialize_validation_database(database, self.output)

        self.assertEqual(imported["runImport"]["products"], 5)
        counts = store.table_counts()
        self.assertEqual(counts["tasks"], 1)
        self.assertEqual(counts["products"], 5)
        self.assertEqual(counts["product_snapshots"], 5)
        self.assertEqual(counts["reviews"], 5)
        self.assertEqual(counts["sampling_list_memberships"], 0)
        products = store.list_products(page_size=100)
        self.assertEqual(len(products), 5)
        self.assertTrue(all(item["review"]["status"] == "pending" for item in products))
        self.assertTrue(all(item["readiness"]["reviewEligible"] for item in products))
        zero_evidence = next(
            item for item in products if item["productId"] == ALLOW_LIST[1].product_id
        )
        self.assertTrue(zero_evidence["readiness"]["analysisReady"])
        self.assertEqual(zero_evidence["counts"]["evidence"], 0)
        summary = store.get_task_business_summary(DEFAULT_RUN_ID)
        self.assertEqual(summary["displayName"], DEFAULT_DISPLAY_NAME)
        self.assertEqual(summary["archiveSummary"]["pendingReview"], 5)

        web = self.root / "web"
        web.mkdir()
        (web / "index.html").write_text("ok", encoding="utf-8")
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            create_handler(
                self.output,
                web,
                TaskManager(self.output),
                store,
                monitor_config=None,
                inspection_config=None,
                risk_substance_config=None,
            ),
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with urlopen(
                f"http://127.0.0.1:{server.server_port}/api/products?page_size=100"
            ) as response:
                payload = json.load(response)
            self.assertEqual(payload["total"], 5)
            self.assertEqual(
                {item["productId"] for item in payload["products"]},
                {item.product_id for item in ALLOW_LIST},
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(2)

    def test_exact_match_negative_does_not_create_weight_loss_bridge(self):
        self._build()
        recommendation = read_json(
            self.output
            / DEFAULT_RUN_ID
            / "products"
            / ALLOW_LIST[2].product_id
            / "inspection_recommendation.json"
        )

        self.assertEqual(recommendation["risk_findings"], [])
        self.assertEqual(len(recommendation["unmapped_evidence"]), 1)
        self.assertEqual(recommendation["unmapped_evidence"][0]["effect"], "减脂")

    def test_archive_moves_current_data_without_deleting_content(self):
        workspace = self.root / "workspace"
        current_run = workspace / "output" / "run-one"
        current_run.mkdir(parents=True)
        write_json(current_run / "web_snapshot.json", {"task": {"id": "run-one"}})
        sampling = workspace / "output" / "sampling_lists"
        sampling.mkdir()
        (sampling / "keep.txt").write_text("sampling", encoding="utf-8")
        database = workspace / "data" / "app.db"
        database.parent.mkdir()
        database.write_bytes(b"database-before-validation")
        source_hash = hashlib.sha256(database.read_bytes()).hexdigest()
        archive = workspace / "archive" / "pre-validation"

        manifest = archive_current_data(
            workspace, archive, archived_at="2026-09-11T13:00:00+08:00"
        )

        self.assertEqual(manifest["output"]["runIds"], ["run-one"])
        self.assertEqual(manifest["databaseFiles"][0]["sha256"], source_hash)
        self.assertFalse(manifest["deletionPerformed"])
        self.assertEqual(
            (archive / "output" / "sampling_lists" / "keep.txt").read_text(
                encoding="utf-8"
            ),
            "sampling",
        )
        self.assertEqual((archive / "data" / "app.db").read_bytes(), b"database-before-validation")
        self.assertTrue((workspace / "output").is_dir())
        self.assertEqual(list((workspace / "output").iterdir()), [])
        self.assertFalse(database.exists())


if __name__ == "__main__":
    unittest.main()
