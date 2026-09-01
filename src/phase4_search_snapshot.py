"""Phase 4: parse a manually saved, real Taobao search-result snapshot.

Browser control was blocked for ``s.taobao.com`` by the browser safety layer,
so the user saved the already loaded page as complete HTML.  This module does
not fetch Taobao or guess a hypothetical DOM.  Its selectors are derived from
that real 2026-08-17 snapshot and every output records the source hash.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


DEFAULT_SNAPSHOT = Path("manual_input/taobao_search.html")
DEFAULT_KEYWORD = "酸枣仁"
VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}
CARD_ID_RE = re.compile(r"item_id_(\d+)$")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def class_tokens(attributes: dict[str, str | None]) -> list[str]:
    return (attributes.get("class") or "").split()


def has_class_prefix(attributes: dict[str, str | None], prefix: str) -> bool:
    return any(token.startswith(prefix) for token in class_tokens(attributes))


def clean_text(parts: list[str]) -> str:
    return " ".join(" ".join(parts).split())


def extract_product_id(url: str) -> str | None:
    values = parse_qs(urlparse(url).query).get("id")
    if values and values[0].isdigit():
        return values[0]
    match = re.search(r"(?:^|[?&])id=(\d+)", url)
    return match.group(1) if match else None


def canonical_product_url(url: str, product_id: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host == "detail.tmall.com":
        return f"https://detail.tmall.com/item.htm?id={product_id}"
    if host == "item.taobao.com":
        return f"https://item.taobao.com/item.htm?id={product_id}"
    # Advertising redirect links are valid product URLs, but their Taobao host
    # does not prove whether the destination detail page is Taobao or Tmall.
    return url


def product_platform(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host == "detail.tmall.com":
        return "tmall"
    if host == "item.taobao.com":
        return "taobao"
    if host.endswith("simba.taobao.com"):
        return "ad_redirect"
    return "unknown"


def source_page_url(document: str) -> str:
    match = re.search(r"<!--\s*saved from url=\(\d+\)(.*?)-->", document, re.S | re.I)
    return html.unescape(match.group(1).strip()) if match else ""


class SearchCardParser(HTMLParser):
    """Extract cards under the observed ``a#item_id_<id>`` boundary."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, dict[str, str | None], str | None]] = []
        self.cards: list[dict[str, Any]] = []
        self.current: dict[str, Any] | None = None
        self.card_parent_depth: int | None = None
        self.observed_classes: dict[str, set[str]] = {
            "card": set(),
            "title": set(),
            "shop": set(),
            "region": set(),
        }

    @staticmethod
    def role_for(attributes: dict[str, str | None]) -> str | None:
        roles = (
            ("title--", "title_text"),
            ("shopNameText--", "shop_parts"),
            ("procity--", "region_parts"),
            ("realSales--", "sales_parts"),
            ("priceInt--", "price_int_parts"),
            ("priceFloat--", "price_float_parts"),
        )
        for prefix, role in roles:
            if has_class_prefix(attributes, prefix):
                return role
        return None

    def _capture_start(
        self, tag: str, attributes: dict[str, str | None]
    ) -> str | None:
        if self.current is None:
            return None
        role = self.role_for(attributes)
        if has_class_prefix(attributes, "title--"):
            self.observed_classes["title"].update(class_tokens(attributes))
            title = (attributes.get("title") or "").strip()
            if title:
                self.current["product_name"] = title
        if has_class_prefix(attributes, "shopNameText--"):
            self.observed_classes["shop"].update(class_tokens(attributes))
        if has_class_prefix(attributes, "procity--"):
            self.observed_classes["region"].update(class_tokens(attributes))
        if tag == "img" and (
            has_class_prefix(attributes, "mainPic--")
            or has_class_prefix(attributes, "mainImg--")
        ):
            if not self.current.get("snapshot_image_path"):
                self.current["snapshot_image_path"] = attributes.get("src") or ""
        return role

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        card_match = CARD_ID_RE.fullmatch(attributes.get("id") or "")
        if tag == "a" and card_match and self.current is None:
            product_id = card_match.group(1)
            raw_url = attributes.get("href") or ""
            self.current = {
                "product_id": product_id,
                "source_product_url": raw_url,
                "product_name": "",
                "title_text": [],
                "shop_parts": [],
                "region_parts": [],
                "sales_parts": [],
                "price_int_parts": [],
                "price_float_parts": [],
                "source_index": attributes.get("data-spm") or "",
                "snapshot_image_path": "",
            }
            self.card_parent_depth = len(self.stack)
            self.observed_classes["card"].update(class_tokens(attributes))

        role = self._capture_start(tag, attributes)
        if tag not in VOID_TAGS:
            self.stack.append((tag, attributes, role))

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self._capture_start(tag, dict(attrs))

    def handle_data(self, data: str) -> None:
        if self.current is None or not data.strip():
            return
        role = next((entry[2] for entry in reversed(self.stack) if entry[2]), None)
        if role:
            value = self.current.get(role)
            if isinstance(value, list):
                value.append(data.strip())

    def handle_endtag(self, tag: str) -> None:
        match_index = next(
            (index for index in range(len(self.stack) - 1, -1, -1) if self.stack[index][0] == tag),
            None,
        )
        if match_index is None:
            return
        self.stack = self.stack[:match_index]
        if (
            self.current is not None
            and self.card_parent_depth is not None
            and len(self.stack) <= self.card_parent_depth
        ):
            self._finish_card()

    def _finish_card(self) -> None:
        assert self.current is not None
        product_id = self.current["product_id"]
        raw_url = self.current["source_product_url"]
        fallback_title = clean_text(self.current.pop("title_text"))
        self.current["product_name"] = self.current["product_name"] or fallback_title
        self.current["shop_name"] = clean_text(self.current.pop("shop_parts"))
        self.current["region"] = clean_text(self.current.pop("region_parts"))
        self.current["sales_text"] = clean_text(self.current.pop("sales_parts"))
        price_int = clean_text(self.current.pop("price_int_parts"))
        price_float = clean_text(self.current.pop("price_float_parts"))
        self.current["price_text"] = f"{price_int}{price_float}" if price_int else ""
        self.current["product_url"] = canonical_product_url(raw_url, product_id)
        self.current["platform"] = product_platform(raw_url)
        self.cards.append(self.current)
        self.current = None
        self.card_parent_depth = None


