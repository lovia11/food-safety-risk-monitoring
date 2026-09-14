from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from src.claim_consistency import (
    ATTENTION_GAP,
    CLAIM_CONSISTENCY_ERROR_FILE,
    CLAIM_CONSISTENCY_FILE,
    ClaimConsistencyConfigError,
    derive_claim_consistency,
    load_claim_consistency,
    load_claim_health_function_mapping,
    load_health_function_dataset,
    record_claim_consistency_failure,
    resolve_official_function,
    validate_claim_health_function_mapping,
    validate_health_function_dataset,
    write_claim_consistency_from_artifacts,
)
from src.runtime import read_json, write_json


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "claim_consistency_v2"
    / "contract_cases.json"
)
NON_NUTRIENT_FRAMEWORK = "hf-framework-non-nutrient-cn-2023"


def make_identity(
    state: str,
    raw_functions: list[str],
    *,
    framework_id: str | None | object = ...,
) -> dict:
    record = {
        "identifier": "国食健字GTEST0001",
        "officialHealthFunctions": raw_functions,
        "sourceName": "recorded official fixture",
        "sourceReference": "tests/fixtures/registry.json",
        "retrievedAt": "2026-09-15T00:00:00+08:00",
        "rawArtifactHash": "a" * 64,
        "rawArtifactPath": "registry_raw.json",
    }
    if framework_id is not ...:
        record["frameworkId"] = framework_id
    return {
        "schemaVersion": 1,
        "extractorVersion": "health-food-identity-v2",
        "generatedAt": "2026-09-15T00:00:00+08:00",
        "snapshotId": "snapshot-test",
        "clues": [],
        "identifierCandidates": [],
        "officialLookup": {"status": "found", "record": record},
        "identityAssessment": {"state": state, "productMatch": {}},
        "gaps": [],
        "diagnostics": {},
    }


def make_claim_analysis(claim_types: list[str]) -> dict:
    mentions = []
    signals = []
    for index, claim_type in enumerate(claim_types, start=1):
        mention_id = f"cm-{index}"
        signal_id = f"cs-{index}"
        mentions.append(
            {
                "claimMentionId": mention_id,
                "snapshotId": "snapshot-test",
                "claimType": claim_type,
                "expressionId": f"expression-{index}",
                "rawText": claim_type,
                "normalizedText": claim_type,
                "matchedExpression": claim_type,
                "evidenceId": f"evidence-{index}",
                "sourceScope": "seller_managed",
                "sourceAssetType": "ocr",
                "sourceLocator": {"sourcePath": "ocr/text.txt", "lineNumber": index},
                "extractionMethod": "exact_literal_occurrence",
                "taxonomyVersion": "claim-taxonomy-v2.0",
                "createdAt": "2026-09-15T00:00:00+08:00",
            }
        )
        signals.append(
            {
                "claimSignalId": signal_id,
                "snapshotId": "snapshot-test",
                "claimType": claim_type,
                "displayLabel": claim_type,
                "mentionIds": [mention_id],
                "evidenceIds": [f"evidence-{index}"],
                "taxonomyVersion": "claim-taxonomy-v2.0",
                "status": "normalized",
                "createdAt": "2026-09-15T00:00:00+08:00",
            }
        )
    return {
        "schemaVersion": 1,
        "status": "complete",
        "taxonomyVersion": "claim-taxonomy-v2.0",
        "snapshotId": "snapshot-test",
        "generatedAt": "2026-09-15T00:00:00+08:00",
        "claimMentions": mentions,
        "claimSignals": signals,
    }


class ClaimConsistencyRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.health_functions = load_health_function_dataset()
        cls.mapping = load_claim_health_function_mapping(
            health_functions=cls.health_functions
        )

    def derive(
        self,
        identity_state: str,
        claim_status: str,
        claim_types: list[str],
        raw_functions: list[str],
        *,
        framework_id: str | None | object = ...,
    ) -> dict:
        return derive_claim_consistency(
            "snapshot-test",
            make_identity(
                identity_state, raw_functions, framework_id=framework_id
            ),
            claim_status,
            make_claim_analysis(claim_types) if claim_status == "complete" else None,
            health_functions=self.health_functions,
            mapping_dataset=self.mapping,
            generated_at="2026-09-15T00:00:00+08:00",
        )

    def test_governed_config_counts_and_validation(self) -> None:
        self.assertEqual(len(self.health_functions["frameworks"]), 2)
        self.assertEqual(len(self.health_functions["functions"]), 25)
        self.assertEqual(len(self.health_functions["aliases"]), 40)
        self.assertEqual(len(self.mapping["mappings"]), 4)

        duplicate = copy.deepcopy(self.health_functions)
        duplicate["aliases"][1]["alias_text"] = duplicate["aliases"][0]["alias_text"]
        with self.assertRaises(ClaimConsistencyConfigError):
            validate_health_function_dataset(duplicate)

        invalid_mapping = copy.deepcopy(self.mapping)
        invalid_mapping["mappings"][0]["substance_id"] = "forbidden"
        with self.assertRaises(ClaimConsistencyConfigError):
            validate_claim_health_function_mapping(
                invalid_mapping,
                health_functions=self.health_functions,
                claim_taxonomy=json.loads(
                    Path("config/claim_taxonomy_v2.json").read_text(encoding="utf-8")
                ),
            )

    def test_exact_official_resolution_and_no_string_cleanup(self) -> None:
        current = resolve_official_function(
            "有助于改善睡眠", health_functions=self.health_functions
        )
        alias = resolve_official_function(
            "改善睡眠", health_functions=self.health_functions
        )
        wrapper = resolve_official_function(
            "本品经动物实验评价，具有对化学性肝损伤有辅助保护作用的保健功能",
            health_functions=self.health_functions,
        )
        whitespace = resolve_official_function(
            " 改善睡眠", health_functions=self.health_functions
        )
        self.assertEqual(current["resolutionSource"], "current_official_name")
        self.assertEqual(alias["resolutionSource"], "official_transition_alias")
        self.assertEqual(alias["healthFunctionId"], "hf-non-nutrient-cn-2023-06")
        self.assertEqual(wrapper["resolutionStatus"], "unresolved")
        self.assertEqual(whitespace["resolutionStatus"], "unresolved")

    def test_frozen_contract_cases_a_to_l(self) -> None:
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(len(fixture["cases"]), 12)
        for case in fixture["cases"]:
            with self.subTest(case=case["case_id"]):
                # The design fixture omits the framework field when its recorded
                # Registry fixture provides explicit non-nutrient provenance.
                # An explicit JSON null is the unknown-framework case.
                framework_id = (
                    case["registry_framework_id"]
                    if "registry_framework_id" in case
                    else NON_NUTRIENT_FRAMEWORK
                )
                artifact = self.derive(
                    case["identity_state"],
                    case["claim_analysis_status"],
                    case["claim_types"],
                    case["raw_official_functions"],
                    framework_id=framework_id,
                )
                self.assertEqual(artifact["state"], case["expected_state"])
                self.assertEqual(
                    [item["relation"] for item in artifact["perClaimAssessments"]],
                    case["expected_relations"],
                )
                if case.get("expected_resolution_source"):
                    self.assertEqual(
                        artifact["resolvedHealthFunctions"][0]["resolutionSource"],
                        case["expected_resolution_source"],
                    )

    def test_partial_unresolved_negative_is_not_recorded_is_forbidden(self) -> None:
        artifact = self.derive(
            "verified_match",
            "complete",
            ["sleep_related"],
            ["有助于增强免疫力", "某个无法治理解析的官方原文"],
        )
        self.assertEqual(artifact["state"], "official_function_unresolved")
        self.assertEqual(
            artifact["perClaimAssessments"][0]["relation"], "mapping_unresolved"
        )

    def test_partial_unresolved_positive_retains_positive_evidence(self) -> None:
        artifact = self.derive(
            "verified_match",
            "complete",
            ["sleep_related"],
            ["有助于改善睡眠", "某个无法治理解析的官方原文"],
        )
        self.assertEqual(artifact["state"], "official_function_unresolved")
        item = artifact["perClaimAssessments"][0]
        self.assertEqual(item["relation"], "function_topic_recorded")
        self.assertEqual(len(item["supportingResolvedOfficialFunctions"]), 1)

    def test_multiple_claims_and_nutrient_framework_are_independent(self) -> None:
        multiple = self.derive(
            "verified_match",
            "complete",
            [
                "sleep_related",
                "blood_pressure_related",
                "weight_management",
                "male_function_related",
            ],
            ["有助于改善睡眠", "有助于维持血压健康水平"],
        )
        self.assertEqual(
            [item["relation"] for item in multiple["perClaimAssessments"]],
            [
                "function_topic_recorded",
                "function_topic_recorded",
                "function_topic_not_recorded",
                "no_governed_function_mapping",
            ],
        )
        nutrient = self.derive(
            "verified_match",
            "complete",
            ["sleep_related"],
            ["补充维生素、矿物质等营养物质"],
            framework_id="hf-framework-nutrient-supplement-cn-2023",
        )
        self.assertEqual(nutrient["state"], "assessed")
        self.assertEqual(
            nutrient["perClaimAssessments"][0]["relation"],
            "no_governed_function_mapping",
        )

    def test_registry_alias_is_not_claim_wording_approval(self) -> None:
        artifact = self.derive(
            "verified_match",
            "complete",
            ["weight_management"],
            ["减肥"],
        )
        self.assertEqual(
            artifact["perClaimAssessments"][0]["relation"],
            "function_topic_recorded",
        )
        serialized = json.dumps(artifact, ensure_ascii=False)
        for forbidden in (
            "approvedWording",
            "officialAliasMatchedForClaim",
            "compliant",
            "riskLevel",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_only_formal_claim_artifact_is_consumed_and_attention_stays_empty(self) -> None:
        artifact = self.derive(
            "verified_match",
            "complete",
            [],
            ["有助于改善睡眠"],
        )
        self.assertEqual(artifact["state"], "no_page_claims")
        self.assertEqual(artifact["claimSignalIds"], [])
        self.assertEqual(artifact["mentionAttentions"], [])
        self.assertIn(ATTENTION_GAP, artifact["gaps"])
        self.assertEqual(artifact["summary"]["attentionMentionCount"], 0)

    def test_output_is_deterministic_except_time(self) -> None:
        first = self.derive(
            "verified_match", "complete", ["sleep_related"], ["改善睡眠"]
        )
        second = self.derive(
            "verified_match", "complete", ["sleep_related"], ["改善睡眠"]
        )
        self.assertEqual(first, second)

    def test_artifact_write_load_and_error_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            identity = make_identity(
                "verified_match", ["有助于改善睡眠"], framework_id=NON_NUTRIENT_FRAMEWORK
            )
            write_json(root / "health_food_identity.json", identity)
            from src.claim_analysis import write_claim_analysis

            write_claim_analysis(
                root,
                "snapshot-test",
                [
                    {
                        "evidenceId": "evidence-1",
                        "snapshotId": "snapshot-test",
                        "text": "帮助改善睡眠",
                        "content_origin": "seller_managed",
                        "source_type": "ocr",
                        "source_path": "ocr/text.txt",
                        "line_number": 1,
                    }
                ],
            )
            artifact = write_claim_consistency_from_artifacts(root, "snapshot-test")
            self.assertEqual(artifact["state"], "assessed")
            self.assertEqual(
                load_claim_consistency(
                    root / CLAIM_CONSISTENCY_FILE,
                    expected_snapshot_id="snapshot-test",
                )["state"],
                "assessed",
            )
            failure = record_claim_consistency_failure(
                root, "snapshot-test", RuntimeError("fixture failure")
            )
            self.assertEqual(failure["status"], "error")
            self.assertTrue((root / CLAIM_CONSISTENCY_ERROR_FILE).is_file())
            self.assertEqual(
                read_json(root / CLAIM_CONSISTENCY_ERROR_FILE)["errorType"],
                "RuntimeError",
            )


if __name__ == "__main__":
    unittest.main()
