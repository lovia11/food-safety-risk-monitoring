"""Standalone Playwright search support for real Taobao result pages.

The module uses a visible, persistent Chrome profile and pauses for manual
login/verification.  It does not solve CAPTCHAs or bypass platform controls.
"""

from __future__ import annotations

import csv
import logging
import os
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from src.runtime import extract_product_id, iso_now, write_json


SEARCH_URL = "https://s.taobao.com/search?q={keyword}"
TAOBAO_HOME_URL = "https://www.taobao.com/"
SEARCH_CARD_SELECTOR = 'a[id^="item_id_"]'
SELECTOR_WARNING_COVERAGE = 0.8


@dataclass(frozen=True)
class BrowserSettings:
    profile_dir: Path
    channel: str = "chrome"
    mode: str = "cdp"
    executable_path: Path | None = None
    cdp_port: int = 9222
    headless: bool = False
    non_interactive: bool = False
    proxy_server: str | None = None
    direct_connection: bool = False
    slow_mo_ms: int = 0


@dataclass
class BrowserSession:
    context: Any
    browser: Any | None = None
    process: subprocess.Popen[Any] | None = None
    logger: logging.Logger | None = None

    def close(self) -> None:
        """Best-effort cleanup that never hides the pipeline's primary error."""

        try:
            if self.browser is not None:
                self.browser.close()
            else:
                self.context.close()
        except Exception as exc:
            if self.logger:
                self.logger.debug("关闭浏览器连接时忽略次生异常：%s", exc)
        if self.process is None or self.process.poll() is not None:
            return
        try:
            self.process.terminate()
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)
        except Exception as exc:
            if self.logger:
                self.logger.debug("结束项目浏览器进程时忽略次生异常：%s", exc)


def launch_persistent_context(playwright: Any, settings: BrowserSettings) -> Any:
    settings.profile_dir.mkdir(parents=True, exist_ok=True)
    options: dict[str, Any] = {
        "user_data_dir": str(settings.profile_dir.resolve()),
        "channel": settings.channel,
        "headless": settings.headless,
        "no_viewport": not settings.headless,
        "accept_downloads": True,
        "slow_mo": settings.slow_mo_ms,
    }
    if settings.proxy_server:
        options["proxy"] = {"server": settings.proxy_server}
    elif settings.direct_connection:
        # Keep the project's Taobao browser off the Windows system proxy without
        # changing the proxy used by Codex or any other application.
        options["args"] = ["--no-proxy-server"]
    return playwright.chromium.launch_persistent_context(**options)


def browser_candidates(channel: str) -> list[Path]:
    program_files = os.environ.get("PROGRAMFILES", r"C:\Program Files")
    program_files_x86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    chrome = [
        Path(program_files) / "Google/Chrome/Application/chrome.exe",
        Path(program_files_x86) / "Google/Chrome/Application/chrome.exe",
    ]
    if local_app_data:
        chrome.append(Path(local_app_data) / "Google/Chrome/Application/chrome.exe")
    edge = [
        Path(program_files) / "Microsoft/Edge/Application/msedge.exe",
        Path(program_files_x86) / "Microsoft/Edge/Application/msedge.exe",
    ]
    return edge + chrome if channel.lower() in {"msedge", "edge"} else chrome + edge


def resolve_browser_executable(settings: BrowserSettings) -> Path:
    if settings.executable_path is not None:
        path = settings.executable_path.expanduser().resolve()
        if not path.is_file():
            raise RuntimeError(f"浏览器程序不存在：{path}")
        return path
    for path in browser_candidates(settings.channel):
        if path.is_file():
            return path.resolve()
    raise RuntimeError("未找到Chrome或Edge；可使用--browser-executable指定浏览器程序")


def find_available_port(start_port: int) -> int:
    if not 1 <= start_port <= 65535:
        raise ValueError("cdp_port必须在1到65535之间")
    for port in range(start_port, min(start_port + 100, 65536)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"未找到可用调试端口：{start_port}-{min(start_port + 99, 65535)}")


