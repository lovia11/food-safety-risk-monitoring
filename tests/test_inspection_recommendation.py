import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.data_store import DataStore
from src.inspection_applicability import ProductInspectionContext
from src.inspection_recommendation import (
    DISCLAIMER,
    REGULATORY_CONTEXT_NOTE,
    InspectionRecommendationBuilder,
    ProductInspectionRecommendationResult,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INSPECTION_REFERENCE_CONFIG = PROJECT_ROOT / "config" / "inspection_reference.json"
RISK_REFERENCE_CONFIG = PROJECT_ROOT / "config" / "risk_substance_reference.json"

SIBUTRAMINE_ID = "substance-cas-106650-56-0"
MELATONIN_ID = "substance-cas-73-31-4"
WEIGHT_LOSS_GROUP_MAPPING_ID = "weight-loss-sibutramine-group-cn-2025"


def evidence(
    effect: str,
    keywords: list[str],
    *,
    text: str | None = None,
    content_origin: str = "seller_managed",
    line_number: int = 1,
) -> dict:
    user_generated = content_origin == "user_generated"
    return {
        "effect": effect,
        "text": text or "、".join(keywords),
        "matched_keywords": keywords,
        "source_type": "dom_qa" if user_generated else "dom_product",
        "source_label": "用户问答" if user_generated else "当前商品 DOM",
        "content_origin": content_origin,
        "source_path": "dom_text.txt",
        "line_number": line_number,
    }


def analysis(*items: dict, include_identity: bool = True) -> dict:
    payload = {
        "detected_effects": list(dict.fromkeys(item["effect"] for item in items)),
        "evidence_details": list(items),
    }
    if include_identity:
        payload.update(
            {
                "product_id": "product-123",
                "product_name": "测试减肥饼干",
                "product_url": "https://item.example/product-123",
            }
        )
    return payload


def product_context(
    *,
    product_category: str | None = "饼干",
    product_form: str | None = "饼干",
    ingredients: list[str] | None = None,
) -> ProductInspectionContext:
    return ProductInspectionContext(
        product_category=product_category,
        product_form=product_form,
        confirmed_ingredient_contexts=ingredients or [],
        context_evidence=[
            {
                "field": "product_category",
                "value": product_category,
                "source_type": "seller_managed",
                "source_path": "confirmed-context.json",
                "text": "调用者确认的结构化商品上下文",
            }
        ],
    )


class InspectionRecommendationBuilderTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.store = DataStore(root / "data" / "app.db", root / "output")
        self.store.initialize()
        self.store.import_inspection_config(INSPECTION_REFERENCE_CONFIG)
        self.store.import_risk_substance_config(RISK_REFERENCE_CONFIG)
        self.builder = InspectionRecommendationBuilder(self.store)

    def tearDown(self):
        self.temporary.cleanup()

    def _execute(self, sql: str, parameters: tuple = ()) -> None:
        with sqlite3.connect(self.store.database_path) as connection:
            connection.execute(sql, parameters)

    def _build_weight_loss(
        self,
        *,
        origin: str = "seller_managed",
        context: ProductInspectionContext | None = None,
        keywords: list[str] | None = None,
    ) -> ProductInspectionRecommendationResult:
        return self.builder.build(
            analysis(
                evidence(
                    "减脂",
                    keywords or ["减肥"],
                    text="页面宣称帮助减肥",
                    content_origin=origin,
                )
            ),
            context or product_context(),
        )

    @staticmethod
    def _finding(result, risk_category: str = "weight_loss") -> dict:
        return next(
            item
            for item in result.risk_findings
            if item["risk_category"] == risk_category
        )

    @classmethod
    def _follow_up(cls, result, substance_id: str = SIBUTRAMINE_ID) -> dict:
        finding = cls._finding(result)
        return next(
            item
            for item in finding["substance_follow_ups"]
            if item["substance_id"] == substance_id
        )

    def test_product_identity_is_preserved_from_analysis(self):
        result = self._build_weight_loss()

        self.assertEqual(result.product_id, "product-123")
        self.assertEqual(result.product_name, "测试减肥饼干")
        self.assertEqual(result.product_url, "https://item.example/product-123")

    def test_missing_product_identity_uses_empty_strings(self):
        result = self.builder.build(
            analysis(
                evidence("减脂", ["减肥"]),
                include_identity=False,
            ),
            product_context(),
        )

        self.assertEqual(result.product_id, "")
        self.assertEqual(result.product_name, "")
        self.assertEqual(result.product_url, "")

    def test_seller_evidence_qualification_is_primary(self):
        finding = self._finding(self._build_weight_loss())

        self.assertEqual(
            finding["evidence_qualification"], "seller_managed_primary"
        )

    def test_ugc_only_evidence_is_auxiliary_and_never_suggests_testing(self):
        result = self._build_weight_loss(origin="user_generated")
        finding = self._finding(result)
        follow_up = self._follow_up(result)

        self.assertEqual(
            finding["evidence_qualification"],
            "user_generated_auxiliary_only",
        )
        self.assertEqual(follow_up["follow_up_status"], "auxiliary_evidence_only")
        self.assertEqual(follow_up["suggested_methods"], [])
        self.assertTrue(follow_up["other_known_methods"])
        self.assertIn("用户生成内容", follow_up["reason"])

    def test_mixed_seller_and_ugc_evidence_uses_primary_qualification(self):
        seller = evidence("减脂", ["减肥"], text="商家页面减肥", line_number=2)
        ugc = evidence(
            "减脂",
            ["减肥"],
            text="用户评论减肥",
            content_origin="user_generated",
            line_number=8,
        )
        result = self.builder.build(
            analysis(seller, ugc),
            product_context(),
        )
        finding = self._finding(result)

        self.assertEqual(
            finding["evidence_qualification"], "seller_managed_primary"
        )
        self.assertEqual(len(finding["trigger_evidence"]), 2)
        self.assertEqual(
            {item["content_origin"] for item in finding["trigger_evidence"]},
            {"seller_managed", "user_generated"},
        )
        self.assertEqual(
            self._follow_up(result)["follow_up_status"], "suggest_testing"
        )

    def test_real_weight_loss_chain_suggests_sibutramine_testing(self):
        result = self._build_weight_loss()
        finding = self._finding(result)
        follow_up = self._follow_up(result)

        self.assertEqual(finding["risk_labels"], ["减肥/减重宣传"])
        self.assertEqual(follow_up["canonical_name"], "西布曲明")
        self.assertEqual(follow_up["follow_up_status"], "suggest_testing")
        self.assertEqual(
            [item["method_id"] for item in follow_up["suggested_methods"]],
            ["bjs-201701"],
        )

    def test_suggested_bjs_201701_keeps_method_and_source_facts(self):
        method = self._follow_up(self._build_weight_loss())["suggested_methods"][0]

        self.assertEqual(
            {
                key: method[key]
                for key in (
                    "method_id",
                    "method_no",
                    "method_name",
                    "method_type",
                    "method_status",
                    "determination_role",
                    "applicability_status",
                )
            },
            {
                "method_id": "bjs-201701",
                "method_no": "BJS 201701",
                "method_name": "食品中西布曲明等化合物的测定",
                "method_type": "supplementary_bjs",
                "method_status": "current",
                "determination_role": "qualitative",
                "applicability_status": "applicable",
            },
        )
        self.assertEqual(
            method["matched_applicability_ids"], ["bjs-201701-scope-02"]
        )
        self.assertTrue(method["source_name"])
        self.assertTrue(method["source_reference"])
        self.assertEqual(method["source_date"], "2017-02-28")

    def test_unknown_context_requires_review_and_does_not_suggest_testing(self):
        result = self._build_weight_loss(
            context=product_context(product_category=None, product_form=None)
        )
        follow_up = self._follow_up(result)

        self.assertEqual(follow_up["follow_up_status"], "needs_context_review")
        self.assertEqual(follow_up["suggested_methods"], [])
        self.assertEqual(
            {item["method_id"] for item in follow_up["methods_needing_context"]},
            {"bjs-201701", "bjs-201710"},
        )
        self.assertIn("人工确认商品类别、剂型", follow_up["reason"])

    def test_conditional_current_method_remains_conditional_and_is_suggested(self):
        result = self._build_weight_loss(
            context=product_context(
                product_category="其他低糖、低脂、低蛋白类基质",
                product_form="其他剂型",
            )
        )
        follow_up = self._follow_up(result)
        method = follow_up["suggested_methods"][0]

        self.assertEqual(follow_up["follow_up_status"], "suggest_testing")
        self.assertEqual(method["method_id"], "bjs-201701")
        self.assertEqual(method["applicability_status"], "conditional")
        self.assertEqual(
            method["conditional_applicability_ids"], ["bjs-201701-scope-04"]
        )
        self.assertNotIn("完全适用", follow_up["reason"])

    def test_not_applicable_method_is_kept_out_of_suggested_methods(self):
        follow_up = self._follow_up(self._build_weight_loss())

        self.assertNotIn(
            "bjs-201710",
            {item["method_id"] for item in follow_up["suggested_methods"]},
        )
        bjs_201710 = next(
            item
            for item in follow_up["other_known_methods"]
            if item["method_id"] == "bjs-201710"
        )
        self.assertEqual(bjs_201710["applicability_status"], "not_applicable")

    def test_superseded_applicable_method_is_only_other_known(self):
        self._execute(
            "UPDATE inspection_methods SET method_status = 'superseded' "
            "WHERE method_id = 'bjs-201701'"
        )
        follow_up = self._follow_up(self._build_weight_loss())
        bjs_201701 = next(
            item
            for item in follow_up["other_known_methods"]
            if item["method_id"] == "bjs-201701"
        )

        self.assertEqual(follow_up["follow_up_status"], "no_applicable_verified_method")
        self.assertEqual(follow_up["suggested_methods"], [])
        self.assertEqual(bjs_201701["method_status"], "superseded")
        self.assertEqual(bjs_201701["applicability_status"], "applicable")

    def test_composition_gap_blocks_suggestion_but_keeps_known_methods(self):
        self._execute(
            "DELETE FROM risk_substance_mappings WHERE mapping_id = ?",
            (WEIGHT_LOSS_GROUP_MAPPING_ID,),
        )
        result = self._build_weight_loss()
        follow_up = self._follow_up(result)

        self.assertEqual(len(result.composition_gaps), 1)
        self.assertEqual(follow_up["follow_up_status"], "knowledge_integrity_gap")
        self.assertEqual(follow_up["suggested_methods"], [])
        self.assertIn(
            "bjs-201701",
            {item["method_id"] for item in follow_up["other_known_methods"]},
        )

    def test_composition_gap_has_priority_over_ugc_auxiliary_status(self):
        self._execute(
            "DELETE FROM risk_substance_mappings WHERE mapping_id = ?",
            (WEIGHT_LOSS_GROUP_MAPPING_ID,),
        )
        follow_up = self._follow_up(
            self._build_weight_loss(origin="user_generated")
        )

        self.assertEqual(follow_up["follow_up_status"], "knowledge_integrity_gap")

    def test_unresolved_group_does_not_block_known_substance_follow_up(self):
        result = self._build_weight_loss()
        finding = self._finding(result)

        self.assertEqual(finding["group_targets"][0]["resolution_status"], "partial")
        self.assertIn(
            "unresolved_group",
            {gap["type"] for gap in result.knowledge_gaps},
        )
        self.assertEqual(
            self._follow_up(result)["follow_up_status"], "suggest_testing"
        )

    def test_substance_without_method_has_no_applicable_method_status_and_gap(self):
        self._execute(
            "DELETE FROM inspection_method_substances WHERE substance_id = ?",
            (SIBUTRAMINE_ID,),
        )
        result = self._build_weight_loss()
        follow_up = self._follow_up(result)

        self.assertEqual(
            follow_up["follow_up_status"], "no_applicable_verified_method"
        )
        self.assertEqual(follow_up["suggested_methods"], [])
        self.assertEqual(follow_up["methods_needing_context"], [])
        self.assertEqual(follow_up["other_known_methods"], [])
        self.assertIn(
            "no_verified_method",
            {gap["type"] for gap in result.knowledge_gaps},
        )

    def test_unmapped_evidence_is_preserved_alongside_recommendation(self):
        result = self._build_weight_loss(keywords=["减肥", "燃脂"])

        self.assertEqual(len(result.risk_findings), 1)
        self.assertEqual(len(result.unmapped_evidence), 1)
        self.assertEqual(result.unmapped_evidence[0]["unmapped_keywords"], ["燃脂"])
        self.assertEqual(
            self._follow_up(result)["follow_up_status"], "suggest_testing"
        )

    def test_trigger_evidence_is_preserved_completely(self):
        item = evidence(
            "减脂",
            ["减肥"],
            text="评论说能够减肥",
            content_origin="user_generated",
            line_number=17,
        )
        finding = self._finding(
            self.builder.build(analysis(item), product_context())
        )

        self.assertEqual(
            finding["trigger_evidence"][0],
            {**item, "bridge_matched_keywords": ["减肥"]},
        )

    def test_regulatory_context_is_preserved_with_fixed_review_note(self):
        self._execute(
            "UPDATE risk_substance_mappings SET substance_id = ? "
            "WHERE mapping_id = 'weight-loss-sibutramine-cn-2025'",
            (MELATONIN_ID,),
        )
        result = self._build_weight_loss(
            context=product_context(
                product_category="保健食品",
                product_form="片剂",
            )
        )
        follow_up = self._follow_up(result, MELATONIN_ID)

        self.assertEqual(len(follow_up["regulatory_contexts"]), 1)
        self.assertEqual(
            follow_up["regulatory_contexts"][0]["context_status"],
            "legal_health_food_raw_material",
        )
        self.assertNotIn("legal", follow_up["regulatory_contexts"][0])
        self.assertEqual(
            follow_up["regulatory_context_note"], REGULATORY_CONTEXT_NOTE
        )

    def test_regulatory_context_does_not_change_follow_up_status(self):
        self._execute(
            "UPDATE risk_substance_mappings SET substance_id = ? "
            "WHERE mapping_id = 'weight-loss-sibutramine-cn-2025'",
            (MELATONIN_ID,),
        )
        context = product_context(
            product_category="保健食品",
            product_form="片剂",
        )
        with_context = self._follow_up(
            self.builder.build(
                analysis(evidence("减脂", ["减肥"])),
                context,
            ),
            MELATONIN_ID,
        )
        self._execute(
            "DELETE FROM substance_regulatory_contexts WHERE substance_id = ?",
            (MELATONIN_ID,),
        )
        without_context = self._follow_up(
            self.builder.build(
                analysis(evidence("减脂", ["减肥"])),
                context,
            ),
            MELATONIN_ID,
        )

        self.assertEqual(
            with_context["follow_up_status"], without_context["follow_up_status"]
        )
        self.assertEqual(without_context["regulatory_contexts"], [])
        self.assertEqual(without_context["regulatory_context_note"], "")

    def test_suggested_methods_have_no_ranking_fields(self):
        suggested = self._follow_up(self._build_weight_loss())["suggested_methods"]
        forbidden = {"priority", "rank", "score", "best"}

        self.assertTrue(suggested)
        for method in suggested:
            self.assertTrue(forbidden.isdisjoint(method))

    def test_one_substance_is_output_once(self):
        follow_ups = self._finding(self._build_weight_loss())[
            "substance_follow_ups"
        ]

        self.assertEqual(
            [item["substance_id"] for item in follow_ups],
            [SIBUTRAMINE_ID],
        )

    def test_multiple_evidence_for_one_risk_outputs_one_finding(self):
        result = self.builder.build(
            analysis(
                evidence("男性相关", ["补肾"], line_number=2),
                evidence("男性相关", ["壮阳"], line_number=9),
            ),
            product_context(product_category="保健食品", product_form="片剂"),
        )

        self.assertEqual(len(result.risk_findings), 1)
        self.assertEqual(result.risk_findings[0]["risk_category"], "male_function")

    def test_risk_substance_and_method_ordering_is_deterministic(self):
        result = self.builder.build(
            analysis(
                evidence("减脂", ["减肥"]),
                evidence("男性相关", ["补肾", "壮阳"]),
            ),
            product_context(product_category="保健食品", product_form="片剂"),
        )

        self.assertEqual(
            [item["risk_category"] for item in result.risk_findings],
            ["male_function", "weight_loss"],
        )
        for finding in result.risk_findings:
            follow_ups = finding["substance_follow_ups"]
            self.assertEqual(
                [item["substance_id"] for item in follow_ups],
                sorted(item["substance_id"] for item in follow_ups),
            )
            for follow_up in follow_ups:
                for field in (
                    "suggested_methods",
                    "methods_needing_context",
                    "other_known_methods",
                ):
                    methods = follow_up[field]
                    self.assertEqual(
                        [(item["method_no"], item["method_id"]) for item in methods],
                        sorted(
                            (item["method_no"], item["method_id"])
                            for item in methods
                        ),
                    )

    def test_disclaimer_is_fixed_and_not_weakened(self):
        result = self._build_weight_loss()

        self.assertEqual(result.disclaimer, DISCLAIMER)
        self.assertIn("仅用于监管抽检辅助筛查", result.disclaimer)
        self.assertIn("不表示商品实际含有上述化合物", result.disclaimer)
        self.assertIn("不构成违法认定或实验室检出结论", result.disclaimer)
        self.assertIn("由检验人员及监管人员确认", result.disclaimer)

    def test_possible_risk_text_uses_regulatory_attention_boundary(self):
        finding = self._finding(self._build_weight_loss())

        self.assertEqual(
            finding["possible_risk_summary"],
            "页面中发现与“减肥/减重宣传”相关的可桥接功效线索，"
            "作为基于页面宣传线索的监管关注方向。",
        )
        self.assertNotIn("非法添加西布曲明风险", finding["possible_risk_summary"])

    def test_output_text_never_claims_detection_or_actual_presence(self):
        result = self._build_weight_loss().to_dict()

        def collect_strings(value):
            if isinstance(value, dict):
                for nested in value.values():
                    yield from collect_strings(nested)
            elif isinstance(value, list):
                for nested in value:
                    yield from collect_strings(nested)
            elif isinstance(value, str):
                yield value

        output_text = "\n".join(collect_strings(result))
        self.assertNotIn("检测出", output_text)
        self.assertNotIn("已检出", output_text)
        self.assertNotIn("商品含有西布曲明", output_text)
        self.assertIn("不表示该商品实际含有上述化合物", output_text)

    def test_output_has_no_numeric_scoring_fields(self):
        result = self._build_weight_loss().to_dict()
        forbidden = {
            "risk_score",
            "confidence",
            "probability",
            "priority_score",
            "recommendation_score",
        }

        def assert_no_forbidden_fields(value):
            if isinstance(value, dict):
                self.assertTrue(forbidden.isdisjoint(value))
                for nested in value.values():
                    assert_no_forbidden_fields(nested)
            elif isinstance(value, list):
                for nested in value:
                    assert_no_forbidden_fields(nested)

        assert_no_forbidden_fields(result)

    def test_result_contract_has_required_top_level_fields(self):
        result = self._build_weight_loss()

        self.assertIsInstance(result, ProductInspectionRecommendationResult)
        self.assertEqual(
            set(result.to_dict()),
            {
                "product_id",
                "product_name",
                "product_url",
                "product_context",
                "risk_findings",
                "unmapped_evidence",
                "composition_gaps",
                "knowledge_gaps",
                "disclaimer",
            },
        )

    def test_schema_version_is_eight(self):
        with sqlite3.connect(self.store.database_path) as connection:
            schema_version = connection.execute("PRAGMA user_version").fetchone()[0]

        self.assertEqual(schema_version, 8)


if __name__ == "__main__":
    unittest.main()
