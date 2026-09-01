import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.taobao_live import (
    BrowserSettings,
    TAOBAO_HOME_URL,
    build_search_diagnostics,
    build_selector_health,
    build_cdp_launch_args,
    deduplicate_live_cards,
    launch_persistent_context,
    open_search_from_home,
    product_platform,
    search_error_stop_reason,
)


class _FakeChromium:
    def __init__(self):
        self.options = None

    def launch_persistent_context(self, **options):
        self.options = options
        return object()


class _FakePlaywright:
    def __init__(self):
        self.chromium = _FakeChromium()


class _FakeSearchInput:
    def __init__(self):
        self.value = None
        self.key = None

    def fill(self, value):
        self.value = value

    def press(self, key):
        self.key = key


class _FakeLocator:
    def __init__(self, element=None):
        self.element = element

    def count(self):
        return 1 if self.element else 0

    def nth(self, _index):
        return self

    def is_visible(self):
        return self.element is not None

    def __getattr__(self, name):
        return getattr(self.element, name)


class _FakePage:
    def __init__(self):
        self.search_input = _FakeSearchInput()
        self.goto_calls = []
        self.load_states = []
        self.context = type("FakeContext", (), {"pages": [self]})()

    def goto(self, url, **_kwargs):
        self.goto_calls.append(url)

    def wait_for_timeout(self, _timeout):
        return None

    def wait_for_load_state(self, state, **_kwargs):
        self.load_states.append(state)

    def locator(self, selector):
        if selector == 'input[name="q"]':
            return _FakeLocator(self.search_input)
        return _FakeLocator()


class TaobaoLiveHelpersTest(unittest.TestCase):
    def test_direct_browser_is_scoped_to_launched_chrome(self):
        playwright = _FakePlaywright()
        with tempfile.TemporaryDirectory() as temp_dir:
            launch_persistent_context(
                playwright,
                BrowserSettings(
                    profile_dir=Path(temp_dir) / "profile",
                    direct_connection=True,
                ),
            )
        self.assertEqual(playwright.chromium.options["args"], ["--no-proxy-server"])
        self.assertNotIn("proxy", playwright.chromium.options)

    def test_proxy_takes_precedence_over_direct_flag(self):
        playwright = _FakePlaywright()
        with tempfile.TemporaryDirectory() as temp_dir:
            launch_persistent_context(
                playwright,
                BrowserSettings(
                    profile_dir=Path(temp_dir) / "profile",
                    proxy_server="http://127.0.0.1:7890",
                    direct_connection=True,
                ),
            )
        self.assertEqual(
            playwright.chromium.options["proxy"],
            {"server": "http://127.0.0.1:7890"},
        )
        self.assertNotIn("args", playwright.chromium.options)

    def test_home_page_search_uses_visible_input_without_preencoding(self):
        page = _FakePage()
        with patch("src.taobao_live.wait_until_unblocked") as wait_ready:
            result_page = open_search_from_home(
                page,
                keyword="酸枣仁",
                logger=logging.getLogger("test"),
                non_interactive=False,
            )
        self.assertEqual(page.goto_calls, [TAOBAO_HOME_URL])
        self.assertEqual(page.search_input.value, "酸枣仁")
        self.assertEqual(page.search_input.key, "Enter")
        self.assertEqual(wait_ready.call_count, 2)
        self.assertIs(result_page, page)

    def test_home_page_search_switches_to_new_result_tab(self):
        home_page = _FakePage()
        result_page = _FakePage()

        def open_new_tab(key):
            home_page.search_input.key = key
            home_page.context.pages.append(result_page)

        home_page.search_input.press = open_new_tab
        with patch("src.taobao_live.wait_until_unblocked"):
            selected_page = open_search_from_home(
                home_page,
                keyword="酸枣仁",
                logger=logging.getLogger("test"),
                non_interactive=False,
            )
        self.assertIs(selected_page, result_page)
        self.assertEqual(result_page.load_states, ["domcontentloaded"])

    def test_deduplicates_cards_and_fills_missing_fields(self):
        cards = deduplicate_live_cards(
            [
                {
                    "product_id": "123",
                    "source_product_url": "https://item.taobao.com/item.htm?id=123",
                    "product_name": "  酸枣仁  茶 ",
                    "shop_name": "",
                },
                {
                    "product_id": "123",
                    "source_product_url": "https://item.taobao.com/item.htm?id=123",
                    "shop_name": "测试店铺",
                },
                {"product_id": "not-an-id", "source_product_url": "https://example.com"},
            ]
        )
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["product_name"], "酸枣仁 茶")
        self.assertEqual(cards[0]["shop_name"], "测试店铺")
        self.assertEqual(cards[0]["platform"], "taobao")

    def test_platform_detection(self):
        self.assertEqual(product_platform("https://detail.tmall.com/item.htm?id=1"), "tmall")
        self.assertEqual(product_platform("https://item.taobao.com/item.htm?id=1"), "taobao")

    def test_cdp_arguments_keep_browser_security_and_do_not_add_stealth_flags(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = BrowserSettings(
                profile_dir=Path(temp_dir) / "profile",
                direct_connection=True,
            )
            args = build_cdp_launch_args(Path("chrome.exe"), settings, 9222)
        joined = " ".join(args)
        self.assertIn("--remote-debugging-address=127.0.0.1", args)
        self.assertIn("--no-proxy-server", args)
        self.assertNotIn("AutomationControlled", joined)
        self.assertNotIn("exclude-switches", joined)
        self.assertNotIn("--no-sandbox", args)

    def test_search_diagnostics_separates_candidates_from_detail_selection(self):
        candidates = [
            {
                "product_id": str(index),
                "product_name": f"商品{index}",
                "shop_name": "店铺",
                "region": "河北",
            }
            for index in range(1, 47)
        ]
        diagnostics = build_search_diagnostics(
            query="酸枣仁",
            candidate_limit=50,
            detail_limit=10,
            candidates=candidates,
            scroll_count=8,
            duration_seconds=12.3456,
            stop_reason="stagnant_no_new_products",
        )
        self.assertEqual(diagnostics["actual_unique_candidates"], 46)
        self.assertEqual(diagnostics["selected_for_detail"], 10)
        self.assertEqual(diagnostics["stop_reason"], "stagnant_no_new_products")
        self.assertEqual(diagnostics["duration_seconds"], 12.346)

    def test_selector_health_warns_on_large_title_coverage_drop(self):
        candidates = [
            {
                "product_id": str(index),
                "product_name": "有标题" if index < 5 else "",
                "shop_name": "店铺",
                "region": "河北",
            }
            for index in range(50)
        ]
        health = build_selector_health(candidates)
        self.assertEqual(health["status"], "warning")
        self.assertEqual(health["fields"]["product_name"]["present"], 5)
        self.assertIn("product_name", health["warning_fields"])

    def test_search_error_stop_reason_is_explicit(self):
        self.assertEqual(
            search_error_stop_reason(RuntimeError("需要人工操作：淘宝登录")),
            "login_required",
        )
        self.assertEqual(
            search_error_stop_reason(RuntimeError("需要人工操作：淘宝人工验证")),
            "manual_verification_required",
        )
        self.assertEqual(
            search_error_stop_reason(RuntimeError("淘宝首页未找到可见搜索框")),
            "page_structure_unexpected",
        )


if __name__ == "__main__":
    unittest.main()
