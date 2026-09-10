import logging
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.manual_action_gate import ManualActionGate, WebManualActionAdapter
from src.phase1_experiment import (
    PhaseOneCollector,
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

    def test_web_adapter_rechecks_detail_blocker_without_terminal_input(self) -> None:
        gate = ManualActionGate()
        page = Mock()
        checks = iter(["淘宝人工验证", None])
        waiting_generations = []
        adapter = WebManualActionAdapter(
            task_id="detail-task",
            gate=gate,
            blocker_checker=lambda _page: next(checks),
            on_waiting=lambda state: waiting_generations.append(state["generation"]),
            on_resolved=lambda _state: None,
            recheck_interval=30,
        )
        with tempfile.TemporaryDirectory() as temporary:
            collector = PhaseOneCollector(
                product_url="https://item.taobao.com/item.htm?id=123",
                output_root=Path(temporary),
                profile_dir=Path(temporary) / "profile",
                logger=logging.getLogger("test.detail.manual-action"),
                manual_action_adapter=adapter,
            )
            errors = []

            def wait_for_detail() -> None:
                try:
                    collector._wait_until_unblocked(page)
                except Exception as exc:  # pragma: no cover - assertion captures it
                    errors.append(exc)

            with patch.object(collector, "_blocker", return_value="verification"):
                with patch("builtins.input") as terminal_input:
                    worker = threading.Thread(target=wait_for_detail)
                    worker.start()
                    deadline = time.monotonic() + 1
                    while gate.snapshot("detail-task")["generation"] != 1 and time.monotonic() < deadline:
                        time.sleep(0.005)
                    gate.acknowledge("detail-task", 1)
                    deadline = time.monotonic() + 1
                    while gate.snapshot("detail-task")["generation"] != 2 and time.monotonic() < deadline:
                        time.sleep(0.005)
                    self.assertTrue(worker.is_alive())
                    gate.acknowledge("detail-task", 2)
                    worker.join(1)
                    terminal_input.assert_not_called()

        self.assertFalse(worker.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(waiting_generations, [1, 2])
        self.assertEqual(gate.snapshot("detail-task")["status"], "resolved")

    def test_cli_detail_blocker_keeps_terminal_confirmation_fallback(self) -> None:
        page = Mock()
        with tempfile.TemporaryDirectory() as temporary:
            collector = PhaseOneCollector(
                product_url="https://item.taobao.com/item.htm?id=123",
                output_root=Path(temporary),
                profile_dir=Path(temporary) / "profile",
                logger=logging.getLogger("test.detail.cli-manual-action"),
            )
            with patch.object(
                collector, "_blocker", side_effect=["login", None]
            ), patch("builtins.input") as terminal_input:
                collector._wait_until_unblocked(page)

        terminal_input.assert_called_once_with()
        self.assertGreaterEqual(page.wait_for_timeout.call_count, 2)


if __name__ == "__main__":
    unittest.main()
