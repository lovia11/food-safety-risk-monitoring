"""Phase 2: run PaddleOCR on the real high-resolution detail images."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import re
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_HINTS = (
    "酸枣仁",
    "茯苓",
    "百合",
    "桂圆",
    "桑葚",
    "阿胶",
    "配料",
    "原料",
    "睡眠",
    "助眠",
    "入睡",
    "安睡",
    "好眠",
    "深睡",
    "失眠",
    "血压",
    "减脂",
)


@dataclass
class OCRRuntime:
    engine: Any
    cv2: Any
    numpy: Any
    model_info: dict[str, Any]


class OCRStageError(RuntimeError):
    """The OCR stage did not produce any usable image result."""


class OCRRuntimeCompatibilityError(OCRStageError):
    """The installed OCR runtime cannot satisfy the requested model contract."""


def iso_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def image_number(path: Path) -> int | None:
    stem = path.stem
    if not stem.startswith("original_"):
        return None
    tail = stem.removeprefix("original_")
    return int(tail) if tail.isdigit() else None


def select_images(
    directory: Path,
    start: int = 2,
    end: int = 16,
    image_numbers: set[int] | None = None,
) -> list[Path]:
    supported = {".jpg", ".jpeg", ".png", ".webp"}
    selected: list[tuple[int, Path]] = []
    for path in directory.iterdir():
        number = image_number(path)
        if (
            path.is_file()
            and path.suffix.lower() in supported
            and number is not None
            and (
                number in image_numbers
                if image_numbers is not None
                else start <= number <= end
            )
        ):
            selected.append((number, path))
    return [path for _, path in sorted(selected)]


def extract_lines(
    results: Iterable[dict[str, Any]], threshold: float
) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    for page_index, result in enumerate(results):
        texts = list(result.get("rec_texts") or [])
        scores = list(result.get("rec_scores") or [])
        boxes = list(result.get("rec_boxes") or [])
        polys = list(result.get("rec_polys") or [])
        for index, text in enumerate(texts):
            clean = str(text).strip()
            score = float(scores[index]) if index < len(scores) else None
            if not clean:
                continue
            lines.append(
                {
                    "pageIndex": page_index,
                    "lineIndex": index,
                    "text": clean,
                    "score": score,
                    "includedInPlainText": score is None or score >= threshold,
                    "box": boxes[index] if index < len(boxes) else None,
                    "polygon": polys[index] if index < len(polys) else None,
                }
            )
    return lines


def keyword_hits(text: str, hints: Iterable[str] = DEFAULT_HINTS) -> list[str]:
    return [hint for hint in hints if hint in text]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _installed_version(distribution: str) -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def _version_tuple(value: str) -> tuple[int, ...]:
    match = re.match(r"^(\d+(?:\.\d+)*)", value)
    return tuple(int(part) for part in match.group(1).split(".")) if match else ()


def validate_ocr_runtime_compatibility(
    ocr_version: str,
    paddleocr_version: str,
    paddlex_version: str | None = None,
    paddlepaddle_version: str | None = None,
    python_version: tuple[int, int] | None = None,
) -> None:
    """Fail before model construction for known incompatible combinations."""

    if ocr_version == "PP-OCRv6" and _version_tuple(paddleocr_version) < (3, 7, 0):
        raise OCRRuntimeCompatibilityError(
            "PP-OCRv6需要paddleocr>=3.7.0；"
            f"当前检测到paddleocr=={paddleocr_version}。"
            "请按requirements-ocr.txt重建或同步当前Python环境。"
        )
    if ocr_version == "PP-OCRv6" and paddlex_version is not None:
        if _version_tuple(paddlex_version) < (3, 7, 2):
            raise OCRRuntimeCompatibilityError(
                "PP-OCRv6稳定基线需要paddlex>=3.7.2；"
                f"当前检测到paddlex=={paddlex_version}。"
            )
    if paddlepaddle_version is not None and paddlepaddle_version != "3.2.0":
        raise OCRRuntimeCompatibilityError(
            "当前项目OCR稳定基线需要paddlepaddle==3.2.0；"
            f"当前检测到paddlepaddle=={paddlepaddle_version}。"
        )
    actual_python = python_version or sys.version_info[:2]
    if tuple(actual_python) != (3, 10):
        raise OCRRuntimeCompatibilityError(
            "当前项目OCR稳定基线需要Python 3.10.x；"
            f"当前检测到Python {actual_python[0]}.{actual_python[1]}。"
        )


def ocr_environment_info(
    ocr_version: str,
    model_source: str,
    score_threshold: float,
    device: str = "cpu",
) -> dict[str, Any]:
    paddle_version = _installed_version("paddlepaddle")
    return {
        "pythonVersion": ".".join(str(part) for part in sys.version_info[:3]),
        "paddlepaddleVersion": paddle_version,
        # Keep the historical key readable for existing run consumers.
        "paddleVersion": paddle_version,
        "paddleocrVersion": _installed_version("paddleocr"),
        "paddlexVersion": _installed_version("paddlex"),
        "ocrVersion": ocr_version,
        "modelSource": model_source,
        "device": device,
        "scoreThreshold": score_threshold,
    }


def _record_stage_error(output_dir: Path, exc: BaseException) -> None:
    write_json(
        output_dir / "stage_error.json",
        {
            "status": "failed",
            "failedAt": iso_now(),
            "errorType": type(exc).__name__,
            "message": str(exc),
        },
    )


def ocr_image_numbers_from_meta(product_root: Path) -> set[int] | None:
    meta_path = product_root / "meta.json"
    if not meta_path.exists():
        return None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    explicit = meta.get("ocrImageNumbers")
    if isinstance(explicit, list):
        return {int(value) for value in explicit if str(value).isdigit()}
    images = meta.get("images")
    if isinstance(images, list):
        selected = {
            int(item["index"])
            for item in images
            if item.get("index") is not None
            and (item.get("ocrCandidate") or item.get("ocrSizeCandidate"))
        }
        if selected:
            return selected
    image_range = meta.get("ocrImageRange")
    if (
        isinstance(image_range, list)
        and len(image_range) == 2
        and all(str(value).isdigit() for value in image_range)
    ):
        start, end = (int(value) for value in image_range)
        return set(range(start, end + 1))
    return None


def create_ocr_runtime(
    cache_dir: Path,
    ocr_version: str = "PP-OCRv6",
    model_source: str = "bos",
) -> OCRRuntime:
    cache_dir = cache_dir.resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(cache_dir))
    os.environ.setdefault("PADDLE_PDX_MODEL_SOURCE", model_source)
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

    import cv2
    import numpy as np
    import paddle
    import paddleocr as paddleocr_package
    import paddlex as paddlex_package

    validate_ocr_runtime_compatibility(
        ocr_version,
        str(paddleocr_package.__version__),
        str(paddlex_package.__version__),
        str(paddle.__version__),
    )
    from paddleocr import PaddleOCR

    print(f"Initializing PaddleOCR {ocr_version} on CPU", flush=True)
    engine = PaddleOCR(
        lang="ch",
        ocr_version=ocr_version,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        device="cpu",
        engine="paddle",
    )
    return OCRRuntime(
        engine=engine,
        cv2=cv2,
        numpy=np,
        model_info={
            "pythonVersion": ".".join(str(part) for part in sys.version_info[:3]),
            "paddlepaddleVersion": paddle.__version__,
            "paddleVersion": paddle.__version__,
            "paddleocrVersion": paddleocr_package.__version__,
            "paddlexVersion": paddlex_package.__version__,
            "ocrVersion": ocr_version,
            "modelSource": model_source,
            "device": paddle.get_device(),
        },
    )


def result_to_dict(result: Any) -> dict[str, Any]:
    payload = result.json
    if isinstance(payload, dict) and "res" in payload:
        return payload["res"]
    if isinstance(payload, dict):
        return payload
    raise TypeError(f"Unexpected PaddleOCR result type: {type(payload)!r}")


def build_report(
    product_root: Path,
    manifest: list[dict[str, Any]],
    model_info: dict[str, Any],
    started_at: str,
    elapsed_seconds: float,
) -> str:
    successes = [item for item in manifest if item["status"] == "success"]
    failures = [item for item in manifest if item["status"] != "success"]
    total_lines = sum(item.get("lineCount", 0) for item in successes)
    total_chars = sum(item.get("characterCount", 0) for item in successes)
    hit_images = [item for item in successes if item.get("keywordHits")]
    confidence_values = [
        score
        for item in successes
        for score in item.get("scores", [])
        if score is not None
    ]
    average_confidence = (
        statistics.fmean(confidence_values) if confidence_values else None
    )
    rows = []
    for item in manifest:
        hits = "、".join(item.get("keywordHits", [])) or "—"
        avg = item.get("averageConfidence")
        avg_text = f"{avg:.3f}" if isinstance(avg, float) else "—"
        rows.append(
            f"| `{item['image']}` | {item['status']} | {item.get('lineCount', 0)} | "
            f"{item.get('characterCount', 0)} | {avg_text} | {hits} |"
        )
    failure_lines = [
        f"- `{item['image']}`：{item.get('error', 'unknown error')}" for item in failures
    ] or ["- 无"]
    avg_summary = f"{average_confidence:.3f}" if average_confidence is not None else "—"
    image_range = "—"
    if manifest:
        first_image = manifest[0]["image"]
        last_image = manifest[-1]["image"]
        image_range = first_image if first_image == last_image else f"{first_image}～{last_image}"
    return "\n".join(
        [
            "# Phase 2 单商品 OCR 报告",
            "",
            "## 结论",
            "",
            f"对真实商品原图 `{image_range}` 共 {len(manifest)} 张执行 PaddleOCR。"
            f"成功 {len(successes)} 张，失败 {len(failures)} 张。",
            "",
            "本报告只评价 OCR 数据获取质量，不进行违法认定，也不预测非法添加剂。",
            "",
            "## 运行信息",
            "",
            f"- 开始时间：{started_at}",
            f"- 耗时：{elapsed_seconds:.1f} 秒",
            f"- PaddlePaddle：`{model_info['paddleVersion']}`",
            f"- PaddleOCR：`{model_info['paddleocrVersion']}`",
            f"- 模型：`{model_info['ocrVersion']}` / 中文 / CPU",
            f"- 纯文本置信度阈值：`{model_info['scoreThreshold']}`",
            f"- OCR 行数：{total_lines}",
            f"- OCR 字符数：{total_chars}",
            f"- 平均行置信度：{avg_summary}",
            f"- 命中业务提示词的图片数：{len(hit_images)}",
            "",
            "## 逐图结果",
            "",
            "| 图片 | 状态 | 文本行 | 字符数 | 平均置信度 | 业务提示词 |",
            "| --- | --- | ---: | ---: | ---: | --- |",
            *rows,
            "",
            "## 失败记录",
            "",
            *failure_lines,
            "",
            "## 输出",
            "",
            f"- 纯文本：`{(product_root / 'ocr').as_posix()}/original_###.txt`",
            f"- 结构化结果：`{(product_root / 'ocr').as_posix()}/original_###.json`",
            f"- 汇总清单：`{(product_root / 'ocr' / 'manifest.json').as_posix()}`",
            f"- 合并文本：`{(product_root / 'ocr' / 'combined_text.txt').as_posix()}`",
            "",
            "本结果可与商品标题和 DOM 文本合并后执行本地规则分类。",
            "",
        ]
    )


def run_ocr(
    product_root: Path,
    cache_dir: Path,
    start: int = 2,
    end: int = 16,
    score_threshold: float = 0.5,
    ocr_version: str = "PP-OCRv6",
    model_source: str = "bos",
    image_numbers: set[int] | None = None,
    runtime: OCRRuntime | None = None,
) -> Path:
    product_root = product_root.resolve()
    output_dir = product_root / "ocr"
    output_dir.mkdir(parents=True, exist_ok=True)
    model_info = ocr_environment_info(
        ocr_version,
        model_source,
        score_threshold,
    )
    write_json(output_dir / "run_info.json", model_info)
    if image_numbers is None:
        image_numbers = ocr_image_numbers_from_meta(product_root)
    image_dir = product_root / "images" / "original"
    images = (
        select_images(image_dir, start, end, image_numbers=image_numbers)
        if image_dir.is_dir()
        else []
    )
    if not images:
        error = FileNotFoundError("没有找到符合OCR选择规则的原始详情图片")
        _record_stage_error(output_dir, error)
        raise error

    started_at = iso_now()
    started_clock = time.perf_counter()
    if runtime is None:
        try:
            runtime = create_ocr_runtime(cache_dir, ocr_version, model_source)
        except Exception as exc:
            _record_stage_error(output_dir, exc)
            raise
    engine = runtime.engine
    cv2 = runtime.cv2
    np = runtime.numpy
    print(f"PaddleOCR images={len(images)}", flush=True)

    manifest: list[dict[str, Any]] = []
    combined_sections: list[str] = []
    for ordinal, image_path in enumerate(images, start=1):
        item_started = time.perf_counter()
        print(f"[{ordinal:02d}/{len(images):02d}] OCR {image_path.name}", flush=True)
        item: dict[str, Any] = {
            "image": image_path.name,
            "sourcePath": image_path.relative_to(product_root).as_posix(),
            "startedAt": iso_now(),
            "status": "failed",
        }
        try:
            # Paddle Inference/OpenCV on Windows may not open non-ASCII paths.
            # Decode from bytes and pass an ndarray so the project directory can
            # safely contain Chinese characters.
            image_array = cv2.imdecode(
                np.frombuffer(image_path.read_bytes(), dtype=np.uint8),
                cv2.IMREAD_COLOR,
            )
            if image_array is None:
                raise ValueError("OpenCV failed to decode the image bytes")
            result_objects = list(engine.predict(image_array))
            structured = [result_to_dict(result) for result in result_objects]
            lines = extract_lines(structured, score_threshold)
            plain_lines = [
                line["text"] for line in lines if line["includedInPlainText"]
            ]
            plain_text = "\n".join(plain_lines)
            scores = [line["score"] for line in lines if line["score"] is not None]
            json_path = output_dir / f"{image_path.stem}.json"
            text_path = output_dir / f"{image_path.stem}.txt"
            write_json(
                json_path,
                {
                    "image": image_path.name,
                    "sourcePath": image_path.relative_to(product_root).as_posix(),
                    "ocrVersion": ocr_version,
                    "scoreThreshold": score_threshold,
                    "capturedAt": iso_now(),
                    "lines": lines,
                    "rawResults": structured,
                },
            )
            text_path.write_text(plain_text, encoding="utf-8")
            hits = keyword_hits(plain_text)
            item.update(
                {
                    "status": "success",
                    "lineCount": len(plain_lines),
                    "detectedLineCount": len(lines),
                    "characterCount": len(plain_text.replace("\n", "")),
                    "averageConfidence": statistics.fmean(scores) if scores else None,
                    "minimumConfidence": min(scores) if scores else None,
                    "scores": scores,
                    "keywordHits": hits,
                    "textPath": text_path.relative_to(product_root).as_posix(),
                    "jsonPath": json_path.relative_to(product_root).as_posix(),
                }
            )
            combined_sections.append(f"## {image_path.name}\n{plain_text}")
        except Exception as exc:
            item["error"] = f"{type(exc).__name__}: {exc}"
            print(f"  failed: {item['error']}", file=sys.stderr, flush=True)
        item["elapsedSeconds"] = round(time.perf_counter() - item_started, 3)
        manifest.append(item)
        write_json(output_dir / "manifest.json", manifest)

    combined_text = "\n\n".join(combined_sections).strip() + "\n"
    (output_dir / "combined_text.txt").write_text(combined_text, encoding="utf-8")
    elapsed = time.perf_counter() - started_clock
    model_info.update(runtime.model_info)
    model_info["pythonVersion"] = model_info.get("pythonVersion") or ".".join(
        str(part) for part in sys.version_info[:3]
    )
    model_info["paddlepaddleVersion"] = model_info.get(
        "paddlepaddleVersion", model_info.get("paddleVersion", "unknown")
    )
    model_info["paddleVersion"] = model_info["paddlepaddleVersion"]
    model_info["paddlexVersion"] = model_info.get(
        "paddlexVersion", _installed_version("paddlex")
    )
    model_info["ocrVersion"] = ocr_version
    model_info["modelSource"] = model_source
    model_info["device"] = model_info.get("device") or "cpu"
    model_info["scoreThreshold"] = score_threshold
    write_json(output_dir / "run_info.json", model_info)
    report = build_report(product_root, manifest, model_info, started_at, elapsed)
    report_path = product_root / "phase2_ocr_report.md"
    report_path.write_text(report, encoding="utf-8")
    success_count = sum(item.get("status") == "success" for item in manifest)
    if success_count == 0:
        error = OCRStageError(
            f"OCR阶段失败：{len(manifest)}张输入图片均未产生可用OCR结果"
        )
        _record_stage_error(output_dir, error)
        raise error
    (output_dir / "stage_error.json").unlink(missing_ok=True)
    return report_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="对 Phase 1 真实详情原图运行 PaddleOCR")
    parser.add_argument(
        "--product-root",
        type=Path,
        default=Path("output/20260817T171318/products/606232126144"),
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path.home() / ".cache" / "paddlex",
        help="Windows Paddle inference requires a model path without Chinese characters",
    )
    parser.add_argument("--start", type=int, default=2)
    parser.add_argument("--end", type=int, default=16)
    parser.add_argument("--score-threshold", type=float, default=0.5)
    parser.add_argument("--ocr-version", default="PP-OCRv6")
    parser.add_argument("--model-source", default="bos")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_ocr(
        product_root=args.product_root,
        cache_dir=args.cache_dir,
        start=args.start,
        end=args.end,
        score_threshold=args.score_threshold,
        ocr_version=args.ocr_version,
        model_source=args.model_source,
    )
    print(f"Phase 2 report: {report}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
