import tempfile
import unittest
from pathlib import Path

from src.health_food_identity import (
    assess_product_match,
    classify_registration_identifier,
    extract_health_food_identity,
    load_health_food_identity,
    normalize_product_name,
)
from src.health_food_registry import ImportedOfficialRecordProvider
from src.runtime import write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_FIXTURE = PROJECT_ROOT / "tests/fixtures/health_food_registry/registration_G20190188.metadata.json"


class IdentifierContractTest(unittest.TestCase):
    CASES = (
        ("国食健注G20241234", "registration_current_domestic", "valid_current", "国食健注G20241234"),
        ("国食健注J20241234", "registration_current_imported", "valid_current", "国食健注J20241234"),
        ("食健备G202413123456", "filing_domestic", "valid_current", "食健备G202413123456"),
        ("食健备J202400123456", "filing_imported", "valid_current", "食健备J202400123456"),
        ("国食健字G20050123", "registration_legacy_domestic", "legacy_identifier_candidate", "国食健字G20050123"),
        ("国食健字J20050123", "registration_legacy_imported", "legacy_identifier_candidate", "国食健字J20050123"),
        (" 国食健注 G 2024 1234 ", "registration_current_domestic", "valid_current", "国食健注G20241234"),
        ("（国食健注G20241234）", "registration_current_domestic", "valid_current", "国食健注G20241234"),
        ("国食健注ｇ２０２４１２３４", "registration_current_domestic", "valid_current", "国食健注G20241234"),
        ("国食健注G99123456", "registration_current_domestic", "invalid", "国食健注G99123456"),
        ("国食健注G2024123", "registration_current_domestic", "invalid", "国食健注G2024123"),
        ("食健备J202411123456", "filing_imported", "invalid", "食健备J202411123456"),
        ("卫食健字(2003)第001号", "unknown", "invalid", "卫食健字(2003)第001号"),
    )

    def test_identifier_formats_and_lossless_normalization(self):
        for raw, expected_type, state, normalized in self.CASES:
            with self.subTest(raw=raw):
                result = classify_registration_identifier(raw)
                self.assertEqual(result["identifierType"], expected_type)
                self.assertEqual(result["formatState"], state)
                self.assertEqual(result["normalizedValue"], normalized)

    def test_ocr_ambiguous_characters_are_never_silently_corrected(self):
        for raw in (
            "国食健注G2O241234",
            "国食健注G2024I234",
            "国食健注G2024S234",
            "国食健注G2024B234",
        ):
            with self.subTest(raw=raw):
                result = classify_registration_identifier(raw, source_type="ocr_detail_image")
                self.assertEqual(result["formatState"], "ambiguous_ocr")
                self.assertEqual(result["normalizedValue"], raw)


class HealthFoodIdentityExtractionTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "product"
        self.root.mkdir(parents=True)
        write_json(self.root / "meta.json", {"productName": "很长的淘宝营销标题"})

    def tearDown(self):
        self.temporary.cleanup()

    def _dom(self, value: str):
        (self.root / "dom_text.txt").write_text(value, encoding="utf-8")

    def _ocr(self, lines: list[str]):
        ocr = self.root / "ocr"
        ocr.mkdir(exist_ok=True)
        (ocr / "original_001.txt").write_text("\n".join(lines), encoding="utf-8")
        write_json(
            ocr / "manifest.json",
            [{"status": "success", "textPath": "ocr/original_001.txt", "sourcePath": "images/original/original_001.jpg"}],
        )

    def _extract(self, provider=None):
        return extract_health_food_identity(
            self.root,
            "ps_test",
            provider=provider,
            generated_at="2026-09-13T10:00:00+08:00",
        )

    def test_no_identity_and_explicit_negative_parameter_stay_no_indicator(self):
        self._dom("参数信息\n是否保健食品（国食健字号）\n否\n图文详情")
        payload = self._extract()
        self.assertEqual(payload["identityAssessment"]["state"], "no_indicator")
        self.assertEqual(payload["clues"], [])

    def test_blue_hat_text_is_candidate_indicator_only(self):
        self._dom("参数信息\n品牌：测试\n图文详情\n包装展示小蓝帽")
        payload = self._extract()
        self.assertEqual(payload["identityAssessment"]["state"], "candidate_indicator_only")
        self.assertEqual(payload["clues"][0]["contentOrigin"], "seller_managed")

    def test_valid_identifier_without_provider_is_only_candidate(self):
        self._dom("参数信息\n批准文号：国食健注G20190188\n图文详情")
        payload = self._extract()
        self.assertEqual(payload["identityAssessment"]["state"], "candidate_identifier")
        self.assertFalse(payload["diagnostics"]["registryLookupAttempted"])

    def test_ugc_and_recommendation_identifier_are_excluded(self):
        self._dom(
            "用户评价\n国食健注G20190188\n查看全部评价\n参数信息\n品牌：测试\n图文详情\n"
            "本店推荐\n商品 ¥88 国食健注G20190188"
        )
        payload = self._extract()
        self.assertEqual(payload["identifierCandidates"], [])
        self.assertEqual(payload["identityAssessment"]["state"], "no_indicator")

    def test_ocr_ambiguity_is_retained_and_not_queried(self):
        self._dom("参数信息\n品牌：测试\n图文详情")
        self._ocr(["批准文号 国食健注G2O190188"])
        provider = _Provider("found")
        payload = self._extract(provider)
        self.assertEqual(payload["identityAssessment"]["state"], "identifier_ambiguous")
        self.assertEqual(provider.calls, [])

    def test_duplicate_identifier_sources_do_not_create_conflict(self):
        self._dom("参数信息\n批准文号：国食健注G20190188\n图文详情")
        self._ocr(["国食健注G20190188"])
        payload = self._extract()
        self.assertEqual(payload["identityAssessment"]["state"], "candidate_identifier")
        self.assertEqual(len(payload["identifierCandidates"]), 2)

    def test_two_distinct_identifiers_create_conflict_without_lookup(self):
        self._dom("参数信息\n批准文号：国食健注G20190188\n图文详情")
        self._ocr(["国食健注G20240001"])
        provider = _Provider("found")
        payload = self._extract(provider)
        self.assertEqual(payload["identityAssessment"]["state"], "conflict")
        self.assertEqual(provider.calls, [])

    def test_official_positive_exact_product_name_is_verified(self):
        self._dom(
            "参数信息\n产品名称：谷宜甘牌谷胱甘肽茶多酚片\n批准文号：国食健注G20190188\n图文详情"
        )
        payload = self._extract(ImportedOfficialRecordProvider(REGISTRY_FIXTURE))
        self.assertEqual(payload["identityAssessment"]["state"], "verified_match")
        self.assertEqual(payload["officialLookup"]["record"]["officialHealthFunctions"], [
            "本品经动物实验评价，具有对化学性肝损伤有辅助保护作用的保健功能"
        ])
        self.assertIsNotNone(load_health_food_identity(self.root / "health_food_identity.json", expected_snapshot_id="ps_test"))

    def test_title_only_never_verifies_official_record(self):
        write_json(self.root / "meta.json", {"productName": "谷宜甘牌谷胱甘肽茶多酚片"})
        self._dom("参数信息\n批准文号：国食健注G20190188\n图文详情")
        payload = self._extract(ImportedOfficialRecordProvider(REGISTRY_FIXTURE))
        self.assertEqual(payload["identityAssessment"]["state"], "registry_record_found_identity_unverified")

    def test_official_lookup_outcomes_are_explicit(self):
        self._dom("参数信息\n批准文号：国食健注G20190188\n图文详情")
        for status, expected in (
            ("not_found", "registry_record_not_found"),
            ("unavailable", "registry_lookup_unavailable"),
            ("malformed", "registry_lookup_unavailable"),
        ):
            with self.subTest(status=status):
                payload = self._extract(_Provider(status))
                self.assertEqual(payload["identityAssessment"]["state"], expected)

    def test_product_name_matching_is_exact_after_formatting_only(self):
        official = "谷宜甘牌谷胱甘肽茶多酚片"
        exact = assess_product_match([{"value": official}], official)
        formatting = assess_product_match([{"value": "谷宜甘牌·谷胱甘肽 茶多酚片®"}], official)
        missing = assess_product_match([], official, title_auxiliary=official)
        mismatch = assess_product_match([{"value": "B牌钙片"}], official)
        conflict = assess_product_match([{"value": official}, {"value": "B牌钙片"}], official)
        self.assertEqual(exact["state"], "strong_match")
        self.assertEqual(formatting["state"], "strong_match")
        self.assertEqual(missing["state"], "unverified")
        self.assertEqual(mismatch["state"], "mismatch")
        self.assertEqual(conflict["state"], "conflict")
        self.assertEqual(normalize_product_name("A 品®"), normalize_product_name("A·品"))


class _Provider:
    def __init__(self, status):
        self.status = status
        self.calls = []

    def lookup(self, identifier):
        self.calls.append(identifier)
        record = None
        if self.status == "found":
            record = {"identifier": identifier, "productName": "测试产品", "officialHealthFunctions": []}
        return {
            "status": self.status,
            "queriedIdentifier": identifier,
            "sourceName": "official",
            "sourceReference": "https://example.invalid",
            "queriedAt": "2026-09-13T10:00:00+08:00",
            "record": record,
            "rawArtifactPath": None,
            "rawArtifactSha256": None,
            "error": "offline" if self.status == "unavailable" else None,
        }


if __name__ == "__main__":
    unittest.main()
