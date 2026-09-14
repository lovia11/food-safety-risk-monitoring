import copy
import json
import tempfile
import unittest
from pathlib import Path

from src.claim_analysis import (
    CLAIM_ANALYSIS_ERROR_FILE,
    CLAIM_ANALYSIS_FILE,
    ClaimTaxonomyValidationError,
    derive_claim_analysis,
    load_claim_analysis,
    load_claim_taxonomy,
    record_claim_analysis_failure,
    validate_claim_taxonomy,
    write_claim_analysis,
)
from src.runtime import read_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TAXONOMY_PATH = PROJECT_ROOT / "config" / "claim_taxonomy_v2.json"


def evidence(
    evidence_id: str,
    text: str,
    *,
    origin: str = "seller_managed",
    source_type: str = "dom_product",
    source_path: str = "dom_text.txt",
    line_number: int = 1,
    snapshot_id: str = "ps_claim_test",
) -> dict:
    return {
        "evidenceId": evidence_id,
        "snapshotId": snapshot_id,
        "text": text,
        "contentOrigin": origin,
        "sourceType": source_type,
        "sourcePath": source_path,
        "lineNumber": line_number,
    }


class ClaimAnalysisTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.taxonomy = load_claim_taxonomy(TAXONOMY_PATH)

    def derive(self, records: list[dict], snapshot_id: str = "ps_claim_test") -> dict:
        return derive_claim_analysis(
            snapshot_id,
            records,
            self.taxonomy,
            generated_at="2026-09-14T10:00:00+08:00",
        )

    def test_seller_managed_literal_match_retains_complete_evidence_trace(self):
        result = self.derive(
            [
                evidence(
                    "ev-ocr-1",
                    "本品帮助安睡",
                    source_type="ocr",
                    source_path="ocr/original_002.txt",
                    line_number=7,
                )
            ]
        )
        self.assertEqual(result["status"], "complete")
        self.assertEqual(len(result["claimMentions"]), 1)
        mention = result["claimMentions"][0]
        self.assertEqual(mention["rawText"], "本品帮助安睡")
        self.assertEqual(mention["matchedExpression"], "安睡")
        self.assertEqual(mention["evidenceId"], "ev-ocr-1")
        self.assertEqual(mention["sourceScope"], "seller_managed")
        self.assertEqual(mention["sourceAssetType"], "ocr")
        self.assertEqual(
            mention["sourceLocator"],
            {"sourcePath": "ocr/original_002.txt", "lineNumber": 7},
        )
        self.assertEqual(result["claimSignals"][0]["claimType"], "sleep_related")

    def test_ugc_and_excluded_other_product_never_create_formal_claims(self):
        for origin in ("user_generated", "excluded_other_product"):
            with self.subTest(origin=origin):
                result = self.derive([evidence(f"ev-{origin}", "减肥壮阳", origin=origin)])
                self.assertEqual(result["claimMentions"], [])
                self.assertEqual(result["claimSignals"], [])

    def test_discovery_keyword_is_not_an_input_and_unknown_text_is_not_inferred(self):
        discovery_keyword = "减肥"
        result = self.derive([evidence("ev-neutral", "红枣莲子羹")])
        self.assertEqual(discovery_keyword, "减肥")
        self.assertEqual(result["claimMentions"], [])
        self.assertEqual(result["claimSignals"], [])

    def test_multiple_expressions_aggregate_to_one_signal_without_loss(self):
        result = self.derive([evidence("ev-weight", "减脂减肥")])
        mentions = result["claimMentions"]
        self.assertEqual(
            [item["matchedExpression"] for item in mentions], ["减脂", "减肥"]
        )
        self.assertEqual(len(result["claimSignals"]), 1)
        signal = result["claimSignals"][0]
        self.assertEqual(signal["claimType"], "weight_management")
        self.assertEqual(
            signal["mentionIds"], [item["claimMentionId"] for item in mentions]
        )
        self.assertEqual(signal["evidenceIds"], ["ev-weight"])

    def test_multiple_evidence_aggregate_and_preserve_canonical_order(self):
        result = self.derive(
            [
                evidence("ev-title", "助眠", source_type="title", source_path="meta.json#productName"),
                evidence("ev-ocr", "帮助安睡", source_type="ocr", source_path="ocr/a.txt"),
            ]
        )
        signal = result["claimSignals"][0]
        self.assertEqual(signal["claimType"], "sleep_related")
        self.assertEqual(signal["evidenceIds"], ["ev-title", "ev-ocr"])
        self.assertEqual(len(signal["mentionIds"]), 2)

    def test_multiple_signals_follow_taxonomy_type_order(self):
        result = self.derive([evidence("ev-multi-signal", "助眠减肥壮阳")])
        self.assertEqual(
            [item["claimType"] for item in result["claimSignals"]],
            ["sleep_related", "weight_management", "male_function_related"],
        )
        self.assertEqual(
            [item["matchedExpression"] for item in result["claimMentions"]],
            ["助眠", "减肥", "壮阳"],
        )

    def test_repeated_expression_has_distinct_stable_occurrence_ids(self):
        first = self.derive([evidence("ev-repeat", "助眠，帮助助眠")])
        second = self.derive([evidence("ev-repeat", "助眠，帮助助眠")])
        ids = [item["claimMentionId"] for item in first["claimMentions"]]
        self.assertEqual(len(ids), 2)
        self.assertEqual(len(set(ids)), 2)
        self.assertEqual(
            ids, [item["claimMentionId"] for item in second["claimMentions"]]
        )

    def test_overlapping_expressions_are_all_retained_in_taxonomy_order(self):
        result = self.derive([evidence("ev-overlap", "高血压")])
        self.assertEqual(
            [item["matchedExpression"] for item in result["claimMentions"]],
            ["血压", "高血压"],
        )
        self.assertEqual(len(result["claimSignals"]), 1)

    def test_zero_claim_is_a_valid_complete_artifact(self):
        result = self.derive([evidence("ev-zero", "红枣莲子羹")])
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["claimMentions"], [])
        self.assertEqual(result["claimSignals"], [])
        self.assertEqual(result["summary"]["claimMentionCount"], 0)

    def test_snapshot_identity_changes_ids_and_prevents_cross_snapshot_inheritance(self):
        snapshot_a = self.derive([evidence("ev-a", "助眠")])
        snapshot_b = derive_claim_analysis(
            "ps_claim_other",
            [evidence("ev-b", "普通食品", snapshot_id="ps_claim_other")],
            self.taxonomy,
            generated_at="2026-09-14T10:00:00+08:00",
        )
        self.assertEqual(len(snapshot_a["claimSignals"]), 1)
        self.assertEqual(snapshot_b["claimSignals"], [])

    def test_artifact_write_is_idempotent_and_failure_is_independently_diagnostic(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            records = [evidence("ev-write", "帮助安睡")]
            first = write_claim_analysis(
                root,
                "ps_claim_test",
                records,
                taxonomy_path=TAXONOMY_PATH,
                generated_at="2026-09-14T10:00:00+08:00",
            )
            second = write_claim_analysis(
                root,
                "ps_claim_test",
                records,
                taxonomy_path=TAXONOMY_PATH,
                generated_at="2026-09-14T10:00:00+08:00",
            )
            self.assertEqual(first, second)
            self.assertEqual(
                load_claim_analysis(
                    root / CLAIM_ANALYSIS_FILE,
                    expected_snapshot_id="ps_claim_test",
                    expected_evidence_ids={"ev-write"},
                ),
                second,
            )
            failure = RuntimeError("sidecar failed")
            record_claim_analysis_failure(root, "ps_claim_test", failure)
            self.assertFalse((root / CLAIM_ANALYSIS_FILE).exists())
            error = read_json(root / CLAIM_ANALYSIS_ERROR_FILE)
            self.assertEqual(error["status"], "error")
            self.assertEqual(error["errorType"], "RuntimeError")

    def test_invalid_taxonomy_contracts_fail_fast(self):
        cases = {}
        duplicate_type = copy.deepcopy(self.taxonomy)
        duplicate_type["claim_types"].append(copy.deepcopy(duplicate_type["claim_types"][0]))
        cases["duplicate type"] = duplicate_type
        duplicate_expression = copy.deepcopy(self.taxonomy)
        duplicate_expression["expressions"].append(copy.deepcopy(duplicate_expression["expressions"][0]))
        cases["duplicate expression"] = duplicate_expression
        unknown_type = copy.deepcopy(self.taxonomy)
        unknown_type["expressions"][0]["claim_type"] = "unknown"
        cases["unknown type"] = unknown_type
        unsupported_mode = copy.deepcopy(self.taxonomy)
        unsupported_mode["expressions"][0]["match_mode"] = "fuzzy"
        cases["unsupported mode"] = unsupported_mode
        missing_source = copy.deepcopy(self.taxonomy)
        missing_source["expressions"][0]["source"] = ""
        cases["missing source"] = missing_source
        for forbidden_key in (
            "risk_mappings",
            "health_function_mappings",
            "substance_mappings",
            "method_mappings",
            "legal_status",
        ):
            forbidden_mapping = copy.deepcopy(self.taxonomy)
            forbidden_mapping[forbidden_key] = []
            cases[f"forbidden {forbidden_key}"] = forbidden_mapping
        for name, payload in cases.items():
            with self.subTest(name=name):
                with self.assertRaises(ClaimTaxonomyValidationError):
                    validate_claim_taxonomy(payload)

    def test_taxonomy_file_is_the_runtime_authority(self):
        loaded = load_claim_taxonomy(TAXONOMY_PATH)
        disk = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(loaded, disk)
        self.assertEqual(
            len([item for item in loaded["expressions"] if item["status"] == "active"]),
            len(loaded["expressions"]),
        )


if __name__ == "__main__":
    unittest.main()
