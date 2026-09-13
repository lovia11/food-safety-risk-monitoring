"""Snapshot-scoped health-food identity candidates and conservative matching."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path
from typing import Any, Iterable

from src.health_food_registry import HealthFoodRegistryProvider, SOURCE_NAME, SOURCE_REFERENCE
from src.phase3_analysis import TextUnit, parse_dom_units
from src.runtime import iso_now, read_json, write_json


HEALTH_FOOD_IDENTITY_SCHEMA_VERSION = 1
HEALTH_FOOD_IDENTITY_EXTRACTOR_VERSION = "health-food-identity-v1"
HEALTH_FOOD_IDENTITY_FILE = "health_food_identity.json"

IDENTITY_STATES = frozenset(
    {
        "no_indicator",
        "candidate_indicator_only",
        "candidate_identifier",
        "identifier_ambiguous",
        "registry_lookup_unavailable",
        "registry_record_not_found",
        "registry_record_found_identity_unverified",
        "verified_match",
        "identity_mismatch",
        "conflict",
    }
)

_CLUE_RE = re.compile(r"小蓝帽|蓝帽|保健食品")
_EXPLICIT_NEGATIVE_RE = re.compile(
    r"(?:是否(?:为|是)?保健食品|是否保健食品(?:（国食健字号）)?)\s*[:：]?\s*(?:否|不是|不属于)"
    r"|(?:不是|不属于|不当)保健食品"
)
_IDENTIFIER_SCAN_RE = re.compile(
    r"(?:国食健注|国食健字|食健备)\s*[GJgj]\s*[0-9OISBolisb](?:[\s0-9OISBolisb]{6,17})"
)
_SURROUNDING_TRIM = " \t\r\n,，;；。.!！?？:：()（）[]【】<>《》'\""
_AMBIGUOUS_MAP = str.maketrans({"O": "0", "I": "1", "L": "1", "S": "5", "B": "8"})


def normalize_registration_identifier(raw: Any) -> str:
    text = unicodedata.normalize("NFKC", str(raw or "")).strip(_SURROUNDING_TRIM)
    return re.sub(r"\s+", "", text).upper()


def _valid_identifier(identifier: str) -> tuple[str, str] | None:
    patterns = (
        (r"国食健注G20\d{6}", "registration_current_domestic", "valid_current"),
        (r"国食健注J20\d{6}", "registration_current_imported", "valid_current"),
        (r"食健备G20\d{10}", "filing_domestic", "valid_current"),
        (r"食健备J20\d{2}00\d{6}", "filing_imported", "valid_current"),
        (r"国食健字G\d{8}", "registration_legacy_domestic", "legacy_identifier_candidate"),
        (r"国食健字J\d{8}", "registration_legacy_imported", "legacy_identifier_candidate"),
    )
    for pattern, identifier_type, state in patterns:
        if re.fullmatch(pattern, identifier):
            return identifier_type, state
    return None


def classify_registration_identifier(raw: Any, *, source_type: str = "dom_detail") -> dict[str, str]:
    normalized = normalize_registration_identifier(raw)
    valid = _valid_identifier(normalized)
    if valid:
        identifier_type, format_state = valid
    else:
        prefix = next(
            (
                item
                for item in ("国食健注G", "国食健注J", "食健备G", "食健备J", "国食健字G", "国食健字J")
                if normalized.startswith(item)
            ),
            "",
        )
        suffix = normalized[len(prefix) :] if prefix else normalized
        corrected = prefix + suffix.translate(_AMBIGUOUS_MAP)
        corrected_valid = _valid_identifier(corrected)
        if prefix and corrected_valid and corrected != normalized:
            identifier_type = corrected_valid[0]
            format_state = "ambiguous_ocr" if source_type.startswith("ocr") else "invalid"
        else:
            identifier_type = {
                "国食健注G": "registration_current_domestic",
                "国食健注J": "registration_current_imported",
                "食健备G": "filing_domestic",
                "食健备J": "filing_imported",
                "国食健字G": "registration_legacy_domestic",
                "国食健字J": "registration_legacy_imported",
            }.get(prefix, "unknown")
            format_state = "invalid"
    return {
        "rawValue": str(raw).strip(),
        "normalizedValue": normalized,
        "identifierType": identifier_type,
        "formatState": format_state,
    }


def _stable_id(*parts: str) -> str:
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:24]


def _read_sources(product_root: Path) -> tuple[list[TextUnit], list[dict[str, Any]], list[dict[str, Any]]]:
    units: list[TextUnit] = []
    diagnostics: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    dom_path = product_root / "dom_text.txt"
    if dom_path.is_file():
        try:
            included, excluded = parse_dom_units(dom_path.read_text(encoding="utf-8"))
            seller = [unit for unit in included if unit.content_origin == "seller_managed"]
            ugc = [unit for unit in included if unit.content_origin == "user_generated"]
            units.extend(seller)
            sources.append({"type": "dom", "path": "dom_text.txt", "lines": len(seller)})
            if ugc:
                diagnostics.append(
                    {
                        "code": "ugc",
                        "reason": "User reviews and Q&A were excluded from identity candidates",
                        "count": len(ugc),
                    }
                )
            if excluded:
                diagnostics.append(
                    {
                        "code": "other_product",
                        "reason": "Recommendation-area DOM was excluded",
                        "count": len(excluded),
                    }
                )
        except (OSError, UnicodeError) as exc:
            diagnostics.append({"code": "source_read_error", "sourcePath": "dom_text.txt", "message": str(exc)})
    else:
        diagnostics.append({"code": "source_missing", "sourcePath": "dom_text.txt"})

    manifest_path = product_root / "ocr" / "manifest.json"
    if manifest_path.is_file():
        try:
            manifest = read_json(manifest_path)
            success_count = 0
            if not isinstance(manifest, list):
                raise ValueError("OCR manifest is not an array")
            for item in manifest:
                if not isinstance(item, dict) or item.get("status") != "success":
                    continue
                relative = str(item.get("textPath") or "").replace("\\", "/").lstrip("/")
                path = (product_root / relative).resolve()
                if not relative or not path.is_relative_to(product_root) or not path.is_file():
                    diagnostics.append({"code": "source_invalid", "sourcePath": relative or "ocr/manifest.json"})
                    continue
                success_count += 1
                for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                    text = raw_line.strip()
                    if text:
                        units.append(TextUnit("ocr", relative, line_number, text))
            sources.append({"type": "ocr", "path": "ocr/manifest.json", "successImages": success_count})
        except (OSError, UnicodeError, ValueError, TypeError) as exc:
            diagnostics.append({"code": "source_read_error", "sourcePath": "ocr/manifest.json", "message": str(exc)})
    else:
        diagnostics.append({"code": "source_missing", "sourcePath": "ocr/manifest.json"})
    return units, sources, diagnostics


def _source_type(unit: TextUnit) -> str:
    return "ocr_detail_image" if unit.source_type == "ocr" else "dom_detail"


def _extract_clues_and_identifiers(
    units: Iterable[TextUnit], snapshot_id: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    source_units = list(units)
    clues: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for index, unit in enumerate(source_units):
        adjacent_negative = (
            "是否保健食品" in unit.text
            and index + 1 < len(source_units)
            and source_units[index + 1].source_path == unit.source_path
            and source_units[index + 1].text.strip(" :：") in {"否", "不是", "不属于"}
        )
        if _EXPLICIT_NEGATIVE_RE.search(unit.text) or adjacent_negative:
            diagnostics.append(
                {
                    "code": "explicit_negative_health_food_parameter",
                    "reason": "An explicit negative parameter is not a positive identity clue",
                    "sourcePath": f"{unit.source_path}#L{unit.line_number}",
                    "sourceText": unit.text,
                }
            )
            continue
        for match in _CLUE_RE.finditer(unit.text):
            raw = match.group(0)
            source_path = f"{unit.source_path}#L{unit.line_number}"
            clues.append(
                {
                    "clueId": "hfc_" + _stable_id(snapshot_id, raw, source_path),
                    "clueType": "blue_hat_text" if "蓝帽" in raw else "health_food_text",
                    "text": raw,
                    "sourceType": _source_type(unit),
                    "sourcePath": source_path,
                    "sourceText": unit.text,
                    "contentOrigin": "seller_managed",
                    "extractionMethod": "explicit_text_match",
                }
            )
        for match in _IDENTIFIER_SCAN_RE.finditer(unit.text):
            raw = match.group(0).rstrip()
            source_type = _source_type(unit)
            classified = classify_registration_identifier(raw, source_type=source_type)
            source_path = f"{unit.source_path}#L{unit.line_number}"
            candidate = {
                "candidateId": "hfi_" + _stable_id(
                    snapshot_id, classified["normalizedValue"], source_type, source_path, raw
                ),
                **classified,
                "sourceType": source_type,
                "sourcePath": source_path,
                "sourceText": unit.text,
                "contentOrigin": "seller_managed",
                "extractionMethod": "registration_identifier_pattern",
            }
            candidates.append(candidate)
            if classified["formatState"] in {"invalid", "ambiguous_ocr"}:
                diagnostics.append(
                    {
                        "code": "ambiguous_ocr" if classified["formatState"] == "ambiguous_ocr" else "invalid_identifier_format",
                        "reason": "Candidate is retained but is not eligible for automatic official lookup",
                        "sourcePath": source_path,
                        "sourceText": raw,
                    }
                )
    unique_clues = {item["clueId"]: item for item in clues}
    unique_candidates = {item["candidateId"]: item for item in candidates}
    return list(unique_clues.values()), list(unique_candidates.values()), diagnostics


_PRODUCT_NAME_RE = re.compile(r"^(?:产品名称|商品名称)\s*[:：=]\s*(?P<value>.+)$")


def _valid_product_name(value: str) -> bool:
    return bool(value and len(value) <= 120 and re.search(r"[\w\u3400-\u9fff]", value))


def _extract_page_product_names(units: list[TextUnit]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, unit in enumerate(units):
        match = _PRODUCT_NAME_RE.match(unit.text)
        value = match.group("value").strip() if match else ""
        method = "explicit_product_name_same_line"
        if not value and unit.text in {"产品名称", "商品名称"} and index + 1 < len(units):
            following = units[index + 1]
            if following.source_path == unit.source_path:
                value = following.text.strip()
                method = "explicit_product_name_adjacent"
        if not _valid_product_name(value):
            continue
        result.append(
            {
                "value": value,
                "sourceType": _source_type(unit),
                "sourcePath": f"{unit.source_path}#L{unit.line_number}",
                "sourceText": unit.text if match else f"{unit.text}\n{value}",
                "contentOrigin": "seller_managed",
                "extractionMethod": method,
            }
        )
    unique = {
        (normalize_product_name(item["value"]), item["sourcePath"]): item
        for item in result
    }
    return list(unique.values())


def normalize_product_name(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).replace("®", "").replace("™", "")
    return re.sub(r"[^0-9A-Za-z\u3400-\u9fff]", "", text).casefold()


def assess_product_match(
    page_product_names: list[dict[str, Any]],
    official_product_name: str | None,
    *,
    title_auxiliary: str = "",
) -> dict[str, Any]:
    official_normalized = normalize_product_name(official_product_name)
    normalized_page = {
        normalize_product_name(item.get("value"))
        for item in page_product_names
        if normalize_product_name(item.get("value"))
    }
    if not official_normalized or not normalized_page:
        state = "unverified"
    elif len(normalized_page) > 1:
        state = "conflict"
    elif official_normalized in normalized_page:
        state = "strong_match"
    else:
        state = "mismatch"
    return {
        "state": state,
        "pageProductNames": page_product_names,
        "officialProductName": official_product_name,
        "titleAuxiliary": title_auxiliary or None,
        "matchingRule": "formatting_normalized_exact_equality",
    }


def empty_health_food_identity() -> dict[str, Any]:
    return {
        "state": "no_indicator",
        "clues": [],
        "identifiers": [],
        "registryRecord": None,
        "productMatch": {
            "state": "not_assessed",
            "pageProductNames": [],
            "officialProductName": None,
            "titleAuxiliary": None,
            "matchingRule": "formatting_normalized_exact_equality",
        },
        "verification": {"status": "not_attempted", "queriedIdentifier": None, "queriedAt": None, "error": None},
        "officialSource": {"name": SOURCE_NAME, "reference": SOURCE_REFERENCE},
        "gaps": [],
        "diagnostics": {
            "sourcesScanned": [],
            "cluesFound": 0,
            "identifierCandidates": 0,
            "excludedCandidates": 0,
            "registryLookupAttempted": False,
            "registryLookupStatus": "not_attempted",
            "matchAssessment": "not_assessed",
            "errors": [],
        },
    }


def extract_health_food_identity(
    product_root: Path,
    snapshot_id: str,
    *,
    provider: HealthFoodRegistryProvider | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Persist identity facts; provider failure is represented, never raised."""

    product_root = product_root.resolve()
    generated = generated_at or iso_now()
    units, sources, errors = _read_sources(product_root)
    clues, candidates, candidate_errors = _extract_clues_and_identifiers(units, snapshot_id)
    errors.extend(candidate_errors)
    page_names = _extract_page_product_names(units)
    meta: dict[str, Any] = {}
    try:
        raw_meta = read_json(product_root / "meta.json") if (product_root / "meta.json").is_file() else {}
        meta = raw_meta if isinstance(raw_meta, dict) else {}
    except (OSError, ValueError, TypeError) as exc:
        errors.append({"code": "source_read_error", "sourcePath": "meta.json", "message": str(exc)})
    title = str(meta.get("productName") or "").strip()

    valid_candidates = [
        item for item in candidates
        if item["formatState"] in {"valid_current", "legacy_identifier_candidate"}
    ]
    identifiers = sorted({item["normalizedValue"] for item in valid_candidates})
    ambiguous = any(item["formatState"] == "ambiguous_ocr" for item in candidates)
    lookup: dict[str, Any] = {
        "status": "not_attempted",
        "queriedIdentifier": None,
        "sourceName": SOURCE_NAME,
        "sourceReference": SOURCE_REFERENCE,
        "queriedAt": None,
        "record": None,
        "rawArtifactPath": None,
        "rawArtifactSha256": None,
        "error": None,
    }
    match = assess_product_match(page_names, None, title_auxiliary=title)
    if len(identifiers) > 1:
        state = "conflict"
    elif len(identifiers) == 1:
        identifier = identifiers[0]
        if provider is None:
            state = "candidate_identifier"
        else:
            try:
                lookup = provider.lookup(identifier)
            except Exception as exc:  # provider implementations remain degradable
                lookup = {**lookup, "status": "unavailable", "queriedIdentifier": identifier, "queriedAt": iso_now(), "error": f"{type(exc).__name__}: {exc}"}
            status = str(lookup.get("status") or "unavailable")
            record = lookup.get("record") if isinstance(lookup.get("record"), dict) else None
            if status == "found" and record:
                match = assess_product_match(
                    page_names,
                    str(record.get("productName") or "") or None,
                    title_auxiliary=title,
                )
                state = {
                    "strong_match": "verified_match",
                    "mismatch": "identity_mismatch",
                    "conflict": "conflict",
                }.get(match["state"], "registry_record_found_identity_unverified")
            elif status == "not_found":
                state = "registry_record_not_found"
            else:
                state = "registry_lookup_unavailable"
    elif ambiguous:
        state = "identifier_ambiguous"
    elif candidates:
        state = "candidate_identifier"
    elif clues:
        state = "candidate_indicator_only"
    else:
        state = "no_indicator"

    gaps: list[str] = []
    if state == "candidate_indicator_only":
        gaps.append("registration_identifier_missing")
    if state == "registry_record_found_identity_unverified":
        gaps.append("strong_page_product_name_missing")
    if state in {"identity_mismatch", "conflict"}:
        gaps.append("manual_identity_review_required")
    diagnostics = {
        "sourcesScanned": sources,
        "cluesFound": len(clues),
        "identifierCandidates": len(candidates),
        "excludedCandidates": sum(item.get("code") in {"ugc", "other_product", "invalid_identifier_format", "ambiguous_ocr", "search_result_only"} for item in errors),
        "registryLookupAttempted": lookup.get("status") != "not_attempted",
        "registryLookupStatus": lookup.get("status") or "not_attempted",
        "matchAssessment": match["state"],
        "errors": errors,
    }
    payload = {
        "schemaVersion": HEALTH_FOOD_IDENTITY_SCHEMA_VERSION,
        "extractorVersion": HEALTH_FOOD_IDENTITY_EXTRACTOR_VERSION,
        "generatedAt": generated,
        "snapshotId": snapshot_id,
        "clues": clues,
        "identifierCandidates": candidates,
        "officialLookup": lookup,
        "identityAssessment": {"state": state, "productMatch": match},
        "gaps": gaps,
        "diagnostics": diagnostics,
    }
    write_json(product_root / HEALTH_FOOD_IDENTITY_FILE, payload)
    return payload