def build_cdp_launch_args(
    executable: Path,
    settings: BrowserSettings,
    port: int,
) -> list[str]:
    args = [
        str(executable),
        f"--remote-debugging-port={port}",
        "--remote-debugging-address=127.0.0.1",
        f"--user-data-dir={settings.profile_dir.resolve()}",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    if settings.headless:
        args.append("--headless=new")
    else:
        args.append("--start-maximized")
    if settings.proxy_server:
        args.append(f"--proxy-server={settings.proxy_server}")
    elif settings.direct_connection:
        args.append("--no-proxy-server")
    args.append("about:blank")
    return args


def wait_for_debug_port(port: int, process: subprocess.Popen[Any], timeout: float = 20) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"浏览器启动后立即退出，exit_code={process.returncode}")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.25)
    raise RuntimeError(f"浏览器调试端口{port}在{timeout:g}秒内未就绪")


def launch_cdp_session(
    playwright: Any,
    settings: BrowserSettings,
    logger: logging.Logger | None = None,
) -> BrowserSession:
    settings.profile_dir.mkdir(parents=True, exist_ok=True)
    executable = resolve_browser_executable(settings)
    port = find_available_port(settings.cdp_port)
    args = build_cdp_launch_args(executable, settings, port)
    creation_flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    if logger:
        logger.info("以CDP模式启动%s，调试端口=%s", executable.name, port)
    process = subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags,
    )
    try:
        wait_for_debug_port(port, process)
        browser = playwright.chromium.connect_over_cdp(
            f"http://127.0.0.1:{port}",
            timeout=30_000,
        )
        if not browser.contexts:
            raise RuntimeError("CDP浏览器未提供默认上下文")
        return BrowserSession(
            context=browser.contexts[0],
            browser=browser,
            process=process,
            logger=logger,
        )
    except Exception:
        if process.poll() is None:
            process.terminate()
        raise


def launch_browser_session(
    playwright: Any,
    settings: BrowserSettings,
    logger: logging.Logger | None = None,
) -> BrowserSession:
    if settings.mode == "persistent":
        return BrowserSession(
            context=launch_persistent_context(playwright, settings),
            logger=logger,
        )
    if settings.mode == "cdp":
        return launch_cdp_session(playwright, settings, logger=logger)
    raise ValueError(f"不支持的browser mode：{settings.mode}")


def blocker_reason(page: Any) -> str | None:
    try:
        verification_locators = page.locator(
            'iframe[src*="captcha"], iframe[src*="punish"], iframe[src*="x5secdata"], '
            'iframe[src*="verify"], [class*="captcha"], [id*="captcha"]'
        )
        for index in range(min(verification_locators.count(), 12)):
            if verification_locators.nth(index).is_visible():
                return "淘宝人工验证"
        login_locators = page.locator(
            'iframe[src*="login.taobao.com"], input[type="password"], input[placeholder*="账号名"], '
            'input[placeholder*="手机号"], button:has-text("登录")'
        )
        for index in range(min(login_locators.count(), 12)):
            if login_locators.nth(index).is_visible():
                return "淘宝登录"
        url = page.url.lower()
        title = page.title().lower()
        body_text = page.locator("body").inner_text(timeout=5_000).lower()
        text = body_text[:5_000] + "\n" + body_text[-5_000:]
    except Exception:
        return "页面尚未正常加载"
    haystack = "\n".join((url, title, text))
    verification_signals = (
        "captcha",
        "punish",
        "x5secdata",
        "验证码",
        "验证失败",
        "异常访问",
        "滑块",
        "安全验证",
    )
    login_signals = (
        "login.taobao.com",
        "账号登录",
        "扫码登录",
        "密码登录",
        "短信登录",
        "请重新登录",
        "请输入登录密码",
        "账号名/邮箱/手机号",
    )
    if any(signal in haystack for signal in verification_signals):
        return "淘宝人工验证"
    if any(signal in haystack for signal in login_signals):
        return "淘宝登录"
    return None


