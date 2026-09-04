import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.data_store import DataStore
from src.inspection_reference import validate_inspection_config
from src.runtime import read_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_CONFIG = PROJECT_ROOT / "config" / "inspection_reference.json"
DATASET_SOURCE_REFERENCE = "https://www.samr.gov.cn/spcjs/bcjyff/"
BJS_202209_SOURCE_REFERENCE = (
    "https://www.samr.gov.cn/spcjs/bz/cs/art/2022/"
    "art_46900b84fdad41d2ab711489f22c052b.html"
)
BJS_201701_SOURCE_REFERENCE = (
    "https://www.samr.gov.cn/spcjs/bz/cs/art/2017/"
    "art_24cbba1f9bb44ba0972de88180925b12.html"
)

EXPECTED_BJS_202209_SUBSTANCES = [
    ("阿米洛利", "2609-46-3"),
    ("茶碱", "58-55-9"),
    ("纳曲酮", "16590-41-3"),
    ("氨苯蝶啶", "396-01-0"),
    ("脱乙酰比沙可啶", "603-41-8"),
    ("氯苯丁胺", "461-78-9"),
    ("苯甲吗酮", "5588-29-4"),
    ("西酞普兰", "59729-33-8"),
    ("苯佐卡因", "94-09-7"),
    ("托吡酯", "97240-79-4"),
    ("帕罗西汀", "61869-08-7"),
    ("舍曲林", "79617-96-2"),
    ("奈法唑酮", "83366-66-9"),
    ("螺内酯", "52-01-7"),
    ("双醋酚丁", "115-33-3"),
    ("新利司他", "282526-98-1"),
    ("唑尼沙胺", "68291-97-4"),
    ("依他尼酸", "58-54-8"),
    ("大黄素", "518-82-1"),
]

EXPECTED_BJS_202209_CATEGORIES = {
    "压片糖果",
    "蜜饯",
    "果冻",
    "除含乳饮料外的饮料",
    "果蔬粉",
    "饼干",
    "代用茶",
    "配制酒",
    "果酒",
}

EXPECTED_BJS_201701_SUBSTANCES = [
    ("苯丙醇胺", "37577-28-9", "Phenylpropanolamine"),
    ("去甲伪麻黄碱", "37577-07-4", "Norpseudoephedrine"),
    ("麻黄碱", "299-42-3", "Ephedrine"),
    ("伪麻黄碱", "321-97-1", "Pseudoephedrine"),
    ("甲基麻黄碱", "552-79-4", "Methylephedrine"),
    ("安非他明", "300-62-9", "Amphetamine"),
    ("氯噻嗪", "58-94-6", "Chlorothiazide"),
    ("氢氯噻嗪", "58-93-5", "Hydrochlorothiazide"),
    ("甲基安非他明", "4846-07-5", "Methylamphetamine"),
    ("咖啡因", "58-08-2", "Caffeine"),
    ("分特拉明", "122-09-8", "Phentermine"),
    ("氯卡色林", "616202-92-7", "Lorcaserin"),
    ("安非他酮", "34841-39-9", "Bupropion"),
    ("芬氟拉明", "458-24-2", "Fenfluramine"),
    ("普伐他汀", "81093-37-0", "Pravastatin"),
    ("呋塞米", "54-31-9", "Furosemide"),
    ("N,N-双去甲基西布曲明", "84467-54-9", "N-Didesmethyl Sibutramine"),
    ("氟西汀", "54910-89-3", "Fluoxetine"),
    ("酚酞", "77-09-8", "Phenolphthalein"),
    ("N-单去甲基西布曲明", "168835-59-4", "N-monodesmethyl sibutramine"),
    ("吲达帕胺", "26807-65-8", "Indapamide"),
    ("西布曲明", "106650-56-0", "Sibutramine"),
    ("苄基西布曲明", "1446140-91-5", "11-Desisobutyl-11-benzyl Sibutramine"),
    ("豪莫西布曲明", "935888-80-5", "Homosibutramine"),
    ("比沙可啶", "603-50-9", "Bisacodyl"),
    ("氯代西布曲明", "766462-77-5", "Chloro Sibutramine"),
    ("苯扎贝特", "41859-67-0", "Bezafibrate"),
    ("布美他尼", "28395-03-1", "Bumetanide"),
    ("洛伐他汀", "75330-75-5", "Lovastatin"),
    ("辛伐他汀", "79902-63-9", "Simvastatin"),
    ("利莫那班", "168273-06-1", "Rimonabant"),
    ("非诺贝特", "49562-28-9", "Fenofibrate"),
    ("奥利司他", "96829-58-2", "Orlistat"),
]


