import json
import tempfile
import unittest
from pathlib import Path

from src.phase5_batch import (
    build_batch_record,
    ingest_browser_capture,
    is_ocr_candidate,
)


class PhaseFiveBatchTest(unittest.TestCase):
    def test_ocr_candidate_filters_short_and_generic_footer(self):
        self.assertTrue(
            is_ocr_candidate(
                {"naturalWidth": 1440, "naturalHeight": 1650, "src": "detail.jpg"}
            )
        )
        self.assertFalse(
            is_ocr_candidate(
                {"naturalWidth": 790, "naturalHeight": 450, "src": "header.jpg"}
            )
        )
        self.assertFalse(
            is_ocr_candidate(
                {
                    "naturalWidth": 1125,
                    "naturalHeight": 1446,
                    "src": "6000000002284-2-tps-1125-1446.png",
                }
            )
        )

    def test_ingests_capture_with_real_asset_association(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            asset = root / "download.jpg"
            asset.write_bytes(b"real-image-bytes")
            capture_path = root / "capture.json"
            capture_path.write_text(
                json.dumps(
                    {
                        "capturedAt": "2026-08-17T10:00:00.000Z",
                        "pageUrl": "https://detail.tmall.com/item.htm?id=123",
                        "pageTitle": "商品详情",
                        "bodyText": "标题\n图文详情",
                        "bodyLineCount": 2,
                        "bodyCharacterCount": 6,
                        "selectorEvidence": {"detailContainer": "#observed"},
                        "detailImages": [
                            {
                                "src": "https://img.alicdn.com/detail.jpg",
                                "naturalWidth": 790,
                                "naturalHeight": 1200,
                                "className": "observed-image",
                                "dataName": "singleImage",
                            }
                        ],
                        "assetInventory": {"summary": {"image": 1}},
                        "bundle": {
                            "assets": [
                                {
                                    "id": "asset-1",
                                    "url": "https://img.alicdn.com/detail.jpg",
                                    "path": str(asset),
                                    "contentType": "image/webp",
                                }
                            ],
                            "summary": {"downloadedCount": 1, "failedCount": 0},
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            candidate = {
                "keyword": "酸枣仁",
                "product_id": "123",
                "product_name": "真实商品",
                "product_url": "https://detail.tmall.com/item.htm?id=123",
                "shop_name": "真实店铺",
                "region": "山西 太原",
            }
            destination = root / "batch" / "products" / "123"
            meta = ingest_browser_capture(capture_path, candidate, destination, "batch")
            self.assertEqual(meta["imageCount"], 1)
            self.assertEqual(meta["ocrCandidateCount"], 1)
            self.assertTrue(
                (destination / "images" / "original" / "original_001.webp").exists()
            )
            self.assertEqual(
                (destination / "dom_text.txt").read_text(encoding="utf-8"),
                "标题\n图文详情",
            )

    def test_pending_record_does_not_invent_analysis(self):
        candidate = {
            "keyword": "酸枣仁",
            "product_id": "456",
            "product_name": "待处理商品",
            "product_url": "https://item.taobao.com/item.htm?id=456",
        }
        state = {"status": "pending_detail_collection", "errors": []}
        record = build_batch_record(candidate, None, state)
        self.assertEqual(record["original_image_count"], 0)
        self.assertEqual(record["detected_effects"], [])
        self.assertIsNone(record["review_required"])

    def test_processed_record_prefers_verified_detail_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            product_root = Path(temporary) / "products" / "123"
            product_root.mkdir(parents=True)
            (product_root / "meta.json").write_text(
                json.dumps(
                    {
                        "productId": "123",
                        "productName": "详情页名称",
                        "productUrl": "https://detail.tmall.com/item.htm?id=123",
                        "shopName": "详情页店铺",
                        "region": "详情页地区",
                        "imageCount": 0,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            candidate = {
                "product_id": "123",
                "product_name": "搜索页名称",
                "product_url": "https://click.simba.taobao.com/redirect?id=123",
            }
            state = {"status": "success", "errors": []}
            record = build_batch_record(candidate, product_root, state)
            self.assertEqual(record["product_name"], "详情页名称")
            self.assertEqual(
                record["product_url"],
                "https://detail.tmall.com/item.htm?id=123",
            )


if __name__ == "__main__":
    unittest.main()