def wait_for_manual_action(
    page: Any,
    reason: str,
    logger: logging.Logger,
    non_interactive: bool,
) -> None:
    if non_interactive:
        raise RuntimeError(f"需要人工操作：{reason}")
    logger.warning(
        "检测到%s。请在项目打开的Chrome中人工完成，完成后回到终端按Enter；程序不会绕过验证。",
        reason,
    )
    input()
    try:
        page.wait_for_timeout(1_000)
    except Exception as exc:
        raise RuntimeError(
            "项目浏览器已被关闭，本次采集已安全停止；请勿把该次生错误误认为验证码根因"
        ) from None


def wait_until_unblocked(
    page: Any,
    logger: logging.Logger,
    non_interactive: bool,
    max_manual_attempts: int = 1,
    manual_action_adapter: Any | None = None,
) -> None:
    """Pause for permitted manual login/CAPTCHA work and verify the result."""

    for attempt in range(1, max_manual_attempts + 1):
        reason = blocker_reason(page)
        if not reason:
            return
        logger.warning("页面阻塞状态：%s（人工处理 %s/%s）", reason, attempt, max_manual_attempts)
        if manual_action_adapter is not None:
            manual_action_adapter.wait(page, reason, logger)
            return
        wait_for_manual_action(page, reason, logger, non_interactive)
        page.wait_for_timeout(1_500)
    remaining = blocker_reason(page)
    if remaining:
        raise RuntimeError(
            f"人工处理后页面仍被{remaining}阻塞；本次记为平台风控，程序未尝试绕过验证"
        )


def first_visible(page: Any, selectors: tuple[str, ...]) -> Any | None:
    for selector in selectors:
        locator = page.locator(selector)
        for index in range(min(locator.count(), 8)):
            candidate = locator.nth(index)
            if candidate.is_visible():
                return candidate
    return None


