"""Build one current-contract validation run from audited historical artifacts.

The historical source is treated as read-only.  This adapter copies only the
five explicitly audited products, preserves their collected artifacts byte for
byte, and derives only current-version Recommendation and run wrapper files.
It never invokes the collector, OCR, or Phase 3 analysis.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data_store import DEFAULT_MONITOR_CONFIG_PATHS, DataStore
from src.inspection_runtime import (
    INSPECTION_RECOMMENDATION_ERROR_FILE,
    INSPECTION_RECOMMENDATION_FILE,
    InspectionRuntime,
)
from src.phase5_batch import build_batch_record, build_batch_summary, write_batch_csv
from src.runtime import iso_now, read_json, write_json
from src.web_contract import build_web_snapshot


DEFAULT_SOURCE_ROOT = Path(r"D:\毕业设计\output")
DEFAULT_OUTPUT_ROOT = Path("output")
DEFAULT_DATABASE_PATH = Path("data/app.db")
DEFAULT_RUN_ID = "historical_validation_20260911"
DEFAULT_DISPLAY_NAME = "历史真实样例验收集"
CODE_BASELINE = "38904fb5c648ea4a6f66b86d6107f387041cbda4"


class HistoricalValidationError(RuntimeError):
    """A historical source or destination violates the validation contract."""


@dataclass(frozen=True)
class ValidationItem:
    source_run_id: str
    product_id: str
    role: str


ALLOW_LIST = (
    ValidationItem(
        "20260902T005526_task",
        "707564797952",
        "sleep_positive_mixed_origin",
    ),
    ValidationItem(
        "20260903T014401_task",
        "674221193698",
        "analysis_zero_evidence",
    ),
    ValidationItem(
        "20260905T161011_task",
        "673981586940",
        "d2_exact_match_negative",
    ),
    ValidationItem(
        "20260902T005526_task",
        "634471255780",
        "rich_evidence",
    ),
    ValidationItem(
        "20260817T181659_batch",
        "600949052422",
        "legacy_batch_compatibility",
    ),
)

_CURRENT_RECOMMENDATION_FILES = {
    INSPECTION_RECOMMENDATION_FILE,
    INSPECTION_RECOMMENDATION_ERROR_FILE,
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = read_json(path)
    except (OSError, ValueError, TypeError) as exc:
        raise HistoricalValidationError(f"{label} 无法解析：{path}: {exc}") from exc
    if not isinstance(value, dict):
        raise HistoricalValidationError(f"{label} 必须包含 JSON 对象：{path}")
    return value


def _json_list(path: Path, label: str) -> list[Any]:
    try:
        value = read_json(path)
    except (OSError, ValueError, TypeError) as exc:
        raise HistoricalValidationError(f"{label} 无法解析：{path}: {exc}") from exc
    if not isinstance(value, list):
        raise HistoricalValidationError(f"{label} 必须包含 JSON 数组：{path}")
    return value


def _parse_json(path: Path, label: str) -> Any:
    try:
        return read_json(path)
    except (OSError, ValueError, TypeError) as exc:
        raise HistoricalValidationError(f"{label} 无法解析：{path}: {exc}") from exc


def _safe_artifact_path(product_root: Path, raw_path: Any, label: str) -> Path:
    normalized = str(raw_path or "").replace("\\", "/").lstrip("/")
    if not normalized:
        raise HistoricalValidationError(f"{label} 缺少 artifact 路径")
    candidate = (product_root / normalized).resolve()
    if not candidate.is_relative_to(product_root) or not candidate.is_file():
        raise HistoricalValidationError(f"{label} artifact 不存在或越界：{normalized}")
    return candidate


def _relative_inventory(product_root: Path) -> list[str]:
    return [
        path.relative_to(product_root).as_posix()
        for path in sorted(product_root.rglob("*"), key=lambda item: item.as_posix())
        if path.is_file()
    ]


def validate_source_item(source_root: Path, item: ValidationItem) -> dict[str, Any]:
    """Validate one audited Level-A source and return its immutable inventory."""

    source_root = source_root.resolve()
    product_root = (
        source_root / item.source_run_id / "products" / item.product_id
    ).resolve()
    expected_parent = (source_root / item.source_run_id / "products").resolve()
    if product_root.parent != expected_parent or not product_root.is_dir():
        raise HistoricalValidationError(f"历史商品目录不存在：{product_root}")

    meta_path = product_root / "meta.json"
    analysis_path = product_root / "analysis.json"
    manifest_path = product_root / "ocr" / "manifest.json"
    combined_path = product_root / "ocr" / "combined_text.txt"
    run_info_path = product_root / "ocr" / "run_info.json"
    meta = _json_object(meta_path, "meta.json")
    analysis = _json_object(analysis_path, "analysis.json")
    manifest = _json_list(manifest_path, "ocr/manifest.json")

    if str(meta.get("productId") or "") != item.product_id:
        raise HistoricalValidationError(
            f"meta.json Product ID 与目录不一致：{item.source_run_id}/{item.product_id}"
        )
    if str(analysis.get("product_id") or "") != item.product_id:
        raise HistoricalValidationError(
            f"analysis.json Product ID 与目录不一致：{item.source_run_id}/{item.product_id}"
        )
    collected_at = str(meta.get("crawlTime") or "").strip()
    if not collected_at:
        raise HistoricalValidationError(f"meta.json 缺少 crawlTime：{product_root}")
    if not combined_path.is_file():
        raise HistoricalValidationError(f"缺少 OCR combined_text.txt：{product_root}")
    if not run_info_path.is_file():
        raise HistoricalValidationError(f"缺少 OCR run_info.json：{product_root}")
    _json_object(run_info_path, "ocr/run_info.json")

    original_root = product_root / "images" / "original"
    originals = sorted(
        (path for path in original_root.iterdir() if path.is_file()),
        key=lambda path: path.name,
    ) if original_root.is_dir() else []
    if not originals:
        raise HistoricalValidationError(f"没有实际原图：{product_root}")

    for ordinal, image in enumerate(meta.get("images") or [], start=1):
        if not isinstance(image, dict):
            raise HistoricalValidationError(f"meta.images[{ordinal}] 不是对象：{product_root}")
        local_path = image.get("localPath") or image.get("savedPath")
        if local_path:
            _safe_artifact_path(product_root, local_path, f"meta.images[{ordinal}]")

    success_items: list[dict[str, Any]] = []
    core_paths = {
        meta_path.resolve(),
        analysis_path.resolve(),
        manifest_path.resolve(),
        combined_path.resolve(),
        run_info_path.resolve(),
        *(path.resolve() for path in originals),
    }
    for ordinal, manifest_item in enumerate(manifest, start=1):
        if not isinstance(manifest_item, dict):
            raise HistoricalValidationError(
                f"ocr/manifest.json 第 {ordinal} 项不是对象：{product_root}"
            )
        if manifest_item.get("status") != "success":
            continue
        source_path = _safe_artifact_path(
            product_root, manifest_item.get("sourcePath"), f"OCR success[{ordinal}] source"
        )
        text_path = _safe_artifact_path(
            product_root, manifest_item.get("textPath"), f"OCR success[{ordinal}] text"
        )
        json_path = _safe_artifact_path(
            product_root, manifest_item.get("jsonPath"), f"OCR success[{ordinal}] json"
        )
        _parse_json(json_path, f"OCR success[{ordinal}] json")
        core_paths.update((source_path, text_path, json_path))
        success_items.append(manifest_item)
    if not success_items:
        raise HistoricalValidationError(f"OCR 没有 success 项：{product_root}")

    inventory = _relative_inventory(product_root)
    source_hashes = {
        path.relative_to(product_root).as_posix(): _sha256(path)
        for path in sorted(core_paths, key=lambda value: value.as_posix())
    }
    evidence_details = analysis.get("evidence_details") or []
    if not isinstance(evidence_details, list):
        raise HistoricalValidationError(f"analysis.evidence_details 必须是数组：{product_root}")
    return {
        "item": item,
        "product_root": product_root,
        "meta": meta,
        "analysis": analysis,
        "manifest": manifest,
        "inventory": inventory,
        "source_hashes": source_hashes,
        "original_count": len(originals),
        "ocr_success_count": len(success_items),
        "ocr_total_count": len(manifest),
        "evidence_count": len(evidence_details),
        "collected_at": collected_at,
    }


def _copy_item(source: dict[str, Any], destination: Path) -> list[str]:
    source_root: Path = source["product_root"]
    copied: list[str] = []
    for relative in source["inventory"]:
        source_path = source_root / relative
        relative_path = Path(relative)
        if relative_path.parent == Path(".") and relative_path.name in _CURRENT_RECOMMENDATION_FILES:
            target = destination / "provenance" / "archive" / f"source_{relative_path.name}"
        else:
            target = destination / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target)
        copied.append(target.relative_to(destination).as_posix())
    return sorted(copied)


def _candidate_from_meta(meta: dict[str, Any], rank: int) -> dict[str, Any]:
    return {
        "keyword": str(meta.get("keyword") or ""),
        "product_id": str(meta.get("productId") or ""),
        "product_name": str(meta.get("productName") or ""),
        "product_url": str(meta.get("productUrl") or ""),
        "source_product_url": str(meta.get("sourceProductUrl") or ""),
        "shop_name": str(meta.get("shopName") or ""),
        "region": str(meta.get("region") or ""),
        "rank": rank,
    }


def _make_recommendation_runtime(output_root: Path) -> tuple[InspectionRuntime, tempfile.TemporaryDirectory[str]]:
    holder = tempfile.TemporaryDirectory(prefix="historical_validation_reference_")
    database_path = Path(holder.name) / "reference.db"
    store = DataStore(database_path, output_root)
    return InspectionRuntime.from_store(store), holder


def build_validation_set(
    source_root: Path,
    output_root: Path,
    *,
    run_id: str = DEFAULT_RUN_ID,
    created_at: str | None = None,
    code_baseline: str = CODE_BASELINE,
    force: bool = False,
    recommendation_runtime: InspectionRuntime | None = None,
) -> dict[str, Any]:
    """Construct one validation run and atomically publish its directory."""

    source_root = source_root.resolve()
    output_root = output_root.resolve()
    if not source_root.is_dir():
        raise HistoricalValidationError(f"历史 source root 不存在：{source_root}")
    if not run_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in run_id):
        raise HistoricalValidationError("validation run_id 只能包含字母、数字、下划线或连字符")
    output_root.mkdir(parents=True, exist_ok=True)
    destination = (output_root / run_id).resolve()
    staging = (output_root / f".{run_id}.building").resolve()
    if destination.parent != output_root or staging.parent != output_root:
        raise HistoricalValidationError("validation destination 必须是 output 的直接子目录")
    if destination.exists() and not force:
        raise HistoricalValidationError(f"validation run 已存在；如需重建请显式使用 --force：{destination}")
    if staging.exists():
        if not force:
            raise HistoricalValidationError(f"发现未完成 staging；如需清理请显式使用 --force：{staging}")
        shutil.rmtree(staging)

    # Validate every source before writing or replacing any destination.
    validated = [validate_source_item(source_root, item) for item in ALLOW_LIST]
    import_time = created_at or iso_now()
    runtime_holder: tempfile.TemporaryDirectory[str] | None = None
    if recommendation_runtime is None:
        recommendation_runtime, runtime_holder = _make_recommendation_runtime(output_root)

    try:
        staging.mkdir(parents=True)
        products_root = staging / "products"
        products_root.mkdir()
        candidates: list[dict[str, Any]] = []
        states: list[dict[str, Any]] = []
        records: list[dict[str, Any]] = []
        manifest_items: list[dict[str, Any]] = []
        for rank, source in enumerate(validated, start=1):
            item: ValidationItem = source["item"]
            product_root = products_root / item.product_id
            copied = _copy_item(source, product_root)
            recommendation_status = "available"
            try:
                recommendation_runtime.generate(product_root)
            except Exception as exc:  # Current runtime owns its formal error artifact.
                recommendation_runtime.record_error(product_root, exc)
                recommendation_status = "error"

            candidate = _candidate_from_meta(source["meta"], rank)
            state = {
                "product_id": item.product_id,
                "rank": rank,
                "status": "success",
                "errors": [],
                "updated_at": import_time,
            }
            record = build_batch_record(candidate, product_root, state)
            record["rank"] = rank
            candidates.append(candidate)
            states.append(state)
            records.append(record)
            manifest_items.append(
                {
                    "sourceRunId": item.source_run_id,
                    "sourceProductId": item.product_id,
                    "sourceProductRoot": source["product_root"].as_posix(),
                    "validationProductRoot": (destination / "products" / item.product_id).as_posix(),
                    "originalCollectedAt": source["collected_at"],
                    "role": item.role,
                    "copiedArtifacts": copied,
                    "sourceHashes": source["source_hashes"],
                    "originalImageCount": source["original_count"],
                    "ocrSuccessCount": source["ocr_success_count"],
                    "ocrTotalCount": source["ocr_total_count"],
                    "evidenceCount": source["evidence_count"],
                    "currentRecommendationStatus": recommendation_status,
                }
            )

        batch_payload = {
            "run_id": run_id,
            "phase": "historical_validation",
            "generated_at": import_time,
            "keyword": "历史真实样例",
            "search_raw_count": len(candidates),
            "search_deduplicated_count": len(candidates),
            "candidate_count": len(candidates),
            "candidates": candidates,
            "products": records,
        }
        task_request = {
            "task_id": run_id,
            "task_type": "quick",
            "keyword": "历史真实样例",
            "display_name": DEFAULT_DISPLAY_NAME,
            "candidate_limit": len(candidates),
            "detail_limit": len(candidates),
            "created_at": import_time,
            "purpose": "historical_validation",
            "no_live_collection": True,
            "runtime_owned": False,
        }
        run_config = {
            "run_id": run_id,
            "generated_at": import_time,
            "task_type": "quick",
            "keyword": "历史真实样例",
            "display_name": DEFAULT_DISPLAY_NAME,
            "candidate_limit": len(candidates),
            "detail_limit": len(candidates),
            "resolved_candidate_limit": len(candidates),
            "resolved_detail_limit": len(candidates),
            "skip_ocr": False,
            "purpose": "historical_validation",
            "no_live_collection": True,
            "source_collection_timestamps_preserved": True,
        }
        search_payload = {
            "run_id": run_id,
            "keyword": "历史真实样例",
            "raw_card_count": len(candidates),
            "deduplicated_count": len(candidates),
            "candidates": candidates,
            "purpose": "historical_validation",
            "no_live_collection": True,
        }
        web_snapshot = build_web_snapshot(
            staging,
            batch_payload,
            records,
            "completed",
            "历史真实样例已导入；未执行实时淘宝采集。",
        )
        web_snapshot["generatedAt"] = import_time
        web_snapshot["task"]["id"] = run_id
        web_snapshot["api"]["self"] = f"/api/runs/{run_id}"
        web_snapshot["api"]["assetBase"] = f"/api/runs/{run_id}/files/"

        write_json(staging / "task_request.json", task_request)
        write_json(staging / "run_config.json", run_config)
        write_json(staging / "batch_state.json", states)
        write_json(staging / "products.json", batch_payload)
        write_batch_csv(staging / "products.csv", records)
        (staging / "summary.md").write_text(
            build_batch_summary(batch_payload, records), encoding="utf-8"
        )
        (staging / "run.log").touch()
        write_json(staging / "search" / "search_candidates.json", search_payload)
        write_json(staging / "web_snapshot.json", web_snapshot)
        validation_manifest = {
            "manifestVersion": 1,
            "purpose": "historical_validation",
            "createdAt": import_time,
            "sourceRoot": source_root.as_posix(),
            "codeBaseline": code_baseline,
            "validationRunId": run_id,
            "displayName": DEFAULT_DISPLAY_NAME,
            "noLiveCollection": True,
            "sourceCollectionTimestampsPreserved": True,
            "items": manifest_items,
        }
        write_json(staging / "historical_validation_manifest.json", validation_manifest)

        if destination.exists():
            if not force:
                raise HistoricalValidationError(f"validation run 已存在：{destination}")
            shutil.rmtree(destination)
        staging.replace(destination)
        return validation_manifest
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    finally:
        if runtime_holder is not None:
            runtime_holder.cleanup()


def initialize_validation_database(
    database_path: Path,
    output_root: Path,
    *,
    run_id: str = DEFAULT_RUN_ID,
    monitor_configs: Iterable[Path] = DEFAULT_MONITOR_CONFIG_PATHS,
) -> tuple[DataStore, dict[str, Any]]:
    """Initialize a fresh current database and import only the validation run."""

    database_path = database_path.resolve()
    output_root = output_root.resolve()
    run_root = (output_root / run_id).resolve()
    if run_root.parent != output_root or not (run_root / "web_snapshot.json").is_file():
        raise HistoricalValidationError(f"validation run 不完整：{run_root}")
    related = [database_path, Path(f"{database_path}-wal"), Path(f"{database_path}-shm")]
    existing = [path for path in related if path.exists()]
    if existing:
        raise HistoricalValidationError(
            "数据库必须由空路径重建；仍存在：" + "、".join(str(path) for path in existing)
        )
    store = DataStore(database_path, output_root)
    store.initialize()
    monitor_imports = []
    for path in monitor_configs:
        if path.is_file():
            monitor_imports.append(store.import_monitor_config(path))
    InspectionRuntime.from_store(store)
    imported = store.import_run(run_root)
    return store, {"monitorImports": monitor_imports, "runImport": imported}


def archive_current_data(
    workspace_root: Path,
    archive_root: Path,
    *,
    archived_at: str | None = None,
) -> dict[str, Any]:
    """Move current output/database into a new audit archive without deletion."""

    workspace_root = workspace_root.resolve()
    output_root = (workspace_root / "output").resolve()
    data_root = (workspace_root / "data").resolve()
    archive_root = archive_root.resolve()
    if output_root.parent != workspace_root or data_root.parent != workspace_root:
        raise HistoricalValidationError("当前 output/data 路径不在 workspace 直接子级")
    if not archive_root.is_relative_to(workspace_root):
        raise HistoricalValidationError("archive 必须位于当前 workspace 内")
    if archive_root.exists():
        raise HistoricalValidationError(f"archive 已存在，拒绝覆盖：{archive_root}")
    if not output_root.is_dir():
        raise HistoricalValidationError(f"当前 output 不存在：{output_root}")

    top_level_directories = sorted(
        path.name for path in output_root.iterdir() if path.is_dir()
    )
    run_ids = sorted(
        path.name
        for path in output_root.iterdir()
        if path.is_dir()
        and (
            (path / "web_snapshot.json").is_file()
            or (path / "task_request.json").is_file()
        )
    )
    database = data_root / "app.db"
    database_files = [
        path
        for path in (database, Path(f"{database}-wal"), Path(f"{database}-shm"))
        if path.is_file()
    ]
    if database not in database_files:
        raise HistoricalValidationError(f"当前 app.db 不存在：{database}")
    database_entries = [
        {
            "sourcePath": path.as_posix(),
            "archivePath": (archive_root / "data" / path.name).as_posix(),
            "sha256": _sha256(path),
            "byteLength": path.stat().st_size,
        }
        for path in database_files
    ]
    manifest = {
        "manifestVersion": 1,
        "purpose": "pre_historical_validation_archive",
        "archivedAt": archived_at or iso_now(),
        "workspaceRoot": workspace_root.as_posix(),
        "output": {
            "sourcePath": output_root.as_posix(),
            "archivePath": (archive_root / "output").as_posix(),
            "runIds": run_ids,
            "topLevelDirectories": top_level_directories,
        },
        "databaseFiles": database_entries,
        "deletionPerformed": False,
    }

    archive_root.mkdir(parents=True)
    shutil.move(str(output_root), str(archive_root / "output"))
    output_root.mkdir()
    archive_data = archive_root / "data"
    archive_data.mkdir()
    for path in database_files:
        shutil.move(str(path), str(archive_data / path.name))
    write_json(archive_root / "archive_manifest.json", manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="从固定白名单历史商品构建当前 Historical Validation Run"
    )
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--created-at")
    parser.add_argument("--code-baseline", default=CODE_BASELINE)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--archive-current-to",
        type=Path,
        help="构建前将当前 output 与 data/app.db 无删除地移动到指定 workspace archive",
    )
    parser.add_argument(
        "--initialize-database",
        action="store_true",
        help="构建后初始化全新数据库并只导入该 validation run",
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE_PATH)
    args = parser.parse_args(argv)
    archive_manifest = None
    if args.archive_current_to is not None:
        archive_manifest = archive_current_data(
            Path.cwd(), args.archive_current_to, archived_at=args.created_at
        )
    manifest = build_validation_set(
        args.source_root,
        args.output_root,
        run_id=args.run_id,
        created_at=args.created_at,
        code_baseline=args.code_baseline,
        force=args.force,
    )
    result: dict[str, Any] = {
        "run": str((args.output_root / args.run_id).resolve()),
        "manifest": manifest,
    }
    if archive_manifest is not None:
        result["archive"] = archive_manifest
    if args.initialize_database:
        store, imported = initialize_validation_database(
            args.database, args.output_root, run_id=args.run_id
        )
        result["database"] = str(args.database.resolve())
        result["databaseImport"] = imported
        result["counts"] = store.table_counts()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
