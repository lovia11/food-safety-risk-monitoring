import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.data_store import DataStore
from src.inspection_reference import validate_inspection_config
from src.risk_substance_reference import validate_risk_substance_config
from src.runtime import read_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RISK_REFERENCE_CONFIG = PROJECT_ROOT / "config" / "risk_substance_reference.json"
INSPECTION_REFERENCE_CONFIG = PROJECT_ROOT / "config" / "inspection_reference.json"

EXPECTED_GROUP_MAPPING_IDS = {
    "weight-loss-sibutramine-group-cn-2025",
    "male-function-nafei-lafei-group-cn-2025",
    "anti-fatigue-nafei-lafei-group-cn-2025",
}
EXPECTED_SUBSTANCE_MAPPING_IDS = {
    "weight-loss-sibutramine-cn-2025",
    "male-function-sildenafil-cn-2025",
    "male-function-tadalafil-cn-2025",
    "anti-fatigue-sildenafil-cn-2025",
    "anti-fatigue-tadalafil-cn-2025",
}
EXPECTED_MAPPING_IDS = EXPECTED_GROUP_MAPPING_IDS | EXPECTED_SUBSTANCE_MAPPING_IDS
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
EXPECTED_SUBSTANCE_IDENTITIES = {
    "substance-cas-106650-56-0": "西布曲明",
    "substance-cas-139755-83-2": "西地那非",
    "substance-cas-171596-29-5": "他达拉非",
}
EXPECTED_SUBSTANCE_TARGETS = {
    "weight_loss": {"substance-cas-106650-56-0"},
    "male_function": {
        "substance-cas-139755-83-2",
        "substance-cas-171596-29-5",
    },
    "anti_fatigue": {
        "substance-cas-139755-83-2",
        "substance-cas-171596-29-5",
    },
}
EXPECTED_GROUP_MAPPINGS = {
    "weight-loss-sibutramine-group-cn-2025": {
        "mapping_id": "weight-loss-sibutramine-group-cn-2025",
        "dataset_id": "risk-substance-reference",
        "risk_category": "weight_loss",
        "risk_label": "减肥/减重宣传",
        "target_type": "substance_group",
        "substance_id": None,
        "target_group_label": "西布曲明及其系列衍生物",
        "evidence_grade": "A",
        "basis_type": "current_official_guidance",
        "temporal_status": "current",
        "product_scope": "宣称减肥功能的食品",
        "source_name": "市场监管总局办公厅关于发布西布曲明及其系列衍生物有毒有害认定意见及执法检验方法的通知",
        "source_reference": SIBUTRAMINE_SOURCE,
        "source_date": "2025-10-18",
        "source_basis_text": "市场监管总局在查办宣称减肥功能食品非法添加案件中，发现食品中非法添加西布曲明新型衍生物，并对食品中的西布曲明及其系列衍生物作出有毒有害认定。",
        "note": "本Mapping表示“减肥/减重宣传”是当前官方来源明确出现的西布曲明及其系列衍生物监管关注方向。不得解释为出现减肥宣传的商品实际含有西布曲明，也不得解释为页面宣传本身构成非法添加证据。",
    },
    "male-function-nafei-lafei-group-cn-2025": {
        "mapping_id": "male-function-nafei-lafei-group-cn-2025",
        "dataset_id": "risk-substance-reference",
        "risk_category": "male_function",
        "risk_label": "补肾壮阳/男性功能宣传",
        "target_type": "substance_group",
        "substance_id": None,
        "target_group_label": "那非类、拉非类物质",
        "evidence_grade": "A",
        "basis_type": "current_official_guidance",
        "temporal_status": "current",
        "product_scope": "酒类、压片糖果、咖啡等食品（来源列举的典型食品场景）",
        "source_name": "市场监管总局等两部委将那非类、拉非类物质纳入食品中可能添加的非食用物质名录",
        "source_reference": NAFEI_LAFEI_SOURCE,
        "source_date": "2025-06-28",
        "source_basis_text": "市场监管总局官方解读指出，那非类、拉非类物质包括西地那非、他达拉非等药物及其衍生物；部分不法商家将其掺入酒类、压片糖果、咖啡等食品，并以补肾壮阳等功效进行宣传。",
        "note": "本Mapping表示“补肾壮阳/男性功能宣传”是当前官方来源明确关联的那非类、拉非类监管关注方向。不得解释为出现该宣传的商品实际含有相关物质。",
    },
    "anti-fatigue-nafei-lafei-group-cn-2025": {
        "mapping_id": "anti-fatigue-nafei-lafei-group-cn-2025",
        "dataset_id": "risk-substance-reference",
        "risk_category": "anti_fatigue",
        "risk_label": "抗疲劳宣传",
        "target_type": "substance_group",
        "substance_id": None,
        "target_group_label": "那非类、拉非类物质",
        "evidence_grade": "A",
        "basis_type": "current_official_guidance",
        "temporal_status": "current",
        "product_scope": "酒类、压片糖果、咖啡等食品（来源列举的典型食品场景）",
        "source_name": "市场监管总局等两部委将那非类、拉非类物质纳入食品中可能添加的非食用物质名录",
        "source_reference": NAFEI_LAFEI_SOURCE,
        "source_date": "2025-06-28",
        "source_basis_text": "市场监管总局官方解读指出，部分不法商家将那非类、拉非类物质掺入酒类、压片糖果、咖啡等食品，并以抗疲劳等功效进行宣传。",
        "note": "本Mapping表示“抗疲劳宣传”是当前官方来源明确关联的那非类、拉非类监管关注方向。不得解释为出现抗疲劳宣传的商品实际含有相关物质。",
    },
}


