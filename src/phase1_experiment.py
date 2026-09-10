"""Phase 1: compare DOM, network-resource, and screenshot collection.

This module intentionally does not automate CAPTCHA solving, fingerprint
spoofing, proxy rotation, or any other platform-control bypass.  It launches a
visible Chrome profile and pauses for manual intervention when a login or
verification page is detected.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import shutil
import sys
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse


IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
IMAGE_URL_RE = re.compile(r"\.(?:jpe?g|png|webp)(?:\?|$)", re.IGNORECASE)
TAOBAO_IMAGE_HOST_RE = re.compile(r"(?:alicdn|tbcdn|taobao|tmall)", re.IGNORECASE)


def iso_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def extract_product_id(url: str) -> str | None:
    values = parse_qs(urlparse(url).query).get("id")
    if values and values[0].isdigit():
        return values[0]
    match = re.search(r"(?:^|[?&])id=(\d+)", url)
    return match.group(1) if match else None


def normalize_content_type(value: str | None) -> str | None:
    if not value:
        return None
    return value.split(";", 1)[0].strip().lower() or None


def extension_for_content(content_type: str | None, url: str = "") -> str:
    content_type = normalize_content_type(content_type)
    if content_type == "image/webp":
        return ".webp"
    if content_type == "image/png":
        return ".png"
    if content_type == "image/jpeg":
        return ".jpg"
    suffix = Path(urlparse(url).path).suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".webp"} else ".bin"


def is_image_response(content_type: str | None, url: str, resource_type: str) -> bool:
    normalized = normalize_content_type(content_type)
    return (
        normalized in IMAGE_CONTENT_TYPES
        or resource_type == "image"
        or bool(IMAGE_URL_RE.search(url))
        or bool(TAOBAO_IMAGE_HOST_RE.search(url))
    )


def is_size_candidate(width: int, height: int, minimum: int = 700) -> bool:
    """Threshold derived from the 2026-08-17 real-item experiment."""
    return width >= minimum and height >= minimum


def scroll_stop_reason(
    state: dict[str, Any],
    stable_content_rounds: int,
    unchanged_position_rounds: int,
    fallback_ratio: float = 0.92,
) -> str | None:
    """Return a semantic stop reason for detail-page scrolling.

    The detail container is authoritative.  Page percentage is intentionally
    only a fallback because recommendation blocks make Taobao page heights vary
    substantially between products.
    """

    viewport_bottom = int(state.get("y") or 0) + int(state.get("v") or 0)
    detail_bottom = state.get("detailBottom")
    if (
        detail_bottom is not None
        and viewport_bottom >= int(detail_bottom) - 80
        and stable_content_rounds >= 2
    ):
        return "detail_container_stable"

    recommendation_top = state.get("recommendationTop")
    if (
        detail_bottom is None
        and recommendation_top is not None
        and viewport_bottom >= int(recommendation_top) - 80
        and stable_content_rounds >= 1
    ):
        return "recommendation_boundary"

    page_height = max(int(state.get("h") or 0), 1)
    at_page_bottom = viewport_bottom >= page_height - 80
    if at_page_bottom and stable_content_rounds >= 2:
        return "page_bottom_stable"

    if (
        detail_bottom is None
        and viewport_bottom / page_height >= fallback_ratio
        and stable_content_rounds >= 2
    ):
        return "fallback_page_ratio"

    if unchanged_position_rounds >= 3:
        return "scroll_position_unchanged"
    return None


def load_image_info(data: bytes) -> tuple[int | None, int | None, str | None]:
    try:
        from PIL import Image

        with Image.open(BytesIO(data)) as image:
            width, height = image.size
            return width, height, image.format
    except Exception:
        return None, None, None


def json_dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


@dataclass
class ExperimentPaths:
    run_root: Path
    product_root: Path
    page: Path
    network: Path
    original: Path
    manifests: Path

    @classmethod
    def create(
        cls,
        output_root: Path,
        product_id: str,
        run_root: Path | None = None,
    ) -> "ExperimentPaths":
        if run_root is None:
            run_id = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
            run_root = output_root / run_id
        product_root = run_root / "products" / product_id
        result = cls(
            run_root=run_root,
            product_root=product_root,
            page=product_root / "page",
            network=product_root / "images" / "network",
            original=product_root / "images" / "original",
            manifests=product_root / "manifests",
        )
        for directory in (
            result.page,
            result.network,
            result.original,
            result.manifests,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        return result


class PhaseOneCollector:
    def __init__(
        self,
        product_url: str,
        output_root: Path,
        profile_dir: Path,
        channel: str = "chrome",
        scroll_step: int = 900,
        max_scrolls: int = 50,
        non_interactive: bool = False,
        run_root: Path | None = None,
        candidate: dict[str, Any] | None = None,
        logger: logging.Logger | None = None,
        manual_action_adapter: Any | None = None,
    ) -> None:
        product_id = extract_product_id(product_url) or "unknown_product"
        self.product_url = product_url
        self.product_id = product_id
        self.paths = ExperimentPaths.create(output_root, product_id, run_root=run_root)
        self.profile_dir = profile_dir
        self.channel = channel
        self.scroll_step = scroll_step
        self.max_scrolls = max_scrolls
        self.non_interactive = non_interactive
        self.candidate = candidate or {}
        self.logger = logger
        self.manual_action_adapter = manual_action_adapter
        self.network_records: list[dict[str, Any]] = []
        self._network_by_url: dict[str, list[dict[str, Any]]] = {}
        self._network_lock = threading.Lock()
        self._response_counter = 0

    def log(self, message: str) -> None:
        if self.logger:
            self.logger.info(message)
        else:
            print(f"[{datetime.now().astimezone():%H:%M:%S}] {message}", flush=True)

    def _record_response(self, response: Any) -> None:
        resource_type = response.request.resource_type
        try:
            headers = response.all_headers()
        except Exception:
            headers = dict(response.headers)
        content_type = normalize_content_type(headers.get("content-type"))
        if not is_image_response(content_type, response.url, resource_type):
            return

        with self._network_lock:
            self._response_counter += 1
            sequence = self._response_counter

        record: dict[str, Any] = {
            "sequence": sequence,
            "url": response.url,
            "status": response.status,
            "contentType": content_type,
            "contentLengthHeader": headers.get("content-length"),
            "resourceType": resource_type,
            "sourcePage": response.frame.url if response.frame else None,
            "capturedAt": iso_now(),
            "fromServiceWorker": getattr(response, "from_service_worker", False),
            "savedPath": None,
            "byteLength": None,
            "sha256": None,
            "error": None,
        }
        try:
            body = response.body()
            if body:
                digest = hashlib.sha256(body).hexdigest()
                suffix = extension_for_content(content_type, response.url)
                destination = self.paths.network / f"network_{sequence:03d}_{digest[:12]}{suffix}"
                destination.write_bytes(body)
                record.update(
                    {
                        "savedPath": destination.relative_to(self.paths.product_root).as_posix(),
                        "byteLength": len(body),
                        "sha256": digest,
                    }
                )
        except Exception as exc:  # response bodies can be unavailable from cache
            record["error"] = f"{type(exc).__name__}: {exc}"

        with self._network_lock:
            self.network_records.append(record)
            self._network_by_url.setdefault(response.url, []).append(record)

    @staticmethod
    def _blocker(page: Any) -> str | None:
        try:
            verification = page.locator(
                'iframe[src*="captcha"], iframe[src*="punish"], '
                'iframe[src*="x5secdata"], iframe[src*="verify"], '
                '[class*="captcha"], [id*="captcha"]'
            )
            for index in range(min(verification.count(), 12)):
                if verification.nth(index).is_visible():
                    return "verification"
            login = page.locator(
                'iframe[src*="login.taobao.com"], input[type="password"], '
                'input[placeholder*="账号名"], input[placeholder*="手机号"]'
            )
            for index in range(min(login.count(), 12)):
                if login.nth(index).is_visible():
                    return "login"
            url = page.url.lower()
            title = page.title().lower()
            text = page.locator("body").inner_text(timeout=5_000)[:8_000].lower()
        except Exception:
            return "page_not_ready"
        signals = {
            "login": ("login", "登录", "账号登录", "扫码登录"),
            "verification": (
                "captcha",
                "punish",
                "x5secdata",
                "验证码",
                "验证失败",
                "异常访问",
                "滑块",
            ),
        }
        haystack = "\n".join((url, title, text))
        for name, needles in signals.items():
            if any(needle in haystack for needle in needles):
                return name
        return None

    def _wait_for_manual_action(self, page: Any, reason: str) -> None:
        if self.manual_action_adapter is not None:
            public_reason = {
                "login": "淘宝登录",
                "verification": "淘宝人工验证",
                "page_not_ready": "淘宝页面尚未就绪",
            }.get(reason, reason)
            self.manual_action_adapter.wait(
                page,
                public_reason,
                self.logger or logging.getLogger(__name__),
            )
            return
        if self.non_interactive:
            raise RuntimeError(f"manual action required: {reason}")
        self.log(
            f"检测到 {reason}。请在可见 Chrome 中人工完成登录/验证，"
            "不要关闭窗口；完成后回到终端按 Enter。"
        )
        input()
        page.wait_for_timeout(1_000)

    def _wait_until_unblocked(self, page: Any, max_manual_attempts: int = 1) -> None:
        for _ in range(max_manual_attempts):
            blocker = self._blocker(page)
            if not blocker:
                return
            self._wait_for_manual_action(page, blocker)
            if self.manual_action_adapter is not None:
                return
            page.wait_for_timeout(1_500)
        blocker = self._blocker(page)
        if blocker:
            raise RuntimeError(
                f"page remains blocked by {blocker}; collector did not bypass platform controls"
            )

    @staticmethod
    def _click_detail_tab(page: Any) -> dict[str, Any]:
        candidates: list[tuple[str, Any]] = []
        title_tabs = page.locator("#titleTabs")
        if title_tabs.count():
            candidates.append(("#titleTabs text=图文详情", title_tabs.get_by_text("图文详情", exact=True)))
        candidates.append(("text=图文详情", page.get_by_text("图文详情", exact=True)))

        for label, locator in candidates:
            for index in range(locator.count()):
                item = locator.nth(index)
                try:
                    if item.is_visible():
                        box = item.bounding_box()
                        item.click(timeout=8_000)
                        page.wait_for_timeout(800)
                        return {"strategy": label, "index": index, "box": box}
                except Exception:
                    continue
        detail = page.locator("#imageTextInfo-container")
        if detail.count():
            return {
                "strategy": "#imageTextInfo-container already present",
                "index": None,
                "box": detail.first.bounding_box(),
            }
        raise RuntimeError("未找到可点击的‘图文详情’入口；请检查 manifests/dom_probe.json")

    @staticmethod
    def _extract_dom(page: Any) -> dict[str, Any]:
        return page.evaluate(
            """
            () => {
              const cssPath = (el) => {
                const parts = [];
                let cur = el;
                while (cur && cur.nodeType === 1 && parts.length < 10) {
                  let part = cur.tagName.toLowerCase();
                  if (cur.id) {
                    part += '#' + CSS.escape(cur.id);
                    parts.unshift(part);
                    break;
                  }
                  const classes = Array.from(cur.classList || []).filter(Boolean).slice(0, 3);
                  if (classes.length) part += '.' + classes.map(x => CSS.escape(x)).join('.');
                  const parent = cur.parentElement;
                  if (parent) {
                    const peers = Array.from(parent.children).filter(x => x.tagName === cur.tagName);
                    if (peers.length > 1) part += `:nth-of-type(${peers.indexOf(cur) + 1})`;
                  }
                  parts.unshift(part);
                  cur = parent;
                }
                return parts.join(' > ');
              };

              const headings = Array.from(document.querySelectorAll('body *'))
                .filter(el => (el.innerText || '').trim() === '图文详情');
              const heading = headings.find(el => el.closest('#titleTabs') == null && el.tagName === 'P')
                || headings.find(el => el.closest('#titleTabs') == null);
              const detail = document.querySelector('#imageTextInfo-container')
                || heading?.parentElement?.querySelector('div');

              const images = Array.from(document.images).map((img, index) => {
                const box = img.getBoundingClientRect();
                return {
                  index,
                  src: img.getAttribute('src'),
                  currentSrc: img.currentSrc,
                  srcset: img.getAttribute('srcset'),
                  dataSrc: img.getAttribute('data-src'),
                  attributes: Object.fromEntries(Array.from(img.attributes).map(a => [a.name, a.value])),
                  naturalWidth: img.naturalWidth,
                  naturalHeight: img.naturalHeight,
                  renderedWidth: Math.round(box.width),
                  renderedHeight: Math.round(box.height),
                  documentTop: Math.round(box.top + scrollY),
                  domPath: cssPath(img),
                  inDetailContainer: Boolean(detail && detail.contains(img)),
                  enclosingLink: img.closest('a')?.href || null,
                  alt: img.alt || ''
                };
              });

              const backgrounds = Array.from(document.querySelectorAll('body *')).flatMap((el) => {
                const value = getComputedStyle(el).backgroundImage;
                if (!value || value === 'none' || !value.includes('url(')) return [];
                const box = el.getBoundingClientRect();
                return [{
                  backgroundImage: value,
                  renderedWidth: Math.round(box.width),
                  renderedHeight: Math.round(box.height),
                  documentTop: Math.round(box.top + scrollY),
                  domPath: cssPath(el),
                  inDetailContainer: Boolean(detail && detail.contains(el))
                }];
              });

              return {
                capturedAt: new Date().toISOString(),
                pageUrl: location.href,
                pageTitle: document.title,
                scrollY: Math.round(scrollY),
                viewport: {width: innerWidth, height: innerHeight},
                document: {
                  width: document.documentElement.scrollWidth,
                  height: document.documentElement.scrollHeight
                },
                detailContainer: detail ? {
                  id: detail.id,
                  className: typeof detail.className === 'string' ? detail.className : '',
                  domPath: cssPath(detail),
                  imageCount: detail.querySelectorAll('img').length,
                  linkCount: detail.querySelectorAll('a').length
                } : null,
                images,
                backgrounds,
                domText: (
                  document.querySelector('#left-content-area')?.innerText
                  || document.body?.innerText
                  || ''
                ).trim()
              };
            }
            """
        )

    def _scroll_and_capture(self, page: Any) -> list[dict[str, Any]]:
        states: list[dict[str, Any]] = []
        stable_content_rounds = 0
        unchanged_position_rounds = 0
        previous_content_signature: tuple[int, int, int, int, int] | None = None
        previous_position_signature: tuple[int, int] | None = None
        segment = 1
        stop_reason = "max_scrolls"
        while len(states) < self.max_scrolls:
            state = page.evaluate(
                """() => {
                  const detail = document.querySelector('#imageTextInfo-container');
                  const detailBox = detail?.getBoundingClientRect();
                  const detailImages = Array.from(detail?.querySelectorAll('img') || []);
                  const sourceCount = new Set(detailImages.flatMap(img => [
                    img.currentSrc,
                    img.getAttribute('src'),
                    img.getAttribute('data-src')
                  ]).filter(Boolean)).size;
                  const loadedCount = detailImages.filter(img =>
                    img.complete && img.naturalWidth > 0 && img.naturalHeight > 0
                  ).length;
                  const recommendationPattern = /^(本店推荐|猜你喜欢|看了又看|相关推荐)$/;
                  const recommendation = Array.from(document.querySelectorAll('h1,h2,h3,h4,p,span,div'))
                    .find(el => {
                      const text = (el.textContent || '').trim();
                      return recommendationPattern.test(text)
                        && (!detail || !detail.contains(el));
                    });
                  const recommendationBox = recommendation?.getBoundingClientRect();
                  return {
                    y: Math.round(scrollY),
                    h: document.documentElement.scrollHeight,
                    v: innerHeight,
                    detailExists: Boolean(detail),
                    detailTop: detailBox ? Math.round(detailBox.top + scrollY) : null,
                    detailBottom: detailBox ? Math.round(detailBox.bottom + scrollY) : null,
                    detailImages: detailImages.length,
                    detailLoadedImages: loadedCount,
                    detailSourceCount: sourceCount,
                    recommendationTop: recommendationBox
                      ? Math.round(recommendationBox.top + scrollY)
                      : null
                  };
                }"""
            )
            content_signature = (
                int(state.get("detailImages") or 0),
                int(state.get("detailLoadedImages") or 0),
                int(state.get("detailSourceCount") or 0),
                int(state.get("detailBottom") or 0),
                int(state.get("h") or 0),
            )
            position_signature = (
                int(state.get("y") or 0),
                int(state.get("h") or 0),
            )
            stable_content_rounds = (
                stable_content_rounds + 1
                if content_signature == previous_content_signature
                else 0
            )
            unchanged_position_rounds = (
                unchanged_position_rounds + 1
                if position_signature == previous_position_signature
                else 0
            )
            previous_content_signature = content_signature
            previous_position_signature = position_signature
            state["stableContentRounds"] = stable_content_rounds
            state["unchangedPositionRounds"] = unchanged_position_rounds
            states.append(state)
            if len(states) == 1 or len(states) % 6 == 0:
                page.screenshot(path=self.paths.page / f"detail_context_{segment:02d}.png")
                segment += 1

            reason = scroll_stop_reason(
                state,
                stable_content_rounds=stable_content_rounds,
                unchanged_position_rounds=unchanged_position_rounds,
            )
            if reason:
                stop_reason = reason
                break

            viewport_bottom = int(state.get("y") or 0) + int(state.get("v") or 0)
            detail_bottom = state.get("detailBottom")
            if detail_bottom is None or viewport_bottom < int(detail_bottom) - 80:
                page.mouse.wheel(0, self.scroll_step)
            page.wait_for_timeout(650)
        if states:
            states[-1]["stopReason"] = stop_reason
        page.screenshot(path=self.paths.page / f"detail_context_{segment:02d}.png")
        return states

    def _obtain_original(self, context: Any, page: Any, image: dict[str, Any]) -> dict[str, Any]:
        url = urljoin(page.url, image.get("currentSrc") or image.get("src") or "")
        matching = next(
            (item for item in reversed(self._network_by_url.get(url, [])) if item.get("savedPath")),
            None,
        )
        acquisition = "Network response body"
        content_type = matching.get("contentType") if matching else None
        source_path: Path | None = None
        body: bytes | None = None
        if matching:
            source_path = self.paths.product_root / matching["savedPath"]
            body = source_path.read_bytes()
        else:
            acquisition = "BrowserContext request fallback"
            response = context.request.get(url, headers={"Referer": page.url}, timeout=30_000)
            if not response.ok:
                raise RuntimeError(f"image request failed: HTTP {response.status}")
            body = response.body()
            content_type = normalize_content_type(response.headers.get("content-type"))

        width, height, image_format = load_image_info(body)
        suffix = extension_for_content(content_type, url)
        if image_format == "WEBP":
            suffix = ".webp"
        elif image_format == "PNG":
            suffix = ".png"
        elif image_format in {"JPEG", "JPG"}:
            suffix = ".jpg"
        index = int(image["detailIndex"])
        destination = self.paths.original / f"original_{index:03d}{suffix}"
        if source_path:
            shutil.copyfile(source_path, destination)
        else:
            destination.write_bytes(body)
        return {
            "index": index,
            "url": url,
            "localPath": destination.relative_to(self.paths.product_root).as_posix(),
            "contentType": content_type,
            "byteLength": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            "naturalWidth": width,
            "naturalHeight": height,
            "domPath": image.get("domPath"),
            "acquisitionMethod": acquisition,
            "ocrSizeCandidate": is_size_candidate(width or 0, height or 0),
            "ocrCandidate": is_size_candidate(width or 0, height or 0),
        }

    def collect_in_context(self, context: Any, page: Any | None = None) -> Path:
        """Collect one product inside an already running browser context."""

        own_page = page is None
        page = page or context.new_page()
        self.network_records.clear()
        self._network_by_url.clear()
        self._response_counter = 0
        page.on("response", self._record_response)
        self.log(f"开始采集商品 {self.product_id}：{self.product_url}")
        try:
            page.goto(self.product_url, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(2_000)
            self._wait_until_unblocked(page)

            page.screenshot(path=self.paths.page / "overview.png")
            initial_dom = self._extract_dom(page)
            json_dump(self.paths.manifests / "dom_before_scroll.json", initial_dom)

            click_evidence = self._click_detail_tab(page)
            json_dump(self.paths.manifests / "detail_click.json", click_evidence)
            detail = page.locator("#imageTextInfo-container")
            if detail.count():
                detail.first.scroll_into_view_if_needed(timeout=10_000)
            scroll_states = self._scroll_and_capture(page)
            page.screenshot(path=self.paths.page / "full_page.png", full_page=True)
            page.wait_for_timeout(1_000)

            final_dom = self._extract_dom(page)
            detail_images = [
                item for item in final_dom["images"] if item["inDetailContainer"]
            ]
            for index, image in enumerate(detail_images, start=1):
                image["detailIndex"] = index
                image["ocrSizeCandidate"] = is_size_candidate(
                    image["naturalWidth"], image["naturalHeight"]
                )
            final_dom["detailImages"] = detail_images
            json_dump(self.paths.manifests / "dom_after_scroll.json", final_dom)
            json_dump(self.paths.manifests / "scroll_states.json", scroll_states)
            (self.paths.page / "page_after_scroll.html").write_text(
                page.content(), encoding="utf-8"
            )

            originals: list[dict[str, Any]] = []
            failures: list[dict[str, Any]] = []
            for image in detail_images:
                try:
                    originals.append(self._obtain_original(context, page, image))
                except Exception as exc:
                    failures.append(
                        {
                            "index": image["detailIndex"],
                            "url": image.get("currentSrc") or image.get("src"),
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                    )

            json_dump(
                self.paths.manifests / "network_responses.json", self.network_records
            )
            json_dump(self.paths.manifests / "original_images.json", originals)
            (self.paths.product_root / "dom_text.txt").write_text(
                final_dom.get("domText", ""), encoding="utf-8"
            )
            ocr_numbers = [
                int(item["index"])
                for item in originals
                if item.get("ocrCandidate") or item.get("ocrSizeCandidate")
            ]
            meta = {
                "schemaVersion": 1,
                "runId": self.paths.run_root.name,
                "keyword": self.candidate.get("keyword") or "",
                "rank": self.candidate.get("rank"),
                "productId": self.product_id,
                "productUrl": page.url,
                "sourceProductUrl": self.product_url,
                "productName": self.candidate.get("product_name") or page.title(),
                "shopName": self.candidate.get("shop_name") or "",
                "region": self.candidate.get("region") or "",
                "crawlTime": iso_now(),
                "crawlStatus": "detail_collected",
                "detailSelectorEvidence": click_evidence,
                "domImageCount": len(final_dom["images"]),
                "detailImageCount": len(detail_images),
                "networkImageCount": len(self.network_records),
                "savedOriginalCount": len(originals),
                "imageCount": len(originals),
                "ocrCandidateCount": len(ocr_numbers),
                "ocrImageNumbers": ocr_numbers,
                "ocrImageRange": (
                    [min(ocr_numbers), max(ocr_numbers)] if ocr_numbers else []
                ),
                "scrollStopReason": (
                    scroll_states[-1].get("stopReason") if scroll_states else None
                ),
                "scrollStateCount": len(scroll_states),
                "failures": failures,
                "screenshots": sorted(
                    item.relative_to(self.paths.product_root).as_posix()
                    for item in self.paths.page.glob("*.png")
                ),
                "images": originals,
                "collectionMethods": [
                    "standalone Python Playwright",
                    "DOM detail-image association",
                    "Network response listener/fallback request",
                    "segmented and full-page screenshots",
                ],
            }
            json_dump(self.paths.product_root / "meta.json", meta)
            self.log(
                f"完成商品 {self.product_id}：DOM详情图 {len(detail_images)}，"
                f"Network响应 {len(self.network_records)}，原图 {len(originals)}"
            )
            return self.paths.product_root
        except Exception as exc:
            try:
                page.screenshot(path=self.paths.page / "collection_error.png", full_page=True)
                (self.paths.page / "collection_error.html").write_text(
                    page.content(), encoding="utf-8"
                )
            except Exception:
                pass
            json_dump(
                self.paths.product_root / "collection_error.json",
                {
                    "productId": self.product_id,
                    "productUrl": self.product_url,
                    "failedAt": iso_now(),
                    "error": f"{type(exc).__name__}: {exc}",
                },
            )
            raise
        finally:
            if own_page and not page.is_closed():
                page.close()

    def run(self) -> Path:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise SystemExit(
                "缺少 Playwright。请先运行：python -m pip install -r requirements-phase1.txt"
            ) from exc

        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.log(f"实验目录：{self.paths.run_root}")
        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir.resolve()),
                channel=self.channel,
                headless=False,
                no_viewport=True,
                accept_downloads=True,
            )
            try:
                self.collect_in_context(context)
            finally:
                context.close()
        return self.paths.run_root


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="淘宝/天猫单商品图片采集对比实验")
    parser.add_argument("--url", help="真实淘宝或天猫商品 URL")
    parser.add_argument("--output", type=Path, default=Path("output"))
    parser.add_argument("--profile-dir", type=Path, default=Path(".browser-profile"))
    parser.add_argument("--channel", default="chrome", help="Playwright 浏览器通道，默认 chrome")
    parser.add_argument("--scroll-step", type=int, default=900)
    parser.add_argument("--max-scrolls", type=int, default=50)
    parser.add_argument("--non-interactive", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    url = args.url
    if not url:
        if args.non_interactive:
            print("--non-interactive 模式必须提供 --url", file=sys.stderr)
            return 2
        url = input("请输入真实淘宝/天猫商品 URL：").strip()
    if not url:
        print("商品 URL 不能为空", file=sys.stderr)
        return 2
    collector = PhaseOneCollector(
        product_url=url,
        output_root=args.output,
        profile_dir=args.profile_dir,
        channel=args.channel,
        scroll_step=args.scroll_step,
        max_scrolls=args.max_scrolls,
        non_interactive=args.non_interactive,
    )
    collector.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
