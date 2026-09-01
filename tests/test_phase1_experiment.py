import unittest

from src.phase1_experiment import (
    extension_for_content,
    extract_product_id,
    is_image_response,
    is_size_candidate,
    scroll_stop_reason,
)


class PhaseOneHelpersTest(unittest.TestCase):
    def test_extract_product_id(self) -> None:
        self.assertEqual(
            extract_product_id("https://detail.tmall.com/item.htm?id=606232126144&skuId=1"),
            "606232126144",
        )
        self.assertIsNone(extract_product_id("https://www.taobao.com/"))

    def test_real_response_mime_wins_over_jpg_url(self) -> None:
        self.assertEqual(
            extension_for_content("image/webp", "https://img.alicdn.com/a.jpg"),
            ".webp",
        )

    def test_image_response_detection(self) -> None:
        self.assertTrue(is_image_response("image/png", "https://example.test/a", "fetch"))
        self.assertTrue(is_image_response(None, "https://img.alicdn.com/a.jpg", "other"))
        self.assertFalse(is_image_response("text/html", "https://example.test/", "document"))

    def test_threshold_comes_from_real_experiment(self) -> None:
        self.assertTrue(is_size_candidate(790, 778))
        self.assertFalse(is_size_candidate(200, 200))

    def test_scroll_stops_at_stable_detail_boundary(self) -> None:
        state = {"y": 18200, "v": 1200, "h": 49000, "detailBottom": 19300}
        self.assertEqual(
            scroll_stop_reason(state, stable_content_rounds=2, unchanged_position_rounds=2),
            "detail_container_stable",
        )

    def test_scroll_percentage_does_not_override_known_detail_boundary(self) -> None:
        state = {"y": 34000, "v": 1200, "h": 40000, "detailBottom": 38000}
        self.assertIsNone(
            scroll_stop_reason(state, stable_content_rounds=3, unchanged_position_rounds=0)
        )

    def test_scroll_ratio_is_only_a_missing_container_fallback(self) -> None:
        state = {"y": 36000, "v": 1200, "h": 40000, "detailBottom": None}
        self.assertEqual(
            scroll_stop_reason(state, stable_content_rounds=2, unchanged_position_rounds=0),
            "fallback_page_ratio",
        )


if __name__ == "__main__":
    unittest.main()
