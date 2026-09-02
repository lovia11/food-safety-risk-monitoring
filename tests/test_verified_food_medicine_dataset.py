import json
import tempfile
import threading
import unittest
from collections import Counter
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

from src.data_store import DataStore
from src.local_api import create_handler
from src.runtime import read_json
from src.task_runtime import TaskManager, TaskValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_CONFIG = PROJECT_ROOT / "config" / "monitor_targets.reference.json"
DEVELOPMENT_CONFIG = PROJECT_ROOT / "config" / "monitor_targets.development.json"

BASE_2002_URL = (
    "https://www.nhc.gov.cn/wjw/gfxwj/200203/"
    "5e9768a72af64db89acb45fe30a810af.shtml"
)
ADD_2019_URL = (
    "https://www.nhc.gov.cn/wjw/c100175/202001/"
    "60977058ce3b4449b1b1d46cff283e73.shtml"
)
ADD_2023_URL = (
    "https://www.nhc.gov.cn/sps/c100088/202311/"
    "5b062dd13fe646198b56c7d76a99aab4.shtml"
)
ADD_2024_URL = (
    "https://www.nhc.gov.cn/sps/c100088/202408/"
    "53150d0918ec40899b5293147ec0dd01.shtml"
)
TOTAL_2025_URL = (
    "https://www.nhc.gov.cn/wjw/jiany/202508/"
    "952b2b3fac1244a389c43182c58380be.shtml"
)

EXPECTED_GROUPS = {
    BASE_2002_URL: [
        "丁香", "八角茴香", "刀豆", "小茴香", "小蓟", "山药", "山楂",
        "马齿苋", "乌梢蛇", "乌梅", "木瓜", "火麻仁", "代代花", "玉竹",
        "甘草", "白芷", "白果", "白扁豆", "白扁豆花", "龙眼肉（桂圆）",
        "决明子", "百合", "肉豆蔻", "肉桂", "余甘子", "佛手",
        "杏仁（甜、苦）", "沙棘", "牡蛎", "芡实", "花椒", "赤小豆",
        "阿胶", "鸡内金", "麦芽", "昆布", "枣（大枣、酸枣、黑枣）",
        "罗汉果", "郁李仁", "金银花", "青果", "鱼腥草", "姜（生姜、干姜）",
        "枳椇子", "枸杞子", "栀子", "砂仁", "胖大海", "茯苓", "香橼",
        "香薷", "桃仁", "桑叶", "桑椹", "桔红", "桔梗", "益智仁",
        "荷叶", "莱菔子", "莲子", "高良姜", "淡竹叶", "淡豆豉", "菊花",
        "菊苣", "黄芥子", "黄精", "紫苏", "紫苏籽", "葛根", "黑芝麻",
        "黑胡椒", "槐米", "槐花", "蒲公英", "蜂蜜", "榧子", "酸枣仁",
        "鲜白茅根", "鲜芦根", "蝮蛇", "橘皮", "薄荷", "薏苡仁", "薤白",
        "覆盆子", "藿香",
    ],
    ADD_2019_URL: ["当归", "山柰", "西红花", "草果", "姜黄", "荜茇"],
    ADD_2023_URL: [
        "党参", "肉苁蓉（荒漠）", "铁皮石斛", "西洋参", "黄芪", "灵芝",
        "山茱萸", "天麻", "杜仲叶",
    ],
    ADD_2024_URL: ["地黄", "麦冬", "天冬", "化橘红"],
}

EXPECTED_DATES = {
    BASE_2002_URL: "2002-02-28",
    ADD_2019_URL: "2019-11-25",
    ADD_2023_URL: "2023-11-09",
    ADD_2024_URL: "2024-08-12",
}


class VerifiedFoodMedicineDatasetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = read_json(REFERENCE_CONFIG)
        cls.targets = cls.payload["targets"]

    def _new_store(self, root: Path) -> DataStore:
        store = DataStore(root / "data" / "app.db", root / "output")
        store.initialize()
        return store

    def test_dataset_metadata_and_total_are_verified(self):
        self.assertEqual(self.payload["dataset_id"], "food-medicine-reference")
        self.assertEqual(self.payload["dataset_version"], "2024.08")
        self.assertEqual(self.payload["dataset_status"], "verified_reference")
        self.assertEqual(self.payload["source_reference"], TOTAL_2025_URL)
        self.assertEqual(len(self.targets), 106)

    def test_four_official_groups_have_exact_names_and_order(self):
        for source_reference, expected_names in EXPECTED_GROUPS.items():
            with self.subTest(source_reference=source_reference):
                actual_names = [
                    target["standard_name"]
                    for target in self.targets
                    if target["source_reference"] == source_reference
                ]
                self.assertEqual(actual_names, expected_names)

    def test_source_group_counts_are_87_6_9_4(self):
        counts = Counter(target["source_reference"] for target in self.targets)
        self.assertEqual(
            [counts[url] for url in EXPECTED_GROUPS],
            [87, 6, 9, 4],
        )

    def test_ids_types_and_names_are_valid_and_unique(self):
        target_ids = [target["target_id"] for target in self.targets]
        names = [target["standard_name"] for target in self.targets]
        self.assertEqual(len(set(target_ids)), 106)
        self.assertEqual(len(set(names)), 106)
        self.assertTrue(all(target["target_type"] == "food_medicine" for target in self.targets))
        self.assertTrue(all(target["dataset_id"] == self.payload["dataset_id"] for target in self.targets))

    def test_every_target_has_its_first_inclusion_provenance(self):
        for target in self.targets:
            with self.subTest(target_id=target["target_id"]):
                source_reference = target["source_reference"]
                self.assertIn(source_reference, EXPECTED_GROUPS)
                self.assertTrue(target["source_name"].strip())
                self.assertEqual(target["source_date"], EXPECTED_DATES[source_reference])

    def test_only_search_validated_pilots_are_enabled_and_nonpilots_are_queryless(self):
        pilot_targets = [target for target in self.targets if target["queries"]]
        self.assertEqual(len(pilot_targets), 6)
        self.assertEqual(sum(len(target["queries"]) for target in pilot_targets), 9)
        self.assertEqual(
            {target["standard_name"] for target in self.targets if target["enabled"]},
            {"酸枣仁", "茯苓", "龙眼肉（桂圆）", "铁皮石斛", "化橘红"},
        )
        self.assertTrue(
            all(
                query["validation_status"] == "search_validated"
                for target in pilot_targets
                for query in target["queries"]
            )
        )
        danggui = next(target for target in pilot_targets if target["standard_name"] == "当归")
        self.assertFalse(danggui["enabled"])
        self.assertFalse(danggui["queries"][0]["enabled"])
        self.assertIn("仅作为香辛料和调味品使用", self.payload["description"])

    def test_development_seed_is_independent_and_acid_jujube_is_not_overwritten(self):
        development = read_json(DEVELOPMENT_CONFIG)
        development_target = development["targets"][0]
        reference_target = next(
            target for target in self.targets if target["standard_name"] == "酸枣仁"
        )
        self.assertEqual(development["dataset_status"], "development_seed")
        self.assertNotEqual(development["dataset_id"], self.payload["dataset_id"])
        self.assertNotEqual(development_target["target_id"], reference_target["target_id"])
        self.assertEqual(len(development_target["queries"]), 2)
        self.assertEqual(
            [query["query_text"] for query in reference_target["queries"]],
            ["酸枣仁", "酸枣仁茶"],
        )
        self.assertTrue(all(query["enabled"] for query in reference_target["queries"]))

    def test_reference_import_is_idempotent_and_sqlite_has_106_targets(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = self._new_store(Path(temporary))
            first = store.import_monitor_config(REFERENCE_CONFIG)
            first_counts = store.table_counts()
            second = store.import_monitor_config(REFERENCE_CONFIG)
            self.assertEqual(first, {"datasets": 1, "targets": 106, "queries": 9})
            self.assertEqual(second, first)
            self.assertEqual(store.table_counts(), first_counts)
            self.assertEqual(len(store.list_monitor_targets()), 106)

    def test_sqlite_keeps_development_queries_separate(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = self._new_store(Path(temporary))
            store.import_monitor_config(DEVELOPMENT_CONFIG)
            store.import_monitor_config(REFERENCE_CONFIG)
            targets = store.list_monitor_targets()
            formal = [
                target
                for target in targets
                if target["dataset_status"] == "verified_reference"
            ]
            development = [
                target
                for target in targets
                if target["dataset_status"] == "development_seed"
            ]
            self.assertEqual(len(formal), 106)
            self.assertEqual(len(development), 1)
            self.assertEqual(store.table_counts()["search_queries"], 11)

    def test_api_exposes_provenance_and_hides_disabled_targets_from_task_list(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = self._new_store(root)
            store.import_monitor_config(DEVELOPMENT_CONFIG)
            store.import_monitor_config(REFERENCE_CONFIG)
            web_root = root / "web"
            web_root.mkdir()
            (web_root / "index.html").write_text("ok", encoding="utf-8")
            manager = TaskManager(root / "output")
            server = ThreadingHTTPServer(
                ("127.0.0.1", 0),
                create_handler(
                    root / "output",
                    web_root,
                    manager,
                    data_store=store,
                    monitor_config=None,
                ),
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                with urlopen(f"{base}/api/monitor-targets") as response:
                    listed = json.load(response)
                self.assertEqual(listed["count"], 6)
                self.assertEqual(
                    {target["standard_name"] for target in listed["targets"]},
                    {"酸枣仁", "茯苓", "龙眼肉（桂圆）", "铁皮石斛", "化橘红"},
                )
                self.assertIn(
                    "dev-food-medicine-suanzaoren",
                    {target["target_id"] for target in listed["targets"]},
                )
                self.assertNotIn(
                    "food-medicine-2019-001",
                    {target["target_id"] for target in listed["targets"]},
                )
                with urlopen(
                    f"{base}/api/monitor-targets/food-medicine-2002-078"
                ) as response:
                    target = json.load(response)
                self.assertEqual(target["standard_name"], "酸枣仁")
                self.assertEqual(target["source_reference"], BASE_2002_URL)
                self.assertEqual(target["queries"][0]["query_source"], "standard_name")
                self.assertIn(
                    target["queries"][0]["validation_status"],
                    {"search_validated"},
                )
                self.assertEqual(target["dataset"]["dataset_version"], "2024.08")
                self.assertEqual(
                    target["dataset"]["dataset_status"], "verified_reference"
                )
                self.assertIn("106", target["dataset"]["description"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(2)

    def test_queryless_disabled_target_is_rejected_safely_by_task_runtime(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = self._new_store(root)
            store.import_monitor_config(REFERENCE_CONFIG)
            manager = TaskManager(
                root / "output",
                monitor_target_provider=store.get_monitor_target,
            )
            with self.assertRaisesRegex(TaskValidationError, "不存在或未启用"):
                manager.create_task(
                    {
                        "task_type": "monitor",
                        "target_id": "food-medicine-2002-001",
                        "per_query_candidate_limit": 10,
                        "detail_limit": 2,
                    }
                )
            self.assertEqual(list((root / "output").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
