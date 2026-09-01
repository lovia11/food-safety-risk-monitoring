"""Phase 3: local, explainable effect-signal classification.

The analyzer combines the real product title, current-product DOM text, and
per-image OCR text.  It keeps user-generated content separate from
seller-managed content and excludes the DOM recommendation section so another
product's claims cannot be attributed to the current item.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_PRODUCT_ROOT = Path("output/20260817T171318/products/606232126144")
DEFAULT_CONFIG = Path("config/effect_keywords.json")
SELLER_MANAGED_TYPES = {"title", "dom_product", "ocr"}
UGC_TYPES = {"dom_user_review", "dom_qa"}
SOURCE_LABELS = {
    "title": "商品标题",
    "dom_product": "当前商品 DOM",
    "dom_user_review": "用户评价",
    "dom_qa": "用户问答",
    "ocr": "详情图 OCR",
    "dom_recommendation": "其他商品推荐（已排除）",
}


def iso_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class TextUnit:
    source_type: str
    source_path: str
    line_number: int
    text: str

    @property
    def source_label(self) -> str:
        return SOURCE_LABELS[self.source_type]

    @property
    def content_origin(self) -> str:
        if self.source_type in SELLER_MANAGED_TYPES:
            return "seller_managed"
        if self.source_type in UGC_TYPES:
            return "user_generated"
        return "excluded_other_product"


def recommendation_cutoff(lines: list[str]) -> int:
    """Return a zero-based cutoff for the observed recommendation section.

    The real page contains one ``本店推荐`` navigation label near the top and a
    second heading before recommendation cards.  Taking the final heading avoids
    cutting the current-product content at the navigation label.  With only one
    occurrence, price/payment markers are required before treating it as a real
    recommendation section.
    """

    candidates = [index for index, line in enumerate(lines) if line.strip() == "本店推荐"]
    if len(candidates) >= 2:
        return candidates[-1]
    if len(candidates) == 1:
        index = candidates[0]
        tail = lines[index + 1 :]
        if any("¥" in line or "人付款" in line for line in tail):
            return index
    return len(lines)


def parse_dom_units(text: str, source_path: str = "dom_text.txt") -> tuple[list[TextUnit], list[TextUnit]]:
    lines = text.splitlines()
    cutoff = recommendation_cutoff(lines)
    included: list[TextUnit] = []
    excluded: list[TextUnit] = []
    source_type = "dom_product"

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue
        if line_number - 1 >= cutoff:
            excluded.append(
                TextUnit("dom_recommendation", source_path, line_number, line)
            )
            continue
        if re.fullmatch(r"用户评价(?:·.*)?", line):
            source_type = "dom_user_review"
        elif line == "查看全部评价":
            source_type = "dom_product"
        elif re.fullmatch(r"问大家(?:·.*)?", line):
            source_type = "dom_qa"
        elif line == "查看全部问答":
            source_type = "dom_product"
        included.append(TextUnit(source_type, source_path, line_number, line))
    return included, excluded


def load_effect_config(path: Path) -> dict[str, Any]:
    config = read_json(path)
    categories = config.get("effect_categories")
    if not isinstance(categories, dict) or not categories:
        raise ValueError("effect_keywords.json 缺少 effect_categories")
    for effect, keywords in categories.items():
        if not isinstance(effect, str) or not effect.strip():
            raise ValueError("功效分类名必须是非空字符串")
        if not isinstance(keywords, list) or not all(
            isinstance(keyword, str) and keyword.strip() for keyword in keywords
        ):
            raise ValueError(f"功效分类 {effect} 的关键词必须是非空字符串数组")
    return config


def load_text_units(product_root: Path, meta: dict[str, Any]) -> tuple[list[TextUnit], list[TextUnit], dict[str, Any]]:
    units = [
        TextUnit(
            "title",
            "meta.json#productName",
            1,
            str(meta.get("productName") or "").strip(),
        )
    ]
    units = [unit for unit in units if unit.text]

    dom_path = product_root / "dom_text.txt"
    dom_units, excluded_units = parse_dom_units(
        dom_path.read_text(encoding="utf-8"), "dom_text.txt"
    )
    units.extend(dom_units)

    ocr_manifest_path = product_root / "ocr" / "manifest.json"
    manifest = read_json(ocr_manifest_path)
    ocr_files = 0
    ocr_lines = 0
    for item in manifest:
        if item.get("status") != "success" or not item.get("textPath"):
            continue
        text_path = product_root / item["textPath"]
        if not text_path.exists():
            continue
        ocr_files += 1
        for line_number, raw_line in enumerate(
            text_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            line = raw_line.strip()
            if line:
                ocr_lines += 1
                units.append(
                    TextUnit("ocr", item["textPath"], line_number, line)
                )

    input_summary = {
        "title_units": sum(unit.source_type == "title" for unit in units),
        "dom_included_lines": len(dom_units),
        "dom_excluded_recommendation_lines": len(excluded_units),
        "ocr_success_images": ocr_files,
        "ocr_lines": ocr_lines,
        "total_in_scope_units": len(units),
    }
    return units, excluded_units, input_summary


def match_units(
    units: Iterable[TextUnit], categories: dict[str, list[str]]
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, int]] = set()
    for unit in units:
        for effect, keywords in categories.items():
            hits = [keyword for keyword in keywords if keyword in unit.text]
            key = (effect, unit.source_path, unit.text, unit.line_number)
            if not hits or key in seen:
                continue
            seen.add(key)
            matches.append(
                {
                    "effect": effect,
                    "text": unit.text,
                    "matched_keywords": hits,
                    "source_type": unit.source_type,
                    "source_label": unit.source_label,
                    "content_origin": unit.content_origin,
                    "source_path": unit.source_path,
                    "line_number": unit.line_number,
                }
            )
    return matches


def build_risk_reason(effects: list[str], evidence: list[dict[str, Any]]) -> str:
    if not effects:
        return "未检测到配置词库中的明确功效表达；仍需结合图片质量和未收录的隐含表达人工判断。"
    effect_text = "、".join(effects)
    origins = {item["content_origin"] for item in evidence}
    if origins == {"user_generated"}:
        return (
            f"当前商品页面的用户评价/问答中检测到{effect_text}相关表达；"
            "商品标题、当前商品 DOM 正文及详情图 OCR 未出现同类功效词，"
            "建议人工复核页面展示语境和内容来源。"
        )
    return (
        f"当前商品范围内检测到{effect_text}相关表达，建议人工复核其内容来源、"
        "页面语境和是否属于商品功效宣传。"
    )


def serialize_analysis_input(units: list[TextUnit]) -> str:
    lines = []
    previous_source: tuple[str, str] | None = None
    for unit in units:
        source = (unit.source_type, unit.source_path)
        if source != previous_source:
            if lines:
                lines.append("")
            lines.append(f"## {unit.source_label} | {unit.source_path}")
            previous_source = source
        lines.append(f"L{unit.line_number}: {unit.text}")
    return "\n".join(lines).rstrip() + "\n"


def build_analysis(
    product_root: Path,
    config_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], list[TextUnit]]:
    meta_path = product_root / "meta.json"
    meta = read_json(meta_path)
    config = load_effect_config(config_path)
    categories = config["effect_categories"]
    units, excluded_units, input_summary = load_text_units(product_root, meta)
    evidence_details = match_units(units, categories)
    excluded_evidence = match_units(excluded_units, categories)
    detected_effects = [
        effect
        for effect in categories
        if any(item["effect"] == effect for item in evidence_details)
    ]
    matched_keywords = {
        effect: list(
            dict.fromkeys(
                keyword
                for item in evidence_details
                if item["effect"] == effect
                for keyword in item["matched_keywords"]
            )
        )
        for effect in detected_effects
    }
    evidence = list(dict.fromkeys(item["text"] for item in evidence_details))
    source_counts = Counter(item["source_type"] for item in evidence_details)
    origin_counts = Counter(item["content_origin"] for item in evidence_details)
    analysis = {
        "product_id": str(meta.get("productId") or product_root.name),
        "product_name": meta.get("productName") or "",
        "product_url": meta.get("productUrl") or "",
        "keyword": meta.get("keyword") or "",
        "analyzed_at": iso_now(),
        "analysis_method": "local_configured_keyword_rules",
        "rule_config": {
            "path": config_path.as_posix(),
            "version": config.get("version"),
            "sha256": file_sha256(config_path),
        },
        "input_summary": input_summary,
        "input_files": {
            "meta": {"path": "meta.json", "sha256": file_sha256(meta_path)},
            "dom": {
                "path": "dom_text.txt",
                "sha256": file_sha256(product_root / "dom_text.txt"),
            },
            "ocr_manifest": {
                "path": "ocr/manifest.json",
                "sha256": file_sha256(product_root / "ocr" / "manifest.json"),
            },
        },
        "detected_effects": detected_effects,
        "matched_keywords": matched_keywords,
        "evidence": evidence,
        "evidence_details": evidence_details,
        "evidence_source_counts": dict(source_counts),
        "evidence_origin_counts": dict(origin_counts),
        "risk_reason": build_risk_reason(detected_effects, evidence_details),
        "review_required": bool(detected_effects),
        "excluded_evidence": excluded_evidence,
        "exclusion_reason": (
            "DOM 中最终“本店推荐”标题之后的内容属于其他商品推荐，"
            "不计入当前商品的 detected_effects 或 evidence。"
            if excluded_units
            else "本页采集文本中没有可确认的其他商品推荐卡片内容，未产生跨商品排除证据。"
        ),
        "disclaimer": (
            "本结果仅为基于页面文本的风险线索，不认定商品违法、功效真实、"
            "存在非法添加或检出任何药物。"
        ),
    }
    return analysis, meta, units


def markdown_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def evidence_origin_note(evidence_details: list[dict[str, Any]]) -> str:
    if not evidence_details:
        return "本次未发现配置词库中的明确功效线索。"
    origins = {item["content_origin"] for item in evidence_details}
    if origins == {"user_generated"}:
        return "本次有效线索均为用户生成内容，不等同于商家作出的功效承诺。"
    if origins == {"seller_managed"}:
        return "本次有效线索来自商品标题、当前商品正文或详情图 OCR，建议人工核对原页面语境。"
    return "本次有效线索同时包含商品内容和用户生成内容，报告已逐条标注来源，不能混同归因。"


def build_product_report(analysis: dict[str, Any]) -> str:
    evidence_rows = [
        "| 功效分类 | 来源 | 行号 | 命中词 | 证据 |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for item in analysis["evidence_details"]:
        evidence_rows.append(
            "| {effect} | {source} | {line} | {keywords} | {text} |".format(
                effect=markdown_escape(item["effect"]),
                source=markdown_escape(item["source_label"]),
                line=item["line_number"],
                keywords=markdown_escape("、".join(item["matched_keywords"])),
                text=markdown_escape(item["text"]),
            )
        )
    if not analysis["evidence_details"]:
        evidence_rows.append("| — | — | — | — | 未发现明确功效词 |")

    excluded_rows = [
        "| 分类 | 来源行 | 命中词 | 文本 |",
        "| --- | ---: | --- | --- |",
    ]
    for item in analysis["excluded_evidence"]:
        excluded_rows.append(
            "| {effect} | {line} | {keywords} | {text} |".format(
                effect=markdown_escape(item["effect"]),
                line=item["line_number"],
                keywords=markdown_escape("、".join(item["matched_keywords"])),
                text=markdown_escape(item["text"]),
            )
        )
    if not analysis["excluded_evidence"]:
        excluded_rows.append("| — | — | — | 无 |")

    effect_text = "、".join(analysis["detected_effects"]) or "无"
    review_text = "是" if analysis["review_required"] else "否"
    summary = analysis["input_summary"]
    return "\n".join(
        [
            "# Phase 3 单商品功效线索分析报告",
            "",
            "## 真实分析结果",
            "",
            f"- 商品：{analysis['product_name']}",
            f"- 商品 ID：`{analysis['product_id']}`",
            f"- 检测到的功效分类：**{effect_text}**",
            f"- 建议人工复核：**{review_text}**",
            f"- 风险理由：{analysis['risk_reason']}",
            "",
            "## 当前商品范围内证据",
            "",
            *evidence_rows,
            "",
            evidence_origin_note(analysis["evidence_details"]),
            "",
            "## 已排除的跨商品干扰",
            "",
            *excluded_rows,
            "",
            analysis["exclusion_reason"],
            "",
            "## 输入审计",
            "",
            f"- 标题：{summary['title_units']} 条",
            f"- 当前商品 DOM：{summary['dom_included_lines']} 行",
            f"- 排除推荐商品 DOM：{summary['dom_excluded_recommendation_lines']} 行",
            f"- OCR：{summary['ocr_success_images']} 张、{summary['ocr_lines']} 行",
            f"- 规则配置：`{analysis['rule_config']['path']}`，版本 {analysis['rule_config']['version']}",
            "",
            "## 结论边界",
            "",
            analysis["disclaimer"],
            "",
        ]
    )


CSV_FIELDS = [
    "keyword",
    "product_name",
    "shop_name",
    "region",
    "product_url",
    "original_image_count",
    "ocr_image_count",
    "detected_effects",
    "evidence",
    "risk_reason",
    "review_required",
    "crawl_status",
    "screenshot_path",
]


def build_product_record(
    product_root: Path, meta: dict[str, Any], analysis: dict[str, Any]
) -> dict[str, Any]:
    screenshots = meta.get("screenshots") or []
    screenshot_path = (
        f"products/{product_root.name}/{screenshots[0]}" if screenshots else ""
    )
    return {
        "keyword": meta.get("keyword") or "",
        "product_name": meta.get("productName") or "",
        "shop_name": meta.get("shopName") or "",
        "region": meta.get("region") or "",
        "product_url": meta.get("productUrl") or "",
        "product_id": str(meta.get("productId") or product_root.name),
        "crawl_time": meta.get("crawlTime") or "",
        "original_image_count": int(meta.get("imageCount") or 0),
        "ocr_image_count": analysis["input_summary"]["ocr_success_images"],
        "detected_effects": analysis["detected_effects"],
        "evidence": analysis["evidence"],
        "evidence_details": analysis["evidence_details"],
        "risk_reason": analysis["risk_reason"],
        "review_required": analysis["review_required"],
        "crawl_status": "phase1_success_phase2_success_phase3_success",
        "screenshot_path": screenshot_path,
        "analysis_path": f"products/{product_root.name}/analysis.json",
    }


def write_products_csv(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        row = dict(record)
        row["detected_effects"] = "、".join(record["detected_effects"])
        row["evidence"] = " | ".join(record["evidence"])
        row["review_required"] = str(record["review_required"]).lower()
        writer.writerow(row)


def build_run_summary(run_root: Path, record: dict[str, Any], analysis: dict[str, Any]) -> str:
    effect_count = 1 if analysis["detected_effects"] else 0
    review_count = 1 if analysis["review_required"] else 0
    return "\n".join(
        [
            "# Phase 3 运行摘要",
            "",
            f"- 搜索关键词：{record['keyword']}",
            "- 搜索商品数量：未执行（Phase 4 尚未开始）",
            "- 去重商品数量：1（真实单商品实验输入，不代表淘宝搜索结果）",
            "- 成功打开详情页数量：1",
            f"- 成功获取原始详情图数量：{record['original_image_count']}",
            f"- OCR 成功数量：{record['ocr_image_count']}",
            f"- 检测到功效相关页面线索的商品数量：{effect_count}",
            f"- 建议人工复核数量：{review_count}",
            "- 失败原因：无",
            "",
            "## 结果说明",
            "",
            f"当前商品命中：{'、'.join(analysis['detected_effects']) or '无'}。",
            analysis["risk_reason"],
            "",
            "本阶段只处理 Phase 1/2 的真实单商品数据，没有伪造搜索商品数量。",
            "",
            f"运行目录：`{run_root.as_posix()}`",
            "",
        ]
    )


def run_analysis(
    product_root: Path,
    config_path: Path,
    write_run_outputs: bool = True,
) -> dict[str, Path]:
    product_root = product_root.resolve()
    config_path = config_path.resolve()
    run_root = product_root.parent.parent
    analysis, meta, units = build_analysis(product_root, config_path)

    analysis_path = product_root / "analysis.json"
    analysis_input_path = product_root / "analysis_input.txt"
    report_path = product_root / "phase3_analysis_report.md"
    products_csv_path = run_root / "products.csv"
    products_json_path = run_root / "products.json"
    summary_path = run_root / "summary.md"

    write_json(analysis_path, analysis)
    analysis_input_path.write_text(serialize_analysis_input(units), encoding="utf-8")
    report_path.write_text(build_product_report(analysis), encoding="utf-8")
    record = build_product_record(product_root, meta, analysis)
    outputs = {
        "analysis": analysis_path,
        "analysis_input": analysis_input_path,
        "report": report_path,
    }
    if write_run_outputs:
        write_products_csv(products_csv_path, record)
        write_json(
            products_json_path,
            {
                "run_id": meta.get("runId") or run_root.name,
                "generated_at": iso_now(),
                "phase": 3,
                "products": [record],
            },
        )
        summary_path.write_text(
            build_run_summary(run_root, record, analysis), encoding="utf-8"
        )
        outputs.update(
            {
                "products_csv": products_csv_path,
                "products_json": products_json_path,
                "summary": summary_path,
            }
        )
    return outputs


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="对真实标题、DOM 和 OCR 文本执行本地功效规则分析")
    parser.add_argument("--product-root", type=Path, default=DEFAULT_PRODUCT_ROOT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    outputs = run_analysis(args.product_root, args.config)
    print(f"Phase 3 analysis: {outputs['analysis']}")
    print(f"Phase 3 report: {outputs['report']}")
    print(f"Run summary: {outputs['summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
