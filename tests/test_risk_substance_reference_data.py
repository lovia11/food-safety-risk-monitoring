import tempfile
import unittest
from pathlib import Path

from src.data_store import DataStore
from src.risk_substance_reference import validate_risk_substance_config
from src.runtime import read_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RISK_REFERENCE_CONFIG = PROJECT_ROOT / "config" / "risk_substance_reference.json"
INSPECTION_REFERENCE_CONFIG = PROJECT_ROOT / "config" / "inspection_reference.json"

EXPECTED_MAPPING_IDS = {
    "weight-loss-sibutramine-group-cn-2025",
    "male-function-nafei-lafei-group-cn-2025",
    "anti-fatigue-nafei-lafei-group-cn-2025",
}
EXPECTED_CATEGORIES = {"weight_loss", "male_function", "anti_fatigue"}
SIBUTRAMINE_SOURCE = (
    "https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/zfjcs/art/2025/"
    "art_935c1a68c87445729ad2e6c1d88607c6.html"
)
NAFEI_LAFEI_SOURCE = (
    "https://www.samr.gov.cn/xw/zj/art/2025/"
    "art_b066d669285e4494bbee7c988b6dfb2e.html"
)
INSPECTION_COUNTS = {
    "inspection_methods": 5,
    "inspection_substances": 117,
    "inspection_method_substances": 132,
    "inspection_method_applicabilities": 37,
    "substance_regulatory_contexts": 1,
}


def load_verified_risk_dataset() -> dict:
    return validate_risk_substance_config(read_json(RISK_REFERENCE_CONFIG))


class VerifiedRiskSubstanceReferenceDataTest(unittest.TestCase):
    def test_verified_dataset_contract_and_identity_are_exact(self):
        payload = load_verified_risk_dataset()
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["dataset_id"], "risk-substance-reference")
        self.assertEqual(payload["dataset_version"], "2026.09-c2")
        self.assertEqual(payload["dataset_status"], "verified_reference")
        self.assertEqual(len(payload["mappings"]), 3)
        self.assertEqual(
            {mapping["mapping_id"] for mapping in payload["mappings"]},
            EXPECTED_MAPPING_IDS,
        )
        self.assertEqual(
            {mapping["risk_category"] for mapping in payload["mappings"]},
            EXPECTED_CATEGORIES,
        )

    def test_all_mappings_are_grade_a_current_group_targets(self):
        mappings = load_verified_risk_dataset()["mappings"]
        self.assertTrue(
            all(mapping["target_type"] == "substance_group" for mapping in mappings)
        )
        self.assertTrue(all(mapping["substance_id"] is None for mapping in mappings))
        self.assertFalse(
            any(mapping["target_type"] == "substance" for mapping in mappings)
        )
        self.assertTrue(all(mapping["evidence_grade"] == "A" for mapping in mappings))
        self.assertTrue(
            all(
                mapping["basis_type"] == "current_official_guidance"
                for mapping in mappings
            )
        )
        self.assertTrue(
            all(mapping["temporal_status"] == "current" for mapping in mappings)
        )

        by_category = {mapping["risk_category"]: mapping for mapping in mappings}
        self.assertEqual(
            by_category["weight_loss"]["target_group_label"],
            "西布曲明及其系列衍生物",
        )
        self.assertEqual(
            by_category["male_function"]["target_group_label"],
            "那非类、拉非类物质",
        )
        self.assertEqual(
            by_category["anti_fatigue"]["target_group_label"],
            "那非类、拉非类物质",
        )

    def test_mapping_sources_dates_and_nonconclusion_boundaries_are_exact(self):
        mappings = load_verified_risk_dataset()["mappings"]
        by_category = {mapping["risk_category"]: mapping for mapping in mappings}
        weight_loss = by_category["weight_loss"]
        self.assertEqual(weight_loss["source_reference"], SIBUTRAMINE_SOURCE)
        self.assertEqual(weight_loss["source_date"], "2025-10-18")

        for category in ("male_function", "anti_fatigue"):
            self.assertEqual(
                by_category[category]["source_reference"], NAFEI_LAFEI_SOURCE
            )
            self.assertEqual(by_category[category]["source_date"], "2025-06-28")

        for mapping in mappings:
            self.assertTrue(mapping["source_basis_text"])
            self.assertIn("不得解释", mapping["note"])

    def test_sqlite_import_is_idempotent_and_preserves_inspection_counts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = DataStore(root / "data" / "app.db", root / "output")
            store.initialize()
            store.import_inspection_config(INSPECTION_REFERENCE_CONFIG)
            before = store.table_counts()
            self.assertEqual(
                {key: before[key] for key in INSPECTION_COUNTS},
                INSPECTION_COUNTS,
            )

            expected = {"dataset": 1, "mappings": 3}
            self.assertEqual(
                store.import_risk_substance_config(RISK_REFERENCE_CONFIG), expected
            )
            first = store.table_counts()
            self.assertEqual(first["risk_mapping_datasets"], 1)
            self.assertEqual(first["risk_substance_mappings"], 3)

            self.assertEqual(
                store.import_risk_substance_config(RISK_REFERENCE_CONFIG), expected
            )
            after = store.table_counts()
            self.assertEqual(after, first)
            self.assertEqual(
                {key: after[key] for key in INSPECTION_COUNTS},
                INSPECTION_COUNTS,
            )


if __name__ == "__main__":
    unittest.main()
