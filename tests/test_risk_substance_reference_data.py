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
    "weight-loss-bisacodyl-group-cn-2025",
    "weight-loss-phenbut-phenolphthalein-group-cn-2025",
    "male-function-nafei-lafei-group-cn-2025",
    "male-function-yohimbine-group-cn-2025",
    "anti-fatigue-nafei-lafei-group-cn-2025",
}
EXPECTED_SUBSTANCE_MAPPING_IDS = {
    "weight-loss-sibutramine-cn-2025",
    "weight-loss-bisacodyl-cn-2025",
    "weight-loss-phenolphthalein-cn-2025",
    "male-function-sildenafil-cn-2025",
    "male-function-tadalafil-cn-2025",
    "anti-fatigue-sildenafil-cn-2025",
    "anti-fatigue-tadalafil-cn-2025",
}
EXPECTED_CURRENT_MAPPING_IDS = EXPECTED_GROUP_MAPPING_IDS | EXPECTED_SUBSTANCE_MAPPING_IDS
SLEEP_HISTORICAL_GROUP_MAPPING_ID = "sleep-aid-historical-screening-group-cn-2018"
SLEEP_HISTORICAL_SUBSTANCE_IDENTITIES = {
    "substance-cas-43200-80-2": "佐匹克隆",
    "substance-cas-2934-97-6": "罗通定",
    "substance-cas-28911-01-5": "三唑仑",
    "substance-cas-115-53-7": "青藤碱",
    "substance-cas-846-49-1": "劳拉西泮",
    "substance-cas-1622-61-3": "氯硝西泮",
    "substance-cas-28981-97-7": "阿普唑仑",
    "substance-cas-151319-34-5": "扎来普隆",
    "substance-cas-29975-16-4": "艾司唑仑",
    "substance-cas-604-75-1": "奥沙西泮",
    "substance-cas-439-14-5": "地西泮",
    "substance-cas-146-22-5": "硝西泮",
    "substance-cas-93413-69-5": "文拉法辛",
    "substance-cas-132-22-9": "氯苯那敏",
    "substance-cas-80-77-3": "氯美扎酮",
    "substance-cas-76-73-3": "司可巴比妥",
    "substance-cas-73-31-4": "褪黑素",
    "substance-cas-50-06-6": "苯巴比妥",
    "substance-cas-57-43-2": "异戊巴比妥",
    "substance-cas-57-44-3": "巴比妥",
}
SLEEP_HISTORICAL_SUBSTANCE_MAPPING_IDS = {
    f"sleep-aid-cas-{substance_id.removeprefix('substance-cas-')}-historical-cn-2018"
    for substance_id in SLEEP_HISTORICAL_SUBSTANCE_IDENTITIES
}
CARDIOMETABOLIC_HISTORICAL_SUBSTANCE_IDENTITIES = {
    "blood_pressure": {
        "substance-cas-29122-68-7": "阿替洛尔",
        "substance-cas-58-93-5": "氢氯噻嗪",
        "substance-cas-62571-86-2": "卡托普利",
        "substance-cas-19216-56-9": "哌唑嗪",
        "substance-cas-50-55-5": "利血平",
        "substance-cas-21829-25-4": "硝苯地平",
        "substance-cas-88150-42-9": "氨氯地平",
        "substance-cas-39562-70-4": "尼群地平",
        "substance-cas-66085-59-4": "尼莫地平",
        "substance-cas-63675-72-9": "尼索地平",
        "substance-cas-72509-76-3": "非洛地平",
    },
    "blood_lipid": {
        "substance-cas-75330-75-5": "洛伐他汀",
        "substance-cas-79902-63-9": "辛伐他汀",
        "substance-cas-73573-88-3": "美伐他汀",
        "substance-cas-75225-50-2": "洛伐他汀羟酸钠盐",
    },
    "blood_glucose": {
        "substance-cas-64-77-7": "甲苯磺丁脲",
        "substance-cas-10238-21-8": "格列苯脲",
        "substance-cas-21187-98-4": "格列齐特",
        "substance-cas-29094-61-9": "格列吡嗪",
        "substance-cas-33342-05-1": "格列喹酮",
        "substance-cas-93479-97-1": "格列美脲",
        "substance-cas-122320-73-4": "罗格列酮",
        "substance-cas-135062-02-1": "瑞格列奈",
        "substance-cas-26944-48-9": "格列波脲",
    },
}
CARDIOMETABOLIC_HISTORICAL_GROUP_MAPPING_IDS = {
    "blood_pressure": "blood-pressure-historical-screening-group-cn-2018",
    "blood_lipid": "blood-lipid-historical-screening-group-cn-2018",
    "blood_glucose": "blood-glucose-historical-screening-group-cn-2018",
}
CARDIOMETABOLIC_HISTORICAL_SUBSTANCE_MAPPING_IDS = {
    category: {
        f"{category.replace('_', '-')}-cas-{substance_id.removeprefix('substance-cas-')}-historical-cn-2018"
        for substance_id in identities
    }
    for category, identities in CARDIOMETABOLIC_HISTORICAL_SUBSTANCE_IDENTITIES.items()
}
WEIGHT_HISTORICAL_GROUP_MAPPING_ID = "weight-loss-historical-screening-group-cn-2018"
WEIGHT_HISTORICAL_SUBSTANCE_IDENTITIES = {
    "substance-cas-106650-56-0": "西布曲明",
    "substance-cas-168835-59-4": "N-单去甲基西布曲明",
    "substance-cas-84467-54-9": "N,N-双去甲基西布曲明",
    "substance-cas-458-24-2": "芬氟拉明",
    "substance-cas-299-42-3": "麻黄碱",
    "substance-cas-77-09-8": "酚酞",
    "substance-cas-54-31-9": "呋塞米",
}
WEIGHT_HISTORICAL_SUBSTANCE_MAPPING_IDS = {
    f"weight-loss-cas-{substance_id.removeprefix('substance-cas-')}-historical-cn-2018"
    for substance_id in WEIGHT_HISTORICAL_SUBSTANCE_IDENTITIES
}
ANTI_FATIGUE_HISTORICAL_GROUP_MAPPING_ID = "anti-fatigue-historical-screening-group-cn-2018"
ANTI_FATIGUE_HISTORICAL_SUBSTANCE_IDENTITIES = {
    "substance-cas-949091-38-7": "那红地那非",
    "substance-cas-831217-01-7": "红地那非",
    "substance-cas-224785-90-4": "伐地那非",
    "substance-cas-139755-85-4": "羟基豪莫西地那非",
    "substance-cas-139755-83-2": "西地那非",
    "substance-cas-642928-07-2": "豪莫西地那非",
    "substance-cas-385769-84-6": "氨基他达拉非",
    "substance-cas-171596-29-5": "他达拉非",
    "substance-cas-856190-47-1": "硫代艾地那非",
    "substance-cas-224788-34-5": "伪伐地那非",
    "substance-cas-371959-09-0": "那莫西地那非",
    "substance-cas-171596-36-4": "去甲基他达拉非",
    "substance-cas-479073-79-5": "硫代西地那非",
}
ANTI_FATIGUE_HISTORICAL_SUBSTANCE_MAPPING_IDS = {
    f"anti-fatigue-cas-{substance_id.removeprefix('substance-cas-')}-historical-cn-2018"
    for substance_id in ANTI_FATIGUE_HISTORICAL_SUBSTANCE_IDENTITIES
}
EXPECTED_HISTORICAL_MAPPING_IDS = (
    {SLEEP_HISTORICAL_GROUP_MAPPING_ID}
    | SLEEP_HISTORICAL_SUBSTANCE_MAPPING_IDS
    | set(CARDIOMETABOLIC_HISTORICAL_GROUP_MAPPING_IDS.values())
    | set().union(*CARDIOMETABOLIC_HISTORICAL_SUBSTANCE_MAPPING_IDS.values())
    | {WEIGHT_HISTORICAL_GROUP_MAPPING_ID}
    | WEIGHT_HISTORICAL_SUBSTANCE_MAPPING_IDS
    | {ANTI_FATIGUE_HISTORICAL_GROUP_MAPPING_ID}
    | ANTI_FATIGUE_HISTORICAL_SUBSTANCE_MAPPING_IDS
)
EXPECTED_MAPPING_IDS = EXPECTED_CURRENT_MAPPING_IDS | EXPECTED_HISTORICAL_MAPPING_IDS
EXPECTED_CURRENT_CATEGORIES = {"weight_loss", "male_function", "anti_fatigue"}
EXPECTED_HISTORICAL_CATEGORIES = {
    "sleep_aid", "blood_pressure", "blood_lipid", "blood_glucose",
    "weight_loss", "anti_fatigue",
}
EXPECTED_CATEGORIES = EXPECTED_CURRENT_CATEGORIES | EXPECTED_HISTORICAL_CATEGORIES
SLEEP_HISTORICAL_SOURCE = (
    "https://www.samr.gov.cn/cms_files/filemanager/1647978232/attach/20233/"
    "P020181214555096215303.pdf"
)
SIBUTRAMINE_SOURCE = (
    "https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/zfjcs/art/2025/"
    "art_935c1a68c87445729ad2e6c1d88607c6.html"
)
NAFEI_LAFEI_SOURCE = (
    "https://www.samr.gov.cn/xw/zj/art/2025/"
    "art_b066d669285e4494bbee7c988b6dfb2e.html"
)
BISACODYL_SOURCE = (
    "https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/zfjcs/art/2025/"
    "art_e357c00946a24d19905b2098cdf4f955.html"
)
PHENOLPHTHALEIN_SOURCE = (
    "https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/zfjcs/art/2025/"
    "art_d39285cfe10f402aa9479a33d552ec35.html"
)
YOHIMBINE_SOURCE = (
    "https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/zfjcs/art/2025/"
    "art_7d3c1941d493408eb57a0038fd14358b.html"
)
CURRENT_SOURCE_EXPECTATIONS = {
    "weight-loss-sibutramine-group-cn-2025": (SIBUTRAMINE_SOURCE, "2025-10-18"),
    "weight-loss-sibutramine-cn-2025": (SIBUTRAMINE_SOURCE, "2025-10-18"),
    "weight-loss-bisacodyl-group-cn-2025": (BISACODYL_SOURCE, "2025-02-14"),
    "weight-loss-bisacodyl-cn-2025": (BISACODYL_SOURCE, "2025-02-14"),
    "weight-loss-phenbut-phenolphthalein-group-cn-2025": (
        PHENOLPHTHALEIN_SOURCE,
        "2025-03-05",
    ),
    "weight-loss-phenolphthalein-cn-2025": (
        PHENOLPHTHALEIN_SOURCE,
        "2025-03-05",
    ),
    "male-function-nafei-lafei-group-cn-2025": (NAFEI_LAFEI_SOURCE, "2025-06-28"),
    "male-function-sildenafil-cn-2025": (NAFEI_LAFEI_SOURCE, "2025-06-28"),
    "male-function-tadalafil-cn-2025": (NAFEI_LAFEI_SOURCE, "2025-06-28"),
    "male-function-yohimbine-group-cn-2025": (YOHIMBINE_SOURCE, "2025-10-18"),
    "anti-fatigue-nafei-lafei-group-cn-2025": (NAFEI_LAFEI_SOURCE, "2025-06-28"),
    "anti-fatigue-sildenafil-cn-2025": (NAFEI_LAFEI_SOURCE, "2025-06-28"),
    "anti-fatigue-tadalafil-cn-2025": (NAFEI_LAFEI_SOURCE, "2025-06-28"),
}
INSPECTION_COUNTS = {
    "inspection_methods": 9,
    "inspection_substances": 201,
    "inspection_method_substances": 231,
    "inspection_method_applicabilities": 46,
    "substance_regulatory_contexts": 1,
}
EXPECTED_SUBSTANCE_IDENTITIES = {
    "substance-cas-106650-56-0": "西布曲明",
    "substance-cas-603-50-9": "比沙可啶",
    "substance-cas-77-09-8": "酚酞",
    "substance-cas-139755-83-2": "西地那非",
    "substance-cas-171596-29-5": "他达拉非",
}
EXPECTED_SUBSTANCE_TARGETS = {
    "weight_loss": {
        "substance-cas-106650-56-0",
        "substance-cas-603-50-9",
        "substance-cas-77-09-8",
    },
    "male_function": {
        "substance-cas-139755-83-2",
        "substance-cas-171596-29-5",
    },
    "anti_fatigue": {
        "substance-cas-139755-83-2",
        "substance-cas-171596-29-5",
    },
}


