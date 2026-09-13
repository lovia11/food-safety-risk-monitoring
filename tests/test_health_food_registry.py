import tempfile
import unittest
from pathlib import Path
from urllib.error import URLError

from src.health_food_registry import (
    ImportedOfficialRecordProvider,
    OfficialOnlineProvider,
)
from src.runtime import read_json, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = (
    PROJECT_ROOT
    / "tests"
    / "fixtures"
    / "health_food_registry"
    / "registration_G20190188.metadata.json"
)
IDENTIFIER = "国食健注G20190188"


class HealthFoodRegistryProviderTest(unittest.TestCase):
    def test_imported_official_record_is_normalized_without_invented_fields(self):
        result = ImportedOfficialRecordProvider(FIXTURE).lookup(IDENTIFIER)
        self.assertEqual(result["status"], "found")
        record = result["record"]
        self.assertEqual(record["identifier"], IDENTIFIER)
        self.assertEqual(record["productName"], "谷宜甘牌谷胱甘肽茶多酚片")
        self.assertEqual(
            record["officialHealthFunctions"],
            ["本品经动物实验评价，具有对化学性肝损伤有辅助保护作用的保健功能"],
        )
        self.assertEqual(
            record["functionalOrMarkerIngredients"],
            ["每100g含：谷胱甘肽 28.0g、茶多酚 13.5g"],
        )
        self.assertIsNone(record["status"])
        self.assertNotIn("mainIngredients", record)
        self.assertEqual(len(record), 18)
        self.assertEqual(result["rawArtifactSha256"], read_json(FIXTURE)["rawSha256"])

    def test_imported_provider_returns_not_found_for_another_identifier(self):
        result = ImportedOfficialRecordProvider(FIXTURE).lookup("国食健注G20240001")
        self.assertEqual(result["status"], "not_found")
        self.assertIsNone(result["record"])

    def test_imported_provider_rejects_bad_hash_as_malformed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw_source = FIXTURE.parent / "registration_G20190188.raw.json"
            (root / "raw.json").write_bytes(raw_source.read_bytes())
            (root / "meta.json").write_text(
                '{"identifier":"国食健注G20190188","rawArtifact":"raw.json","rawSha256":"bad"}',
                encoding="utf-8",
            )
            result = ImportedOfficialRecordProvider(root / "meta.json").lookup(IDENTIFIER)
        self.assertEqual(result["status"], "malformed")
        self.assertIn("hash", result["error"])

    def test_online_provider_saves_raw_artifact_and_reuses_fresh_cache(self):
        raw = read_json(FIXTURE.parent / "registration_G20190188.raw.json")
        calls = []

        def transport(method, url, payload, timeout):
            calls.append((method, url, payload, timeout))
            return raw["query"] if method == "POST" else raw["detail"]

        with tempfile.TemporaryDirectory() as temporary:
            provider = OfficialOnlineProvider(Path(temporary), transport=transport)
            first = provider.lookup(IDENTIFIER)
            second = provider.lookup(IDENTIFIER)
            self.assertEqual(first["status"], "found")
            self.assertTrue(Path(first["rawArtifactPath"]).is_file())
            self.assertFalse(first["cache"]["hit"])
            self.assertTrue(second["cache"]["hit"])
            self.assertEqual(len(calls), 2)

    def test_stale_cache_is_visible_and_refreshed_instead_of_used_forever(self):
        raw = read_json(FIXTURE.parent / "registration_G20190188.raw.json")
        calls = []

        def transport(method, url, payload, timeout):
            calls.append(method)
            return raw["query"] if method == "POST" else raw["detail"]

        with tempfile.TemporaryDirectory() as temporary:
            provider = OfficialOnlineProvider(Path(temporary), freshness_days=1, transport=transport)
            provider.lookup(IDENTIFIER)
            lookup_path = next(Path(temporary).glob("*/lookup.json"))
            cached = read_json(lookup_path)
            cached["queriedAt"] = "2000-01-01T00:00:00+00:00"
            write_json(lookup_path, cached)
            refreshed = provider.lookup(IDENTIFIER)
        self.assertEqual(calls, ["POST", "GET", "POST", "GET"])
        self.assertFalse(refreshed["cache"]["hit"])

    def test_online_provider_persists_not_found_raw_response(self):
        def transport(method, url, payload, timeout):
            return {"state": 200, "data": {"count": 0, "list": []}}

        with tempfile.TemporaryDirectory() as temporary:
            result = OfficialOnlineProvider(Path(temporary), transport=transport).lookup(IDENTIFIER)
            self.assertEqual(result["status"], "not_found")
            self.assertTrue(Path(result["rawArtifactPath"]).is_file())

    def test_online_provider_reports_unavailable_without_raising(self):
        def transport(method, url, payload, timeout):
            raise URLError("offline")

        with tempfile.TemporaryDirectory() as temporary:
            result = OfficialOnlineProvider(Path(temporary), transport=transport).lookup(IDENTIFIER)
        self.assertEqual(result["status"], "unavailable")
        self.assertIn("offline", result["error"])

    def test_detail_transport_failure_retains_successful_query_artifact(self):
        raw = read_json(FIXTURE.parent / "registration_G20190188.raw.json")

        def transport(method, url, payload, timeout):
            if method == "POST":
                return raw["query"]
            raise URLError("detail offline")

        with tempfile.TemporaryDirectory() as temporary:
            result = OfficialOnlineProvider(Path(temporary), transport=transport).lookup(IDENTIFIER)
            self.assertEqual(result["status"], "unavailable")
            self.assertTrue(Path(result["rawArtifactPath"]).is_file())
            self.assertIsNotNone(result["rawArtifactSha256"])
            saved = read_json(Path(result["rawArtifactPath"]))
        self.assertEqual(saved["query"], raw["query"])
        self.assertIsNone(saved["detail"])

    def test_online_provider_reports_malformed_response_without_record(self):
        def transport(method, url, payload, timeout):
            return {"unexpected": True}

        with tempfile.TemporaryDirectory() as temporary:
            result = OfficialOnlineProvider(Path(temporary), transport=transport).lookup(IDENTIFIER)
            self.assertTrue(Path(result["rawArtifactPath"]).is_file())
        self.assertEqual(result["status"], "malformed")
        self.assertIsNone(result["record"])


if __name__ == "__main__":
    unittest.main()
