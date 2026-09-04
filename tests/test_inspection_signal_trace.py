import copy
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.effect_risk_bridge import load_effect_risk_bridge_config
from src.inspection_knowledge import InspectionKnowledgeResolver
from src.inspection_signal_trace import (
    InspectionSignalTraceResolver,
    InspectionSignalTraceResult,
)
from src.data_store import DataStore


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INSPECTION_REFERENCE_CONFIG = PROJECT_ROOT / "config" / "inspection_reference.json"
RISK_REFERENCE_CONFIG = PROJECT_ROOT / "config" / "risk_substance_reference.json"

SIBUTRAMINE_ID = "substance-cas-106650-56-0"
SILDENAFIL_ID = "substance-cas-139755-83-2"
TADALAFIL_ID = "substance-cas-171596-29-5"
WEIGHT_LOSS_GROUP_MAPPING_ID = "weight-loss-sibutramine-group-cn-2025"
MALE_FUNCTION_GROUP_MAPPING_ID = "male-function-nafei-lafei-group-cn-2025"


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


def analysis(*items: dict) -> dict:
    return {
        "detected_effects": list(dict.fromkeys(item["effect"] for item in items)),
        "evidence_details": list(items),
    }


class InspectionSignalTraceResolverTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.store = DataStore(root / "data" / "app.db", root / "output")
        self.store.initialize()
        self.store.import_inspection_config(INSPECTION_REFERENCE_CONFIG)
        self.store.import_risk_substance_config(RISK_REFERENCE_CONFIG)
        self.resolver = InspectionSignalTraceResolver(self.store)

    def tearDown(self):
        self.temporary.cleanup()

    def _execute(self, sql: str, parameters: tuple = ()) -> None:
        with sqlite3.connect(self.store.database_path) as connection:
            connection.execute(sql, parameters)

    def _resolve_weight_loss(self) -> InspectionSignalTraceResult:
        return self.resolver.resolve_analysis(
            analysis(evidence("减脂", ["减肥"], text="帮助减肥"))
        )

    def _resolve_male_function(self) -> InspectionSignalTraceResult:
        return self.resolver.resolve_analysis(
            analysis(evidence("男性相关", ["补肾", "壮阳"], text="补肾壮阳"))
        )

    def test_seller_weight_loss_evidence_produces_one_signal(self):
        result = self._resolve_weight_loss()

        self.assertIsInstance(result, InspectionSignalTraceResult)
        self.assertEqual(result.bridge_id, "phase3-effect-risk-bridge")
        self.assertEqual(result.bridge_version, "2026.09-d2")
        self.assertEqual(len(result.risk_knowledge_signals), 1)
        self.assertEqual(
            result.risk_knowledge_signals[0]["risk_category"], "weight_loss"
        )
        self.assertEqual(result.composition_gaps, [])

    def test_weight_loss_bridge_mapping_ids_are_inherited(self):
        signal = self._resolve_weight_loss().risk_knowledge_signals[0]

        self.assertEqual(signal["bridge_mapping_ids"], ["jianfei-to-weight-loss"])

    def test_weight_loss_reference_mapping_ids_come_from_bridge(self):
        signal = self._resolve_weight_loss().risk_knowledge_signals[0]

        self.assertEqual(
            signal["reference_mapping_ids"], [WEIGHT_LOSS_GROUP_MAPPING_ID]
        )

    def test_weight_loss_trace_has_one_group_and_one_substance(self):
        trace = self._resolve_weight_loss().risk_knowledge_signals[0][
            "knowledge_trace"
        ]

        self.assertEqual(len(trace["group_targets"]), 1)
        self.assertEqual(
            trace["group_targets"][0]["target_group_label"],
            "西布曲明及其系列衍生物",
        )
        self.assertEqual(len(trace["substance_targets"]), 1)
        self.assertEqual(
            trace["substance_targets"][0]["substance_id"], SIBUTRAMINE_ID
        )

    def test_method_chain_remains_a_dynamic_d1_query(self):
        before = self._resolve_weight_loss().risk_knowledge_signals[0][
            "knowledge_trace"
        ]["substance_targets"][0]
        self.assertEqual(
            [method["method_id"] for method in before["inspection_methods"]],
            ["bjs-201701", "bjs-201710"],
        )

        self._execute(
            "DELETE FROM inspection_method_substances "
            "WHERE method_id = 'bjs-201710' AND substance_id = ?",
            (SIBUTRAMINE_ID,),
        )
        after = self._resolve_weight_loss().risk_knowledge_signals[0][
            "knowledge_trace"
        ]["substance_targets"][0]
        self.assertEqual(
            [method["method_id"] for method in after["inspection_methods"]],
            ["bjs-201701"],
        )

    def test_bushen_zhuangyang_produces_one_male_function_signal(self):
        result = self._resolve_male_function()

        self.assertEqual(len(result.risk_knowledge_signals), 1)
        self.assertEqual(
            result.risk_knowledge_signals[0]["risk_category"], "male_function"
        )

    def test_bushen_zhuangyang_retains_two_bridge_mapping_ids(self):
        signal = self._resolve_male_function().risk_knowledge_signals[0]

        self.assertEqual(
            signal["bridge_mapping_ids"],
            ["bushen-to-male-function", "zhuangyang-to-male-function"],
        )

    def test_bushen_zhuangyang_deduplicates_reference_mapping_id(self):
        signal = self._resolve_male_function().risk_knowledge_signals[0]

        self.assertEqual(
            signal["reference_mapping_ids"], [MALE_FUNCTION_GROUP_MAPPING_ID]
        )

    def test_male_function_trace_has_one_group_and_two_substances(self):
        trace = self._resolve_male_function().risk_knowledge_signals[0][
            "knowledge_trace"
        ]

        self.assertEqual(len(trace["group_targets"]), 1)
        self.assertEqual(
            trace["group_targets"][0]["target_group_label"],
            "那非类、拉非类物质",
        )
        self.assertEqual(
            {item["substance_id"] for item in trace["substance_targets"]},
            {SILDENAFIL_ID, TADALAFIL_ID},
        )

    def test_multiple_evidence_units_share_one_risk_knowledge_signal(self):
        result = self.resolver.resolve_analysis(
            analysis(
                evidence("男性相关", ["补肾"], text="补肾配方", line_number=3),
                evidence("男性相关", ["壮阳"], text="壮阳宣传", line_number=8),
            )
        )

        self.assertEqual(len(result.risk_knowledge_signals), 1)
        self.assertEqual(
            len(result.risk_knowledge_signals[0]["trigger_evidence"]), 2
        )

    def test_seller_managed_trigger_provenance_is_preserved(self):
        trigger = self._resolve_weight_loss().risk_knowledge_signals[0][
            "trigger_evidence"
        ][0]

        self.assertEqual(
            trigger,
            {
                **evidence("减脂", ["减肥"], text="帮助减肥"),
                "bridge_matched_keywords": ["减肥"],
            },
        )

    def test_user_generated_trigger_provenance_is_preserved(self):
        item = evidence(
            "减脂",
            ["减肥"],
            text="吃了感觉能减肥",
            content_origin="user_generated",
            line_number=12,
        )
        trigger = self.resolver.resolve_analysis(analysis(item)).risk_knowledge_signals[
            0
        ]["trigger_evidence"][0]

        self.assertEqual(trigger["content_origin"], "user_generated")
        self.assertEqual(trigger["source_type"], "dom_qa")
        self.assertEqual(trigger["source_label"], "用户问答")
        self.assertEqual(trigger["text"], "吃了感觉能减肥")
        self.assertEqual(trigger["line_number"], 12)

    def test_mapped_and_unmapped_keywords_are_both_retained(self):
        result = self.resolver.resolve_analysis(
            analysis(evidence("男性相关", ["补肾", "早泄"], text="补肾早泄"))
        )

        self.assertEqual(len(result.risk_knowledge_signals), 1)
        self.assertEqual(
            result.risk_knowledge_signals[0]["risk_category"], "male_function"
        )
        self.assertEqual(len(result.unmapped_evidence), 1)
        self.assertEqual(result.unmapped_evidence[0]["unmapped_keywords"], ["早泄"])
        self.assertEqual(
            result.unmapped_evidence[0]["reason"], "no_verified_keyword_bridge"
        )

    def test_only_unmapped_evidence_produces_no_knowledge_signal(self):
        result = self.resolver.resolve_analysis(
            analysis(evidence("减脂", ["燃脂"], text="帮助燃脂"))
        )

        self.assertEqual(result.risk_knowledge_signals, [])
        self.assertEqual(result.unmapped_evidence[0]["unmapped_keywords"], ["燃脂"])
        self.assertEqual(result.composition_gaps, [])

    def test_no_evidence_returns_all_empty_result_lists(self):
        result = self.resolver.resolve_analysis(
            {"detected_effects": ["减脂"], "evidence_details": []}
        )

        self.assertEqual(result.risk_knowledge_signals, [])
        self.assertEqual(result.unmapped_evidence, [])
        self.assertEqual(result.composition_gaps, [])

    def test_unknown_effect_does_not_call_knowledge_resolver(self):
        item = evidence("未知功效", ["减肥"], text="未知分类中的减肥")
        with mock.patch.object(
            self.resolver.knowledge_resolver,
            "resolve",
            wraps=self.resolver.knowledge_resolver.resolve,
        ) as resolve:
            result = self.resolver.resolve_analysis(analysis(item))

        resolve.assert_not_called()
        self.assertEqual(result.risk_knowledge_signals, [])
        self.assertEqual(result.unmapped_evidence[0]["effect"], "未知功效")

    def test_d1_knowledge_gaps_and_contract_are_preserved_unchanged(self):
        expected = InspectionKnowledgeResolver(self.store).resolve("weight_loss").to_dict()
        actual = self._resolve_weight_loss().risk_knowledge_signals[0][
            "knowledge_trace"
        ]

        self.assertEqual(actual, expected)
        self.assertEqual(
            [gap["type"] for gap in actual["knowledge_gaps"]],
            ["unresolved_group"],
        )

    def test_include_historical_is_forwarded_to_d1_only(self):
        with mock.patch.object(
            self.resolver.knowledge_resolver,
            "resolve",
            wraps=self.resolver.knowledge_resolver.resolve,
        ) as resolve:
            result = self.resolver.resolve_analysis(
                analysis(evidence("减脂", ["减肥"])),
                include_historical=True,
            )

        resolve.assert_called_once_with("weight_loss", include_historical=True)
        self.assertEqual(result.risk_knowledge_signals[0]["risk_category"], "weight_loss")

    def test_stale_sqlite_keeps_signal_and_substance_but_adds_composition_gap(self):
        self._execute(
            "DELETE FROM risk_substance_mappings WHERE mapping_id = ?",
            (WEIGHT_LOSS_GROUP_MAPPING_ID,),
        )

        result = self._resolve_weight_loss()
        signal = result.risk_knowledge_signals[0]
        self.assertEqual(signal["risk_category"], "weight_loss")
        self.assertEqual(signal["reference_mapping_ids"], [WEIGHT_LOSS_GROUP_MAPPING_ID])
        self.assertEqual(signal["knowledge_trace"]["group_targets"], [])
        self.assertEqual(
            [
                item["substance_id"]
                for item in signal["knowledge_trace"]["substance_targets"]
            ],
            [SIBUTRAMINE_ID],
        )
        self.assertEqual(
            result.composition_gaps,
            [
                {
                    "type": "bridge_reference_not_in_knowledge_trace",
                    "risk_category": "weight_loss",
                    "bridge_mapping_ids": ["jianfei-to-weight-loss"],
                    "reference_mapping_id": WEIGHT_LOSS_GROUP_MAPPING_ID,
                    "message": (
                        "The verified Bridge reference mapping is not present "
                        "in the current SQLite KnowledgeTrace."
                    ),
                }
            ],
        )

    def test_two_bridges_to_one_missing_reference_produce_one_aggregated_gap(self):
        self._execute(
            "DELETE FROM risk_substance_mappings WHERE mapping_id = ?",
            (MALE_FUNCTION_GROUP_MAPPING_ID,),
        )

        result = self._resolve_male_function()

        self.assertEqual(len(result.risk_knowledge_signals), 1)
        self.assertEqual(
            {
                item["substance_id"]
                for item in result.risk_knowledge_signals[0]["knowledge_trace"][
                    "substance_targets"
                ]
            },
            {SILDENAFIL_ID, TADALAFIL_ID},
        )
        self.assertEqual(len(result.composition_gaps), 1)
        self.assertEqual(
            result.composition_gaps[0]["bridge_mapping_ids"],
            ["bushen-to-male-function", "zhuangyang-to-male-function"],
        )
        self.assertEqual(
            result.composition_gaps[0]["reference_mapping_id"],
            MALE_FUNCTION_GROUP_MAPPING_ID,
        )

    def test_reference_identity_is_loaded_from_bridge_config(self):
        bridge_config = copy.deepcopy(load_effect_risk_bridge_config())
        mapping = next(
            item
            for item in bridge_config["mappings"]
            if item["bridge_mapping_id"] == "jianfei-to-weight-loss"
        )
        mapping["reference_mapping_id"] = "synthetic-config-reference-id"

        with mock.patch(
            "src.inspection_signal_trace.load_effect_risk_bridge_config",
            return_value=bridge_config,
        ):
            result = self._resolve_weight_loss()

        signal = result.risk_knowledge_signals[0]
        self.assertEqual(
            signal["reference_mapping_ids"], ["synthetic-config-reference-id"]
        )
        self.assertEqual(
            result.composition_gaps[0]["reference_mapping_id"],
            "synthetic-config-reference-id",
        )

    def test_signal_and_gap_ordering_is_deterministic(self):
        self._execute(
            "DELETE FROM risk_substance_mappings WHERE mapping_id IN (?, ?)",
            (WEIGHT_LOSS_GROUP_MAPPING_ID, MALE_FUNCTION_GROUP_MAPPING_ID),
        )
        result = self.resolver.resolve_analysis(
            analysis(
                evidence("减脂", ["减肥"]),
                evidence("男性相关", ["补肾", "壮阳"]),
            )
        )

        self.assertEqual(
            [item["risk_category"] for item in result.risk_knowledge_signals],
            ["male_function", "weight_loss"],
        )
        self.assertEqual(
            [
                (gap["risk_category"], gap["reference_mapping_id"])
                for gap in result.composition_gaps
            ],
            [
                ("male_function", MALE_FUNCTION_GROUP_MAPPING_ID),
                ("weight_loss", WEIGHT_LOSS_GROUP_MAPPING_ID),
            ],
        )

    def test_output_has_no_recommendation_or_scoring_fields(self):
        result = self._resolve_male_function().to_dict()
        forbidden = {
            "recommended",
            "recommendation",
            "priority",
            "risk_score",
            "confidence",
            "illegal",
            "applicable_method",
            "selected_method",
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

    def test_schema_version_remains_seven(self):
        with sqlite3.connect(self.store.database_path) as connection:
            schema_version = connection.execute("PRAGMA user_version").fetchone()[0]

        self.assertEqual(schema_version, 7)


if __name__ == "__main__":
    unittest.main()
