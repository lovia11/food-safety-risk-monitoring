"""Snapshot-scoped ProductFact extraction from existing local artifacts.

This module is deliberately independent from collection, OCR, Phase 3 and
human Review.  It only reads artifacts that already exist below one product
directory and writes the derived ``product_facts.json`` authority file.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from src.runtime import iso_now, read_json, write_json


PRODUCT_FACTS_SCHEMA_VERSION = 1
PRODUCT_FACTS_EXTRACTOR_VERSION = "product-facts-declared-origin-v1"
PRODUCT_FACTS_FILE = "product_facts.json"
DECLARED_ORIGIN = "declared_origin"

DECLARED_ORIGIN_LABELS = (
    "原产国家/地区",
    "原产国/地区",
    "商品产地",
    "产品产地",
    "原产地",
    "产地",
)

# These are exclusion boundaries, not aliases for declared origin.
EXCLUDED_ORIGIN_LABELS = (
    "原材料产地",
    "原料产地",
    "药材产地",
    "原料来源地",
    "发货地址",
    "发货地",
    "商家所在地",
    "卖家所在地",
    "卖家地址",
    "店铺所在地",
    "仓库所在地",
    "仓库地址",
    "生产地",
    "生产地址",
    "生产厂家地址",
    "生产企业地址",
    "厂家地址",
    "厂址",
    "企业注册地址",
    "企业地址",
    "制造商地址",
)

# Used only to determine the local key/value orientation inside Taobao's
# explicit parameter section.  No value from these fields is turned into a
# ProductFact.
_PARAMETER_LABEL_HINTS = frozenset(
    (*DECLARED_ORIGIN_LABELS, *EXCLUDED_ORIGIN_LABELS,
     "品牌", "是否为有机食品", "成分原料", "适用对象", "储存条件",
     "包装方式", "生产日期", "系列", "规格", "省份", "城市", "净含量",
     "厂名", "厂家联系方式", "储藏方法", "保质期", "特产品类", "品名",
     "口味", "是否进口", "单件净含量", "糕点种类", "包装种类",
     "包装规格", "生产许可证编号", "产品标准号", "规格类型", "套餐类型",
     "石斛工艺种类", "颜色分类", "脂肪含量", "蛋白质", "-膳食纤维")
)

_VALUE_TRIM = " \t\r\n:：=,，;；。|｜、"
_ORIGIN_MENTION_RE = re.compile(r"(?:原产国家/地区|原产国/地区|商品产地|产品产地|原产地|产地)")
_SAME_LINE_RE = re.compile(
    r"^(?P<label>" + "|".join(map(re.escape, DECLARED_ORIGIN_LABELS))
    + r")(?:(?:\s*[:：=]\s*)|(?:\s*为\s*)|(?:\s+))(?P<value>.+)$"
)
_EXCLUDED_LINE_RE = re.compile(
    r"^(?P<label>" + "|".join(map(re.escape, EXCLUDED_ORIGIN_LABELS))
    + r")\s*(?:[:：=]|为|\s)\s*(?P<value>.*)$"
)


@dataclass(frozen=True)
class _SourceLine:
    number: int
    text: str
    box: tuple[float, float, float, float] | None = None


def normalize_fact_value(value: Any) -> str:
    """Apply only lossless text cleanup; never infer a geographic hierarchy."""

    text = unicodedata.normalize("NFKC", str(value or ""))
    text = re.sub(r"\s+", " ", text).strip(_VALUE_TRIM)
    return text


def _valid_value(value: str) -> bool:
    if not value or len(value) > 64:
        return False
    if value in _PARAMETER_LABEL_HINTS:
        return False
    if any(label in value for label in EXCLUDED_ORIGIN_LABELS):
        return False
    if re.search(r"[。！？!?]", value):
        return False
    return bool(re.search(r"[\w\u3400-\u9fff]", value))


def _diagnostic(
    code: str,
    reason: str,
    source_path: str,
    source_text: str = "",
) -> dict[str, Any]:
    return {
        "code": code,
        "reason": reason,
        "sourcePath": source_path,
        "sourceText": source_text,
    }


def _fact_id(
    snapshot_id: str,
    normalized_value: str,
    source_type: str,
    source_path: str,
    source_text: str,
) -> str:
    identity = "\0".join(
        (
            snapshot_id,
            DECLARED_ORIGIN,
            normalized_value,
            source_type,
            source_path,
            source_text,
        )
    )
    return "pf_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]


def _make_fact(
    *,
    snapshot_id: str,
    raw_value: str,
    source_type: str,
    source_path: str,
    source_text: str,
    extraction_method: str,
    created_at: str,
) -> dict[str, Any] | None:
    normalized = normalize_fact_value(raw_value)
    if not _valid_value(normalized):
        return None
    return {
        "factId": _fact_id(
            snapshot_id, normalized, source_type, source_path, source_text
        ),
        "snapshotId": snapshot_id,
        "factType": DECLARED_ORIGIN,
        "normalizedValue": normalized,
        "rawValue": str(raw_value).strip(),
        "sourceType": source_type,
        "contentOrigin": "seller_managed",
        "sourcePath": source_path,
        "sourceText": source_text,
        "extractionMethod": extraction_method,
        "verificationState": "extracted",
        "createdAt": created_at,
    }


def _nonempty_lines(text: str) -> list[_SourceLine]:
    return [
        _SourceLine(number=index, text=line.strip())
        for index, line in enumerate(text.splitlines(), start=1)
        if line.strip()
    ]


def _parameter_section(lines: list[_SourceLine]) -> tuple[list[_SourceLine], set[int]]:
    candidates: list[list[_SourceLine]] = []
    for start, line in enumerate(lines):
        if line.text != "参数信息":
            continue
        end = next(
            (
                index
                for index in range(start + 1, len(lines))
                if lines[index].text == "图文详情"
            ),
            len(lines),
        )
        section = lines[start + 1 : end]
        if any(
            item.text in DECLARED_ORIGIN_LABELS or _SAME_LINE_RE.match(item.text)
            for item in section
        ):
            candidates.append(section)
    selected = candidates[-1] if candidates else []
    return selected, {line.number for line in selected}


def _dom_adjacent_value(
    lines: list[_SourceLine], index: int
) -> tuple[_SourceLine, str] | None:
    previous = lines[index - 1] if index > 0 else None
    following = lines[index + 1] if index + 1 < len(lines) else None
    previous_two = lines[index - 2] if index > 1 else None
    following_two = lines[index + 2] if index + 2 < len(lines) else None

    previous_value = normalize_fact_value(previous.text) if previous else ""
    following_value = normalize_fact_value(following.text) if following else ""
    previous_valid = bool(previous and _valid_value(previous_value))
    following_valid = bool(following and _valid_value(following_value))

    # Taobao has used both value/key and key/value layouts.  Resolve only when
    # a neighbouring known parameter label proves the local alternating order.
    if previous_valid and following_two and following_two.text in _PARAMETER_LABEL_HINTS:
        return previous, "dom_parameter_value_before_label"
    if following_valid and previous_two and previous_two.text in _PARAMETER_LABEL_HINTS:
        return following, "dom_parameter_label_before_value"
    if previous_valid and following and following.text in _PARAMETER_LABEL_HINTS:
        return previous, "dom_parameter_value_before_label"
    if following_valid and previous and previous.text in _PARAMETER_LABEL_HINTS:
        return following, "dom_parameter_label_before_value"
    if previous_valid and not following_valid:
        return previous, "dom_parameter_value_before_label"
    if following_valid and not previous_valid:
        return following, "dom_parameter_label_before_value"
    return None


def _extract_dom(
    product_root: Path, snapshot_id: str, created_at: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    path = product_root / "dom_text.txt"
    if not path.is_file():
        return [], [_diagnostic("source_missing", "DOM text artifact is absent", "dom_text.txt")]
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [], [_diagnostic("source_read_error", str(exc), "dom_text.txt")]

    all_lines = _nonempty_lines(text)
    section, section_numbers = _parameter_section(all_lines)
    facts: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    handled_numbers: set[int] = set()

    for index, line in enumerate(section):
        excluded = _EXCLUDED_LINE_RE.match(line.text)
        if excluded:
            diagnostics.append(
                _diagnostic(
                    "excluded_origin_field",
                    f"{excluded.group('label')} is not declared product origin",
                    f"dom_text.txt#L{line.number}",
                    line.text,
                )
            )
            continue
        same_line = _SAME_LINE_RE.match(line.text)
        if same_line:
            fact = _make_fact(
                snapshot_id=snapshot_id,
                raw_value=same_line.group("value"),
                source_type="dom_parameter",
                source_path=f"dom_text.txt#L{line.number}",
                source_text=line.text,
                extraction_method="dom_parameter_labeled_same_line",
                created_at=created_at,
            )
            if fact:
                facts.append(fact)
            else:
                diagnostics.append(
                    _diagnostic(
                        "invalid_origin_value",
                        "Explicit DOM label has no conservative value",
                        f"dom_text.txt#L{line.number}",
                        line.text,
                    )
                )
            handled_numbers.add(line.number)
            continue
        if line.text not in DECLARED_ORIGIN_LABELS:
            continue
        adjacent = _dom_adjacent_value(section, index)
        if adjacent is None:
            diagnostics.append(
                _diagnostic(
                    "ambiguous_adjacent_value",
                    "DOM parameter reading order does not prove one adjacent value",
                    f"dom_text.txt#L{line.number}",
                    line.text,
                )
            )
            handled_numbers.add(line.number)
            continue
        value_line, method = adjacent
        source_lines = sorted((line, value_line), key=lambda item: item.number)
        source_text = "\n".join(item.text for item in source_lines)
        source_path = (
            f"dom_text.txt#L{source_lines[0].number}-L{source_lines[-1].number}"
        )
        fact = _make_fact(
            snapshot_id=snapshot_id,
            raw_value=value_line.text,
            source_type="dom_parameter",
            source_path=source_path,
            source_text=source_text,
            extraction_method=method,
            created_at=created_at,
        )
        if fact:
            facts.append(fact)
        handled_numbers.update((line.number, value_line.number))

    for line in all_lines:
        if line.number in handled_numbers:
            continue
        if any(label in line.text for label in EXCLUDED_ORIGIN_LABELS):
            diagnostics.append(
                _diagnostic(
                    "excluded_origin_field",
                    "Address, shipping, warehouse, manufacturer or raw-material origin is not declared product origin",
                    f"dom_text.txt#L{line.number}",
                    line.text,
                )
            )
        elif _ORIGIN_MENTION_RE.search(line.text):
            diagnostics.append(
                _diagnostic(
                    "unstructured_origin_mention",
                    "Origin wording outside an explicit product parameter was not extracted",
                    f"dom_text.txt#L{line.number}",
                    line.text,
                )
            )

    if not section and any(_ORIGIN_MENTION_RE.search(line.text) for line in all_lines):
        diagnostics.append(
            _diagnostic(
                "parameter_section_missing",
                "No explicit seller-managed parameter section could be established",
                "dom_text.txt",
            )
        )
    return facts, diagnostics


def _box(value: Any) -> tuple[float, float, float, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) < 4:
        return None
    try:
        x1, y1, x2, y2 = (float(value[index]) for index in range(4))
    except (TypeError, ValueError):
        return None
    if x2 <= x1 or y2 <= y1:
        return None
    return x1, y1, x2, y2


def _same_row(left: _SourceLine, right: _SourceLine) -> bool:
    if left.box is None or right.box is None:
        return False
    _, y1, _, y2 = left.box
    _, ry1, _, ry2 = right.box
    left_center = (y1 + y2) / 2
    right_center = (ry1 + ry2) / 2
    return abs(left_center - right_center) <= max(y2 - y1, ry2 - ry1) * 0.35


def _ocr_reading_order_proven(
    lines: list[_SourceLine], index: int
) -> tuple[_SourceLine, str] | None:
    if index + 1 >= len(lines):
        return None
    label = lines[index]
    value = lines[index + 1]
    normalized = normalize_fact_value(value.text)
    if label.box is None or value.box is None or not _valid_value(normalized):
        return None
    lx1, ly1, lx2, ly2 = label.box
    vx1, vy1, _, vy2 = value.box
    height = max(ly2 - ly1, vy2 - vy1)
    method: str | None = None
    if _same_row(label, value) and vx1 >= lx2 and vx1 - lx2 <= height * 4:
        method = "ocr_labeled_adjacent_same_row"
    elif vy1 >= ly2 - height * 0.2 and vy1 - ly2 <= height * 2.2:
        if abs(vx1 - lx1) <= height * 2:
            method = "ocr_labeled_adjacent_next_row"
    if method is None:
        return None
    # Multiple neighbouring OCR tokens on the same row are not a provable
    # one-to-one key/value pair (for example table headers followed by cities).
    if index + 2 < len(lines) and _same_row(value, lines[index + 2]):
        return None
    return value, method


def _ocr_lines(path: Path) -> list[_SourceLine]:
    payload = read_json(path)
    if not isinstance(payload, dict) or not isinstance(payload.get("lines"), list):
        raise ValueError("OCR JSON does not contain a lines array")
    result = []
    for ordinal, item in enumerate(payload["lines"], start=1):
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        raw_number = item.get("lineIndex")
        number = int(raw_number) + 1 if isinstance(raw_number, int) else ordinal
        result.append(_SourceLine(number=number, text=text, box=_box(item.get("box"))))
    return result


def _extract_ocr(
    product_root: Path, snapshot_id: str, created_at: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    manifest_path = product_root / "ocr" / "manifest.json"
    if not manifest_path.is_file():
        return [], [_diagnostic("source_missing", "OCR manifest is absent", "ocr/manifest.json")]
    try:
        manifest = read_json(manifest_path)
    except (OSError, ValueError, TypeError) as exc:
        return [], [_diagnostic("source_read_error", str(exc), "ocr/manifest.json")]
    if not isinstance(manifest, list):
        return [], [_diagnostic("source_invalid", "OCR manifest is not an array", "ocr/manifest.json")]

    facts: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for item in manifest:
        if not isinstance(item, dict) or item.get("status") != "success":
            continue
        raw_text_path = str(item.get("textPath") or "").replace("\\", "/").lstrip("/")
        raw_json_path = str(item.get("jsonPath") or "").replace("\\", "/").lstrip("/")
        text_path = (product_root / raw_text_path).resolve()
        json_path = (product_root / raw_json_path).resolve()
        if (
            not raw_text_path
            or not raw_json_path
            or not text_path.is_relative_to(product_root)
            or not json_path.is_relative_to(product_root)
            or not text_path.is_file()
            or not json_path.is_file()
        ):
            diagnostics.append(
                _diagnostic(
                    "source_invalid",
                    "OCR success item has a missing or unsafe text/JSON artifact",
                    raw_text_path or raw_json_path or "ocr/manifest.json",
                )
            )
            continue
        try:
            lines = _ocr_lines(json_path)
        except (OSError, ValueError, TypeError) as exc:
            diagnostics.append(
                _diagnostic("source_read_error", str(exc), raw_json_path)
            )
            continue
        for index, line in enumerate(lines):
            excluded = _EXCLUDED_LINE_RE.match(line.text)
            if excluded:
                diagnostics.append(
                    _diagnostic(
                        "excluded_origin_field",
                        f"{excluded.group('label')} is not declared product origin",
                        f"{raw_text_path}#L{line.number}",
                        line.text,
                    )
                )
                continue
            same_line = _SAME_LINE_RE.match(line.text)
            if same_line:
                fact = _make_fact(
                    snapshot_id=snapshot_id,
                    raw_value=same_line.group("value"),
                    source_type="ocr_detail_image",
                    source_path=f"{raw_text_path}#L{line.number}",
                    source_text=line.text,
                    extraction_method="ocr_labeled_same_line",
                    created_at=created_at,
                )
                if fact:
                    facts.append(fact)
                continue
            if line.text in DECLARED_ORIGIN_LABELS:
                adjacent = _ocr_reading_order_proven(lines, index)
                if adjacent is None:
                    diagnostics.append(
                        _diagnostic(
                            "ambiguous_adjacent_value",
                            "OCR geometry does not prove one adjacent key/value pair",
                            f"{raw_text_path}#L{line.number}",
                            line.text,
                        )
                    )
                    continue
                value_line, method = adjacent
                fact = _make_fact(
                    snapshot_id=snapshot_id,
                    raw_value=value_line.text,
                    source_type="ocr_detail_image",
                    source_path=f"{raw_text_path}#L{line.number}-L{value_line.number}",
                    source_text=f"{line.text}\n{value_line.text}",
                    extraction_method=method,
                    created_at=created_at,
                )
                if fact:
                    facts.append(fact)
            elif _ORIGIN_MENTION_RE.search(line.text):
                diagnostics.append(
                    _diagnostic(
                        "unstructured_origin_mention",
                        "OCR origin wording without an explicit labeled value was not extracted",
                        f"{raw_text_path}#L{line.number}",
                        line.text,
                    )
                )
    return facts, diagnostics


def extract_product_facts(
    product_root: Path,
    snapshot_id: str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Extract declared-origin facts and persist one auditable artifact."""

    product_root = product_root.resolve()
    created_at = generated_at or iso_now()
    facts: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []

    meta_path = product_root / "meta.json"
    if meta_path.is_file():
        try:
            meta = read_json(meta_path)
            title = str(meta.get("productName") or "") if isinstance(meta, dict) else ""
            if _ORIGIN_MENTION_RE.search(title) or "特产" in title:
                diagnostics.append(
                    _diagnostic(
                        "title_not_authoritative",
                        "Product title wording alone is not declared origin",
                        "meta.json#productName",
                        title,
                    )
                )
        except (OSError, ValueError, TypeError) as exc:
            diagnostics.append(_diagnostic("source_read_error", str(exc), "meta.json"))

    for extractor in (_extract_dom, _extract_ocr):
        try:
            extracted, source_diagnostics = extractor(
                product_root, snapshot_id, created_at
            )
            facts.extend(extracted)
            diagnostics.extend(source_diagnostics)
        except Exception as exc:  # one source must not block the other or Phase 3
            diagnostics.append(
                _diagnostic(
                    "extractor_error",
                    f"{type(exc).__name__}: {exc}",
                    extractor.__name__,
                )
            )

    unique_facts = {str(item["factId"]): item for item in facts}
    payload = {
        "schemaVersion": PRODUCT_FACTS_SCHEMA_VERSION,
        "extractorVersion": PRODUCT_FACTS_EXTRACTOR_VERSION,
        "generatedAt": created_at,
        "facts": sorted(
            unique_facts.values(),
            key=lambda item: (
                str(item["factType"]),
                str(item["normalizedValue"]),
                str(item["sourceType"]),
                str(item["sourcePath"]),
            ),
        ),
        "diagnostics": diagnostics,
    }
    write_json(product_root / PRODUCT_FACTS_FILE, payload)
    return payload


