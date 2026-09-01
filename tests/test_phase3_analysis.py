import json
import tempfile
import unittest
from pathlib import Path

from src.phase3_analysis import (
    TextUnit,
    build_analysis,
    evidence_origin_note,
    match_units,
    parse_dom_units,
    run_analysis,
)


CONFIG = {
    "version": 1,
    "effect_categories": {
        "助眠": ["睡眠", "催眠", "失眠"],
        "男性相关": ["补肾"],
    },
}


class PhaseThreeRulesTest(unittest.TestCase):
    def test_dom_attribution_and_recommendation_exclusion(self):
        text = "\n".join(
            [
                "用户评价",
                "本店推荐",
                "用户评价·2",
                "对睡眠有帮助",
                "查看全部评价",
                "问大家·1",
                "催眠神器",
                "查看全部问答",
                "图文详情",
                "本店推荐",
                "其他商品补肾",
                "其他商品治疗失眠",
            ]
        )
        included, excluded = parse_dom_units(text)
        sleep = next(unit for unit in included if "睡眠" in unit.text)
        hypnosis = next(unit for unit in included if "催眠" in unit.text)
        self.assertEqual(sleep.source_type, "dom_user_review")
        self.assertEqual(hypnosis.source_type, "dom_qa")
        self.assertTrue(all(unit.source_type == "dom_recommendation" for unit in excluded))
        self.assertFalse(any("补肾" in unit.text for unit in included))

    def test_match_units_keeps_source_and_all_keywords(self):
        units = [TextUnit("dom_qa", "dom_text.txt", 8, "改善睡眠的催眠神器")]
        matches = match_units(units, CONFIG["effect_categories"])
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["effect"], "助眠")
        self.assertEqual(matches[0]["matched_keywords"], ["睡眠", "催眠"])
        self.assertEqual(matches[0]["content_origin"], "user_generated")
        self.assertIn("用户生成内容", evidence_origin_note(matches))

    def test_origin_note_handles_seller_and_mixed_sources(self):
        seller = [{"content_origin": "seller_managed"}]
        mixed = seller + [{"content_origin": "user_generated"}]
        self.assertIn("商品标题", evidence_origin_note(seller))
        self.assertIn("同时包含", evidence_origin_note(mixed))

    def test_realistic_fixture_outputs_only_in_scope_effect(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_root = Path(temporary) / "run"
            product_root = run_root / "products" / "123"
            ocr_root = product_root / "ocr"
            ocr_root.mkdir(parents=True)
            config_path = Path(temporary) / "keywords.json"
            config_path.write_text(
                json.dumps(CONFIG, ensure_ascii=False), encoding="utf-8"
            )
            (product_root / "meta.json").write_text(
                json.dumps(
                    {
                        "productId": "123",
                        "productName": "酸枣仁膏",
                        "productUrl": "https://example.invalid/?id=123",
                        "keyword": "酸枣仁",
                        "shopName": "测试店",
                        "region": "",
                        "imageCount": 1,
                        "screenshots": ["page/overview.png"],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (product_root / "dom_text.txt").write_text(
                "用户评价·1\n对睡眠有帮助\n查看全部评价\n本店推荐\n补肾商品\n¥99.00\n10人付款",
                encoding="utf-8",
            )
            (ocr_root / "original_001.txt").write_text("配料表", encoding="utf-8")
            (ocr_root / "manifest.json").write_text(
                json.dumps(
                    [
                        {
                            "status": "success",
                            "textPath": "ocr/original_001.txt",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            analysis, _, _ = build_analysis(product_root, config_path)
            self.assertEqual(analysis["detected_effects"], ["助眠"])
            self.assertEqual(analysis["evidence"], ["对睡眠有帮助"])
            self.assertEqual(
                analysis["evidence_origin_counts"], {"user_generated": 1}
            )
            self.assertEqual(
                analysis["excluded_evidence"][0]["effect"], "男性相关"
            )
            self.assertTrue(analysis["review_required"])

            outputs = run_analysis(product_root, config_path)
            self.assertTrue(all(path.exists() for path in outputs.values()))
            products = json.loads(outputs["products_json"].read_text(encoding="utf-8"))
            self.assertEqual(products["products"][0]["detected_effects"], ["助眠"])


if __name__ == "__main__":
    unittest.main()
