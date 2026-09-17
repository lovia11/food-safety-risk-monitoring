"""Benchmark PP-OCRv6 GPU profiles against an existing CPU OCR run.

This tool is intentionally isolated from the production pipeline. It reads the
already collected product images, writes results under the product's ignored
``benchmarks/`` directory, and never overwrites ``ocr/`` artifacts.
"""

from __future__ import annotations

import argparse
import difflib
import importlib.metadata
import json
import os
import statistics
import time
from pathlib import Path
from typing import Any

from src.phase2_ocr import (
    extract_lines,
    keyword_hits,
    ocr_image_numbers_from_meta,
    result_to_dict,
    select_images,
)


PROFILE_MODELS = {
    "gpu-medium": {
        "detection": "PP-OCRv6_medium_det",
        "recognition": "PP-OCRv6_medium_rec",
    },
    "gpu-small": {
        "detection": "PP-OCRv6_small_det",
        "recognition": "PP-OCRv6_small_rec",
    },
}


def _version(distribution: str) -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default
    except (OSError, ValueError, TypeError):
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalize_text(text: str) -> str:
    return "".join(text.split())


def _similarity(left: str, right: str) -> float | None:
    left = _normalize_text(left)
    right = _normalize_text(right)
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return round(difflib.SequenceMatcher(None, left, right).ratio(), 4)


def baseline_summary(product_root: Path) -> dict[str, Any]:
    manifest = _read_json(product_root / "ocr" / "manifest.json", [])
    items = [item for item in manifest if isinstance(item, dict)]
    elapsed = [
        float(item.get("elapsedSeconds") or 0)
        for item in items
        if item.get("status") == "success"
    ]
    keyword_union = sorted(
        {
            str(term)
            for item in items
            for term in (item.get("keywordHits") or [])
            if str(term).strip()
        }
    )
    return {
        "available": bool(items),
        "imageCount": len(items),
        "successCount": sum(item.get("status") == "success" for item in items),
        "totalImageSeconds": round(sum(elapsed), 3),
        "meanImageSeconds": round(statistics.fmean(elapsed), 3) if elapsed else None,
        "medianImageSeconds": round(statistics.median(elapsed), 3) if elapsed else None,
        "keywordHits": keyword_union,
    }


def profile_config(profile: str) -> dict[str, str]:
    if profile not in PROFILE_MODELS:
        raise ValueError(f"unknown profile: {profile}")
    return dict(PROFILE_MODELS[profile])


def _create_engine(
    profile: str,
    cache_dir: Path,
    recognition_batch_size: int,
):
    cache_dir = cache_dir.resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(cache_dir))
    os.environ.setdefault("PADDLE_PDX_MODEL_SOURCE", "bos")
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

    import paddle
    from paddleocr import PaddleOCR

    if not paddle.is_compiled_with_cuda():
        raise RuntimeError(
            "当前Python环境不是GPU版PaddlePaddle；请使用.venv-gpu执行此工具"
        )
    paddle.set_device("gpu:0")
    models = profile_config(profile)
    started = time.perf_counter()
    engine = PaddleOCR(
        lang="ch",
        ocr_version="PP-OCRv6",
        text_detection_model_name=models["detection"],
        text_recognition_model_name=models["recognition"],
        text_recognition_batch_size=recognition_batch_size,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        device="gpu:0",
        engine="paddle",
    )
    return engine, paddle, round(time.perf_counter() - started, 3)