def _field(item: dict[str, Any], camel: str, snake: str) -> Any:
    return item.get(camel) if camel in item else item.get(snake)


def load_product_facts(
    artifact_path: Path,
    *,
    expected_snapshot_id: str | None = None,
) -> list[dict[str, Any]]:
    """Load valid generic facts from an optional authority artifact."""

    if not artifact_path.is_file():
        return []
    try:
        payload = read_json(artifact_path)
    except (OSError, ValueError, TypeError):
        return []
    if not isinstance(payload, dict) or not isinstance(payload.get("facts"), list):
        return []
    result = []
    required = (
        ("factId", "fact_id"),
        ("snapshotId", "snapshot_id"),
        ("factType", "fact_type"),
        ("normalizedValue", "normalized_value"),
        ("rawValue", "raw_value"),
        ("sourceType", "source_type"),
        ("contentOrigin", "content_origin"),
        ("sourcePath", "source_path"),
        ("sourceText", "source_text"),
        ("extractionMethod", "extraction_method"),
        ("verificationState", "verification_state"),
        ("createdAt", "created_at"),
    )
    for raw in payload["facts"]:
        if not isinstance(raw, dict):
            continue
        item = {camel: _field(raw, camel, snake) for camel, snake in required}
        if any(item[key] is None for key, _ in required):
            continue
        if str(item["factType"]) != DECLARED_ORIGIN:
            continue
        if expected_snapshot_id and str(item["snapshotId"]) != expected_snapshot_id:
            continue
        if not normalize_fact_value(item["normalizedValue"]):
            continue
        result.append({key: str(value) for key, value in item.items()})
    return result


def present_declared_origin(facts: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Project retained provenance facts without arbitrating conflicts."""

    selected = [
        item for item in facts if str(item.get("factType") or "") == DECLARED_ORIGIN
    ]
    values = sorted(
        {
            normalize_fact_value(item.get("normalizedValue"))
            for item in selected
            if normalize_fact_value(item.get("normalizedValue"))
        }
    )
    return {
        "state": "none" if not values else "single" if len(values) == 1 else "conflict",
        "values": values,
        "sources": selected,
    }
