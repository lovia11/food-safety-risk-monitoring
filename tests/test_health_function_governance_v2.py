import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HEALTH_FUNCTION_PATH = PROJECT_ROOT / "config" / "health_functions_v2.json"
MAPPING_PATH = PROJECT_ROOT / "config" / "claim_health_function_mapping_v2.json"
CLAIM_PATH = PROJECT_ROOT / "config" / "claim_taxonomy_v2.json"
CONTRACT_CASES_PATH = (
    PROJECT_ROOT / "tests" / "fixtures" / "claim_consistency_v2" / "contract_cases.json"
)

NON_NUTRIENT_FRAMEWORK = "hf-framework-non-nutrient-cn-2023"
NUTRIENT_FRAMEWORK = "hf-framework-nutrient-supplement-cn-2023"

EXPECTED_NON_NUTRIENT_NAMES = [
    "有助于增强免疫力",
    "有助于抗氧化",
    "辅助改善记忆",
    "缓解视觉疲劳",
    "清咽润喉",
    "有助于改善睡眠",
    "缓解体力疲劳",
    "耐缺氧",
    "有助于控制体内脂肪",
    "有助于改善骨密度",
    "改善缺铁性贫血",
    "有助于改善痤疮",
    "有助于改善黄褐斑",
    "有助于改善皮肤水份状况",
    "有助于调节肠道菌群",
    "有助于消化",
    "有助于润肠通便",
    "辅助保护胃粘膜",
    "有助于维持血脂（胆固醇/甘油三酯）健康水平",
    "有助于维持血糖健康水平",
    "有助于维持血压健康水平",
    "对化学性肝损伤有辅助保护作用",
    "对电离辐射危害有辅助保护作用",
    "有助于排铅",
]

