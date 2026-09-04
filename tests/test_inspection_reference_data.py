import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.data_store import DataStore
from src.inspection_reference import validate_inspection_config
from src.runtime import read_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_CONFIG = PROJECT_ROOT / "config" / "inspection_reference.json"
DATASET_SOURCE_REFERENCE = (
    "https://www.samr.gov.cn/spcjs/xxfb/art/2022/"
    "art_547b6bf10c8e4fa7ab052e250a1aa4b4.html"
)
METHOD_SOURCE_REFERENCE = (
    "https://www.samr.gov.cn/spcjs/bz/cs/art/2022/"
    "art_46900b84fdad41d2ab711489f22c052b.html"
)

EXPECTED_SUBSTANCES = [
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

EXPECTED_CATEGORIES = {
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


class VerifiedInspectionReferenceDataTest(unittest.TestCase):
    def test_bjs_202209_reference_contract_matches_verified_source_facts(self):
        payload = validate_inspection_config(read_json(REFERENCE_CONFIG))
        self.assertEqual(payload["dataset_id"], "inspection-reference")
        self.assertEqual(payload["dataset_status"], "verified_reference")
        self.assertEqual(payload["source_reference"], DATASET_SOURCE_REFERENCE)

        self.assertEqual(len(payload["methods"]), 1)
        method = payload["methods"][0]
        self.assertEqual(method["method_id"], "bjs-202209")
        self.assertEqual(method["method_no"], "BJS 202209")
        self.assertEqual(method["method_status"], "current")
        self.assertEqual(method["source_reference"], METHOD_SOURCE_REFERENCE)
        self.assertTrue(
            payload["source_reference"].startswith("https://www.samr.gov.cn/")
        )
        self.assertTrue(
            method["source_reference"].startswith("https://www.samr.gov.cn/")
        )

        substances = payload["substances"]
        self.assertEqual(len(substances), 19)
        self.assertEqual(
            [(item["canonical_name"], item["cas_no"]) for item in substances],
            EXPECTED_SUBSTANCES,
        )
        self.assertTrue(all(item["english_name"] == "" for item in substances))
        self.assertTrue(all(item["substance_group"] == "" for item in substances))

        substances_by_id = {item["substance_id"]: item for item in substances}
        relations = payload["method_substances"]
        self.assertEqual(len(relations), 19)
        self.assertEqual([item["ordinal"] for item in relations], list(range(1, 20)))
        self.assertEqual(
            {item["source_cas_no"] for item in relations},
            {cas_no for _, cas_no in EXPECTED_SUBSTANCES},
        )
        for relation in relations:
            substance = substances_by_id[relation["substance_id"]]
            self.assertEqual(relation["source_label"], substance["canonical_name"])
            self.assertEqual(relation["source_cas_no"], substance["cas_no"])
            self.assertEqual(relation["determination_role"], "quantitative")
            self.assertEqual(relation["normalization_note"], "")

        applicabilities = payload["method_applicabilities"]
        self.assertEqual(len(applicabilities), 9)
        self.assertTrue(all(item["substance_id"] is None for item in applicabilities))
        self.assertTrue(all(item["scope_type"] == "include" for item in applicabilities))
        self.assertEqual(
            {item["product_category"] for item in applicabilities},
            EXPECTED_CATEGORIES,
        )
        self.assertTrue(
            all(
                item["source_scope_text"] == item["product_category"]
                for item in applicabilities
            )
        )
        self.assertEqual(payload["substance_regulatory_contexts"], [])

    def test_bjs_202209_import_is_idempotent_with_exact_dataset_scoped_counts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = DataStore(root / "data" / "app.db", root / "output")
            store.initialize()
            expected = {
                "dataset": 1,
                "methods": 1,
                "substances": 19,
                "method_substances": 19,
                "applicabilities": 9,
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