def open_search_from_home(
    page: Any,
    keyword: str,
    logger: logging.Logger,
    non_interactive: bool,
    manual_action_adapter: Any | None = None,
) -> Any:
    """Use Taobao's visible home-page search flow instead of a deep-link request."""

    logger.info("先打开淘宝首页建立正常页面会话")
    page.goto(TAOBAO_HOME_URL, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(2_000)
    wait_until_unblocked(
        page, logger, non_interactive,
        manual_action_adapter=manual_action_adapter,
    )
    search_input = first_visible(
        page,
        (
            'input[name="q"]',
            "#q",
            'input[placeholder*="搜索"]',
            'input[aria-label*="搜索"]',
        ),
    )
    if search_input is None:
        raise RuntimeError("淘宝首页未找到可见搜索框，已停止而未改走高风险接口请求")
    pages_before = list(page.context.pages)
    search_input.fill(keyword.strip())
    search_input.press("Enter")
    page.wait_for_timeout(1_000)
    new_pages = [candidate for candidate in page.context.pages if candidate not in pages_before]
    search_page = new_pages[-1] if new_pages else page
    if search_page is not page:
        logger.info("淘宝搜索在新标签页打开，采集器已自动切换")
    search_page.wait_for_load_state("domcontentloaded", timeout=60_000)
    search_page.wait_for_timeout(3_000)
    wait_until_unblocked(
        search_page, logger, non_interactive,
        manual_action_adapter=manual_action_adapter,
    )
    return search_page


def product_platform(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host == "detail.tmall.com":
        return "tmall"
    if host == "item.taobao.com":
        return "taobao"
    if host.endswith("simba.taobao.com"):
        return "ad_redirect"
    return "unknown"


def normalize_live_card(card: dict[str, Any]) -> dict[str, Any] | None:
    raw_url = str(card.get("source_product_url") or card.get("product_url") or "").strip()
    product_id = str(card.get("product_id") or extract_product_id(raw_url) or "").strip()
    if not product_id.isdigit() or not raw_url:
        return None
    return {
        "product_id": product_id,
        "source_product_url": raw_url,
        "product_url": raw_url,
        "product_name": " ".join(str(card.get("product_name") or "").split()),
        "shop_name": " ".join(str(card.get("shop_name") or "").split()),
        "region": " ".join(str(card.get("region") or "").split()),
        "sales_text": " ".join(str(card.get("sales_text") or "").split()),
        "price_text": " ".join(str(card.get("price_text") or "").split()),
        "snapshot_image_path": str(card.get("snapshot_image_path") or ""),
        "platform": product_platform(raw_url),
    }


def deduplicate_live_cards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    for raw in cards:
        card = normalize_live_card(raw)
        if not card:
            continue
        product_id = card["product_id"]
        if product_id not in by_id:
            by_id[product_id] = card
            result.append(card)
            continue
        existing = by_id[product_id]
        for field in (
            "product_name",
            "shop_name",
            "region",
            "sales_text",
            "price_text",
            "snapshot_image_path",
        ):
            if not existing.get(field) and card.get(field):
                existing[field] = card[field]
    return result


LIVE_CARD_SCRIPT = r"""
() => Array.from(document.querySelectorAll('a[id^="item_id_"]')).map((card) => {
  const textOf = (selector) => {
    const el = card.querySelector(selector);
    return (el?.innerText || el?.textContent || '').trim();
  };
  const titleEl = card.querySelector('[class*="title--"]');
  const imageEl = card.querySelector('img[class*="mainPic--"], img[class*="mainImg--"], img');
  const priceInt = textOf('[class*="priceInt--"]');
  const priceFloat = textOf('[class*="priceFloat--"]');
  return {
    product_id: (card.id || '').replace(/^item_id_/, ''),
    source_product_url: card.href || card.getAttribute('href') || '',
    product_name: (titleEl?.getAttribute('title') || titleEl?.innerText || '').trim(),
    shop_name: textOf('[class*="shopNameText--"]'),
    region: textOf('[class*="procity--"]'),
    sales_text: textOf('[class*="realSales--"]'),
    price_text: priceInt ? `${priceInt}${priceFloat}` : '',
    snapshot_image_path: imageEl?.currentSrc || imageEl?.src || ''
  };
})
"""


def extract_live_cards(page: Any) -> list[dict[str, Any]]:
    cards = page.evaluate(LIVE_CARD_SCRIPT)
    return deduplicate_live_cards(cards if isinstance(cards, list) else [])


SEARCH_CSV_FIELDS = [
    "keyword",
    "rank",
    "product_name",
    "product_url",
    "product_id",
    "shop_name",
    "region",
    "crawl_time",
    "platform",
    "price_text",
    "sales_text",
]


def write_search_csv(path: Path, candidates: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SEARCH_CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(candidates)


def build_selector_health(
    candidates: list[dict[str, Any]],
    warning_coverage: float = SELECTOR_WARNING_COVERAGE,
) -> dict[str, Any]:
    """Summarize simple field coverage without guessing replacement selectors."""

    total = len(candidates)
    fields: dict[str, dict[str, Any]] = {}
    warning_fields: list[str] = []
    for field in ("product_id", "product_name", "shop_name", "region"):
        present = sum(bool(item.get(field)) for item in candidates)
        coverage = round(present / total, 4) if total else 0.0
        fields[field] = {
            "present": present,
            "missing": total - present,
            "coverage": coverage,
        }
        if total and coverage < warning_coverage:
            warning_fields.append(field)
    return {
        "total_candidates": total,
        "warning_coverage_threshold": warning_coverage,
        "status": "warning" if warning_fields or not total else "healthy",
        "warning_fields": warning_fields,
        "fields": fields,
    }


def log_selector_health(logger: logging.Logger, health: dict[str, Any]) -> None:
    for field in health.get("warning_fields") or []:
        values = health["fields"][field]
        logger.warning(
            "Selector Health异常：字段%s覆盖率%.1f%%（%s/%s），可能存在淘宝页面结构变化",
            field,
            float(values["coverage"]) * 100,
            values["present"],
            health["total_candidates"],
        )


def search_error_stop_reason(error: Exception) -> str:
    message = str(error)
    if "淘宝登录" in message:
        return "login_required"
    if "人工验证" in message or "验证码" in message or "平台风控" in message:
        return "manual_verification_required"
    if "未找到可见搜索框" in message or "未提取到" in message:
        return "page_structure_unexpected"
    return "error"


def build_search_diagnostics(
    query: str,
    candidate_limit: int,
    detail_limit: int,
    candidates: list[dict[str, Any]],
    scroll_count: int,
    duration_seconds: float,
    stop_reason: str,
) -> dict[str, Any]:
    missing = {
        field: sum(not item.get(field) for item in candidates)
        for field in ("product_name", "shop_name", "region")
    }
    return {
        "query": query.strip(),
        "requested_candidate_limit": candidate_limit,
        "actual_unique_candidates": len(candidates),
        "selected_for_detail": min(len(candidates), detail_limit),
        "scroll_count": scroll_count,
        "duration_seconds": round(max(duration_seconds, 0.0), 3),
        "stop_reason": stop_reason,
        "missing_fields": missing,
        "selector_health": build_selector_health(candidates),
    }


class LiveSearchCollector:
    def __init__(
        self,
        context: Any,
        run_root: Path,
        logger: logging.Logger,
        non_interactive: bool = False,
        scroll_step: int = 900,
        max_scrolls: int = 30,
        wait_ms: int = 900,
        manual_action_adapter: Any | None = None,
    ) -> None:
        self.context = context
        self.run_root = run_root
        self.logger = logger
        self.non_interactive = non_interactive
        self.scroll_step = scroll_step
        self.max_scrolls = max_scrolls
        self.wait_ms = wait_ms
        self.manual_action_adapter = manual_action_adapter

    def collect(
        self,
        keyword: str,
        candidate_limit: int,
        detail_limit: int | None = None,
    ) -> dict[str, Any]:
        if not keyword.strip():
            raise ValueError("搜索关键词不能为空")
        if candidate_limit < 1:
            raise ValueError("candidate_limit必须大于0")
        resolved_detail_limit = candidate_limit if detail_limit is None else detail_limit
        if resolved_detail_limit < 1:
            raise ValueError("detail_limit必须大于0")
        search_root = self.run_root / "search"
        search_root.mkdir(parents=True, exist_ok=True)
        page = self.context.new_page()
        started_at = iso_now()
        started_clock = time.monotonic()
        collected: list[dict[str, Any]] = []
        scroll_count = 0
        stop_reason = "error"
        try:
            self.logger.info(
                "打开淘宝搜索页：keyword=%s, candidate_limit=%s, detail_limit=%s",
                keyword,
                candidate_limit,
                resolved_detail_limit,
            )
            page = open_search_from_home(
                page,
                keyword=keyword,
                logger=self.logger,
                non_interactive=self.non_interactive,
                manual_action_adapter=self.manual_action_adapter,
            )

            by_id: dict[str, dict[str, Any]] = {}
            stagnant = 0
            scroll_states: list[dict[str, Any]] = []
            for scroll_index in range(self.max_scrolls + 1):
                current = extract_live_cards(page)
                before = len(by_id)
                for item in current:
                    by_id.setdefault(item["product_id"], item)
                collected = list(by_id.values())
                state = page.evaluate(
                    "() => ({y: Math.round(scrollY), height: document.documentElement.scrollHeight, viewport: innerHeight})"
                )
                state.update(
                    {
                        "scroll_index": scroll_index,
                        "visible_cards": len(current),
                        "unique_cards": len(collected),
                    }
                )
                scroll_states.append(state)
                self.logger.info(
                    "搜索滚动 %s/%s：当前可见%s，累计去重%s",
                    scroll_index,
                    self.max_scrolls,
                    len(current),
                    len(collected),
                )
                if len(collected) >= candidate_limit:
                    stop_reason = "candidate_limit_reached"
                    break
                stagnant = stagnant + 1 if len(by_id) == before else 0
                if stagnant >= 5:
                    stop_reason = "stagnant_no_new_products"
                    break
                if scroll_index >= self.max_scrolls:
                    stop_reason = "max_scrolls_reached"
                    break
                page.mouse.wheel(0, self.scroll_step)
                scroll_count += 1
                page.wait_for_timeout(self.wait_ms)

            page.screenshot(path=search_root / "search_results.png", full_page=True)
            (search_root / "search_page.html").write_text(page.content(), encoding="utf-8")
            write_json(search_root / "scroll_states.json", scroll_states)
            if not collected:
                stop_reason = "page_structure_unexpected"
                raise RuntimeError(
                    f"实时搜索页未提取到{SEARCH_CARD_SELECTOR}；请查看search/search_results.png和search/search_page.html"
                )

            selected = collected[:candidate_limit]
            crawl_time = iso_now()
            for rank, candidate in enumerate(selected, start=1):
                candidate.update(
                    {
                        "keyword": keyword.strip(),
                        "rank": rank,
                        "crawl_time": crawl_time,
                    }
                )
            diagnostics = build_search_diagnostics(
                query=keyword,
                candidate_limit=candidate_limit,
                detail_limit=resolved_detail_limit,
                candidates=selected,
                scroll_count=scroll_count,
                duration_seconds=time.monotonic() - started_clock,
                stop_reason=stop_reason,
            )
            missing = diagnostics["missing_fields"]
            log_selector_health(self.logger, diagnostics["selector_health"])
            payload = {
                "run_id": self.run_root.name,
                "phase": "standalone_live_search",
                "keyword": keyword.strip(),
                "collection_method": "standalone_python_playwright_live_search",
                "source_page_url": page.url,
                "started_at": started_at,
                "completed_at": iso_now(),
                "raw_card_count": len(collected),
                "deduplicated_count": len(collected),
                "selected_count": len(selected),
                "limit": candidate_limit,
                "candidate_limit": candidate_limit,
                "detail_limit": resolved_detail_limit,
                "selected_for_detail": diagnostics["selected_for_detail"],
                "search_stop_reason": stop_reason,
                "missing_field_counts": missing,
                "selector_health": diagnostics["selector_health"],
                "selector_evidence": {
                    "card": SEARCH_CARD_SELECTOR,
                    "title": '[class*="title--"]',
                    "shop": '[class*="shopNameText--"]',
                    "region": '[class*="procity--"]',
                },
                "candidates": selected,
            }
            write_json(search_root / "search_candidates.json", payload)
            write_json(search_root / "search_diagnostics.json", diagnostics)
            write_search_csv(search_root / "search_candidates.csv", selected)
            self.logger.info(
                "实时搜索完成：累计去重%s，候选%s，进入详情%s，停止原因=%s",
                len(collected),
                len(selected),
                diagnostics["selected_for_detail"],
                stop_reason,
            )
            return payload
        except Exception as exc:
            failure_reason = (
                stop_reason if stop_reason != "error" else search_error_stop_reason(exc)
            )
            partial_candidates = collected[:candidate_limit]
            diagnostics = build_search_diagnostics(
                query=keyword,
                candidate_limit=candidate_limit,
                detail_limit=resolved_detail_limit,
                candidates=partial_candidates,
                scroll_count=scroll_count,
                duration_seconds=time.monotonic() - started_clock,
                stop_reason=failure_reason,
            )
            diagnostics["error_type"] = type(exc).__name__
            diagnostics["error_message"] = str(exc)
            write_json(search_root / "search_diagnostics.json", diagnostics)
            self.logger.error(
                "搜索阶段停止：stop_reason=%s, error=%s: %s",
                failure_reason,
                type(exc).__name__,
                exc,
            )
            try:
                page.screenshot(path=search_root / "search_error.png", full_page=True)
                (search_root / "search_error.html").write_text(page.content(), encoding="utf-8")
            except Exception:
                pass
            raise
        finally:
            if not page.is_closed():
                page.close()
