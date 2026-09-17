import json
import tempfile
import unittest
from pathlib import Path

from tools.benchmark_ocr_gpu import baseline_summary, profile_config


class OcrGpuBenchmarkTest(unittest.TestCase):
    def test_profile_config_uses_explicit_ppocrv6_models(self):
        self.assertEqual(
            profile_config("gpu-medium"),
            {
                "detection": "PP-OCRv6_medium_det",
                "recognition": "PP-OCRv6_medium_rec",
            },
        )
        self.assertEqual(
            profile_config("gpu-small"),
            {
                "detection": "PP-OCRv6_small_det",
                "recognition": "PP-OCRv6_small_rec",
            },
        )

    def test_baseline_summary_aggregates_existing_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            product_root = Path(temporary)
            ocr_root = product_root / "ocr"
            ocr_root.mkdir()
            (ocr_root / "manifest.json").write_text(
                json.dumps(
                    [
                        {
                            "image": "a.webp",
                            "status": "success",
                            "elapsedSeconds": 10,
                            "keywordHits": ["酸枣仁", "原料"],
                        },
                        {
                            "image": "b.webp",
                            "status": "success",
                            "elapsedSeconds": 20,
                            "keywordHits": ["酸枣仁"],
                        },
                        {
                            "image": "c.webp",
                            "status": "failed",
                            "elapsedSeconds": 5,
                            "keywordHits": [],
                        },
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            summary = baseline_summary(product_root)

            self.assertTrue(summary["available"])
            self.assertEqual(summary["imageCount"], 3)
            self.assertEqual(summary["successCount"], 2)
            self.assertEqual(summary["totalImageSeconds"], 30.0)
            self.assertEqual(summary["meanImageSeconds"], 15.0)
            self.assertEqual(summary["medianImageSeconds"], 15.0)
            self.assertEqual(summary["keywordHits"], ["原料", "酸枣仁"])


if __name__ == "__main__":
    unittest.main()
