import unittest

from src.inspection_knowledge import InspectionKnowledgeResolver
from src.inspection_signal_trace import InspectionSignalTraceResolver


class FakeRiskStore:
    def __init__(self) -> None:
        self.rows = [
            {
                "mapping_id": "current-sleep-group",
                "risk_category": "sleep_aid",
                "risk_label": "睡眠相关宣传",
                "target_type": "substance_group",
                "substance_id": None,
                "target_group_label": "当前关注物质组",
                "evidence_grade": "A",
                "basis_type": "current_official_guidance",
                "temporal_status": "current",
                "product_scope": "当前范围",
                "source_name": "当前官方来源",
                "source_reference": "https://example.invalid/current",
                "source_date": "2025-01-01",
                "source_basis_text": "当前来源原文",
                "note": "current fixture",
            },
            {
                "mapping_id": "historical-sleep-allowed",
                "risk_category": "sleep_aid",
                "risk_label": "睡眠相关宣传",
                "target_type": "substance_group",
                "substance_id": None,
                "target_group_label": "历史关注物质组",
                "evidence_grade": "B",
                "basis_type": "historical_sampling_plan",
                "temporal_status": "historical",
                "product_scope": "历史抽检范围",
                "source_name": "历史中央抽检资料",
                "source_reference": "https://example.invalid/historical-allowed",
                "source_date": "2014-01-01",
                "source_basis_text": "历史抽检资料原文",
                "note": "allowed historical fixture",
            },
            {
                "mapping_id": "historical-sleep-not-allowed",
                "risk_category": "sleep_aid",
                "risk_label": "睡眠相关宣传",
                "target_type": "substance_group",
                "substance_id": None,
                "target_group_label": "未授权历史物质组",
                "evidence_grade": "B",
                "basis_type": "historical_sampling_plan",
                "temporal_status": "historical",
                "product_scope": "另一历史抽检范围",
                "source_name": "另一历史中央抽检资料",
                "source_reference": "https://example.invalid/historical-other",
                "source_date": "2013-01-01",
                "source_basis_text": "另一历史抽检资料原文",
                "note": "not allowed historical fixture",
            },
        ]

    def list_risk_mappings(self, risk_category, *, include_historical=False):
        rows = [row.copy() for row in self.rows if row["risk_category"] == risk_category]
        if include_historical:
            return rows
        return [row for row in rows if row["temporal_status"] == "current"]

    def get_inspection_substance(self, substance_id):
        return None

    def list_substance_methods(self, substance_id, *, recommendation_ready_only=False):
        return []

    def list_method_applicabilities(self, method_id, substance_id):
        return []

    def list_substance_regulatory_contexts(self, substance_id):
        return []


class V2B3TemporalGovernanceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = FakeRiskStore()
        self.resolver = InspectionKnowledgeResolver(self.store)  # type: ignore[arg-type]

    def test_selective_historical_allowlist_keeps_current_and_only_authorized_history(self):
        trace = self.resolver.resolve(
            "sleep_aid",
            allowed_historical_mapping_ids={"historical-sleep-allowed"},
        )

        evidence = {
            target["target_group_label"]: target["mapping_evidence"]
            for target in trace.group_targets
        }
        self.assertIn("当前关注物质组", evidence)
        self.assertIn("历史关注物质组", evidence)
        self.assertNotIn("未授权历史物质组", evidence)
        self.assertEqual(
            evidence["当前关注物质组"][0]["temporal_status"], "current"
        )
        self.assertEqual(
            evidence["历史关注物质组"][0]["temporal_status"], "historical"
        )

    def test_empty_allowlist_does_not_enable_any_historical_mapping(self):
        trace = self.resolver.resolve(
            "sleep_aid",
            allowed_historical_mapping_ids=set(),
        )
        self.assertEqual(
            [target["target_group_label"] for target in trace.group_targets],
            ["当前关注物质组"],
        )

    def test_global_and_selective_historical_switches_cannot_be_combined(self):
        with self.assertRaises(ValueError):
            self.resolver.resolve(
                "sleep_aid",
                include_historical=True,
                allowed_historical_mapping_ids={"historical-sleep-allowed"},
            )

    def test_v2_claim_production_rejects_global_historical_switch(self):
        resolver = InspectionSignalTraceResolver(self.store)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            resolver.resolve_claim_analysis({}, include_historical=True)


if __name__ == "__main__":
    unittest.main()