def parse_snapshot(document: str) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    parser = SearchCardParser()
    parser.feed(document)
    parser.close()
    observed = {
        key: sorted(values) for key, values in parser.observed_classes.items()
    }
    return parser.cards, observed


def deduplicate_cards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduplicated: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    for card in cards:
        product_id = card.get("product_id") or extract_product_id(card.get("product_url", ""))
        if not product_id:
            continue
        if product_id not in by_id:
            by_id[product_id] = card
            deduplicated.append(card)
            continue
        existing = by_id[product_id]
        for field in ("product_name", "shop_name", "region", "sales_text", "price_text"):
            if not existing.get(field) and card.get(field):
                existing[field] = card[field]
    return deduplicated


CSV_FIELDS = [
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


def write_candidates_csv(path: Path, candidates: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(candidates)


def md_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def build_summary(payload: dict[str, Any]) -> str:
    rows = [
        "| 排名 | 商品 ID | 商品名称 | 店铺 | 地区 |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for item in payload["candidates"]:
        rows.append(
            f"| {item['rank']} | `{item['product_id']}` | {md_escape(item['product_name'])} | "
            f"{md_escape(item['shop_name'] or '—')} | {md_escape(item['region'] or '—')} |"
        )
    missing = payload["missing_field_counts"]
    selectors = payload["selector_evidence"]
    return "\n".join(
        [
            "# Phase 4 淘宝搜索候选采集摘要",
            "",
            "## 结论",
            "",
            f"从用户手动保存的真实淘宝搜索页中发现 {payload['raw_card_count']} 个商品卡片，"
            f"按商品 ID 去重后 {payload['deduplicated_count']} 个，保存前 {payload['selected_count']} 个候选。",
            "",
            "由于浏览器控制的站点安全策略不允许读取 `s.taobao.com`，本阶段采用人工保存完整网页、程序本地解析的合规方式。候选均来自真实快照，没有补造商品。",
            "",
            "## 运行信息",
            "",
            f"- 搜索关键词：{payload['keyword']}",
            f"- 搜索页：{payload['source_page_url']}",
            f"- 快照时间：{payload['snapshot_time']}",
            f"- 快照路径：`{payload['snapshot_path']}`",
            f"- SHA-256：`{payload['snapshot_sha256']}`",
            f"- 商品名称缺失：{missing['product_name']}",
            f"- 店铺缺失：{missing['shop_name']}",
            f"- 地区缺失：{missing['region']}",
            "",
            "## 来自真实页面的结构证据",
            "",
            "- 商品卡片：`a[id^=\"item_id_\"]`，观察到类名："
            + "、".join(f"`{value}`" for value in selectors["card"]),
            "- 标题：带 `title` 属性且类名前缀为 `title--`，观察到："
            + "、".join(f"`{value}`" for value in selectors["title"]),
            "- 店铺：类名前缀 `shopNameText--`，观察到："
            + "、".join(f"`{value}`" for value in selectors["shop"]),
            "- 地区：类名前缀 `procity--`，观察到："
            + "、".join(f"`{value}`" for value in selectors["region"]),
            "",
            "## 候选商品",
            "",
            *rows,
            "",
            "本摘要只证明搜索候选的真实来源，不代表商品存在风险。商品详情、OCR 和功效分析将在 Phase 5 逐件执行，单商品失败时继续处理其他商品。",
            "",
        ]
    )


def run_snapshot_search(
    snapshot_path: Path,
    output_root: Path,
    keyword: str = DEFAULT_KEYWORD,
    limit: int = 20,
) -> dict[str, Path]:
    snapshot_path = snapshot_path.resolve()
    if not snapshot_path.exists():
        raise FileNotFoundError(f"搜索页快照不存在：{snapshot_path}")
    if limit < 1:
        raise ValueError("limit 必须大于 0")
    document = snapshot_path.read_text(encoding="utf-8")
    cards, selector_evidence = parse_snapshot(document)
    deduplicated = deduplicate_cards(cards)
    selected = deduplicated[:limit]
    if not selected:
        raise ValueError("快照中未发现 a#item_id_<商品ID> 商品卡片")

    snapshot_time = datetime.fromtimestamp(snapshot_path.stat().st_mtime).astimezone()
    run_id = snapshot_time.strftime("%Y%m%dT%H%M%S") + "_search"
    run_root = output_root.resolve() / run_id
    run_root.mkdir(parents=True, exist_ok=True)
    crawl_time = snapshot_time.isoformat(timespec="seconds")
    for rank, card in enumerate(selected, start=1):
        card["keyword"] = keyword
        card["rank"] = rank
        card["crawl_time"] = crawl_time

    missing_fields = {
        field: sum(not item.get(field) for item in selected)
        for field in ("product_name", "shop_name", "region")
    }
    payload = {
        "run_id": run_id,
        "phase": 4,
        "keyword": keyword,
        "collection_method": "manual_complete_html_snapshot_then_local_parse",
        "source_page_url": source_page_url(document),
        "snapshot_path": snapshot_path.as_posix(),
        "snapshot_time": crawl_time,
        "snapshot_bytes": snapshot_path.stat().st_size,
        "snapshot_sha256": file_sha256(snapshot_path),
        "raw_card_count": len(cards),
        "deduplicated_count": len(deduplicated),
        "selected_count": len(selected),
        "limit": limit,
        "missing_field_counts": missing_fields,
        "selector_evidence": selector_evidence,
        "candidates": selected,
    }

    json_path = run_root / "search_candidates.json"
    csv_path = run_root / "search_candidates.csv"
    summary_path = run_root / "summary.md"
    source_path = run_root / "source_snapshot.json"
    write_json(json_path, payload)
    write_candidates_csv(csv_path, selected)
    summary_path.write_text(build_summary(payload), encoding="utf-8")
    write_json(
        source_path,
        {
            key: payload[key]
            for key in (
                "collection_method",
                "source_page_url",
                "snapshot_path",
                "snapshot_time",
                "snapshot_bytes",
                "snapshot_sha256",
                "selector_evidence",
            )
        },
    )
    return {
        "run_root": run_root,
        "json": json_path,
        "csv": csv_path,
        "summary": summary_path,
        "source": source_path,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="解析用户手动保存的真实淘宝搜索页")
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--output-root", type=Path, default=Path("output"))
    parser.add_argument("--keyword", default=DEFAULT_KEYWORD)
    parser.add_argument("--limit", type=int, default=20)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    outputs = run_snapshot_search(
        snapshot_path=args.snapshot,
        output_root=args.output_root,
        keyword=args.keyword,
        limit=args.limit,
    )
    print(f"Phase 4 candidates: {outputs['json']}")
    print(f"Phase 4 summary: {outputs['summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
