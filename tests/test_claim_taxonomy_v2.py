import json
import re
import unittest
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TAXONOMY_PATH = PROJECT_ROOT / "config" / "claim_taxonomy_v2.json"
LEGACY_EFFECT_PATH = PROJECT_ROOT / "config" / "effect_keywords.json"
LEGACY_BRIDGE_PATH = PROJECT_ROOT / "config" / "effect_risk_bridge.json"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


LEGACY_EFFECT_CATEGORIES = read_json(LEGACY_EFFECT_PATH)["effect_categories"]
EXPECTED_LEGACY_KEYWORDS = {
    keyword
    for keywords in LEGACY_EFFECT_CATEGORIES.values()
    for keyword in keywords
}
EXPECTED_LEGACY_PAIRS = {
    (effect, keyword)
    for effect, keywords in LEGACY_EFFECT_CATEGORIES.items()
    for keyword in keywords
}

EXPECTED_EFFECT_MIGRATION = {
    "助眠": "sleep_related",
    "降压": "blood_pressure_related",
    "降脂": "blood_lipid_related",
    "减脂": "weight_management",
    "男性相关": "male_function_related",
}

CLAIM_TYPE_FIELDS = {"id", "label_zh", "description", "status"}
EXPRESSION_FIELDS = {
    "expression_id",
    "text",
    "claim_type",
    "match_mode",
    "source",
    "status",
    "legacy_reference",
    "migration_confidence",
    "notes",
}
MIGRATION_FIELDS = {
    "legacy_effect",
    "new_claim_type",
    "new_display_label",
    "migration_confidence",
    "notes",
}
FORBIDDEN_MAPPING_KEYS = {
    "risk_level",
    "risk_category",
    "risk_mapping",
    "legal_status",
    "health_function_id",
    "health_function_mapping",
    "official_health_function",
    "inspection_mapping",
    "inspection_substance_ids",
    "reference_mapping_id",
}
IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def all_keys(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from all_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from all_keys(child)


class ClaimTaxonomySchemaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.taxonomy = read_json(TAXONOMY_PATH)

    def test_top_level_contract_and_version_are_exact(self):
        self.assertEqual(
            set(self.taxonomy),
            {
                "version",
                "status",
                "description",
                "claim_types",
                "expressions",
                "migration",
                "metadata",
            },
        )
        self.assertEqual(self.taxonomy["version"], "claim-taxonomy-v2.0")
        self.assertEqual(self.taxonomy["status"], "design_baseline")
        self.assertEqual(
            self.taxonomy["metadata"]["runtime_status"],
            "runtime_active_v2_5b1",
        )

    def test_claim_type_ids_are_unique_and_schema_is_bounded(self):
        claim_types = self.taxonomy["claim_types"]
        ids = [item["id"] for item in claim_types]
        self.assertEqual(len(ids), 5)
        self.assertEqual(len(ids), len(set(ids)))
        for item in claim_types:
            self.assertEqual(set(item), CLAIM_TYPE_FIELDS)
            self.assertRegex(item["id"], IDENTIFIER)
            self.assertTrue(item["label_zh"].endswith("宣传"))
            self.assertEqual(item["status"], "active")

    def test_expression_ids_are_unique_and_all_references_resolve(self):
        expressions = self.taxonomy["expressions"]
        ids = [item["expression_id"] for item in expressions]
        claim_type_ids = {item["id"] for item in self.taxonomy["claim_types"]}
        self.assertEqual(len(ids), len(set(ids)))
        for item in expressions:
            self.assertEqual(set(item), EXPRESSION_FIELDS)
            self.assertRegex(item["expression_id"], IDENTIFIER)
            self.assertIn(item["claim_type"], claim_type_ids)
            self.assertEqual(item["match_mode"], "exact")
            self.assertEqual(item["status"], "active")

    def test_all_active_expressions_have_explicit_non_official_provenance(self):
        allowed_sources = {
            "legacy_system",
            "manual_curated",
            "official_source",
            "project_observation",
        }
        for item in self.taxonomy["expressions"]:
            if item["status"] != "active":
                continue
            self.assertIn(item["source"], allowed_sources)
            self.assertEqual(item["source"], "legacy_system")
            self.assertNotEqual(item["source"], "official_source")

    def test_taxonomy_contains_no_risk_health_function_or_inspection_mapping(self):
        present = set(all_keys(self.taxonomy))
        self.assertEqual(present & FORBIDDEN_MAPPING_KEYS, set())


class ClaimTaxonomyLegacyCoverageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.taxonomy = read_json(TAXONOMY_PATH)

    def test_repo_legacy_inventory_is_five_effects_and_twenty_six_keywords(self):
        self.assertEqual(len(LEGACY_EFFECT_CATEGORIES), 5)
        self.assertEqual(len(EXPECTED_LEGACY_KEYWORDS), 26)
        self.assertEqual(sum(map(len, LEGACY_EFFECT_CATEGORIES.values())), 26)

    def test_every_legacy_keyword_appears_exactly_once_without_silent_loss(self):
        references = [
            item["legacy_reference"] for item in self.taxonomy["expressions"]
        ]
        covered_pairs = [
            (reference["effect"], reference["keyword"])
            for reference in references
        ]
        self.assertEqual(set(covered_pairs), EXPECTED_LEGACY_PAIRS)
        self.assertEqual(len(covered_pairs), len(EXPECTED_LEGACY_PAIRS))
        self.assertTrue(
            all(count == 1 for count in Counter(covered_pairs).values())
        )
        self.assertEqual(
            {reference["keyword"] for reference in references},
            EXPECTED_LEGACY_KEYWORDS,
        )

    def test_expression_text_and_claim_type_match_audited_legacy_migration(self):
        for item in self.taxonomy["expressions"]:
            legacy = item["legacy_reference"]
            self.assertEqual(legacy["config"], "config/effect_keywords.json")
            self.assertEqual(item["text"], legacy["keyword"])
            self.assertEqual(
                item["claim_type"], EXPECTED_EFFECT_MIGRATION[legacy["effect"]]
            )

    def test_every_legacy_effect_has_one_auditable_migration(self):
        migrations = self.taxonomy["migration"]
        self.assertTrue(all(set(item) == MIGRATION_FIELDS for item in migrations))
        actual = {
            item["legacy_effect"]: item["new_claim_type"] for item in migrations
        }
        self.assertEqual(actual, EXPECTED_EFFECT_MIGRATION)
        self.assertEqual(len(migrations), len(LEGACY_EFFECT_CATEGORIES))

    def test_no_taxonomy_gap_was_hidden(self):
        self.assertEqual(self.taxonomy["metadata"]["taxonomy_gaps"], [])

    def test_legacy_bridge_remains_a_separate_three_mapping_runtime_contract(self):
        bridge = read_json(LEGACY_BRIDGE_PATH)
        self.assertEqual(len(bridge["mappings"]), 3)
        self.assertFalse(
            any(key in self.taxonomy for key in ("mappings", "risk_mappings"))
        )


class ClaimTaxonomyEvidenceBoundaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = read_json(TAXONOMY_PATH)["metadata"][
            "formal_claim_source_policy"
        ]

    def test_seller_managed_is_the_only_formal_claim_source(self):
        self.assertEqual(
            self.policy["eligible_content_origins"], ["seller_managed"]
        )

    def test_user_generated_is_auxiliary_only(self):
        self.assertEqual(
            self.policy["auxiliary_only_content_origins"], ["user_generated"]
        )
        self.assertNotIn("user_generated", self.policy["eligible_content_origins"])

    def test_excluded_other_product_is_forbidden(self):
        self.assertEqual(
            self.policy["forbidden_content_origins"], ["excluded_other_product"]
        )
        self.assertNotIn(
            "excluded_other_product", self.policy["eligible_content_origins"]
        )


if __name__ == "__main__":
    unittest.main()
