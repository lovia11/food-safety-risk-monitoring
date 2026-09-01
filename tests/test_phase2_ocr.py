import tempfile
import unittest
from pathlib import Path

from src.phase2_ocr import extract_lines, keyword_hits, select_images


class PhaseTwoHelpersTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()

