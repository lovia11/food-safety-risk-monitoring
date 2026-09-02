"""Stable JSON contract for a small local web dashboard.

The collector remains independent of any frontend framework.  A future page
only needs to poll ``web_snapshot.json`` and serve the relative asset paths from
the run directory.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from src.phase5_batch import build_batch_record
from src.runtime import iso_now, read_json, write_json


WEB_SCHEMA_VERSION = 1

STATUS_PRESENTATION = {
    "pending_detail_collection": ("待采集", "neutral"),
    "collecting_detail": ("详情采集中", "running"),
    "detail_collected": ("详情已采集", "info"),
    "processing_ocr_analysis": ("OCR 与分析中", "running"),
    "success": ("已完成", "success"),
    "failed_collection": ("详情采集失败", "danger"),
    "failed_processing": ("OCR 或分析失败", "danger"),
    "failed_preparation": ("数据准备失败", "danger"),
}

STAGE_PRESENTATION = {
    "initializing": "正在初始化",
    "searching": "正在搜索商品",
    "collecting_details": "正在采集商品详情",
    "processing_ocr_analysis": "正在执行 OCR 与风险分析",
    "manual_action_required": "需要人工登录或验证",
    "collection_completed": "详情采集已完成",
    "completed": "任务已完成",
    "completed_with_errors": "任务完成，但存在失败项",
    "interrupted": "任务已中止，可断点续跑",
    "failed": "任务失败",
}

TERMINAL_STAGES = {
    "collection_completed",
    "completed",
    "completed_with_errors",
    "interrupted",
    "failed",
}

DETAIL_AVAILABLE_STATUSES = {
    "detail_collected",
    "processing_ocr_analysis",
    "failed_processing",
    "success",
}


def _read_optional_json(path: Path, default: Any) -> Any:
    try:
        return read_json(path) if path.exists() else default
    except (OSError, ValueError, TypeError):
        return default


def _asset_path(product_id: str, local_path: str | None) -> str | None:
    if not local_path:
        return None
    normalized = str(local_path).replace("\\", "/")
    return f"products/{product_id}/{normalized}"


def _status_view(code: str) -> dict[str, str]:
    label, tone = STATUS_PRESENTATION.get(code, (code or "未知", "neutral"))
    return {"code": code, "label": label, "tone": tone}


def _risk_view(record: dict[str, Any]) -> dict[str, Any]:
    review_required = record.get("review_required")
    effects = record.get("detected_effects") or []
    if review_required:
        level, label, tone = "review", "发现线索，建议复核", "warning"
    elif review_required is False:
        level, label, tone = "no_explicit_clue", "未发现明确功效表达", "info"
    else:
        level, label, tone = "not_analyzed", "尚未分析", "neutral"
    return {
        "level": level,
        "label": label,
        "tone": tone,
        "detectedEffects": effects,
        "matchedKeywords": record.get("matched_keywords") or {},
        "reason": record.get("risk_reason") or "",
        "reviewRequired": review_required,
        "evidence": record.get("evidence") or [],
        "evidenceDetails": record.get("evidence_details") or [],
        "sourceCounts": record.get("evidence_source_counts") or {},
        "originCounts": record.get("evidence_origin_counts") or {},
    }


def _product_assets(run_root: Path, product_id: str) -> dict[str, Any]:
    product_root = run_root / "products" / product_id
    meta = _read_optional_json(product_root / "meta.json", {})
    images = []
    for item in meta.get("images") or []:
        local_path = item.get("localPath") or item.get("savedPath")
        images.append(
            {
                "index": item.get("index"),
                "path": _asset_path(product_id, local_path),
                "sourceUrl": item.get("url"),
                "width": item.get("naturalWidth"),
                "height": item.get("naturalHeight"),
                "ocrCandidate": bool(
                    item.get("ocrCandidate") or item.get("ocrSizeCandidate")
                ),
                "acquisitionMethod": item.get("acquisitionMethod"),
            }
        )

    screenshots = [
        _asset_path(product_id, item) for item in (meta.get("screenshots") or [])
    ]
    screenshots = [item for item in screenshots if item]

    ocr_items = []
    manifest = _read_optional_json(product_root / "ocr" / "manifest.json", [])
    manifest_items = manifest if isinstance(manifest, list) else []
    for item in manifest_items:
        ocr_items.append(
            {
                "image": item.get("image"),
                "imagePath": _asset_path(product_id, item.get("sourcePath")),
                "status": item.get("status"),
                "lineCount": item.get("lineCount"),
                "characterCount": item.get("characterCount"),
                "averageConfidence": item.get("averageConfidence"),
                "textPath": _asset_path(product_id, item.get("textPath")),
                "jsonPath": _asset_path(product_id, item.get("jsonPath")),
                "error": item.get("error"),
            }
        )

    overview = _asset_path(product_id, "page/overview.png")
    if not (product_root / "page" / "overview.png").exists():
        overview = screenshots[0] if screenshots else None
    return {
        "overview": overview,
        "screenshots": screenshots,
        "originalImages": images,
        "ocrItems": ocr_items,
        "metaPath": _asset_path(product_id, "meta.json")
        if (product_root / "meta.json").exists()
        else None,
        "analysisPath": _asset_path(product_id, "analysis.json")
        if (product_root / "analysis.json").exists()
        else None,
    }


def _product_view(
    run_root: Path,
    record: dict[str, Any],
    rank: int | None,
) -> dict[str, Any]:
    product_id = str(record.get("product_id") or "")
    status_code = str(record.get("crawl_status") or "")
    product_root = run_root / "products" / product_id
    meta = _read_optional_json(product_root / "meta.json", {})
    analysis = _read_optional_json(product_root / "analysis.json", {})
    risk_record = dict(record)
    for field in (
        "detected_effects",
        "matched_keywords",
        "risk_reason",
        "review_required",
        "evidence",
        "evidence_details",
        "evidence_source_counts",
        "evidence_origin_counts",
    ):
        if field in analysis:
            risk_record[field] = analysis[field]
    return {
        "id": product_id,
        "rank": rank if rank is not None else meta.get("rank"),
        "keyword": record.get("keyword") or "",
        "name": record.get("product_name") or "",
        "shopName": record.get("shop_name") or "",
        "region": record.get("region") or "",
        "productUrl": record.get("product_url") or "",
        "collectedAt": meta.get("crawlTime"),
        "status": _status_view(status_code),
        "counts": {
            "originalImages": int(record.get("original_image_count") or 0),
            "ocrImages": int(record.get("ocr_image_count") or 0),
        },
        "risk": _risk_view(risk_record),
        "assets": _product_assets(run_root, product_id),
        "errors": record.get("errors") or [],
    }


def _statistics(batch_payload: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, int]:
    statuses = [str(item.get("crawl_status") or "") for item in records]
    detail_count = sum(
        int(item.get("original_image_count") or 0) > 0
        or str(item.get("crawl_status") or "") in DETAIL_AVAILABLE_STATUSES
        for item in records
    )
    return {
        "searchRaw": int(batch_payload.get("search_raw_count") or 0),
        "searchDeduplicated": int(batch_payload.get("search_deduplicated_count") or 0),
        "selectedProducts": len(records),
        "detailCollectedProducts": detail_count,
        "analyzedProducts": sum(code == "success" for code in statuses),
        "originalImages": sum(int(item.get("original_image_count") or 0) for item in records),
        "ocrImages": sum(int(item.get("ocr_image_count") or 0) for item in records),
        "clueProducts": sum(bool(item.get("detected_effects")) for item in records),
        "reviewRequiredProducts": sum(item.get("review_required") is True for item in records),
        "failedProducts": sum(code.startswith("failed") for code in statuses),
    }


def build_web_snapshot(
    run_root: Path,
    batch_payload: dict[str, Any],
    records: list[dict[str, Any]],
    stage: str,
    message: str = "",
) -> dict[str, Any]:
    run_root = run_root.resolve()
    ranks = {
        str(item.get("product_id")): item.get("rank")
        for item in (batch_payload.get("candidates") or [])
    }
    product_views = [
        _product_view(run_root, record, ranks.get(str(record.get("product_id") or "")))
        for record in records
    ]
    product_views.sort(key=lambda item: int(item.get("rank") or 10**9))
    return {
        "schemaVersion": WEB_SCHEMA_VERSION,
        "generatedAt": iso_now(),
        "task": {
            "id": run_root.name,
            "keyword": batch_payload.get("keyword") or "",
            "stage": stage,
            "stageLabel": STAGE_PRESENTATION.get(stage, stage),
            "terminal": stage in TERMINAL_STAGES,
            "message": message,
        },
        "statistics": _statistics(batch_payload, records),
        "products": product_views,
        "exports": {
            "productsJson": "products.json",
            "productsCsv": "products.csv",
            "summaryMarkdown": "summary.md",
            "runLog": "run.log",
        },
        "api": {
            "self": f"/api/runs/{run_root.name}",
            "assetBase": f"/api/runs/{run_root.name}/files/",
        },
        "disclaimer": "结果仅为页面风险线索，不认定商品违法、功效真实、非法添加或检出任何药物。",
    }


def write_web_snapshot(
    run_root: Path,
    batch_payload: dict[str, Any],
    records: list[dict[str, Any]],
    stage: str,
    message: str = "",
) -> Path:
    destination = run_root.resolve() / "web_snapshot.json"
    write_json(
        destination,
        build_web_snapshot(run_root, batch_payload, records, stage, message),
    )
    return destination


def _derive_stage(states: list[dict[str, Any]], run_config: dict[str, Any]) -> str:
    statuses = [str(item.get("status") or "") for item in states]
    if any(item == "collecting_detail" for item in statuses):
        return "collecting_details"
    if any(item == "processing_ocr_analysis" for item in statuses):
        return "processing_ocr_analysis"
    if any(item.startswith("failed") for item in statuses):
        return "completed_with_errors"
    if statuses and all(item == "success" for item in statuses):
        return "completed"
    if statuses and all(item in DETAIL_AVAILABLE_STATUSES for item in statuses):
        return "collection_completed" if run_config.get("skip_ocr") else "interrupted"
    return "initializing"


def snapshot_existing_run(
    run_root: Path,
    stage: str | None = None,
    message: str = "",
) -> Path:
    """Create the web contract for an existing run without accessing Taobao."""

    run_root = run_root.resolve()
    search_payload = _read_optional_json(
        run_root / "search" / "search_candidates.json", {}
    )
    candidates = search_payload.get("candidates") or []
    states = _read_optional_json(run_root / "batch_state.json", [])
    state_by_id = {
        str(item.get("product_id")): item
        for item in states
        if isinstance(item, dict) and item.get("product_id")
    }
    records = []
    existing_batch = _read_optional_json(run_root / "products.json", {})
    existing_records = [
        item
        for item in (existing_batch.get("products") or [])
        if isinstance(item, dict) and item.get("product_id")
    ]
    # A resumed run can overwrite ``search_candidates.json`` with only the
    # remaining/single product while ``products.json`` still contains the full
    # successfully collected batch.  The web view must never shrink the batch
    # merely because a later resume used a narrower candidate set.
    if existing_records and len(existing_records) >= len(candidates):
        records = existing_records
        candidates = [
            {
                "keyword": item.get("keyword") or existing_batch.get("keyword") or "",
                "product_id": str(item.get("product_id") or ""),
                "product_name": item.get("product_name") or "",
                "product_url": item.get("product_url") or "",
                "shop_name": item.get("shop_name") or "",
                "region": item.get("region") or "",
                "rank": item.get("rank")
                or (state_by_id.get(str(item.get("product_id") or "")) or {}).get(
                    "rank"
                ),
            }
            for item in records
        ]
    if not records:
        for candidate in candidates:
            product_id = str(candidate.get("product_id") or "")
            state = state_by_id.get(
                product_id,
                {"status": "pending_detail_collection", "errors": []},
            )
            product_root = run_root / "products" / product_id
            if stage == "interrupted" and state.get("status") in {
                "collecting_detail",
                "processing_ocr_analysis",
            }:
                state = dict(state)
                state["status"] = (
                    "detail_collected"
                    if (product_root / "meta.json").exists()
                    else "pending_detail_collection"
                )
            records.append(
                build_batch_record(
                    candidate,
                    product_root if (product_root / "meta.json").exists() else None,
                    state,
                )
            )
    batch_payload = {
        "run_id": run_root.name,
        "keyword": search_payload.get("keyword")
        or existing_batch.get("keyword")
        or "",
        "search_raw_count": search_payload.get(
            "raw_card_count", existing_batch.get("search_raw_count", len(candidates))
        ),
        "search_deduplicated_count": search_payload.get(
            "deduplicated_count",
            existing_batch.get("search_deduplicated_count", len(candidates)),
        ),
        "candidates": candidates,
    }
    run_config = _read_optional_json(run_root / "run_config.json", {})
    selected_stage = stage or _derive_stage(states, run_config)
    return write_web_snapshot(
        run_root,
        batch_payload,
        records,
        selected_stage,
        message,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="为已有运行目录生成网页数据快照")
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--stage", choices=tuple(STAGE_PRESENTATION))
    parser.add_argument("--message", default="")
    args = parser.parse_args(argv)
    destination = snapshot_existing_run(args.run_root, args.stage, args.message)
    print(f"网页数据快照：{destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