def load_health_food_identity(
    artifact_path: Path, *, expected_snapshot_id: str | None = None
) -> dict[str, Any] | None:
    if not artifact_path.is_file():
        return None
    try:
        payload = read_json(artifact_path)
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    assessment = payload.get("identityAssessment")
    if not isinstance(assessment, dict) or assessment.get("state") not in IDENTITY_STATES:
        return None
    if expected_snapshot_id and str(payload.get("snapshotId") or "") != expected_snapshot_id:
        return None
    if not isinstance(payload.get("clues"), list) or not isinstance(payload.get("identifierCandidates"), list):
        return None
    return payload


def present_health_food_identity(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return empty_health_food_identity()
    lookup = payload.get("officialLookup") if isinstance(payload.get("officialLookup"), dict) else {}
    assessment = payload.get("identityAssessment") if isinstance(payload.get("identityAssessment"), dict) else {}
    match = assessment.get("productMatch") if isinstance(assessment.get("productMatch"), dict) else empty_health_food_identity()["productMatch"]
    return {
        "state": assessment.get("state") if assessment.get("state") in IDENTITY_STATES else "no_indicator",
        "clues": payload.get("clues") if isinstance(payload.get("clues"), list) else [],
        "identifiers": payload.get("identifierCandidates") if isinstance(payload.get("identifierCandidates"), list) else [],
        "registryRecord": lookup.get("record") if isinstance(lookup.get("record"), dict) else None,
        "productMatch": match,
        "verification": {
            "status": lookup.get("status") or "not_attempted",
            "queriedIdentifier": lookup.get("queriedIdentifier"),
            "queriedAt": lookup.get("queriedAt"),
            "error": lookup.get("error"),
            "rawArtifactPath": lookup.get("rawArtifactPath"),
            "rawArtifactSha256": lookup.get("rawArtifactSha256"),
        },
        "officialSource": {
            "name": lookup.get("sourceName") or SOURCE_NAME,
            "reference": lookup.get("sourceReference") or SOURCE_REFERENCE,
        },
        "gaps": payload.get("gaps") if isinstance(payload.get("gaps"), list) else [],
        "diagnostics": payload.get("diagnostics") if isinstance(payload.get("diagnostics"), dict) else empty_health_food_identity()["diagnostics"],
    }