def run_benchmark(
    product_root: Path,
    profile: str,
    cache_dir: Path,
    score_threshold: float = 0.5,
    recognition_batch_size: int = 8,
    max_images: int | None = None,
) -> Path:
    product_root = product_root.resolve()
    models = profile_config(profile)
    image_numbers = ocr_image_numbers_from_meta(product_root)
    image_dir = product_root / "images" / "original"
    images = (
        select_images(image_dir, 1, 10**9, image_numbers=image_numbers)
        if image_dir.is_dir()
        else []
    )
    if max_images is not None:
        images = images[:max_images]
    if not images:
        raise FileNotFoundError("没有找到可用于benchmark的OCR候选原图")

    output_dir = product_root / "benchmarks" / profile
    output_dir.mkdir(parents=True, exist_ok=True)
    baseline = baseline_summary(product_root)

    wall_started = time.perf_counter()
    engine, paddle, initialization_seconds = _create_engine(
        profile,
        cache_dir,
        recognition_batch_size,
    )

    import cv2
    import numpy as np

    manifest: list[dict[str, Any]] = []
    for ordinal, image_path in enumerate(images, start=1):
        started = time.perf_counter()
        print(
            f"[{ordinal:02d}/{len(images):02d}] {profile} {image_path.name}",
            flush=True,
        )
        item: dict[str, Any] = {
            "image": image_path.name,
            "status": "failed",
        }
        try:
            image_array = cv2.imdecode(
                np.frombuffer(image_path.read_bytes(), dtype=np.uint8),
                cv2.IMREAD_COLOR,
            )
            if image_array is None:
                raise ValueError("OpenCV failed to decode image bytes")
            height, width = image_array.shape[:2]
            result_objects = list(engine.predict(image_array))
            structured = [result_to_dict(result) for result in result_objects]
            lines = extract_lines(structured, score_threshold)
            plain_lines = [
                line["text"] for line in lines if line["includedInPlainText"]
            ]
            plain_text = "\n".join(plain_lines)
            benchmark_text_path = output_dir / f"{image_path.stem}.txt"
            benchmark_json_path = output_dir / f"{image_path.stem}.json"
            benchmark_text_path.write_text(plain_text, encoding="utf-8")
            _write_json(
                benchmark_json_path,
                {
                    "image": image_path.name,
                    "profile": profile,
                    "models": models,
                    "lines": lines,
                },
            )
            baseline_text_path = product_root / "ocr" / f"{image_path.stem}.txt"
            baseline_text = (
                baseline_text_path.read_text(encoding="utf-8")
                if baseline_text_path.is_file()
                else ""
            )
            item.update(
                {
                    "status": "success",
                    "width": width,
                    "height": height,
                    "lineCount": len(plain_lines),
                    "characterCount": len(_normalize_text(plain_text)),
                    "keywordHits": keyword_hits(plain_text),
                    "baselineTextSimilarity": _similarity(baseline_text, plain_text),
                }
            )
        except Exception as exc:
            item["error"] = f"{type(exc).__name__}: {exc}"
        item["elapsedSeconds"] = round(time.perf_counter() - started, 3)
        manifest.append(item)
        _write_json(output_dir / "manifest.json", manifest)

    success_times = [
        float(item["elapsedSeconds"])
        for item in manifest
        if item.get("status") == "success"
    ]
    keyword_union = sorted(
        {
            str(term)
            for item in manifest
            for term in (item.get("keywordHits") or [])
            if str(term).strip()
        }
    )
    similarities = [
        float(item["baselineTextSimilarity"])
        for item in manifest
        if item.get("status") == "success"
        and item.get("baselineTextSimilarity") is not None
    ]
    baseline_total = baseline.get("totalImageSeconds")
    benchmark_total = round(sum(success_times), 3)
    speedup = (
        round(float(baseline_total) / benchmark_total, 2)
        if baseline_total and benchmark_total > 0 and len(images) == baseline.get("imageCount")
        else None
    )
    result = {
        "profile": profile,
        "models": models,
        "device": str(paddle.get_device()),
        "paddleVersion": str(paddle.__version__),
        "paddleOcrVersion": _version("paddleocr"),
        "paddleXVersion": _version("paddlex"),
        "recognitionBatchSize": recognition_batch_size,
        "scoreThreshold": score_threshold,
        "imageCount": len(images),
        "successCount": len(success_times),
        "failedCount": len(images) - len(success_times),
        "engineInitializationSeconds": initialization_seconds,
        "totalImageSeconds": benchmark_total,
        "meanImageSeconds": round(statistics.fmean(success_times), 3)
        if success_times
        else None,
        "medianImageSeconds": round(statistics.median(success_times), 3)
        if success_times
        else None,
        "firstImageSeconds": success_times[0] if success_times else None,
        "medianExcludingFirstSeconds": (
            round(statistics.median(success_times[1:]), 3)
            if len(success_times) > 1
            else None
        ),
        "wallSeconds": round(time.perf_counter() - wall_started, 3),
        "keywordHits": keyword_union,
        "meanBaselineTextSimilarity": (
            round(statistics.fmean(similarities), 4) if similarities else None
        ),
        "baseline": baseline,
        "speedupVsFullCpuBaseline": speedup,
        "missingBaselineKeywordHits": sorted(
            set(baseline.get("keywordHits") or []) - set(keyword_union)
        ),
        "extraKeywordHits": sorted(
            set(keyword_union) - set(baseline.get("keywordHits") or [])
        ),
        "manifest": manifest,
        "note": (
            "baselineTextSimilarity仅表示与现有CPU medium文本的一致程度，不代表OCR真实准确率。"
        ),
    }
    result_path = output_dir / "benchmark.json"
    _write_json(result_path, result)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    print(f"Benchmark result: {result_path}", flush=True)
    return result_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="对已经采集的真实淘宝详情图进行独立PP-OCRv6 GPU benchmark"
    )
    parser.add_argument("--product-root", type=Path, required=True)
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILE_MODELS),
        required=True,
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path.home() / ".cache" / "paddlex-gpu",
    )
    parser.add_argument("--score-threshold", type=float, default=0.5)
    parser.add_argument("--recognition-batch-size", type=int, default=8)
    parser.add_argument(
        "--max-images",
        type=int,
        default=None,
        help="仅用于快速冒烟测试；正式对比请省略此参数",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.recognition_batch_size < 1:
        raise SystemExit("--recognition-batch-size必须大于0")
    if args.max_images is not None and args.max_images < 1:
        raise SystemExit("--max-images必须大于0")
    run_benchmark(
        product_root=args.product_root,
        profile=args.profile,
        cache_dir=args.cache_dir,
        score_threshold=args.score_threshold,
        recognition_batch_size=args.recognition_batch_size,
        max_images=args.max_images,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