def load_verified_risk_dataset() -> dict:
    return validate_risk_substance_config(read_json(RISK_REFERENCE_CONFIG))


class VerifiedRiskSubstanceReferenceDataTest(unittest.TestCase):
    def test_verified_dataset_contract_and_identity_are_exact(self):
        payload = load_verified_risk_dataset()
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["dataset_id"], "risk-substance-reference")
        self.assertEqual(payload["dataset_version"], "2026.09-c3")
        self.assertEqual(payload["dataset_status"], "verified_reference")
        self.assertEqual(len(payload["mappings"]), 8)
        self.assertEqual(
            {mapping["mapping_id"] for mapping in payload["mappings"]},
            EXPECTED_MAPPING_IDS,
        )
        self.assertEqual(
            {mapping["risk_category"] for mapping in payload["mappings"]},
            EXPECTED_CATEGORIES,
        )

    def test_c2_group_mappings_are_preserved_without_changes(self):
        mappings = load_verified_risk_dataset()["mappings"]
        group_mappings = {
            mapping["mapping_id"]: mapping
            for mapping in mappings
            if mapping["target_type"] == "substance_group"
        }
        self.assertEqual(set(group_mappings), EXPECTED_GROUP_MAPPING_IDS)
        self.assertEqual(group_mappings, EXPECTED_GROUP_MAPPINGS)

    def test_exactly_five_verified_substance_mappings_reuse_inspection_entities(self):
        mappings = load_verified_risk_dataset()["mappings"]
        substance_mappings = [
            mapping for mapping in mappings if mapping["target_type"] == "substance"
        ]
        self.assertEqual(len(substance_mappings), 5)
        self.assertEqual(
            {mapping["mapping_id"] for mapping in substance_mappings},
            EXPECTED_SUBSTANCE_MAPPING_IDS,
        )
        self.assertTrue(
            all(mapping["target_group_label"] is None for mapping in substance_mappings)
        )
        self.assertEqual(
            {mapping["substance_id"] for mapping in substance_mappings},
            set(EXPECTED_SUBSTANCE_IDENTITIES),
        )
        self.assertTrue(
            all(mapping["evidence_grade"] == "A" for mapping in substance_mappings)
        )
        self.assertTrue(
            all(
                mapping["basis_type"] == "current_official_guidance"
                for mapping in substance_mappings
            )
        )
        self.assertTrue(
            all(mapping["temporal_status"] == "current" for mapping in substance_mappings)
        )
        self.assertTrue(all("不得解释" in mapping["note"] for mapping in substance_mappings))

        by_category = {
            category: {
                mapping["substance_id"]
                for mapping in substance_mappings
                if mapping["risk_category"] == category
            }
            for category in EXPECTED_CATEGORIES
        }
        self.assertEqual(by_category, EXPECTED_SUBSTANCE_TARGETS)

        inspection = validate_inspection_config(read_json(INSPECTION_REFERENCE_CONFIG))
        canonical_by_id = {
            substance["substance_id"]: substance["canonical_name"]
            for substance in inspection["substances"]
        }
        self.assertEqual(
            {
                substance_id: canonical_by_id[substance_id]
                for substance_id in EXPECTED_SUBSTANCE_IDENTITIES
            },
            EXPECTED_SUBSTANCE_IDENTITIES,
        )

    def test_mapping_sources_dates_and_nonconclusion_boundaries_are_exact(self):
        mappings = load_verified_risk_dataset()["mappings"]
        for mapping in mappings:
            expected_reference = (
                SIBUTRAMINE_SOURCE
                if mapping["risk_category"] == "weight_loss"
                else NAFEI_LAFEI_SOURCE
            )
            expected_date = (
                "2025-10-18"
                if mapping["risk_category"] == "weight_loss"
                else "2025-06-28"
            )
            self.assertEqual(mapping["source_reference"], expected_reference)
            self.assertEqual(mapping["source_date"], expected_date)
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

            expected = {"dataset": 1, "mappings": 8}
            self.assertEqual(
                store.import_risk_substance_config(RISK_REFERENCE_CONFIG), expected
            )
            first = store.table_counts()
            self.assertEqual(first["risk_mapping_datasets"], 1)
            self.assertEqual(first["risk_substance_mappings"], 8)

            connection = sqlite3.connect(store.database_path)
            try:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
            finally:
                connection.close()
            self.assertNotIn("risk_substance_groups", tables)
            self.assertNotIn("risk_substance_group_memberships", tables)
            self.assertNotIn("chemical_groups", tables)

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
