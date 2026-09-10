"""Phase 5: join search, detail assets, OCR, and rule analysis in one batch.

The batch runner accepts product directories already collected by Phase 1 and
browser-capture manifests produced during supervised page collection.  It is
checkpointed per product: one failure is recorded and processing continues.
Uncollected search candidates remain explicit ``pending_detail_collection``
records instead of being filled with invented data.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from src.phase2_ocr import run_ocr
from src.phase3_analysis import run_analysis


DEFAULT_SEARCH_RESULTS = Path(
    "output/20260817T180025_search/search_candidates.json"
)
DEFAULT_RULE_CONFIG = Path("config/effect_keywords.json")
GENERIC_FOOTER_URL_PART = "6000000002284-2-tps-1125-1446.png"


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


def extract_product_id(url: str) -> str | None:
    values = parse_qs(urlparse(url).query).get("id")
    if values and values[0].isdigit():
        return values[0]
    return None


def extension_for_content_type(content_type: str | None, source_path: Path) -> str:
    normalized = (content_type or "").split(";", 1)[0].lower()
    if normalized == "image/webp":
        return ".webp"
    if normalized == "image/png":
        return ".png"
    if normalized == "image/jpeg":
        return ".jpg"
    return source_path.suffix.lower() or ".bin"


def is_ocr_candidate(image: dict[str, Any]) -> bool:
    return (
        int(image.get("naturalWidth") or 0) >= 700
        and int(image.get("naturalHeight") or 0) >= 700
        and GENERIC_FOOTER_URL_PART not in str(image.get("src") or "")
    )


def candidate_map(search_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item["product_id"]): item
        for item in search_payload.get("candidates", [])
        if item.get("product_id")
    }


def copy_reused_product(source_root: Path, destination_root: Path, run_id: str) -> dict[str, Any]:
    source_root = source_root.resolve()
    if not (source_root / "meta.json").exists():
        raise FileNotFoundError(f"复用商品缺少 meta.json：{source_root}")
    shutil.copytree(source_root, destination_root, dirs_exist_ok=True)
    meta = read_json(destination_root / "meta.json")
    meta["runId"] = run_id
    meta["batchSource"] = {
        "method": "reused_verified_phase1_phase2_phase3_product",
        "sourceProductRoot": source_root.as_posix(),
        "ingestedAt": iso_now(),
    }
    write_json(destination_root / "meta.json", meta)
    return meta


def ingest_browser_capture(
    capture_path: Path,
    candidate: dict[str, Any],
    destination_root: Path,
    run_id: str,
) -> dict[str, Any]:
    capture_path = capture_path.resolve()
    capture = read_json(capture_path)
    product_id = extract_product_id(str(capture.get("pageUrl") or ""))
    if product_id != str(candidate.get("product_id") or ""):
        raise ValueError(
            f"采集文件商品 ID {product_id!r} 与候选 {candidate.get('product_id')!r} 不一致"
        )
    assets_by_url = {
        item["url"]: item for item in capture.get("bundle", {}).get("assets", [])
    }
    original_root = destination_root / "images" / "original"
    manifests_root = destination_root / "manifests"
    original_root.mkdir(parents=True, exist_ok=True)
    manifests_root.mkdir(parents=True, exist_ok=True)

    images: list[dict[str, Any]] = []
    for index, image in enumerate(capture.get("detailImages", []), start=1):
        url = str(image.get("src") or "")
        asset = assets_by_url.get(url)
        if not asset:
            raise FileNotFoundError(f"详情图未出现在浏览器导出包中：{url}")
        source_path = Path(asset["path"])
        if not source_path.exists():
            raise FileNotFoundError(f"浏览器导出文件不存在：{source_path}")
        suffix = extension_for_content_type(asset.get("contentType"), source_path)
        destination = original_root / f"original_{index:03d}{suffix}"
        shutil.copy2(source_path, destination)
        record = {
            "index": index,
            "localPath": destination.relative_to(destination_root).as_posix(),
            "url": url,
            "contentType": asset.get("contentType"),
            "byteLength": destination.stat().st_size,
            "sha256": file_sha256(destination),
            "naturalWidth": int(image.get("naturalWidth") or 0),
            "naturalHeight": int(image.get("naturalHeight") or 0),
            "domAttributes": {
                "class": image.get("className") or "",
                "data-name": image.get("dataName") or "",
            },
            "assetId": asset.get("id"),
            "acquisitionMethods": ["DOM", "browser pageAssets bundle"],
            "productId": product_id,
        }
        record["ocrCandidate"] = is_ocr_candidate(image)
        images.append(record)

    body_text = str(capture.get("bodyText") or "")
    (destination_root / "dom_text.txt").write_text(body_text, encoding="utf-8")
    ocr_numbers = [item["index"] for item in images if item["ocrCandidate"]]
    meta = {
        "keyword": candidate.get("keyword") or "",
        "productName": candidate.get("product_name") or "",
        "productUrl": candidate.get("product_url") or capture.get("pageUrl") or "",
        "sourceProductUrl": candidate.get("source_product_url") or "",
        "productId": product_id,
        "shopName": candidate.get("shop_name") or "",
        "region": candidate.get("region") or "",
        "crawlTime": capture.get("capturedAt") or iso_now(),
        "runId": run_id,
        "detailSelectorEvidence": capture.get("selectorEvidence") or {},
        "imageCount": len(images),
        "ocrCandidateCount": len(ocr_numbers),
        "ocrImageRange": [min(ocr_numbers), max(ocr_numbers)] if ocr_numbers else [],
        "images": images,
        "screenshots": [],
        "collectionMethods": [
            "DOM text",
            "DOM detail-image association",
            "browser pageAssets bundle",
        ],
        "batchSource": {
            "method": "supervised_browser_capture",
            "captureManifest": capture_path.as_posix(),
            "captureSha256": file_sha256(capture_path),
            "ingestedAt": iso_now(),
        },
    }
    write_json(destination_root / "meta.json", meta)
    write_json(manifests_root / "original_images.json", images)
    write_json(
        manifests_root / "browser_capture.json",
        {
            "capturedAt": capture.get("capturedAt"),
            "pageTitle": capture.get("pageTitle"),
            "pageUrl": capture.get("pageUrl"),
            "bodyLineCount": capture.get("bodyLineCount"),
            "bodyCharacterCount": capture.get("bodyCharacterCount"),
            "selectorEvidence": capture.get("selectorEvidence"),
            "assetInventory": capture.get("assetInventory"),
            "bundleSummary": capture.get("bundle", {}).get("summary"),
            "sourceCapturePath": capture_path.as_posix(),
            "sourceCaptureSha256": file_sha256(capture_path),
        },
    )
    return meta


def successful_ocr_count(product_root: Path) -> int:
    manifest_path = product_root / "ocr" / "manifest.json"
    if not manifest_path.exists():
        return 0
    try:
        manifest = read_json(manifest_path)
    except (OSError, ValueError, TypeError):
        return 0
    if not isinstance(manifest, list):
        return 0
    resolved_root = product_root.resolve()
    count = 0
    for item in manifest:
        if not isinstance(item, dict) or item.get("status") != "success":
            continue
        artifact_paths = []
        for field in ("textPath", "jsonPath"):
            value = str(item.get(field) or "").replace("\\", "/").lstrip("/")
            if not value:
                break
            try:
                path = (resolved_root / value).resolve()
            except (OSError, RuntimeError):
                break
            if not path.is_relative_to(resolved_root) or not path.is_file():
                break
            artifact_paths.append(path)
        if len(artifact_paths) == 2:
            count += 1
    return count


def screenshot_path_for_batch(meta: dict[str, Any], product_id: str) -> str:
    screenshots = meta.get("screenshots") or []
    return f"products/{product_id}/{screenshots[0]}" if screenshots else ""


BATCH_CSV_FIELDS = [
    "keyword",
    "product_name",
    "shop_name",
    "region",
    "product_url",
    "product_id",
    "original_image_count",
    "ocr_image_count",
    "detected_effects",
    "evidence",
    "risk_reason",
    "review_required",
    "crawl_status",
    "screenshot_path",
]


def build_batch_record(
    candidate: dict[str, Any],
    product_root: Path | None,
    state: dict[str, Any],
) -> dict[str, Any]:
    base = {
        "keyword": candidate.get("keyword") or "",
        "product_name": candidate.get("product_name") or "",
        "shop_name": candidate.get("shop_name") or "",
        "region": candidate.get("region") or "",
        "product_url": candidate.get("product_url") or "",
        "product_id": str(candidate.get("product_id") or ""),
        "original_image_count": 0,
        "ocr_image_count": 0,
        "detected_effects": [],
        "evidence": [],
        "risk_reason": "尚未采集详情，本批次未分析。",
        "review_required": None,
        "crawl_status": state["status"],
        "screenshot_path": "",
        "errors": state.get("errors", []),
    }
    if product_root is None or not (product_root / "meta.json").exists():
        return base
    meta = read_json(product_root / "meta.json")
    verified_fields = {
        "keyword": meta.get("keyword"),
        "product_name": meta.get("productName"),
        "shop_name": meta.get("shopName"),
        "region": meta.get("region"),
        "product_url": meta.get("productUrl"),
    }
    for field, value in verified_fields.items():
        if value:
            base[field] = value
    base["original_image_count"] = int(meta.get("imageCount") or 0)
    base["ocr_image_count"] = successful_ocr_count(product_root)
    base["screenshot_path"] = screenshot_path_for_batch(meta, base["product_id"])
    analysis_path = product_root / "analysis.json"
    if analysis_path.exists():
        analysis = read_json(analysis_path)
        base["detected_effects"] = analysis.get("detected_effects") or []
        base["evidence"] = analysis.get("evidence") or []
        base["risk_reason"] = analysis.get("risk_reason") or ""
        base["review_required"] = analysis.get("review_required")
        base["evidence_details"] = analysis.get("evidence_details") or []
        base["analysis_path"] = f"products/{base['product_id']}/analysis.json"
    return base


def write_batch_csv(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BATCH_CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            row = dict(record)
            row["detected_effects"] = "、".join(record["detected_effects"])
            row["evidence"] = " | ".join(record["evidence"])
            review = record["review_required"]
            row["review_required"] = "" if review is None else str(review).lower()
            writer.writerow(row)


def build_batch_summary(
    batch_payload: dict[str, Any],
    records: list[dict[str, Any]],
) -> str:
    processed = [record for record in records if record["crawl_status"] == "success"]
    detail_available = [
        record
        for record in records
        if record["original_image_count"] > 0
        or record["crawl_status"]
        in {"detail_collected", "processing_ocr_analysis", "failed_processing", "success"}
    ]
    pending = [
        record for record in records if record["crawl_status"] == "pending_detail_collection"
    ]
    failed = [
        record for record in records if record["crawl_status"].startswith("failed")
    ]
    effect_products = [record for record in processed if record["detected_effects"]]
    review_products = [record for record in processed if record["review_required"]]
    failure_lines = [
        f"- `{record['product_id']}`：{'；'.join(record.get('errors') or ['unknown error'])}"
        for record in failed
    ] or ["- 无"]
    result_rows = [
        "| 商品 ID | 状态 | 原图 | OCR | 功效线索 | 人工复核 |",
        "| --- | --- | ---: | ---: | --- | --- |",
    ]
    for record in records:
        result_rows.append(
            f"| `{record['product_id']}` | {record['crawl_status']} | "
            f"{record['original_image_count']} | {record['ocr_image_count']} | "
            f"{'、'.join(record['detected_effects']) or '—'} | "
            f"{'是' if record['review_required'] else '否' if record['review_required'] is False else '—'} |"
        )
    return "\n".join(
        [
            "# Phase 5 批量串联验证摘要",
            "",
            "## 运行统计",
            "",
            f"- 搜索关键词：{batch_payload['keyword']}",
            f"- 搜索页商品卡片数量：{batch_payload['search_raw_count']}",
            f"- 搜索页去重商品数量：{batch_payload['search_deduplicated_count']}",
            f"- 入选候选数量：{len(records)}",
            f"- 本批次详情采集/复用数量：{len(detail_available)}",
            f"- 端到端成功商品数量：{len(processed)}",
            f"- 待后续详情采集数量：{len(pending)}",
            f"- 成功获取原始详情图数量：{sum(r['original_image_count'] for r in detail_available)}",
            f"- OCR 成功图片数量：{sum(r['ocr_image_count'] for r in records)}",
            f"- 检测到功效相关页面线索的商品数量：{len(effect_products)}",
            f"- 建议人工复核数量：{len(review_products)}",
            "",
            "本批次只汇总实际完成的采集、OCR和分析结果；未处理候选保持待采集状态，失败商品保留真实错误，不生成虚构详情或分析数据。",
            "",
            "## 商品状态",
            "",
            *result_rows,
            "",
            "## 失败原因",
            "",
            *failure_lines,
            "",
            "结果仅为风险线索，不认定商品违法、功效真实、非法添加或检出任何药物。",
            "",
        ]
    )


def run_batch(
    search_results: Path,
    output_root: Path,
    rule_config: Path,
    cache_dir: Path,
    reused_product_roots: list[Path],
    capture_paths: list[Path],
    run_id: str | None = None,
    run_ocr_enabled: bool = True,
) -> dict[str, Path]:
    search_results = search_results.resolve()
    rule_config = rule_config.resolve()
    search_payload = read_json(search_results)
    candidates = search_payload.get("candidates") or []
    candidates_by_id = candidate_map(search_payload)
    run_id = run_id or datetime.now().astimezone().strftime("%Y%m%dT%H%M%S_batch")
    run_root = output_root.resolve() / run_id
    products_root = run_root / "products"
    products_root.mkdir(parents=True, exist_ok=True)

    prepared_roots: dict[str, Path] = {}
    preparation_errors: dict[str, list[str]] = {}
    for source_root in reused_product_roots:
        source_meta = read_json(source_root.resolve() / "meta.json")
        product_id = str(source_meta.get("productId") or source_root.name)
        try:
            destination = products_root / product_id
            copy_reused_product(source_root, destination, run_id)
            prepared_roots[product_id] = destination
        except Exception as exc:
            preparation_errors.setdefault(product_id, []).append(
                f"reuse: {type(exc).__name__}: {exc}"
            )

    for capture_path in capture_paths:
        capture = read_json(capture_path.resolve())
        product_id = extract_product_id(str(capture.get("pageUrl") or "")) or "unknown"
        try:
            candidate = candidates_by_id[product_id]
            destination = products_root / product_id
            ingest_browser_capture(capture_path, candidate, destination, run_id)
            prepared_roots[product_id] = destination
        except Exception as exc:
            preparation_errors.setdefault(product_id, []).append(
                f"capture: {type(exc).__name__}: {exc}"
            )

    state_by_id: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        product_id = str(candidate["product_id"])
        state_by_id[product_id] = {
            "product_id": product_id,
            "rank": candidate.get("rank"),
            "status": (
                "detail_collected"
                if product_id in prepared_roots
                else "failed_preparation"
                if product_id in preparation_errors
                else "pending_detail_collection"
            ),
            "errors": preparation_errors.get(product_id, []),
            "updated_at": iso_now(),
        }
    state_path = run_root / "batch_state.json"
    write_json(state_path, list(state_by_id.values()))

    for product_id, product_root in prepared_roots.items():
        state = state_by_id[product_id]
        try:
            meta = read_json(product_root / "meta.json")
            ocr_count = successful_ocr_count(product_root)
            if run_ocr_enabled and ocr_count == 0:
                image_range = meta.get("ocrImageRange") or []
                if len(image_range) != 2:
                    raise ValueError("没有可用于 OCR 的高清详情图范围")
                run_ocr(
                    product_root=product_root,
                    cache_dir=cache_dir,
                    start=int(image_range[0]),
                    end=int(image_range[1]),
                )
            ocr_count = successful_ocr_count(product_root)
            if ocr_count == 0:
                raise ValueError("OCR未产生任何具备完整文本和JSON产物的成功图片")
            run_analysis(product_root, rule_config, write_run_outputs=False)
            state["status"] = "success"
        except Exception as exc:
            state["status"] = "failed_processing"
            state["errors"].append(f"{type(exc).__name__}: {exc}")
        state["updated_at"] = iso_now()
        write_json(state_path, list(state_by_id.values()))

    records = [
        build_batch_record(
            candidate,
            prepared_roots.get(str(candidate["product_id"])),
            state_by_id[str(candidate["product_id"])],
        )
        for candidate in candidates
    ]
    batch_payload = {
        "run_id": run_id,
        "phase": 5,
        "generated_at": iso_now(),
        "keyword": search_payload.get("keyword") or "",
        "search_results_path": search_results.as_posix(),
        "search_snapshot_sha256": search_payload.get("snapshot_sha256"),
        "search_raw_count": search_payload.get("raw_card_count", len(candidates)),
        "search_deduplicated_count": search_payload.get(
            "deduplicated_count", len(candidates)
        ),
        "candidate_count": len(candidates),
        "products": records,
    }
    products_json_path = run_root / "products.json"
    products_csv_path = run_root / "products.csv"
    summary_path = run_root / "summary.md"
    write_json(products_json_path, batch_payload)
    write_batch_csv(products_csv_path, records)
    summary_path.write_text(
        build_batch_summary(batch_payload, records), encoding="utf-8"
    )
    return {
        "run_root": run_root,
        "state": state_path,
        "products_json": products_json_path,
        "products_csv": products_csv_path,
        "summary": summary_path,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="批量串联详情图、OCR 与本地功效规则分析")
    parser.add_argument("--search-results", type=Path, default=DEFAULT_SEARCH_RESULTS)
    parser.add_argument("--output-root", type=Path, default=Path("output"))
    parser.add_argument("--rule-config", type=Path, default=DEFAULT_RULE_CONFIG)
    parser.add_argument(
        "--cache-dir", type=Path, default=Path.home() / ".cache" / "paddlex"
    )
    parser.add_argument("--reuse-product-root", type=Path, action="append", default=[])
    parser.add_argument("--capture", type=Path, action="append", default=[])
    parser.add_argument("--run-id")
    parser.add_argument("--skip-ocr", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    outputs = run_batch(
        search_results=args.search_results,
        output_root=args.output_root,
        rule_config=args.rule_config,
        cache_dir=args.cache_dir,
        reused_product_roots=args.reuse_product_root,
        capture_paths=args.capture,
        run_id=args.run_id,
        run_ocr_enabled=not args.skip_ocr,
    )
    print(f"Phase 5 run: {outputs['run_root']}")
    print(f"Phase 5 summary: {outputs['summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