def load_verified_risk_dataset() -> dict:
    return validate_risk_substance_config(read_json(RISK_REFERENCE_CONFIG))


class VerifiedRiskSubstanceReferenceDataTest(unittest.TestCase):
    def test_verified_dataset_contract_and_identity_are_exact(self):
        payload = load_verified_risk_dataset()
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["dataset_id"], "risk-substance-reference")
        self.assertEqual(payload["dataset_version"], "2026.09-c7")
        self.assertEqual(payload["dataset_status"], "verified_reference")
        self.assertEqual(len(payload["mappings"]), 83)
        self.assertEqual(
            {mapping["mapping_id"] for mapping in payload["mappings"]},
            EXPECTED_MAPPING_IDS,
        )
        self.assertEqual(
            {mapping["risk_category"] for mapping in payload["mappings"]},
            EXPECTED_CATEGORIES,
        )

    def test_current_group_mappings_are_explicit_governed_inventory(self):
        mappings = load_verified_risk_dataset()["mappings"]
        group_mappings = [
            mapping
            for mapping in mappings
            if mapping["target_type"] == "substance_group"
            and mapping["temporal_status"] == "current"
        ]
        self.assertEqual(
            {mapping["mapping_id"] for mapping in group_mappings},
            EXPECTED_GROUP_MAPPING_IDS,
        )
        self.assertTrue(
            all(mapping["evidence_grade"] == "A" for mapping in group_mappings)
        )
        self.assertTrue(
            all(
                mapping["basis_type"] == "current_official_guidance"
                for mapping in group_mappings
            )
        )
        self.assertTrue(
            all(mapping["substance_id"] is None for mapping in group_mappings)
        )

    def test_current_verified_substance_mappings_reuse_inspection_entities(self):
        mappings = load_verified_risk_dataset()["mappings"]
        substance_mappings = [
            mapping
            for mapping in mappings
            if mapping["target_type"] == "substance"
            and mapping["temporal_status"] == "current"
        ]
        self.assertEqual(len(substance_mappings), 7)
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
        self.assertTrue(
            all(
                "不得解释" in mapping["note"]
                or "不表示具体商品实际含有" in mapping["note"]
                for mapping in substance_mappings
            )
        )

        by_category = {
            category: {
                mapping["substance_id"]
                for mapping in substance_mappings
                if mapping["risk_category"] == category
            }
            for category in EXPECTED_CURRENT_CATEGORIES
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

    def test_sleep_historical_mappings_are_source_backed_and_reuse_inspection_entities(self):
        mappings = load_verified_risk_dataset()["mappings"]
        historical = [
            mapping
            for mapping in mappings
            if mapping["risk_category"] == "sleep_aid"
        ]

        self.assertEqual(len(historical), 21)
        self.assertEqual(
            {mapping["mapping_id"] for mapping in historical},
            {SLEEP_HISTORICAL_GROUP_MAPPING_ID}
            | SLEEP_HISTORICAL_SUBSTANCE_MAPPING_IDS,
        )
        self.assertTrue(
            all(mapping["temporal_status"] == "historical" for mapping in historical)
        )
        self.assertTrue(
            all(mapping["basis_type"] == "historical_sampling_plan" for mapping in historical)
        )
        self.assertTrue(all(mapping["evidence_grade"] == "B" for mapping in historical))
        self.assertTrue(
            all(mapping["source_reference"] == SLEEP_HISTORICAL_SOURCE for mapping in historical)
        )
        self.assertTrue(all(mapping["source_date"] == "2018-10-09" for mapping in historical))
        self.assertTrue(
            all("当前统一法定抽检项目" in mapping["note"] for mapping in historical)
        )

        substance_ids = {
            mapping["substance_id"]
            for mapping in historical
            if mapping["target_type"] == "substance"
        }
        self.assertEqual(substance_ids, set(SLEEP_HISTORICAL_SUBSTANCE_IDENTITIES))

        inspection = validate_inspection_config(read_json(INSPECTION_REFERENCE_CONFIG))
        canonical_by_id = {
            substance["substance_id"]: substance["canonical_name"]
            for substance in inspection["substances"]
        }
        self.assertEqual(
            {
                substance_id: canonical_by_id[substance_id]
                for substance_id in SLEEP_HISTORICAL_SUBSTANCE_IDENTITIES
            },
            SLEEP_HISTORICAL_SUBSTANCE_IDENTITIES,
        )

    def test_cardiometabolic_historical_mappings_use_curated_inspection_subset(self):
        mappings = load_verified_risk_dataset()["mappings"]
        inspection = validate_inspection_config(read_json(INSPECTION_REFERENCE_CONFIG))
        canonical_by_id = {
            substance["substance_id"]: substance["canonical_name"]
            for substance in inspection["substances"]
        }

        for category, expected_identities in CARDIOMETABOLIC_HISTORICAL_SUBSTANCE_IDENTITIES.items():
            with self.subTest(category=category):
                historical = [
                    mapping for mapping in mappings
                    if mapping["risk_category"] == category
                ]
                self.assertEqual(
                    {mapping["mapping_id"] for mapping in historical},
                    {CARDIOMETABOLIC_HISTORICAL_GROUP_MAPPING_IDS[category]}
                    | CARDIOMETABOLIC_HISTORICAL_SUBSTANCE_MAPPING_IDS[category],
                )
                self.assertTrue(
                    all(mapping["temporal_status"] == "historical" for mapping in historical)
                )
                substance_ids = {
                    mapping["substance_id"]
                    for mapping in historical
                    if mapping["target_type"] == "substance"
                }
                self.assertEqual(substance_ids, set(expected_identities))
                self.assertEqual(
                    {
                        substance_id: canonical_by_id[substance_id]
                        for substance_id in expected_identities
                    },
                    expected_identities,
                )

        lipid_ids = set(CARDIOMETABOLIC_HISTORICAL_SUBSTANCE_IDENTITIES["blood_lipid"])
        niacin = next(
            substance["substance_id"]
            for substance in inspection["substances"]
            if substance["canonical_name"] == "烟酸"
        )
        self.assertNotIn(niacin, lipid_ids)

    def test_weight_and_anti_fatigue_historical_mappings_are_exact_source_sets(self):
        mappings = load_verified_risk_dataset()["mappings"]
        inspection = validate_inspection_config(read_json(INSPECTION_REFERENCE_CONFIG))
        canonical_by_id = {
            substance["substance_id"]: substance["canonical_name"]
            for substance in inspection["substances"]
        }
        cases = (
            (
                "weight_loss",
                WEIGHT_HISTORICAL_GROUP_MAPPING_ID,
                WEIGHT_HISTORICAL_SUBSTANCE_MAPPING_IDS,
                WEIGHT_HISTORICAL_SUBSTANCE_IDENTITIES,
            ),
            (
                "anti_fatigue",
                ANTI_FATIGUE_HISTORICAL_GROUP_MAPPING_ID,
                ANTI_FATIGUE_HISTORICAL_SUBSTANCE_MAPPING_IDS,
                ANTI_FATIGUE_HISTORICAL_SUBSTANCE_IDENTITIES,
            ),
        )
        for category, group_id, mapping_ids, identities in cases:
            with self.subTest(category=category):
                historical = [
                    mapping
                    for mapping in mappings
                    if mapping["risk_category"] == category
                    and mapping["temporal_status"] == "historical"
                ]
                self.assertEqual(
                    {mapping["mapping_id"] for mapping in historical},
                    {group_id} | mapping_ids,
                )
                substance_ids = {
                    mapping["substance_id"]
                    for mapping in historical
                    if mapping["target_type"] == "substance"
                }
                self.assertEqual(substance_ids, set(identities))
                self.assertEqual(
                    {
                        substance_id: canonical_by_id[substance_id]
                        for substance_id in identities
                    },
                    identities,
                )

    def test_mapping_sources_dates_and_nonconclusion_boundaries_are_exact(self):
        mappings = load_verified_risk_dataset()["mappings"]
        for mapping in mappings:
            if mapping["temporal_status"] == "historical":
                self.assertIn(mapping["risk_category"], EXPECTED_HISTORICAL_CATEGORIES)
                self.assertEqual(mapping["source_reference"], SLEEP_HISTORICAL_SOURCE)
                self.assertEqual(mapping["source_date"], "2018-10-09")
                self.assertEqual(mapping["basis_type"], "historical_sampling_plan")
                self.assertIn("不表示具体商品实际含有", mapping["note"])
            else:
                expected_reference, expected_date = CURRENT_SOURCE_EXPECTATIONS[
                    mapping["mapping_id"]
                ]
                self.assertEqual(mapping["source_reference"], expected_reference)
                self.assertEqual(mapping["source_date"], expected_date)
                self.assertEqual(mapping["basis_type"], "current_official_guidance")
                self.assertEqual(mapping["evidence_grade"], "A")
                self.assertTrue(
                    "不得解释" in mapping["note"]
                    or "不表示具体商品实际含有" in mapping["note"]
                )
            self.assertTrue(mapping["source_basis_text"])

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

            expected = {"dataset": 1, "mappings": 83}
            self.assertEqual(
                store.import_risk_substance_config(RISK_REFERENCE_CONFIG), expected
            )
            first = store.table_counts()
            self.assertEqual(first["risk_mapping_datasets"], 1)
            self.assertEqual(first["risk_substance_mappings"], 83)

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
