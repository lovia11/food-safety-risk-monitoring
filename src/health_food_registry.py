"""Official health-food registry provider contracts and conservative adapters.

The online endpoint is a best-effort enrichment source.  It is deliberately
isolated from Taobao/Playwright and from pipeline readiness.  Recorded official
responses use the same parser so unit tests never depend on the live service.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.runtime import file_sha256, iso_now, read_json, write_json


PROVIDER_VERSION = "samr-special-food-web-v1"
SOURCE_NAME = "国家市场监督管理总局特殊食品信息查询平台"
SOURCE_REFERENCE = "https://ypzsx.gsxt.gov.cn/specialfood/"
BASE_API = "https://ypzsx.gsxt.gov.cn/specialfood_server/"
DEFAULT_FRESHNESS_DAYS = 30


class RegistryProviderError(RuntimeError):
    """Raised only for invalid provider configuration, never for lookup status."""


class HealthFoodRegistryProvider(Protocol):
    def lookup(self, normalized_identifier: str) -> dict[str, Any]: ...


@dataclass(frozen=True)
class _Endpoint:
    query_path: str
    detail_path: str
    query_field: str
    query_payload: dict[str, Any]


def _json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _html_text(value: Any) -> str | None:
    text = _text(value)
    if text is None:
        return None
    return text.replace("&nbsp;", " ").replace("&#160;", " ")


def _list_verbatim(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = _html_text(value)
    return [text] if text else []


def _identifier_type(identifier: str) -> str:
    if identifier.startswith("国食健注G"):
        return "registration_current_domestic"
    if identifier.startswith("国食健注J"):
        return "registration_current_imported"
    if identifier.startswith("食健备G"):
        return "filing_domestic"
    if identifier.startswith("食健备J"):
        return "filing_imported"
    if identifier.startswith("国食健字G"):
        return "registration_legacy_domestic"
    if identifier.startswith("国食健字J"):
        return "registration_legacy_imported"
    return "unknown"


def _endpoint(identifier: str) -> _Endpoint:
    if identifier.startswith("食健备"):
        return _Endpoint(
            query_path="foodRecord/queryHealthFood",
            detail_path="foodRecord/detailsHealthFood",
            query_field="bah",
            query_payload={
                "currentPage": 1,
                "pageSize": 10,
                "cpnameZw": "",
                "barZw": "",
                "bah": identifier,
                "shxydm": "",
                "iofg": "",
            },
        )
    return _Endpoint(
        query_path="healthFood/queryHealthFood",
        detail_path="healthFood/detailsHealthFood",
        query_field="pzwh",
        query_payload={
            "currentPage": 1,
            "pageSize": 10,
            "cpmc": "",
            "sqrmcZw": "",
            "pzwh": identifier,
            "bjgn": "",
            "zyyl": "",
            "scqymcZw": "",
            "scqymcYw": "",
            "scg": "",
            "cpmcYw": "",
            "iofg": "",
        },
    )


def _response_data(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("state") != 200:
        raise ValueError("official response does not contain a successful state")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError("official response data is not an object")
    return data


def parse_official_response(
    normalized_identifier: str,
    raw_response: dict[str, Any],
    *,
    retrieved_at: str,
    raw_artifact_hash: str,
    raw_artifact_path: str | None,
) -> tuple[str, dict[str, Any] | None]:
    """Parse one recorded query+detail response without inventing fields."""

    query = _response_data(raw_response.get("query"))
    items = query.get("list")
    if not isinstance(items, list):
        raise ValueError("official query response list is missing")
    id_field = "bah" if normalized_identifier.startswith("食健备") else "pzwh"
    exact = [
        item
        for item in items
        if isinstance(item, dict)
        and str(item.get(id_field) or "").replace(" ", "").upper()
        == normalized_identifier
    ]
    if not exact:
        return "not_found", None
    if len(exact) != 1:
        raise ValueError("official query returned multiple exact identifier records")
    detail_payload = raw_response.get("detail")
    if detail_payload is None:
        raise ValueError("official detail response is missing")
    detail = _response_data(detail_payload)
    official_identifier = _text(detail.get(id_field)) or _text(exact[0].get(id_field))
    if not official_identifier or official_identifier.replace(" ", "").upper() != normalized_identifier:
        raise ValueError("official detail identifier does not match the query")
    filing = normalized_identifier.startswith("食健备")
    record = {
        "identifier": normalized_identifier,
        "identifierType": _identifier_type(normalized_identifier),
        "productName": _text(detail.get("cpnameZw" if filing else "cpmc")),
        "registrantOrFiler": _text(detail.get("barZw" if filing else "sqrmcZw")),
        "registrantAddress": _text(detail.get("bardzZw" if filing else "sqrdz")),
        "issueOrFilingDate": _text(detail.get("badate" if filing else "pzrq")),
        "validUntil": None if filing else _text(detail.get("yxqz")),
        "status": _text(detail.get("stat")) or _text(exact[0].get("stat")),
        "officialHealthFunctions": _list_verbatim(detail.get("bjgn")),
        "functionalOrMarkerIngredients": _list_verbatim(detail.get("gxcf")),
        "suitablePopulation": _text(detail.get("syrq")),
        "unsuitablePopulation": _text(detail.get("bsyrq")),
        "specification": _text(detail.get("cpgg")),
        "sourceName": SOURCE_NAME,
        "sourceReference": SOURCE_REFERENCE,
        "retrievedAt": retrieved_at,
        "rawArtifactHash": raw_artifact_hash,
        "rawArtifactPath": raw_artifact_path,
    }
    return "found", record


def _result(
    status: str,
    identifier: str,
    *,
    queried_at: str,
    record: dict[str, Any] | None = None,
    raw_path: str | None = None,
    raw_hash: str | None = None,
    error: str | None = None,
    cache: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "queriedIdentifier": identifier,
        "sourceName": SOURCE_NAME,
        "sourceReference": SOURCE_REFERENCE,
        "queriedAt": queried_at,
        "record": record,
        "rawArtifactPath": raw_path,
        "rawArtifactSha256": raw_hash,
        "providerVersion": PROVIDER_VERSION,
        "cache": cache or {"hit": False, "freshnessDays": DEFAULT_FRESHNESS_DAYS},
        "error": error,
    }


class ImportedOfficialRecordProvider:
    """Read a governed official response fixture/snapshot with an external hash."""

    def __init__(self, metadata_path: Path) -> None:
        self.metadata_path = metadata_path.resolve()

    def lookup(self, normalized_identifier: str) -> dict[str, Any]:
        queried_at = iso_now()
        try:
            metadata = read_json(self.metadata_path)
            raw_path = (self.metadata_path.parent / str(metadata["rawArtifact"])).resolve()
            if not raw_path.is_relative_to(self.metadata_path.parent) or not raw_path.is_file():
                raise ValueError("governed raw artifact path is missing or unsafe")
            raw = read_json(raw_path)
            digest = file_sha256(raw_path)
            if digest != str(metadata.get("rawSha256") or ""):
                raise ValueError("governed raw artifact hash does not match metadata")
            if str(metadata.get("identifier") or "") != normalized_identifier:
                return _result("not_found", normalized_identifier, queried_at=queried_at)
            retrieved_at = str(metadata.get("retrievedAt") or queried_at)
            status, record = parse_official_response(
                normalized_identifier,
                raw,
                retrieved_at=retrieved_at,
                raw_artifact_hash=digest,
                raw_artifact_path=raw_path.as_posix(),
            )
            return _result(
                status,
                normalized_identifier,
                queried_at=queried_at,
                record=record,
                raw_path=raw_path.as_posix(),
                raw_hash=digest,
            )
        except (KeyError, OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            return _result(
                "malformed",
                normalized_identifier,
                queried_at=queried_at,
                error=f"{type(exc).__name__}: {exc}",
            )


Transport = Callable[[str, str, dict[str, Any] | None, float], Any]


def _default_transport(
    method: str, url: str, payload: dict[str, Any] | None, timeout: float
) -> Any:
    data = _json_bytes(payload) if payload is not None else None
    request = Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json;charset=UTF-8",
            "User-Agent": "FoodSafetyResearch/health-food-registry-low-frequency",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


class OfficialOnlineProvider:
    """Low-frequency best-effort adapter for the official public web query."""

    def __init__(
        self,
        cache_root: Path,
        *,
        timeout_seconds: float = 8.0,
        freshness_days: int = DEFAULT_FRESHNESS_DAYS,
        transport: Transport | None = None,
    ) -> None:
        self.cache_root = cache_root.resolve()
        self.timeout_seconds = timeout_seconds
        self.freshness_days = freshness_days
        self.transport = transport or _default_transport

    def _folder(self, identifier: str) -> Path:
        key = hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:24]
        return self.cache_root / key

    def _cached(self, identifier: str) -> dict[str, Any] | None:
        path = self._folder(identifier) / "lookup.json"
        if not path.is_file():
            return None
        try:
            result = read_json(path)
            queried = datetime.fromisoformat(str(result.get("queriedAt") or ""))
            if queried.tzinfo is None:
                queried = queried.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) - queried.astimezone(timezone.utc) > timedelta(days=self.freshness_days):
                return None
            if result.get("queriedIdentifier") != identifier:
                return None
            result["cache"] = {
                "hit": True,
                "freshnessDays": self.freshness_days,
                "retrievedAt": result.get("queriedAt"),
            }
            return result
        except (OSError, ValueError, TypeError):
            return None

    def lookup(self, normalized_identifier: str) -> dict[str, Any]:
        cached = self._cached(normalized_identifier)
        if cached is not None:
            return cached
        queried_at = iso_now()
        endpoint = _endpoint(normalized_identifier)
        folder = self._folder(normalized_identifier)
        raw: dict[str, Any] | None = None
        raw_path: Path | None = None
        raw_hash: str | None = None
        try:
            query = self.transport(
                "POST",
                BASE_API + endpoint.query_path,
                endpoint.query_payload,
                self.timeout_seconds,
            )
            raw = {"query": query, "detail": None}
            raw_path = folder / "raw.json"
            write_json(raw_path, raw)
            raw_hash = file_sha256(raw_path)
            query_data = _response_data(query)
            items = query_data.get("list")
            if not isinstance(items, list):
                raise ValueError("official query response list is missing")
            id_field = endpoint.query_field
            exact = [
                item for item in items
                if isinstance(item, dict)
                and str(item.get(id_field) or "").replace(" ", "").upper()
                == normalized_identifier
            ]
            if not exact:
                raw = {"query": query, "detail": None}
            elif len(exact) == 1 and exact[0].get("infosharId"):
                detail_path = endpoint.detail_path
                if (
                    normalized_identifier.startswith("国食健注J")
                    and not normalized_identifier.startswith("食健备")
                ):
                    detail_path = "healthFood/detailsJinHealthFood"
                detail_url = BASE_API + detail_path + "?" + urlencode(
                    {"id": str(exact[0]["infosharId"])}
                )
                detail = self.transport(
                    "GET", detail_url, None, self.timeout_seconds
                )
                raw = {"query": query, "detail": detail}
            else:
                raise ValueError("official query result is not uniquely resolvable")
            raw_path = folder / "raw.json"
            write_json(raw_path, raw)
            raw_hash = file_sha256(raw_path)
            status, record = parse_official_response(
                normalized_identifier,
                raw,
                retrieved_at=queried_at,
                raw_artifact_hash=raw_hash,
                raw_artifact_path=raw_path.as_posix(),
            )
            result = _result(
                status,
                normalized_identifier,
                queried_at=queried_at,
                record=record,
                raw_path=raw_path.as_posix(),
                raw_hash=raw_hash,
                cache={"hit": False, "freshnessDays": self.freshness_days},
            )
            write_json(folder / "lookup.json", result)
            return result
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            return _result(
                "unavailable",
                normalized_identifier,
                queried_at=queried_at,
                raw_path=raw_path.as_posix() if raw_path else None,
                raw_hash=raw_hash,
                error=f"{type(exc).__name__}: {exc}",
            )
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            return _result(
                "malformed",
                normalized_identifier,
                queried_at=queried_at,
                raw_path=raw_path.as_posix() if raw_path else None,
                raw_hash=raw_hash,
                error=f"{type(exc).__name__}: {exc}",
            )
