import tempfile
import unittest
from pathlib import Path

from src.product_facts import (
    DECLARED_ORIGIN_LABELS,
    extract_product_facts,
    load_product_facts,
    normalize_fact_value,
    present_declared_origin,
)
from src.runtime import write_json


class ProductFactExtractionTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "product"
        self.root.mkdir(parents=True)
        self.snapshot_id = "ps_fixture"
        write_json(self.root / "meta.json", {"productName": "普通测试商品"})

    def tearDown(self):
        self.temporary.cleanup()

    def _dom(self, text: str) -> None:
        (self.root / "dom_text.txt").write_text(text, encoding="utf-8")

    def _ocr(self, lines: list[dict], *, name: str = "original_001") -> None:
        text_path = self.root / "ocr" / f"{name}.txt"
        text_path.parent.mkdir(parents=True, exist_ok=True)
        text_path.write_text("\n".join(str(item["text"]) for item in lines), encoding="utf-8")
        write_json(self.root / "ocr" / f"{name}.json", {"lines": lines})
        write_json(
            self.root / "ocr" / "manifest.json",
            [
                {
                    "status": "success",
                    "textPath": f"ocr/{name}.txt",
                    "jsonPath": f"ocr/{name}.json",
                    "sourcePath": f"images/original/{name}.jpg",
                }
            ],
        )

    def _extract(self):
        return extract_product_facts(
            self.root,
            self.snapshot_id,
            generated_at="2026-09-12T12:00:00+08:00",
        )

    def test_a_strong_dom_labels_are_accepted_only_in_parameter_section(self):
        for label in DECLARED_ORIGIN_LABELS:
            for separator in ("：", " "):
                with self.subTest(label=label, separator=separator):
                    self._dom(f"参数信息\n{label}{separator}河北省\n图文详情")
                    payload = self._extract()
                    self.assertEqual(
                        [item["normalizedValue"] for item in payload["facts"]],
                        ["河北省"],
                    )
                    self.assertEqual(payload["facts"][0]["sourceType"], "dom_parameter")

    def test_b_dom_value_before_label_preserves_province_suffix(self):
        self._dom("参数信息\n中国大陆\n产地\n测试品牌\n品牌\n图文详情")
        facts = self._extract()["facts"]
        self.assertEqual(facts[0]["normalizedValue"], "中国大陆")
        self.assertEqual(facts[0]["extractionMethod"], "dom_parameter_value_before_label")
        self.assertEqual(normalize_fact_value(" 河北省。 "), "河北省")

    def test_c_ocr_same_line_key_value_is_accepted(self):
        self._dom("参数信息\n品牌\n测试品牌\n图文详情")
        self._ocr([{"lineIndex": 0, "text": "产地：河北邢台", "box": [10, 10, 150, 40]}])
        facts = self._extract()["facts"]
        self.assertEqual(facts[0]["normalizedValue"], "河北邢台")
        self.assertEqual(facts[0]["sourceType"], "ocr_detail_image")

    def test_d_ocr_adjacent_value_requires_proven_geometry(self):
        self._dom("参数信息\n品牌\n测试品牌\n图文详情")
        self._ocr(
            [
                {"lineIndex": 0, "text": "商品产地", "box": [10, 10, 90, 40]},
                {"lineIndex": 1, "text": "云南省", "box": [10, 46, 90, 76]},
                {"lineIndex": 2, "text": "净含量", "box": [10, 120, 90, 150]},
            ]
        )
        facts = self._extract()["facts"]
        self.assertEqual(facts[0]["normalizedValue"], "云南省")
        self.assertEqual(facts[0]["extractionMethod"], "ocr_labeled_adjacent_next_row")

    def test_e_same_value_from_dom_and_ocr_retains_two_sources(self):
        self._dom("参数信息\n产地：中国大陆\n图文详情")
        self._ocr([{"lineIndex": 0, "text": "产品产地：中国大陆", "box": [10, 10, 180, 40]}])
        payload = self._extract()
        presentation = present_declared_origin(payload["facts"])
        self.assertEqual(len(payload["facts"]), 2)
        self.assertEqual(presentation["state"], "single")
        self.assertEqual(presentation["values"], ["中国大陆"])
        self.assertEqual(len(presentation["sources"]), 2)

    def test_f_conflicting_explicit_values_are_not_arbitrated(self):
        self._dom("参数信息\n产地：中国大陆\n图文详情")
        self._ocr([{"lineIndex": 0, "text": "产地：河北邢台", "box": [10, 10, 180, 40]}])
        presentation = present_declared_origin(self._extract()["facts"])
        self.assertEqual(presentation["state"], "conflict")
        self.assertEqual(presentation["values"], ["中国大陆", "河北邢台"])

    def test_g_no_valid_source_projects_none_without_placeholder_fact(self):
        self._dom("参数信息\n品牌\n测试品牌\n图文详情")
        presentation = present_declared_origin(self._extract()["facts"])
        self.assertEqual(presentation, {"state": "none", "values": [], "sources": []})

    def test_h_title_only_origin_wording_is_rejected_with_diagnostic(self):
        write_json(self.root / "meta.json", {"productName": "云南特产酸枣仁"})
        self._dom("参数信息\n品牌\n测试品牌\n图文详情")
        payload = self._extract()
        self.assertEqual(payload["facts"], [])
        self.assertIn("title_not_authoritative", {item["code"] for item in payload["diagnostics"]})

    def test_i_ugc_or_qa_origin_wording_is_not_a_dom_fact(self):
        self._dom("用户评价\n产地：云南省\n问大家\n参数信息\n品牌\n测试品牌\n图文详情")
        payload = self._extract()
        self.assertEqual(payload["facts"], [])
        self.assertIn("unstructured_origin_mention", {item["code"] for item in payload["diagnostics"]})

    def test_j_shipping_manufacturer_warehouse_and_raw_material_are_excluded(self):
        self._dom(
            "参数信息\n发货地址：杭州\n商家所在地：南京\n生产厂家地址：安徽亳州\n"
            "企业注册地址：合肥\n仓库地址：上海\n原材料产地：云南\n"
            "药材产地：甘肃\n原料来源地：四川\n图文详情"
        )
        payload = self._extract()
        self.assertEqual(payload["facts"], [])
        self.assertGreaterEqual(
            sum(item["code"] == "excluded_origin_field" for item in payload["diagnostics"]),
            8,
        )

    def test_k_isolated_ocr_place_or_marketing_phrase_is_rejected(self):
        self._dom("参数信息\n品牌\n测试品牌\n图文详情")
        self._ocr(
            [
                {"lineIndex": 0, "text": "云南特产", "box": [10, 10, 100, 40]},
                {"lineIndex": 1, "text": "河北邢台", "box": [10, 50, 100, 80]},
            ]
        )
        self.assertEqual(self._extract()["facts"], [])

    def test_l_corrupt_ocr_source_does_not_block_valid_dom_or_stable_ids(self):
        self._dom("参数信息\n原产地：安徽省\n图文详情")
        ocr = self.root / "ocr"
        ocr.mkdir()
        (ocr / "broken.txt").write_text("产地：云南省", encoding="utf-8")
        (ocr / "broken.json").write_text("not-json", encoding="utf-8")
        write_json(
            ocr / "manifest.json",
            [{"status": "success", "textPath": "ocr/broken.txt", "jsonPath": "ocr/broken.json"}],
        )
        first = self._extract()
        first_id = first["facts"][0]["factId"]
        second = extract_product_facts(
            self.root,
            self.snapshot_id,
            generated_at="2026-09-12T13:00:00+08:00",
        )
        self.assertEqual(second["facts"][0]["factId"], first_id)
        self.assertIn("source_read_error", {item["code"] for item in second["diagnostics"]})
        self.assertEqual(
            load_product_facts(
                self.root / "product_facts.json",
                expected_snapshot_id=self.snapshot_id,
            )[0]["normalizedValue"],
            "安徽省",
        )


if __name__ == "__main__":
    unittest.main()
