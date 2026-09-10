import tempfile
import unittest
from pathlib import Path

from src.phase2_ocr import (
    OCRRuntime,
    OCRRuntimeCompatibilityError,
    OCRStageError,
    extract_lines,
    keyword_hits,
    run_ocr,
    select_images,
    validate_ocr_runtime_compatibility,
)
from src.runtime import read_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class _FakeNumpy:
    uint8 = object()

    @staticmethod
    def frombuffer(value, dtype):
        return value


class _FakeCv2:
    IMREAD_COLOR = 1

    @staticmethod
    def imdecode(value, mode):
        return value


class _Result:
    json = {
        "res": {
            "rec_texts": ["酸枣仁配料"],
            "rec_scores": [0.99],
            "rec_boxes": [],
            "rec_polys": [],
        }
    }


class _Engine:
    def predict(self, image):
        if image == b"fail":
            raise RuntimeError("injected image failure")
        return [_Result()]


def fake_runtime() -> OCRRuntime:
    return OCRRuntime(
        engine=_Engine(),
        cv2=_FakeCv2(),
        numpy=_FakeNumpy(),
        model_info={
            "pythonVersion": "3.10.0",
            "paddlepaddleVersion": "3.2.0",
            "paddleocrVersion": "3.7.0",
            "paddlexVersion": "3.7.2",
            "ocrVersion": "PP-OCRv6",
            "modelSource": "bos",
            "device": "cpu",
        },
    )


class PhaseTwoHelpersTest(unittest.TestCase):
    def test_real_ocr_environment_is_exactly_pinned(self) -> None:
        requirements = (PROJECT_ROOT / "requirements-ocr.txt").read_text(
            encoding="utf-8"
        )
        self.assertIn("paddlepaddle==3.2.0", requirements)
        self.assertIn("paddleocr==3.7.0", requirements)
        self.assertIn("paddlex==3.7.2", requirements)
        self.assertNotIn("paddleocr>=", requirements)

    def test_selects_only_requested_original_range(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in (
                "original_001.webp",
                "original_002.webp",
                "original_016.png",
                "original_017.png",
                "other.jpg",
            ):
                (root / name).touch()
            self.assertEqual(
                [item.name for item in select_images(root, 2, 16)],
                ["original_002.webp", "original_016.png"],
            )

    def test_extract_lines_preserves_low_confidence_in_structured_data(self) -> None:
        lines = extract_lines(
            [{"rec_texts": ["酸枣仁", "噪声"], "rec_scores": [0.98, 0.2]}],
            0.5,
        )
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0]["includedInPlainText"])
        self.assertFalse(lines[1]["includedInPlainText"])

    def test_keyword_hits(self) -> None:
        self.assertEqual(keyword_hits("配料含酸枣仁和茯苓")[:3], ["酸枣仁", "茯苓", "配料"])

    def test_pp_ocr_v6_rejects_known_incompatible_package_early(self) -> None:
        with self.assertRaisesRegex(
            OCRRuntimeCompatibilityError, "PP-OCRv6需要paddleocr>=3.7.0"
        ):
            validate_ocr_runtime_compatibility("PP-OCRv6", "3.5.0")
        with self.assertRaisesRegex(OCRRuntimeCompatibilityError, "paddlex>=3.7.2"):
            validate_ocr_runtime_compatibility(
                "PP-OCRv6", "3.7.0", "3.5.2", "3.2.0", (3, 10)
            )
        validate_ocr_runtime_compatibility(
            "PP-OCRv6", "3.7.0", "3.7.2", "3.2.0", (3, 10)
        )

    def test_no_selected_image_is_a_recorded_stage_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            product_root = Path(directory)
            with self.assertRaisesRegex(FileNotFoundError, "OCR选择规则"):
                run_ocr(product_root, product_root / "cache", runtime=fake_runtime())
            self.assertTrue((product_root / "ocr" / "run_info.json").is_file())
            self.assertEqual(
                read_json(product_root / "ocr" / "stage_error.json")["status"],
                "failed",
            )

    def test_all_failed_images_raise_after_preserving_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            product_root = Path(directory)
            image_root = product_root / "images" / "original"
            image_root.mkdir(parents=True)
            (image_root / "original_002.png").write_bytes(b"fail")

            with self.assertRaisesRegex(OCRStageError, "均未产生可用OCR结果"):
                run_ocr(product_root, product_root / "cache", runtime=fake_runtime())

            manifest = read_json(product_root / "ocr" / "manifest.json")
            self.assertEqual(manifest[0]["status"], "failed")
            self.assertTrue((product_root / "ocr" / "combined_text.txt").is_file())
            self.assertTrue((product_root / "phase2_ocr_report.md").is_file())
            self.assertEqual(
                read_json(product_root / "ocr" / "stage_error.json")["errorType"],
                "OCRStageError",
            )

    def test_partial_success_continues_and_records_locked_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            product_root = Path(directory)
            image_root = product_root / "images" / "original"
            image_root.mkdir(parents=True)
            (image_root / "original_002.png").write_bytes(b"success")
            (image_root / "original_003.png").write_bytes(b"fail")

            report = run_ocr(
                product_root,
                product_root / "cache",
                runtime=fake_runtime(),
            )

            self.assertTrue(report.is_file())
            self.assertEqual(
                [item["status"] for item in read_json(product_root / "ocr" / "manifest.json")],
                ["success", "failed"],
            )
            info = read_json(product_root / "ocr" / "run_info.json")
            self.assertEqual(
                {
                    key: info[key]
                    for key in (
                        "pythonVersion",
                        "paddlepaddleVersion",
                        "paddleocrVersion",
                        "paddlexVersion",
                        "ocrVersion",
                        "modelSource",
                        "device",
                        "scoreThreshold",
                    )
                },
                {
                    "pythonVersion": "3.10.0",
                    "paddlepaddleVersion": "3.2.0",
                    "paddleocrVersion": "3.7.0",
                    "paddlexVersion": "3.7.2",
                    "ocrVersion": "PP-OCRv6",
                    "modelSource": "bos",
                    "device": "cpu",
                    "scoreThreshold": 0.5,
                },
            )
            self.assertFalse((product_root / "ocr" / "stage_error.json").exists())


if __name__ == "__main__":
    unittest.main()