class VerifiedInspectionReferenceDataTest(unittest.TestCase):
    def test_bjs_202209_reference_contract_matches_verified_source_facts(self):
        payload = validate_inspection_config(read_json(REFERENCE_CONFIG))
        self.assertEqual(payload["dataset_id"], "inspection-reference")
        self.assertEqual(payload["dataset_version"], "2026.09-b2")
        self.assertEqual(payload["dataset_status"], "verified_reference")
        self.assertEqual(payload["source_reference"], DATASET_SOURCE_REFERENCE)

        self.assertEqual(len(payload["methods"]), 2)
        method = next(
            item for item in payload["methods"] if item["method_id"] == "bjs-202209"
        )
        self.assertEqual(method["method_id"], "bjs-202209")
        self.assertEqual(method["method_no"], "BJS 202209")
        self.assertEqual(method["method_status"], "current")
        self.assertEqual(method["source_reference"], BJS_202209_SOURCE_REFERENCE)
        self.assertTrue(
            payload["source_reference"].startswith("https://www.samr.gov.cn/")
        )
        self.assertTrue(
            method["source_reference"].startswith("https://www.samr.gov.cn/")
        )

        substances_by_id = {
            item["substance_id"]: item for item in payload["substances"]
        }
        relations = [
            item
            for item in payload["method_substances"]
            if item["method_id"] == "bjs-202209"
        ]
        substances = [substances_by_id[item["substance_id"]] for item in relations]
        self.assertEqual(len(relations), 19)
        self.assertEqual(
            [(item["canonical_name"], item["cas_no"]) for item in substances],
            EXPECTED_BJS_202209_SUBSTANCES,
        )
        self.assertTrue(all(item["english_name"] == "" for item in substances))
        self.assertTrue(all(item["substance_group"] == "" for item in substances))

        self.assertEqual([item["ordinal"] for item in relations], list(range(1, 20)))
        self.assertEqual(
            {item["source_cas_no"] for item in relations},
            {cas_no for _, cas_no in EXPECTED_BJS_202209_SUBSTANCES},
        )
        for relation in relations:
            substance = substances_by_id[relation["substance_id"]]
            self.assertEqual(relation["source_label"], substance["canonical_name"])
            self.assertEqual(relation["source_cas_no"], substance["cas_no"])
            self.assertEqual(relation["determination_role"], "quantitative")
            self.assertEqual(relation["normalization_note"], "")

        applicabilities = [
            item
            for item in payload["method_applicabilities"]
            if item["method_id"] == "bjs-202209"
        ]
        self.assertEqual(len(applicabilities), 9)
        self.assertTrue(all(item["substance_id"] is None for item in applicabilities))
        self.assertTrue(all(item["scope_type"] == "include" for item in applicabilities))
        self.assertEqual(
            {item["product_category"] for item in applicabilities},
            EXPECTED_BJS_202209_CATEGORIES,
        )
        self.assertTrue(
            all(
                item["source_scope_text"] == item["product_category"]
                for item in applicabilities
            )
        )
        self.assertEqual(payload["substance_regulatory_contexts"], [])

    def test_bjs_201701_reference_contract_matches_verified_source_facts(self):
        payload = validate_inspection_config(read_json(REFERENCE_CONFIG))
        methods = {item["method_id"]: item for item in payload["methods"]}
        self.assertEqual(set(methods), {"bjs-202209", "bjs-201701"})
        method = methods["bjs-201701"]
        self.assertEqual(method["method_no"], "BJS 201701")
        self.assertEqual(method["method_name"], "食品中西布曲明等化合物的测定")
        self.assertEqual(method["method_status"], "current")
        self.assertEqual(method["published_date"], "2017-02-28")
        self.assertEqual(method["source_date"], "2017-02-28")
        self.assertEqual(method["source_reference"], BJS_201701_SOURCE_REFERENCE)
        self.assertEqual(payload["source_reference"], DATASET_SOURCE_REFERENCE)
        self.assertTrue(
            method["source_reference"].startswith("https://www.samr.gov.cn/")
        )

        substances_by_id = {
            item["substance_id"]: item for item in payload["substances"]
        }
        relations = [
            item
            for item in payload["method_substances"]
            if item["method_id"] == "bjs-201701"
        ]
        self.assertEqual(len(relations), 33)
        self.assertEqual([item["ordinal"] for item in relations], list(range(1, 34)))
        self.assertEqual(
            [
                (
                    item["source_label"],
                    item["source_cas_no"],
                    substances_by_id[item["substance_id"]]["english_name"],
                )
                for item in relations
            ],
            EXPECTED_BJS_201701_SUBSTANCES,
        )
        for relation in relations:
            substance = substances_by_id[relation["substance_id"]]
            self.assertEqual(relation["source_label"], substance["canonical_name"])
            self.assertEqual(relation["source_cas_no"], substance["cas_no"])
            self.assertEqual(relation["determination_role"], "qualitative")
            self.assertEqual(relation["normalization_note"], "")
            self.assertEqual(substance["substance_group"], "")
            self.assertEqual(substance["note"], "BJS 201701附录A")

        applicabilities = [
            item
            for item in payload["method_applicabilities"]
            if item["method_id"] == "bjs-201701"
        ]
        method_level = [item for item in applicabilities if item["substance_id"] is None]
        substance_scoped = [
            item for item in applicabilities if item["substance_id"] is not None
        ]
        self.assertEqual(len(method_level), 4)
        self.assertEqual(len(substance_scoped), 3)
        self.assertEqual(
            {item["applicability_id"] for item in method_level},
            {
                "bjs-201701-scope-01",
                "bjs-201701-scope-02",
                "bjs-201701-scope-03",
                "bjs-201701-scope-04",
            },
        )
        scoped_by_substance = {
            item["substance_id"]: item for item in substance_scoped
        }
        self.assertEqual(
            scoped_by_substance["substance-cas-58-08-2"]["scope_type"],
            "exclude",
        )
        self.assertEqual(
            scoped_by_substance["substance-cas-96829-58-2"]["scope_type"],
            "conditional",
        )
        self.assertEqual(
            scoped_by_substance["substance-cas-75330-75-5"]["scope_type"],
            "exclude",
        )
        relation_pairs = {
            (item["method_id"], item["substance_id"])
            for item in payload["method_substances"]
        }
        self.assertTrue(
            all(
                (item["method_id"], item["substance_id"]) in relation_pairs
                for item in substance_scoped
            )
        )

        self.assertEqual(len(payload["substances"]), 52)
        self.assertEqual(len(payload["method_substances"]), 52)
        self.assertEqual(len(payload["method_applicabilities"]), 16)
        self.assertEqual(payload["substance_regulatory_contexts"], [])

    def test_verified_dataset_import_is_idempotent_with_exact_scoped_counts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = DataStore(root / "data" / "app.db", root / "output")
            store.initialize()
            expected = {
                "dataset": 1,
                "methods": 2,
                "substances": 52,
                "method_substances": 52,
                "applicabilities": 16,
                "regulatory_contexts": 0,
            }
            self.assertEqual(store.import_inspection_config(REFERENCE_CONFIG), expected)
            first = store.table_counts()
            self.assertEqual(store.import_inspection_config(REFERENCE_CONFIG), expected)
            self.assertEqual(first, store.table_counts())

            with sqlite3.connect(store.database_path) as connection:
                scoped_counts = {
                    "dataset": connection.execute(
                        "SELECT COUNT(*) FROM inspection_datasets WHERE dataset_id = ?",
                        ("inspection-reference",),
                    ).fetchone()[0],
                    "methods": connection.execute(
                        "SELECT COUNT(*) FROM inspection_methods WHERE dataset_id = ?",
                        ("inspection-reference",),
                    ).fetchone()[0],
                    "substances": connection.execute(
                        "SELECT COUNT(*) FROM inspection_substances WHERE dataset_id = ?",
                        ("inspection-reference",),
                    ).fetchone()[0],
                    "method_substances": connection.execute(
                        """
                        SELECT COUNT(*)
                        FROM inspection_method_substances ms
                        JOIN inspection_methods m ON m.method_id = ms.method_id
                        WHERE m.dataset_id = ?
                        """,
                        ("inspection-reference",),
                    ).fetchone()[0],
                    "applicabilities": connection.execute(
                        """
                        SELECT COUNT(*)
                        FROM inspection_method_applicabilities a
                        JOIN inspection_methods m ON m.method_id = a.method_id
                        WHERE m.dataset_id = ?
                        """,
                        ("inspection-reference",),
                    ).fetchone()[0],
                    "regulatory_contexts": connection.execute(
                        """
                        SELECT COUNT(*)
                        FROM substance_regulatory_contexts c
                        JOIN inspection_substances s ON s.substance_id = c.substance_id
                        WHERE s.dataset_id = ?
                        """,
                        ("inspection-reference",),
                    ).fetchone()[0],
                }
            connection.close()
            self.assertEqual(scoped_counts, expected)


if __name__ == "__main__":
    unittest.main()