EXPECTED_TRANSITION_ALIASES = {
    "hf-non-nutrient-cn-2023-01": ["免疫调节", "增强免疫力"],
    "hf-non-nutrient-cn-2023-02": ["延缓衰老", "抗氧化"],
    "hf-non-nutrient-cn-2023-03": ["改善记忆"],
    "hf-non-nutrient-cn-2023-04": ["改善视力", "缓解视疲劳"],
    "hf-non-nutrient-cn-2023-05": ["清咽"],
    "hf-non-nutrient-cn-2023-06": ["改善睡眠"],
    "hf-non-nutrient-cn-2023-07": ["抗疲劳"],
    "hf-non-nutrient-cn-2023-08": ["提高缺氧耐受力"],
    "hf-non-nutrient-cn-2023-09": ["减肥"],
    "hf-non-nutrient-cn-2023-10": ["改善骨质疏松", "增加骨密度"],
    "hf-non-nutrient-cn-2023-11": ["改善营养性贫血"],
    "hf-non-nutrient-cn-2023-12": ["美容（祛痤疮）", "祛痤疮"],
    "hf-non-nutrient-cn-2023-13": ["美容（祛黄褐斑）", "祛黄褐斑"],
    "hf-non-nutrient-cn-2023-14": ["美容（改善皮肤水分/油分)", "改善皮肤水分"],
    "hf-non-nutrient-cn-2023-15": ["改善胃肠功能（调节肠道菌群）", "调节肠道菌群"],
    "hf-non-nutrient-cn-2023-16": ["改善胃肠功能（促进消化）", "促进消化"],
    "hf-non-nutrient-cn-2023-17": ["改善胃肠功能（润肠通便）", "通便"],
    "hf-non-nutrient-cn-2023-18": [
        "改善胃肠功能（对胃黏膜损伤有辅助保护作用）",
        "对胃粘膜损伤有辅助保护功能",
    ],
    "hf-non-nutrient-cn-2023-19": [
        "调节血脂（降低总胆固醇、降低甘油三酯）",
        "辅助降血脂",
    ],
    "hf-non-nutrient-cn-2023-20": ["调节血糖", "辅助降血糖"],
    "hf-non-nutrient-cn-2023-21": ["调节血压", "辅助降血压"],
    "hf-non-nutrient-cn-2023-22": [
        "对化学性肝损伤有保护作用",
        "对化学性肝损伤有辅助保护功能",
    ],
    "hf-non-nutrient-cn-2023-23": ["抗辐射", "对辐射危害有辅助保护作用"],
    "hf-non-nutrient-cn-2023-24": ["促进排铅"],
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_registry_function(raw_value: str, dataset: dict) -> dict:
    """Design-test resolver: exact official/transition strings only.

    This helper intentionally lives in governance tests and is not connected to
    the production provider, pipeline, DataStore, API, or frontend.
    """

    current = {item["official_name"]: item["function_id"] for item in dataset["functions"]}
    aliases = {item["alias_text"]: item["function_id"] for item in dataset["aliases"]}
    if raw_value in current:
        return {
            "raw": raw_value,
            "status": "resolved",
            "resolution": "current_official_name",
            "function_id": current[raw_value],
        }
    if raw_value in aliases:
        return {
            "raw": raw_value,
            "status": "resolved",
            "resolution": "official_transition_alias",
            "function_id": aliases[raw_value],
        }
    return {
        "raw": raw_value,
        "status": "unresolved_official_function",
        "resolution": None,
        "function_id": None,
    }


class HealthFunctionDatasetGovernanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = load_json(HEALTH_FUNCTION_PATH)

    def test_dataset_identity_and_sources_are_complete(self):
        self.assertEqual(self.dataset["dataset_id"], "health-functions-v2")
        self.assertEqual(self.dataset["dataset_version"], "health-functions-v2.0")
        self.assertEqual(self.dataset["dataset_status"], "design_baseline")
        self.assertEqual(self.dataset["jurisdiction"], "CN")
        self.assertTrue(self.dataset["collected_at"])
        self.assertTrue(self.dataset["verified_at"])
        self.assertEqual(len(self.dataset["sources"]), 3)
        for source in self.dataset["sources"]:
            for key in ("source_id", "source_name", "source_reference", "source_date", "status", "jurisdiction"):
                self.assertTrue(source[key], (source["source_id"], key))
            self.assertTrue(source["source_reference"].startswith("https://www.samr.gov.cn/"))

    def test_frameworks_are_separate_and_source_backed(self):
        frameworks = {item["framework_id"]: item for item in self.dataset["frameworks"]}
        self.assertEqual(set(frameworks), {NON_NUTRIENT_FRAMEWORK, NUTRIENT_FRAMEWORK})
        self.assertEqual(frameworks[NON_NUTRIENT_FRAMEWORK]["framework_type"], "non_nutrient")
        self.assertEqual(frameworks[NUTRIENT_FRAMEWORK]["framework_type"], "nutrient_supplement")
        self.assertNotEqual(
            frameworks[NON_NUTRIENT_FRAMEWORK]["framework_id"],
            frameworks[NUTRIENT_FRAMEWORK]["framework_id"],
        )
        source_ids = {item["source_id"] for item in self.dataset["sources"]}
        for framework in frameworks.values():
            self.assertTrue(framework["source_ids"])
            self.assertTrue(set(framework["source_ids"]).issubset(source_ids))

    def test_non_nutrient_catalog_is_complete_24_of_24(self):
        functions = [
            item for item in self.dataset["functions"]
            if item["framework_id"] == NON_NUTRIENT_FRAMEWORK
        ]
        self.assertEqual(len(functions), 24)
        self.assertEqual([item["ordinal"] for item in functions], list(range(1, 25)))
        self.assertEqual([item["official_name"] for item in functions], EXPECTED_NON_NUTRIENT_NAMES)
        self.assertEqual(
            self.dataset["metadata"]["coverage"]["non_nutrient_current_functions"],
            "24/24",
        )

    def test_nutrient_supplement_framework_is_not_flattened_into_non_nutrient(self):
        nutrient = [
            item for item in self.dataset["functions"]
            if item["framework_id"] == NUTRIENT_FRAMEWORK
        ]
        self.assertEqual(len(nutrient), 1)
        self.assertEqual(nutrient[0]["official_name"], "补充维生素、矿物质等营养物质")
        self.assertEqual(
            self.dataset["metadata"]["coverage"]["nutrient_registry_string_normalization"],
            "not_yet_governed",
        )

    def test_function_ids_and_ordinals_are_unique_and_records_are_source_backed(self):
        function_ids = [item["function_id"] for item in self.dataset["functions"]]
        self.assertEqual(len(function_ids), len(set(function_ids)))
        ordinal_keys = [(item["framework_id"], item["ordinal"]) for item in self.dataset["functions"]]
        self.assertEqual(len(ordinal_keys), len(set(ordinal_keys)))
        framework_ids = {item["framework_id"] for item in self.dataset["frameworks"]}
        for item in self.dataset["functions"]:
            self.assertIn(item["framework_id"], framework_ids)
            for key in (
                "function_id", "official_name", "jurisdiction", "framework_version",
                "ordinal", "status", "source_name", "source_reference", "source_date",
            ):
                self.assertNotIn(item[key], (None, ""), (item["function_id"], key))

    def test_transition_aliases_are_complete_unambiguous_and_source_backed(self):
        aliases = self.dataset["aliases"]
        self.assertEqual(len(aliases), 40)
        self.assertEqual(
            self.dataset["metadata"]["coverage"]["official_transition_aliases"],
            len(aliases),
        )
        alias_ids = [item["alias_id"] for item in aliases]
        alias_texts = [item["alias_text"] for item in aliases]
        current_names = {item["official_name"] for item in self.dataset["functions"]}
        function_ids = {item["function_id"] for item in self.dataset["functions"]}
        self.assertEqual(len(alias_ids), len(set(alias_ids)))
        self.assertEqual(len(alias_texts), len(set(alias_texts)))
        self.assertFalse(current_names.intersection(alias_texts))
        actual_by_function = {
            function_id: [
                item["alias_text"] for item in aliases
                if item["function_id"] == function_id
            ]
            for function_id in EXPECTED_TRANSITION_ALIASES
        }
        self.assertEqual(actual_by_function, EXPECTED_TRANSITION_ALIASES)
        for alias in aliases:
            self.assertIn(alias["function_id"], function_ids)
            self.assertEqual(alias["alias_type"], "official_transition_name")
            self.assertEqual(alias["status"], "verified_reference")
            for key in ("source_name", "source_reference", "source_date"):
                self.assertTrue(alias[key], (alias["alias_id"], key))

    def test_health_function_dataset_contains_no_cross_domain_mapping(self):
        forbidden_keys = {
            "claim_type", "risk_level", "risk_signal", "substance_id",
            "inspection_method", "method_id", "illegal", "compliant",
        }

        def keys(value):
            if isinstance(value, dict):
                for key, nested in value.items():
                    yield key
                    yield from keys(nested)
            elif isinstance(value, list):
                for nested in value:
                    yield from keys(nested)

        self.assertFalse(forbidden_keys.intersection(keys(self.dataset)))

    def test_normalization_policy_matches_the_frozen_resolution_contract(self):
        policy = self.dataset["metadata"]["normalization_policy"]
        self.assertEqual(
            policy["allowed_resolution_sources"],
            [
                "current_official_name",
                "official_transition_alias",
                "explicit_governed_mapping",
            ],
        )
        self.assertTrue(policy["raw_registry_function_must_be_preserved"])
        self.assertTrue(
            {
                "substring_match",
                "fuzzy_string_similarity",
                "embedding",
                "llm",
                "automatic_edit_distance",
                "ungoverned_semantic_synonym",
            }.issubset(policy["forbidden_resolution_methods"])
        )


class OfficialFunctionNormalizationContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = load_json(HEALTH_FUNCTION_PATH)

    def test_current_official_exact_name_resolves(self):
        result = resolve_registry_function("有助于改善睡眠", self.dataset)
        self.assertEqual(result["function_id"], "hf-non-nutrient-cn-2023-06")
        self.assertEqual(result["resolution"], "current_official_name")

    def test_required_historical_names_resolve_to_current_identity(self):
        expected = {
            "改善睡眠": "hf-non-nutrient-cn-2023-06",
            "减肥": "hf-non-nutrient-cn-2023-09",
            "辅助降血脂": "hf-non-nutrient-cn-2023-19",
            "辅助降血压": "hf-non-nutrient-cn-2023-21",
        }
        for raw, function_id in expected.items():
            with self.subTest(raw=raw):
                result = resolve_registry_function(raw, self.dataset)
                self.assertEqual(result["function_id"], function_id)
                self.assertEqual(result["resolution"], "official_transition_alias")
                self.assertEqual(result["raw"], raw)

    def test_unknown_typo_and_semantic_synonym_remain_unresolved(self):
        for raw in ("完全未知功能", "有助于改善睡眠。", "帮助安睡"):
            with self.subTest(raw=raw):
                result = resolve_registry_function(raw, self.dataset)
                self.assertEqual(result["status"], "unresolved_official_function")
                self.assertIsNone(result["function_id"])

    def test_recorded_positive_fixture_verbatim_string_is_not_substring_normalized(self):
        raw = "本品经动物实验评价，具有对化学性肝损伤有辅助保护作用的保健功能"
        result = resolve_registry_function(raw, self.dataset)
        self.assertEqual(result["status"], "unresolved_official_function")
        self.assertEqual(result["raw"], raw)


class ClaimHealthFunctionMappingGovernanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mapping = load_json(MAPPING_PATH)
        cls.health = load_json(HEALTH_FUNCTION_PATH)
        cls.claim = load_json(CLAIM_PATH)

    def test_mapping_identity_references_and_relation_are_governed(self):
        self.assertEqual(self.mapping["dataset_version"], "claim-health-function-mapping-v2.0")
        self.assertEqual(self.mapping["claim_taxonomy_version"], self.claim["version"])
        self.assertEqual(self.mapping["health_function_dataset_version"], self.health["dataset_version"])
        claim_types = {item["id"] for item in self.claim["claim_types"]}
        function_ids = {item["function_id"] for item in self.health["functions"]}
        mapping_ids = [item["mapping_id"] for item in self.mapping["mappings"]]
        self.assertEqual(len(mapping_ids), len(set(mapping_ids)))
        for item in self.mapping["mappings"]:
            self.assertIn(item["claim_type"], claim_types)
            self.assertIn(item["health_function_id"], function_ids)
            self.assertIn(item["relation"], self.mapping["allowed_relations"])
            self.assertEqual(item["relation"], "topic_related")
            self.assertEqual(item["source_basis"], "project_governed_topic_mapping")
            self.assertTrue(item["source_references"])
            self.assertTrue(item["reviewed_by"])
            self.assertTrue(item["reviewed_at"])

    def test_exact_four_topic_mappings_and_male_function_gap(self):
        mappings = {item["claim_type"]: item for item in self.mapping["mappings"]}
        self.assertEqual(
            set(mappings),
            {"sleep_related", "weight_management", "blood_lipid_related", "blood_pressure_related"},
        )
        self.assertNotIn("male_function_related", mappings)
        gaps = {item["claim_type"]: item for item in self.mapping["mapping_gaps"]}
        self.assertEqual(
            gaps["male_function_related"]["status"],
            "no_governed_health_function_mapping",
        )
        self.assertEqual(
            self.mapping["metadata"]["claim_expression_attention_dataset_status"],
            "pending_manual_governance",
        )

    def test_mapping_is_not_official_equivalence_risk_or_inspection_knowledge(self):
        self.assertFalse(self.mapping["metadata"]["official_equivalence"])
        self.assertFalse(self.mapping["metadata"]["creates_risk_signal"])
        self.assertFalse(self.mapping["metadata"]["creates_inspection_recommendation"])
        for item in self.mapping["mappings"]:
            self.assertNotIn(item["relation"], {"equivalent", "approved", "compliant", "legal"})
            self.assertFalse(
                {"risk_signal_id", "risk_category", "substance_id", "method_id", "inspection_method"}
                .intersection(item)
            )

    def test_registry_alias_does_not_approve_same_page_claim_expression(self):
        registry_resolution = resolve_registry_function("减肥", self.health)
        claim_expression = next(item for item in self.claim["expressions"] if item["text"] == "减肥")
        mapping = next(item for item in self.mapping["mappings"] if item["claim_type"] == "weight_management")
        self.assertEqual(registry_resolution["resolution"], "official_transition_alias")
        self.assertEqual(claim_expression["claim_type"], "weight_management")
        self.assertEqual(mapping["relation"], "topic_related")
        self.assertFalse(self.mapping["metadata"]["official_equivalence"])


class ClaimConsistencyDesignFixtureTest(unittest.TestCase):
    def test_required_design_matrix_and_non_adjudicative_states(self):
        fixture = load_json(CONTRACT_CASES_PATH)
        cases = {item["case_id"]: item for item in fixture["cases"]}
        self.assertEqual(len(cases), 12)
        required = {
            "identity-unverified-with-claims",
            "verified-claim-not-generated",
            "verified-claim-analysis-error",
            "verified-zero-page-claims",
            "verified-sleep-topic-recorded",
            "verified-sleep-topic-not-recorded",
            "verified-male-function-mapping-gap",
            "verified-legacy-sleep-function-name",
            "verified-unresolved-official-function",
            "verified-multiple-claims-and-functions",
            "verified-nutrient-framework-does-not-borrow-non-nutrient-mapping",
            "verified-framework-unresolved",
        }
        self.assertEqual(set(cases), required)
        allowed_states = {
            "identity_not_verified",
            "claim_not_generated",
            "claim_analysis_error",
            "framework_unresolved",
            "official_function_unresolved",
            "no_page_claims",
            "assessed",
        }
        allowed_relations = {
            "function_topic_recorded",
            "function_topic_not_recorded",
            "no_governed_function_mapping",
            "mapping_unresolved",
        }
        forbidden = {"pass", "fail", "compliant", "non_compliant", "legal", "illegal", "violation"}
        for case in cases.values():
            self.assertIn(case["expected_state"], allowed_states)
            self.assertTrue(set(case["expected_relations"]).issubset(allowed_relations))
            self.assertNotIn(case["expected_state"], forbidden)


if __name__ == "__main__":
    unittest.main()
