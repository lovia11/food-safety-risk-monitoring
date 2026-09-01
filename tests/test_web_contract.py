import tempfile
import unittest
from pathlib import Path

from src.runtime import read_json, write_json
from src.web_contract import build_web_snapshot, snapshot_existing_run


class WebContractTest(unittest.TestCase):
    def test_build_snapshot_has_frontend_status_and_statistics(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_root = Path(temporary) / "run"
            record = {
                "keyword": "酸枣仁",
                "product_id": "123",
                "product_name": "测试商品",
                "shop_name": "测试店铺",
                "region": "上海",
                "product_url": "https://item.taobao.com/item.htm?id=123",
                "original_image_count": 2,
                "ocr_image_count": 1,
                "detected_effects": ["助眠"],
                "evidence": ["帮助睡眠"],
                "risk_reason": "检测到助眠表达",
                "review_required": True,
                "crawl_status": "success",
                "errors": [],
            }
            payload = {
                "keyword": "酸枣仁",
                "search_raw_count": 46,
                "search_deduplicated_count": 46,
                "candidates": [{"product_id": "123", "rank": 1}],
            }
            snapshot = build_web_snapshot(
                run_root, payload, [record], "completed", "任务完成"
            )
            self.assertEqual(snapshot["schemaVersion"], 1)
            self.assertEqual(snapshot["task"]["stageLabel"], "任务已完成")
            self.assertEqual(snapshot["statistics"]["selectedProducts"], 1)
            self.assertEqual(snapshot["statistics"]["clueProducts"], 1)
            self.assertEqual(snapshot["products"][0]["risk"]["tone"], "warning")

    def test_existing_run_exports_relative_assets(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_root = Path(temporary) / "run"
            product_root = run_root / "products" / "123"
            image_path = product_root / "images" / "original" / "original_001.webp"
            image_path.parent.mkdir(parents=True)
            image_path.write_bytes(b"image")
            write_json(
                run_root / "search" / "search_candidates.json",
                {
                    "keyword": "酸枣仁",
                    "raw_card_count": 1,
                    "deduplicated_count": 1,
                    "candidates": [
                        {
                            "keyword": "酸枣仁",
                            "product_id": "123",
                            "product_name": "商品",
                            "product_url": "https://item.taobao.com/item.htm?id=123",
                            "rank": 1,
                        }
                    ],
                },
            )
            write_json(
                run_root / "batch_state.json",
                [{"product_id": "123", "status": "detail_collected", "errors": []}],
            )
            write_json(
                product_root / "meta.json",
                {
                    "productId": "123",
                    "productName": "商品",
                    "imageCount": 1,
                    "images": [
                        {
                            "index": 1,
                            "localPath": "images/original/original_001.webp",
                            "naturalWidth": 790,
                            "naturalHeight": 1200,
                            "ocrCandidate": True,
                        }
                    ],
                },
            )
            destination = snapshot_existing_run(
                run_root, stage="collection_completed", message="采集完成"
            )
            snapshot = read_json(destination)
            self.assertEqual(snapshot["statistics"]["detailCollectedProducts"], 1)
            self.assertEqual(
                snapshot["products"][0]["assets"]["originalImages"][0]["path"],
                "products/123/images/original/original_001.webp",
            )
            self.assertFalse(Path(snapshot["products"][0]["assets"]["originalImages"][0]["path"]).is_absolute())

    def test_existing_run_keeps_full_batch_after_single_product_resume(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_root = Path(temporary) / "run"
            write_json(
                run_root / "search" / "search_candidates.json",
                {
                    "keyword": "酸枣仁",
                    "raw_card_count": 46,
                    "deduplicated_count": 46,
                    "candidates": [{"product_id": "1", "rank": 1}],
                },
            )
            write_json(
                run_root / "batch_state.json",
                [
                    {"product_id": "1", "rank": 1, "status": "success"},
                    {"product_id": "2", "rank": 2, "status": "detail_collected"},
                ],
            )
            write_json(
                run_root / "products.json",
                {
                    "keyword": "酸枣仁",
                    "search_raw_count": 46,
                    "search_deduplicated_count": 46,
                    "products": [
                        {
                            "keyword": "酸枣仁",
                            "product_id": "1",
                            "product_name": "已分析商品",
                            "original_image_count": 2,
                            "ocr_image_count": 2,
                            "crawl_status": "success",
                            "review_required": False,
                        },
                        {
                            "keyword": "酸枣仁",
                            "product_id": "2",
                            "product_name": "待分析商品",
                            "original_image_count": 3,
                            "ocr_image_count": 0,
                            "crawl_status": "detail_collected",
                            "review_required": None,
                        },
                    ],
                },
            )

            snapshot = read_json(snapshot_existing_run(run_root))

            self.assertEqual(snapshot["statistics"]["selectedProducts"], 2)
            self.assertEqual(snapshot["statistics"]["detailCollectedProducts"], 2)
            self.assertEqual(snapshot["statistics"]["originalImages"], 5)
            self.assertEqual([item["rank"] for item in snapshot["products"]], [1, 2])


if __name__ == "__main__":
    unittest.main()
