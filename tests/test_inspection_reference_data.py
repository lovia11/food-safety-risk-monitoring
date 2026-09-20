import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.data_store import DataStore
from src.inspection_reference import validate_inspection_config
from src.runtime import read_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_CONFIG = PROJECT_ROOT / "config" / "inspection_reference.json"
DATASET_SOURCE_REFERENCE = "https://www.samr.gov.cn/"
BJS_202209_SOURCE_REFERENCE = (
    "https://www.samr.gov.cn/spcjs/bz/cs/art/2022/"
    "art_46900b84fdad41d2ab711489f22c052b.html"
)
BJS_201701_SOURCE_REFERENCE = (
    "https://www.samr.gov.cn/spcjs/bz/cs/art/2017/"
    "art_24cbba1f9bb44ba0972de88180925b12.html"
)
BJS_201710_SOURCE_REFERENCE = (
    "https://www.samr.gov.cn/spcjs/bz/cs/art/2017/"
    "art_0365495da2fa4ee782b888f0cacd0b5b.html"
)
KJ_201903_SOURCE_REFERENCE = (
    "https://www.samr.gov.cn/spcjs/xxfb/art/2019/"
    "art_2a1de171556f40f2b8f5829fe9810086.html"
)
GBT_45443_2025_SOURCE_REFERENCE = (
    "https://openstd.samr.gov.cn/bzgk/std/"
    "newGbInfo?hcno=647D466911910DA6D8ADAEB957E2E9CD"
)
BJS_202405_SOURCE_REFERENCE = (
    "https://www.samr.gov.cn/spcjs/bcjyff/art/2025/"
    "art_6f2901cf3f95499f8726e3420f3708a7.html"
)
BJS_201808_SOURCE_REFERENCE = (
    "https://www.samr.gov.cn/spcjs/bz/cs/art/2018/"
    "art_304e4c4a5f9d4e8d988c1b30ce408825.html"
)
BJS_201901_ATTACHMENT_REFERENCE = (
    "https://www.samr.gov.cn/cms_files/filemanager/1647978232/"
    "attach/20235/P020190516389935220036.doc"
)
GBT_5009_170_2003_SOURCE_REFERENCE = (
    "https://std.samr.gov.cn/gb/search/"
    "gbDetailed?id=71F772D7B65AD3A7E05397BE0A0AB82A"
)
MELATONIN_CONTEXT_SOURCE_REFERENCE = (
    "https://www.samr.gov.cn/tssps/zcwj/art/2023/"
    "art_f22954c667fc400abddd0b7ece6155a6.html"
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

EXPECTED_BJS_201710_ROWS = [
    ("利血平", "Reserpine", "50-55-5"),
    ("格列喹酮", "Gliquidone", "33342-05-1"),
    ("羟基豪莫西地那非", "Hydroxyhomosildenafil", "139755-85-4"),
    ("硫代艾地那非", "Thioaildenafil", "856190-47-1"),
    ("格列苯脲", "Glibenclamide", "10238-21-8"),
    ("格列美脲", "Glimepiride", "93479-97-1"),
    ("豪莫西地那非", "Homosildenafil", "642928-07-2"),
    ("伐地那非", "Vardenafil", "224785-90-4"),
    ("红地那非", "Hongdenafil", "831217-01-7"),
    ("西地那非", "Sildenafil", "139755-83-2"),
    ("伪伐地那非", "Pseudovardenafil", "224788-34-5"),
    ("那莫西地那非", "Norneosildenafil", "371959-09-0"),
    ("瑞格列奈", "Repaglinide", "135062-02-1"),
    ("那红地那非", "Noracetildenafil", "949091-38-7"),
    ("格列吡嗪", "Glipizide", "29094-61-9"),
    ("洛伐他汀羟酸钠盐", "Lovastatin Hydroxy Acid, Sodium Salt", "75225-50-2"),
    ("尼莫地平", "Nimodipine", "66085-59-4"),
    ("辛伐他汀", "Simvastatin", "79902-63-9"),
    ("氨氯地平", "Amlodipine", "88150-42-9"),
    ("洛伐他汀", "Lovastatin", "75330-75-5"),
    ("美伐他汀", "Mevastatin", "73573-88-3"),
    ("氨基他达拉非", "Aminotadalafil", "385769-84-6"),
    ("他达拉非", "Tadalafil", "171596-29-5"),
    ("佐匹克隆", "Zopiclone", "43200-80-2"),
    ("尼索地平", "Nisoldipine", "63675-72-9"),
    ("脱羟基洛伐他丁", "Dehydro Lovastatin", "109273-98-5"),
    ("哌唑嗪", "Prazosin", "19216-56-9"),
    ("非洛地平", "Felodipine", "72509-76-3"),
    ("格列波脲", "Glibornuride", "26944-48-9"),
    ("尼群地平", "Nitrendipine", "39562-70-4"),
    ("罗格列酮", "Rosiglitazone", "122320-73-4"),
    ("吡咯列酮", "Pioglitazone", "111025-46-8"),
    ("罗通定", "Tetrahydropalmatine", "2934-97-6"),
    ("醋氯芬酸", "Aceclofenac", "89796-99-6"),
    ("硝苯地平", "Nifedipine", "21829-25-4"),
    ("三唑仑", "Triazolam", "28911-01-5"),
    ("青藤碱", "Sinomenine", "115-53-7"),
    ("呋塞米", "Furosemide", "54-31-9"),
    ("咪达唑仑", "Midazolam", "59467-70-8"),
    ("格列齐特", "Gliclazide", "21187-98-4"),
    ("劳拉西泮", "Lorazepam", "846-49-1"),
    ("酚酞", "Phenolphthalein", "77-09-8"),
    ("二氧丙嗪", "Dioxopromethazine", "13754-56-8"),
    ("氯硝西泮", "Clonazepam", "1622-61-3"),
    ("阿普唑仑", "Alprazolam", "28981-97-7"),
    ("扎来普隆", "Zaleplon", "151319-34-5"),
    ("氯氮卓", "Chlordiazepoxide", "58-25-3"),
    ("氢氯噻嗪", "Hydrochlorothiazide", "58-93-5"),
    ("艾司唑仑", "Estazolam", "29975-16-4"),
    ("奥沙西泮", "Oxazepam", "604-75-1"),
    ("地西泮", "Diazepam", "439-14-5"),
    ("硝西泮", "Nitrazepam", "146-22-5"),
    ("西布曲明", "Sibutramine", "106650-56-0"),
    ("文拉法辛", "Venlafaxine", "93413-69-5"),
    ("氯苯那敏", "Chlorphenamine", "132-22-9"),
    ("氯美扎酮", "Chlormezanone", "80-77-3"),
    ("甲苯磺丁脲", "Tolbutamide", "64-77-7"),
    ("阿替洛尔", "Atenolol", "29122-68-7"),
    ("N-单去甲基西布曲明", "N-Monodesmethyl Sibutramine", "168835-59-4"),
    ("N,N-双去甲基西布曲明", "N,N-Didesmethyl Sibutramine", "84467-54-9"),
    ("沙丁胺醇", "Salbutamol", "18559-94-9"),
    ("司可巴比妥", "Secobarbital", "76-73-3"),
    ("褪黑素", "Melatonine", "73-31-4"),
    ("芬氟拉明", "Fenfluramine", "458-24-2"),
    ("苯巴比妥", "Phenobarbital", "50-06-6"),
    ("可乐定", "Clonidine", "4205-90-7"),
    ("异戊巴比妥", "Amobarbital", "57-43-2"),
    ("卡托普利", "Captopril", "62571-86-2"),
    ("苯乙双胍", "Phenformin", "114-86-3"),
    ("巴比妥", "Barbital", "57-44-3"),
    ("麻黄碱", "Ephedrine", "299-42-3"),
    ("丁二胍", "buformin", "692-13-7"),
    ("氨甲环酸", "Tranexamic Acid", "701-54-2"),
    ("二甲双胍", "Metformin", "657-24-9"),
    ("烟酸", "Nicotinic acid", "59-67-6"),
]

EXPECTED_BJS_201901_ROWS = [
    ("苯乙双胍", "Phenformin", "114-86-3"),
    ("丁二胍", "Buformin", "692-13-7"),
    ("二甲双胍", "Metformin", "657-24-9"),
    ("伏格列波糖", "Voglibose", "83480-29-9"),
    ("阿卡波糖", "Acarbose", "56180-94-0"),
    ("维达列汀", "Vildagliptin", "274901-16-5"),
    ("罗格列酮", "Rosiglitazone", "122320-73-4"),
    ("西他列汀", "Sitagliptin", "486460-32-6"),
    ("吡格列酮", "Pioglitazone", "111025-46-8"),
    ("氯磺丙脲", "Chlorpropamide", "94-20-2"),
    ("达格列净", "Dapagliflozin", "461432-26-8"),
    ("格列吡嗪", "Glipizide", "29094-61-9"),
    ("甲苯磺丁脲", "Tolbutamide", "64-77-7"),
    ("醋磺己脲", "Acetohexamide", "968-81-0"),
    ("妥拉磺脲", "Tolazamide", "1156-19-0"),
    ("瑞格列奈", "Repaglinide", "135062-02-1"),
    ("卡格列净", "Canagliflozin", "842133-18-0"),
    ("格列齐特", "Gliclazide", "21187-98-4"),
    ("格列波脲", "Glibornuride", "26944-48-9"),
    ("格列本脲", "Glibenclamide", "10238-21-8"),
    ("那格列奈", "Nateglinide", "105816-04-4"),
    ("格列美脲", "Glimepiride", "93479-97-1"),
    ("曲格列酮", "Troglitazone", "97322-87-7"),
    ("格列喹酮", "Gliquidone", "33342-05-1"),
    ("莫格他唑", "Muraglitazar", "331741-94-7"),
    ("GW501516", "GW501516", "317318-70-0"),
    ("环格列酮", "Ciglitazone", "74772-77-3"),
]

REUSED_BJS_201710_CAS = {
    "79902-63-9",
    "75330-75-5",
    "54-31-9",
    "77-09-8",
    "58-93-5",
    "106650-56-0",
    "168835-59-4",
    "84467-54-9",
    "458-24-2",
    "299-42-3",
}


class VerifiedInspectionReferenceDataTest(unittest.TestCase):
    def test_bjs_202209_reference_contract_matches_verified_source_facts(self):
        payload = validate_inspection_config(read_json(REFERENCE_CONFIG))
        self.assertEqual(payload["dataset_id"], "inspection-reference")
        self.assertEqual(payload["dataset_version"], "2026.09-b11")
        self.assertEqual(payload["dataset_status"], "verified_reference")
        self.assertEqual(payload["source_reference"], DATASET_SOURCE_REFERENCE)

        self.assertEqual(len(payload["methods"]), 11)
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
        self.assertEqual(len(payload["substance_regulatory_contexts"]), 1)

    def test_bjs_201701_reference_contract_matches_verified_source_facts(self):
        payload = validate_inspection_config(read_json(REFERENCE_CONFIG))
        methods = {item["method_id"]: item for item in payload["methods"]}
        self.assertEqual(
            set(methods),
            {
                "bjs-202209",
                "bjs-201701",
                "bjs-201710",
                "kj-201901",
                "kj-201902",
                "kj-201903",
                "gbt-45443-2025",
                "bjs-202405",
                "bjs-201808",
                "bjs-201901",
                "gbt-5009-170-2003",
            },
        )
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

        self.assertEqual(len(payload["substances"]), 219)
        self.assertEqual(len(payload["method_substances"]), 263)
        self.assertEqual(len(payload["method_applicabilities"]), 61)
        self.assertEqual(len(payload["substance_regulatory_contexts"]), 1)

    def test_bjs_201710_reference_contract_matches_verified_source_facts(self):
        payload = validate_inspection_config(read_json(REFERENCE_CONFIG))
        methods = {item["method_id"]: item for item in payload["methods"]}
        method = methods["bjs-201710"]
        self.assertEqual(method["dataset_id"], "inspection-reference")
        self.assertEqual(method["method_no"], "BJS 201710")
        self.assertEqual(method["method_name"], "保健食品中75种非法添加化学药物的检测")
        self.assertEqual(method["method_type"], "supplementary_bjs")
        self.assertEqual(method["method_status"], "current")
        self.assertEqual(method["publisher"], "国家食品药品监督管理总局")
        self.assertEqual(method["published_date"], "2017-11-17")
        self.assertIsNone(method["effective_date"])
        self.assertIsNone(method["replaces_method_no"])
        self.assertIsNone(method["replaced_by_method_no"])
        self.assertEqual(
            method["source_name"],
            "国家市场监督管理总局食品补充检验方法数据库",
        )
        self.assertEqual(method["source_date"], "2017-11-17")
        self.assertEqual(method["source_reference"], BJS_201710_SOURCE_REFERENCE)
        self.assertEqual(
            method["note"],
            "依据BJS 201710正式方法全文逐项录入75种目标物；"
            "本Dataset仅记录检验方法事实，不建立RiskClue映射或商品违法结论。",
        )

        substances_by_id = {
            item["substance_id"]: item for item in payload["substances"]
        }
        relations = [
            item
            for item in payload["method_substances"]
            if item["method_id"] == "bjs-201710"
        ]
        self.assertEqual(len(relations), 75)
        self.assertEqual([item["ordinal"] for item in relations], list(range(1, 76)))
        self.assertEqual(
            [(item["source_label"], item["source_cas_no"]) for item in relations],
            [(name, cas_no) for name, _, cas_no in EXPECTED_BJS_201710_ROWS],
        )
        self.assertTrue(
            all(item["determination_role"] == "qualitative" for item in relations)
        )

        all_cas = [item["cas_no"] for item in payload["substances"]]
        self.assertEqual(len(all_cas), len(set(all_cas)))
        prior_substance_ids = {
            item["substance_id"]
            for item in payload["method_substances"]
            if item["method_id"] in {"bjs-202209", "bjs-201701"}
        }
        reused_substance_ids = {
            item["substance_id"]
            for item in relations
            if item["source_cas_no"] in REUSED_BJS_201710_CAS
        }
        self.assertEqual(
            reused_substance_ids,
            {f"substance-cas-{cas_no}" for cas_no in REUSED_BJS_201710_CAS},
        )
        self.assertTrue(reused_substance_ids.issubset(prior_substance_ids))
        self.assertEqual(
            len({item["substance_id"] for item in relations} - prior_substance_ids),
            65,
        )

        source_english_by_cas = {
            cas_no: english_name
            for _, english_name, cas_no in EXPECTED_BJS_201710_ROWS
        }
        for relation in relations:
            substance = substances_by_id[relation["substance_id"]]
            self.assertEqual(relation["source_cas_no"], substance["cas_no"])
            if relation["source_cas_no"] not in REUSED_BJS_201710_CAS:
                expected_english = source_english_by_cas[relation["source_cas_no"]]
                if relation["source_cas_no"] == "73-31-4":
                    expected_english = "Melatonin"
                self.assertEqual(substance["english_name"], expected_english)
                self.assertEqual(substance["substance_group"], "")
                self.assertEqual(substance["note"], "BJS 201710附录A")

        rows_by_ordinal = {item["ordinal"]: item for item in relations}
        row_26 = rows_by_ordinal[26]
        self.assertEqual(row_26["source_label"], "脱羟基洛伐他丁")
        self.assertEqual(
            substances_by_id[row_26["substance_id"]]["canonical_name"],
            "脱羟基洛伐他汀",
        )
        self.assertTrue(row_26["normalization_note"])

        row_32 = rows_by_ordinal[32]
        self.assertEqual(row_32["source_label"], "吡咯列酮")
        self.assertEqual(
            substances_by_id[row_32["substance_id"]]["canonical_name"],
            "吡格列酮",
        )
        self.assertTrue(row_32["normalization_note"])

        row_63 = rows_by_ordinal[63]
        self.assertEqual(
            substances_by_id[row_63["substance_id"]]["english_name"],
            "Melatonin",
        )
        self.assertIn("Melatonine", row_63["normalization_note"])
        self.assertEqual(
            {item["ordinal"] for item in relations if item["normalization_note"]},
            {26, 32, 63},
        )

        glibenclamide = substances_by_id["substance-cas-10238-21-8"]
        self.assertEqual(glibenclamide["canonical_name"], "格列苯脲")
        self.assertNotEqual(glibenclamide["canonical_name"], "格列本脲")

        applicabilities = [
            item
            for item in payload["method_applicabilities"]
            if item["method_id"] == "bjs-201710"
        ]
        self.assertEqual(len(applicabilities), 8)
        self.assertTrue(all(item["substance_id"] is None for item in applicabilities))
        self.assertTrue(all(item["scope_type"] == "include" for item in applicabilities))
        expected_forms = {"片剂", "口服液", "硬胶囊", "软胶囊"}
        by_category = {
            category: [
                item
                for item in applicabilities
                if item["product_category"] == category
            ]
            for category in {"保健食品", "声称具有保健功效的食品"}
        }
        self.assertEqual(
            {item["product_form"] for item in by_category["保健食品"]},
            expected_forms,
        )
        self.assertEqual(
            {
                item["product_form"]
                for item in by_category["声称具有保健功效的食品"]
            },
            expected_forms,
        )
        self.assertTrue(
            all(
                item["source_scope_text"]
                == "片剂、口服液、硬胶囊和软胶囊保健食品"
                for item in by_category["保健食品"]
            )
        )
        self.assertTrue(
            all(
                item["source_scope_text"]
                == "片剂、口服液、硬胶囊、软胶囊类声称具有保健功效的食品"
                for item in by_category["声称具有保健功效的食品"]
            )
        )

        self.assertEqual(len(payload["methods"]), 11)
        self.assertEqual(len(payload["substances"]), 219)
        self.assertEqual(len(payload["method_substances"]), 263)
        self.assertEqual(len(payload["method_applicabilities"]), 61)
        self.assertEqual(len(payload["substance_regulatory_contexts"]), 1)

    def test_kj_201901_and_201902_match_samr_fulltext_and_scoped_runtime_rules(self):
        payload = validate_inspection_config(read_json(REFERENCE_CONFIG))
        methods = {item["method_id"]: item for item in payload["methods"]}
        substances = {item["substance_id"]: item for item in payload["substances"]}

        kj1 = methods["kj-201901"]
        self.assertEqual(kj1["method_no"], "KJ201901")
        self.assertEqual(
            kj1["method_name"],
            "保健食品中西地那非和他达拉非的快速检测 胶体金免疫层析法",
        )
        self.assertEqual(kj1["method_type"], "rapid_kj")
        self.assertEqual(kj1["method_status"], "current")
        self.assertEqual(kj1["knowledge_depth"], "recommendation_ready")
        self.assertEqual(kj1["published_date"], "2019-09-27")
        self.assertEqual(kj1["source_reference"], KJ_201903_SOURCE_REFERENCE)
        self.assertIn("阳性结果应进一步确证", kj1["note"])
        self.assertIn("anti_fatigue", kj1["note"])
        self.assertIn("不把“调节免疫等”扩写为新Risk", kj1["note"])
        self.assertIn("CA99D709F8B38D6E53AC4DCED58BF99B3D0FF2B99EC8CCC9712B328F1B38D923", kj1["note"])

        kj1_relations = [
            item for item in payload["method_substances"]
            if item["method_id"] == "kj-201901"
        ]
        self.assertEqual(
            [
                (
                    item["source_label"],
                    item["source_cas_no"],
                    item["substance_id"],
                    item["determination_role"],
                )
                for item in kj1_relations
            ],
            [
                ("西地那非", "139755-83-2", "substance-cas-139755-83-2", "rapid_screen"),
                ("他达拉非", "171596-29-5", "substance-cas-171596-29-5", "rapid_screen"),
            ],
        )
        kj1_scope = [
            item for item in payload["method_applicabilities"]
            if item["method_id"] == "kj-201901"
        ]
        self.assertEqual(len(kj1_scope), 1)
        self.assertEqual(kj1_scope[0]["scope_type"], "include")
        self.assertEqual(kj1_scope[0]["product_category"], "保健食品")
        self.assertEqual(kj1_scope[0]["product_form"], "")
        self.assertEqual(kj1_scope[0]["risk_category"], "anti_fatigue")
        self.assertIn("抗疲劳、调节免疫等", kj1_scope[0]["source_scope_text"])

        kj2 = methods["kj-201902"]
        self.assertEqual(kj2["method_no"], "KJ201902")
        self.assertEqual(
            kj2["method_name"],
            "保健食品中罗格列酮和格列苯脲的快速检测 胶体金免疫层析法",
        )
        self.assertEqual(kj2["method_type"], "rapid_kj")
        self.assertEqual(kj2["method_status"], "current")
        self.assertEqual(kj2["knowledge_depth"], "recommendation_ready")
        self.assertEqual(kj2["source_reference"], KJ_201903_SOURCE_REFERENCE)
        self.assertIn("阳性结果应进一步确证", kj2["note"])
        self.assertIn("203DB061A5D171D9AFAC91402B3EAA1B7708C763E37F62DAD1663E231300B69C", kj2["note"])

        kj2_relations = [
            item for item in payload["method_substances"]
            if item["method_id"] == "kj-201902"
        ]
        self.assertEqual(len(kj2_relations), 2)
        rosiglitazone = kj2_relations[0]
        self.assertEqual(rosiglitazone["source_label"], "马来酸罗格列酮")
        self.assertEqual(rosiglitazone["source_cas_no"], "155141-29-0")
        self.assertEqual(
            rosiglitazone["substance_id"],
            "substance-cas-122320-73-4",
        )
        self.assertEqual(
            substances[rosiglitazone["substance_id"]]["canonical_name"],
            "罗格列酮",
        )
        self.assertIn("母体Substance", rosiglitazone["normalization_note"])

        glibenclamide = kj2_relations[1]
        self.assertEqual(glibenclamide["source_label"], "格列苯脲")
        self.assertEqual(glibenclamide["source_cas_no"], "10238-21-8")
        self.assertEqual(
            glibenclamide["substance_id"],
            "substance-cas-10238-21-8",
        )
        self.assertEqual(glibenclamide["normalization_note"], "")

        kj2_scope = [
            item for item in payload["method_applicabilities"]
            if item["method_id"] == "kj-201902"
        ]
        self.assertEqual(len(kj2_scope), 1)
        self.assertEqual(kj2_scope[0]["product_category"], "保健食品")
        self.assertEqual(kj2_scope[0]["risk_category"], "blood_glucose")
        self.assertIn("辅助降血糖", kj2_scope[0]["source_scope_text"])


    def test_bjs_201901_fulltext_promotion_contract_is_governed(self):
        payload = validate_inspection_config(read_json(REFERENCE_CONFIG))
        methods = {item["method_id"]: item for item in payload["methods"]}
        substances = {item["substance_id"]: item for item in payload["substances"]}

        method = methods["bjs-201901"]
        self.assertEqual(method["method_no"], "BJS 201901")
        self.assertEqual(method["method_type"], "supplementary_bjs")
        self.assertEqual(method["method_status"], "current")
        self.assertEqual(method["knowledge_depth"], "recommendation_ready")
        self.assertEqual(method["source_reference"], BJS_201901_ATTACHMENT_REFERENCE)
        self.assertEqual(method["source_date"], "2019-01-29")
        self.assertIn(
            "C4A697A35F4171516C06947C937F0C10D01FDC3AFC671D7780154A5AD9936EE9",
            method["note"],
        )
        self.assertIn("不得反推Claim→Risk或Risk→Substance", method["note"])

        relations = [
            item for item in payload["method_substances"]
            if item["method_id"] == "bjs-201901"
        ]
        self.assertEqual(len(relations), 27)
        self.assertEqual([item["ordinal"] for item in relations], list(range(1, 28)))
        self.assertTrue(all(item["determination_role"] == "quantitative" for item in relations))
        self.assertEqual(
            [(item["source_label"], item["source_cas_no"]) for item in relations],
            [(name, cas) for name, _, cas in EXPECTED_BJS_201901_ROWS],
        )
        by_source = {item["source_label"]: item for item in relations}
        self.assertEqual(by_source["格列本脲"]["substance_id"], "substance-cas-10238-21-8")
        self.assertEqual(substances["substance-cas-10238-21-8"]["canonical_name"], "格列苯脲")
        self.assertTrue(by_source["格列本脲"]["normalization_note"])
        self.assertEqual(by_source["吡格列酮"]["substance_id"], "substance-cas-111025-46-8")
        self.assertEqual(substances["substance-cas-111025-46-8"]["canonical_name"], "吡格列酮")
        self.assertEqual(by_source["吡格列酮"]["normalization_note"], "")

        new_cas = {
            "83480-29-9", "56180-94-0", "274901-16-5", "486460-32-6",
            "94-20-2", "461432-26-8", "968-81-0", "1156-19-0",
            "842133-18-0", "105816-04-4", "97322-87-7", "331741-94-7",
            "317318-70-0", "74772-77-3",
        }
        by_cas = {item["cas_no"]: item for item in substances.values()}
        for source_name, english_name, cas_no in EXPECTED_BJS_201901_ROWS:
            substance = by_cas[cas_no]
            if cas_no in new_cas:
                self.assertEqual(substance["canonical_name"], source_name)
                self.assertEqual(substance["english_name"], english_name)
                self.assertIn("不据此创建Risk映射", substance["note"])

        scopes = [
            item for item in payload["method_applicabilities"]
            if item["method_id"] == "bjs-201901"
        ]
        self.assertEqual(len(scopes), 8)
        self.assertEqual(
            {(item["product_category"], item["product_form"]) for item in scopes},
            {
                ("茶叶", ""), ("奶粉", ""), ("饼干", ""), ("酒", ""), ("饮料", ""),
                ("特殊食品", "片剂"), ("特殊食品", "胶囊剂"), ("特殊食品", "口服液"),
            },
        )
        self.assertTrue(all(item["risk_category"] == "" for item in scopes))
        oral = next(item for item in scopes if item["product_form"] == "口服液")
        self.assertEqual(oral["scope_type"], "conditional")
        self.assertIn("5.1.2", oral["source_scope_text"])
        self.assertEqual(payload["substance_group_memberships"], [])


    def test_bjs_201808_parent_identity_normalization_and_scope_are_governed(self):
        payload = validate_inspection_config(read_json(REFERENCE_CONFIG))
        methods = {item["method_id"]: item for item in payload["methods"]}
        substances = {item["substance_id"]: item for item in payload["substances"]}

        method = methods["bjs-201808"]
        self.assertEqual(method["method_no"], "BJS 201808")
        self.assertEqual(method["method_type"], "supplementary_bjs")
        self.assertEqual(method["method_status"], "current")
        self.assertEqual(method["knowledge_depth"], "recommendation_ready")
        self.assertEqual(method["source_reference"], BJS_201808_SOURCE_REFERENCE)
        self.assertIn(
            "45D85B389553925AF01FCB5EEAB6DE7113E898ED998FCDEE44EBD3476DB696B9",
            method["note"],
        )
        self.assertIn("不得反推任何Claim→Risk", method["note"])

        expected_parents = [
            ("酚妥拉明", "Phentolamine", "50-60-2"),
            ("哌唑嗪", "Prazosin", "19216-56-9"),
            ("特拉唑嗪", "Terazosin", "63590-64-7"),
            ("育亨宾", "Yohimbine", "146-48-5"),
            ("妥拉唑林", "Tolazoline", "59-98-3"),
        ]
        for name, english_name, cas_no in expected_parents:
            substance = substances[f"substance-cas-{cas_no}"]
            self.assertEqual(substance["canonical_name"], name)
            self.assertEqual(substance["english_name"], english_name)
            self.assertEqual(substance["cas_no"], cas_no)
            self.assertEqual(substance["substance_group"], "")

        relations = [
            item
            for item in payload["method_substances"]
            if item["method_id"] == "bjs-201808"
        ]
        self.assertEqual(
            [
                (
                    item["source_label"],
                    item["source_cas_no"],
                    item["substance_id"],
                    item["determination_role"],
                )
                for item in relations
            ],
            [
                ("甲磺酸酚妥拉明", "65-28-1", "substance-cas-50-60-2", "quantitative"),
                ("盐酸哌唑嗪", "19237-84-4", "substance-cas-19216-56-9", "quantitative"),
                ("盐酸特拉唑嗪", "63074-08-8", "substance-cas-63590-64-7", "quantitative"),
                ("盐酸育亨宾", "65-19-0", "substance-cas-146-48-5", "quantitative"),
                ("盐酸妥拉唑林", "59-97-2", "substance-cas-59-98-3", "quantitative"),
            ],
        )
        self.assertTrue(all(item["normalization_note"] for item in relations))

        scopes = [
            item
            for item in payload["method_applicabilities"]
            if item["method_id"] == "bjs-201808"
        ]
        self.assertEqual(len(scopes), 7)
        self.assertEqual(
            {(item["product_category"], item["product_form"]) for item in scopes},
            {
                ("硬质糖果", ""),
                ("凝胶糖果", ""),
                ("酒", ""),
                ("茶饮料", ""),
                ("保健食品", "片剂"),
                ("保健食品", "口服液"),
                ("保健食品", "胶囊剂"),
            },
        )
        self.assertTrue(all(item["risk_category"] == "" for item in scopes))
        self.assertTrue(
            all("其他类似基质可参照本方法" in item["source_scope_text"] for item in scopes)
        )
        self.assertEqual(payload["substance_group_memberships"], [])

    def test_kj_201903_reference_contract_matches_verified_source_facts(self):
        payload = validate_inspection_config(read_json(REFERENCE_CONFIG))
        self.assertEqual(payload["dataset_version"], "2026.09-b11")
        self.assertEqual(payload["source_reference"], DATASET_SOURCE_REFERENCE)

        methods = {item["method_id"]: item for item in payload["methods"]}
        self.assertEqual(
            set(methods),
            {
                "bjs-202209",
                "bjs-201701",
                "bjs-201710",
                "kj-201901",
                "kj-201902",
                "kj-201903",
                "gbt-45443-2025",
                "bjs-202405",
                "bjs-201808",
                "bjs-201901",
                "gbt-5009-170-2003",
            },
        )
        method = methods["kj-201903"]
        self.assertEqual(method["dataset_id"], "inspection-reference")
        self.assertEqual(method["method_no"], "KJ201903")
        self.assertEqual(
            method["method_name"],
            "保健食品中巴比妥类化学成分的快速检测 胶体金免疫层析法",
        )
        self.assertEqual(method["method_type"], "rapid_kj")
        self.assertEqual(method["method_status"], "current")
        self.assertEqual(method["publisher"], "国家市场监督管理总局")
        self.assertEqual(method["published_date"], "2019-09-27")
        self.assertIsNone(method["effective_date"])
        self.assertIsNone(method["replaces_method_no"])
        self.assertIsNone(method["replaced_by_method_no"])
        self.assertEqual(method["source_name"], "市场监管总局2019年第41号公告")
        self.assertEqual(method["source_reference"], KJ_201903_SOURCE_REFERENCE)
        self.assertEqual(method["source_date"], "2019-09-27")
        self.assertIn("阳性结果应进一步确证", method["note"])

        substances_by_id = {
            item["substance_id"]: item for item in payload["substances"]
        }
        kj_relations = [
            item
            for item in payload["method_substances"]
            if item["method_id"] == "kj-201903"
        ]
        self.assertEqual(len(kj_relations), 4)
        self.assertEqual([item["ordinal"] for item in kj_relations], [1, 2, 3, 4])
        self.assertEqual(
            [item["source_cas_no"] for item in kj_relations],
            ["57-44-3", "50-06-6", "57-43-2", "76-73-3"],
        )
        self.assertEqual(
            [item["substance_id"] for item in kj_relations],
            [
                "substance-cas-57-44-3",
                "substance-cas-50-06-6",
                "substance-cas-57-43-2",
                "substance-cas-76-73-3",
            ],
        )
        bjs_201710_substance_ids = {
            item["substance_id"]
            for item in payload["method_substances"]
            if item["method_id"] == "bjs-201710"
        }
        self.assertTrue(
            all(
                item["substance_id"] in bjs_201710_substance_ids
                for item in kj_relations
            )
        )
        self.assertEqual(len(payload["substances"]), 219)
        self.assertTrue(
            all(item["determination_role"] == "rapid_screen" for item in kj_relations)
        )

        fourth = kj_relations[3]
        self.assertEqual(fourth["source_label"], "司可巴比妥钠")
        self.assertEqual(
            substances_by_id[fourth["substance_id"]]["canonical_name"],
            "司可巴比妥",
        )
        self.assertTrue(fourth["normalization_note"])
        self.assertIn("司可巴比妥钠", fourth["normalization_note"])
        self.assertIn("76-73-3", fourth["normalization_note"])

        applicabilities = [
            item
            for item in payload["method_applicabilities"]
            if item["method_id"] == "kj-201903"
        ]
        self.assertEqual(len(applicabilities), 6)
        self.assertTrue(all(item["substance_id"] is None for item in applicabilities))
        self.assertTrue(all(item["scope_type"] == "include" for item in applicabilities))
        self.assertTrue(
            all(item["product_category"] == "保健食品" for item in applicabilities)
        )
        self.assertEqual(
            {item["product_form"] for item in applicabilities},
            {"硬胶囊", "软胶囊", "丸剂", "片剂", "散剂", "口服液"},
        )
        self.assertTrue(
            all(
                item["source_scope_text"]
                == "本方法适用于硬胶囊、软胶囊、丸剂、片剂、"
                "散剂及口服液等保健食品中巴比妥类化学成分的快速测定"
                for item in applicabilities
            )
        )

        self.assertEqual(len(payload["methods"]), 11)
        self.assertEqual(len(payload["substances"]), 219)
        self.assertEqual(len(payload["method_substances"]), 263)
        self.assertEqual(len(payload["method_applicabilities"]), 61)
        self.assertEqual(len(payload["substance_regulatory_contexts"]), 1)

    def test_gbt_45443_and_melatonin_context_match_verified_source_facts(self):
        payload = validate_inspection_config(read_json(REFERENCE_CONFIG))
        self.assertEqual(payload["dataset_version"], "2026.09-b11")

        methods = {item["method_id"]: item for item in payload["methods"]}
        self.assertEqual(
            set(methods),
            {
                "bjs-202209",
                "bjs-201701",
                "bjs-201710",
                "kj-201901",
                "kj-201902",
                "kj-201903",
                "gbt-45443-2025",
                "bjs-202405",
                "bjs-201808",
                "bjs-201901",
                "gbt-5009-170-2003",
            },
        )
        method = methods["gbt-45443-2025"]
        self.assertEqual(method["dataset_id"], "inspection-reference")
        self.assertEqual(method["method_no"], "GB/T 45443-2025")
        self.assertEqual(method["method_name"], "保健食品中褪黑素的测定")
        self.assertEqual(method["method_type"], "national_standard_gbt")
        self.assertEqual(method["method_status"], "current")
        self.assertEqual(
            method["publisher"],
            "国家市场监督管理总局、国家标准化管理委员会",
        )
        self.assertEqual(method["published_date"], "2025-03-28")
        self.assertEqual(method["effective_date"], "2025-10-01")
        self.assertEqual(method["replaces_method_no"], "GB/T 5009.170-2003")
        self.assertIsNone(method["replaced_by_method_no"])
        self.assertEqual(method["source_name"], "国家标准全文公开系统")
        self.assertEqual(method["source_reference"], GBT_45443_2025_SOURCE_REFERENCE)
        self.assertEqual(method["source_date"], "2025-03-28")
        self.assertIn("不是食品非法添加补充检验方法", method["note"])

        relations = [
            item
            for item in payload["method_substances"]
            if item["method_id"] == "gbt-45443-2025"
        ]
        self.assertEqual(len(relations), 1)
        relation = relations[0]
        self.assertEqual(relation["substance_id"], "substance-cas-73-31-4")
        self.assertEqual(relation["source_label"], "褪黑素")
        self.assertEqual(relation["source_cas_no"], "73-31-4")
        self.assertEqual(relation["determination_role"], "quantitative")
        self.assertEqual(relation["normalization_note"], "")
        self.assertEqual(relation["ordinal"], 1)

        substances = payload["substances"]
        self.assertEqual(len(substances), 219)
        melatonin_substances = [
            item for item in substances if item["substance_id"] == "substance-cas-73-31-4"
        ]
        self.assertEqual(len(melatonin_substances), 1)
        self.assertEqual(melatonin_substances[0]["canonical_name"], "褪黑素")
        self.assertEqual(melatonin_substances[0]["english_name"], "Melatonin")
        self.assertEqual(melatonin_substances[0]["cas_no"], "73-31-4")

        applicabilities = [
            item
            for item in payload["method_applicabilities"]
            if item["method_id"] == "gbt-45443-2025"
        ]
        self.assertEqual(len(applicabilities), 7)
        self.assertTrue(all(item["substance_id"] is None for item in applicabilities))
        self.assertTrue(all(item["scope_type"] == "include" for item in applicabilities))
        self.assertTrue(
            all(item["product_category"] == "保健食品" for item in applicabilities)
        )
        self.assertEqual(
            {item["product_form"] for item in applicabilities},
            {"片剂", "硬胶囊", "软胶囊", "颗粒剂", "粉剂", "口服液", "凝胶糖果"},
        )

        contexts = payload["substance_regulatory_contexts"]
        self.assertEqual(len(contexts), 1)
        context = contexts[0]
        self.assertEqual(
            context["context_id"],
            "melatonin-health-food-raw-material-cn-2021",
        )
        self.assertEqual(context["substance_id"], "substance-cas-73-31-4")
        self.assertEqual(context["context_status"], "legal_health_food_raw_material")
        self.assertIn("保健食品", context["product_scope"])
        self.assertEqual(context["jurisdiction"], "CN")
        self.assertEqual(context["valid_from"], "2021-03-01")
        self.assertIsNone(context["valid_to"])
        self.assertEqual(context["source_label"], "褪黑素")
        self.assertEqual(
            context["source_reference"],
            MELATONIN_CONTEXT_SOURCE_REFERENCE,
        )
        self.assertEqual(context["source_date"], "2020-11-23")
        self.assertIn(
            "不得解释为普通食品可以任意添加褪黑素",
            context["note"],
        )

        melatonin_method_ids = {
            item["method_id"]
            for item in payload["method_substances"]
            if item["substance_id"] == "substance-cas-73-31-4"
        }
        self.assertIn("bjs-201710", melatonin_method_ids)
        self.assertIn("gbt-45443-2025", melatonin_method_ids)

        self.assertEqual(len(payload["methods"]), 11)
        self.assertEqual(len(payload["substances"]), 219)
        self.assertEqual(len(payload["method_substances"]), 263)
        self.assertEqual(len(payload["method_applicabilities"]), 61)
        self.assertEqual(len(payload["substance_regulatory_contexts"]), 1)

    def test_verified_dataset_import_is_idempotent_with_exact_scoped_counts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = DataStore(root / "data" / "app.db", root / "output")
            store.initialize()
            expected = {
                "dataset": 1,
                "regulatory_documents": 9,
                "methods": 11,
                "substances": 219,
                "method_substances": 263,
                "applicabilities": 61,
                "regulatory_contexts": 1,
                "group_memberships": 0,
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
                    "regulatory_documents": connection.execute(
                        "SELECT COUNT(*) FROM inspection_regulatory_documents "
                        "WHERE dataset_id = ?",
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
                    "group_memberships": connection.execute(
                        "SELECT COUNT(*) FROM substance_group_memberships "
                        "WHERE dataset_id = ?",
                        ("inspection-reference",),
                    ).fetchone()[0],
                }
            connection.close()
            self.assertEqual(scoped_counts, expected)

    def test_v2_reference_index_depth_documents_and_group_baseline(self):
        payload = validate_inspection_config(read_json(REFERENCE_CONFIG))

        self.assertEqual(payload["schema_version"], 2)
        self.assertEqual(
            {item["knowledge_depth"] for item in payload["methods"]},
            {"reference_only", "recommendation_ready"},
        )
        self.assertEqual(len(payload["regulatory_documents"]), 9)
        self.assertEqual(
            {item["regulatory_document_id"] for item in payload["methods"]},
            {item["document_id"] for item in payload["regulatory_documents"]},
        )
        for document in payload["regulatory_documents"]:
            self.assertTrue(document["source_reference"].startswith("https://"))
            self.assertIn("published_date", document)
            self.assertIn("effective_date", document)
            self.assertNotEqual(document["published_date"], "")
        self.assertEqual(payload["substance_group_memberships"], [])

        successor = next(
            item
            for item in payload["methods"]
            if item["method_id"] == "gbt-45443-2025"
        )
        self.assertEqual(successor["replaces_method_no"], "GB/T 5009.170-2003")
        predecessor = next(
            item
            for item in payload["methods"]
            if item["method_id"] == "gbt-5009-170-2003"
        )
        self.assertEqual(predecessor["method_status"], "revoked")
        self.assertEqual(predecessor["knowledge_depth"], "reference_only")
        self.assertEqual(predecessor["replaced_by_method_no"], "GB/T 45443-2025")

    def test_v2_7c_bjs_deep_method_and_historical_predecessor_match_official_records(self):
        payload = validate_inspection_config(read_json(REFERENCE_CONFIG))
        methods = {item["method_id"]: item for item in payload["methods"]}
        documents = {
            item["document_id"]: item for item in payload["regulatory_documents"]
        }

        bjs = methods["bjs-202405"]
        self.assertEqual(bjs["method_no"], "BJS 202405")
        self.assertEqual(
            bjs["method_name"], "食品中西地那非、他达拉非等化合物的测定"
        )
        self.assertEqual(bjs["method_status"], "current")
        self.assertEqual(bjs["knowledge_depth"], "recommendation_ready")
        self.assertEqual(bjs["publisher"], "国家市场监督管理总局")
        self.assertEqual(bjs["published_date"], "2024-12-22")
        self.assertEqual(bjs["source_reference"], BJS_202405_SOURCE_REFERENCE)
        bjs_relations = [
            item
            for item in payload["method_substances"]
            if item["method_id"] == bjs["method_id"]
        ]
        self.assertEqual(len(bjs_relations), 95)
        self.assertEqual([item["ordinal"] for item in bjs_relations], list(range(1, 96)))
        self.assertEqual(
            (bjs_relations[0]["source_label"], bjs_relations[0]["source_cas_no"]),
            ("吡唑-N-去甲基西地那非", "139755-95-6"),
        )
        self.assertEqual(
            (bjs_relations[-1]["source_label"], bjs_relations[-1]["source_cas_no"]),
            ("双氯地那非", "1446089-84-4"),
        )
        by_label = {item["source_label"]: item for item in bjs_relations}
        self.assertEqual(
            by_label["西地那非"]["substance_id"],
            "substance-cas-139755-83-2",
        )
        self.assertEqual(
            by_label["他达拉非"]["substance_id"],
            "substance-cas-171596-29-5",
        )
        self.assertTrue(
            all(item["determination_role"] == "quantitative" for item in bjs_relations)
        )
        bjs_applicabilities = [
            item
            for item in payload["method_applicabilities"]
            if item["method_id"] == bjs["method_id"]
        ]
        self.assertEqual(len(bjs_applicabilities), 7)
        self.assertEqual(
            {item["product_category"] for item in bjs_applicabilities},
            {"饮料", "糖果", "果冻", "饼干", "咖啡", "酒类", "保健食品"},
        )
        self.assertTrue(
            all(item["scope_type"] == "include" for item in bjs_applicabilities)
        )
        self.assertTrue(
            all("定性和定量测定" in item["source_scope_text"] for item in bjs_applicabilities)
        )
        self.assertIn("附录D给出高分辨液质确证方法", bjs["note"])
        bjs_document = documents[bjs["regulatory_document_id"]]
        self.assertEqual(bjs_document["document_no"], bjs["method_no"])
        self.assertEqual(bjs_document["title"], bjs["method_name"])
        self.assertEqual(bjs_document["status"], "current")

        predecessor = methods["gbt-5009-170-2003"]
        successor = methods["gbt-45443-2025"]
        self.assertEqual(predecessor["method_no"], "GB/T 5009.170-2003")
        self.assertEqual(
            predecessor["method_name"], "保健食品中褪黑素含量的测定"
        )
        self.assertEqual(predecessor["method_status"], "revoked")
        self.assertEqual(predecessor["knowledge_depth"], "reference_only")
        self.assertEqual(
            predecessor["publisher"],
            "中华人民共和国卫生部、中国国家标准化管理委员会",
        )
        self.assertEqual(predecessor["published_date"], "2003-08-11")
        self.assertEqual(predecessor["effective_date"], "2004-01-01")
        self.assertEqual(predecessor["replaced_by_method_no"], successor["method_no"])
        self.assertEqual(successor["replaces_method_no"], predecessor["method_no"])
        self.assertNotEqual(predecessor["method_name"], successor["method_name"])
        self.assertEqual(
            predecessor["source_reference"], GBT_5009_170_2003_SOURCE_REFERENCE
        )
        self.assertFalse(
            any(
                item["method_id"] == predecessor["method_id"]
                for item in payload["method_substances"]
            )
        )
        self.assertFalse(
            any(
                item["method_id"] == predecessor["method_id"]
                for item in payload["method_applicabilities"]
            )
        )
        predecessor_document = documents[predecessor["regulatory_document_id"]]
        successor_document = documents[successor["regulatory_document_id"]]
        self.assertEqual(predecessor_document["status"], "revoked")
        self.assertEqual(
            predecessor_document["superseded_by"], [successor_document["document_id"]]
        )
        self.assertEqual(
            successor_document["supersedes"], [predecessor_document["document_id"]]
        )


if __name__ == "__main__":
    unittest.main()
