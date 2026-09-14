# ADR-007: Separate HealthFunction identity, official transition normalization, and Claim consistency assessment

> Status: CANONICAL
> Applies to: V2
> Design starting baseline: `696bf4178cbc018fca6d257ba156ec6f3a33fc1e`
> Owner: Project
> ADR Status: Accepted
> Date: 2026-09-15

## Context

Registry records preserve official function strings verbatim, including historical wording and descriptive wrappers. The current V2 Claim taxonomy describes page marketing topics. String equality alone would falsely treat documented old/current official names as different functions, while fuzzy similarity would falsely turn marketing language into official identity or approval.

The 2023 official framework supplies 24 current non-nutrient function names and a source-backed transition table. Nutrient-supplement functions belong to a separate official framework. The project needs reproducible comparison clues without collapsing page Claims, official functions, risk knowledge, or legal judgments.

## Decision

1. `HealthFunction` has a stable `function_id` under a stable `framework_id`; the official current name remains verbatim display/source data.
2. Registry normalization preserves every raw string and resolves only exact current official names, exact officially documented transition aliases, or a future explicit governed mapping.
3. Official aliases apply only to Registry strings. They are never marketing synonyms and never approve an identical page expression.
4. `ClaimHealthFunctionMapping` is a separate versioned project-governed dataset. Its relation is `topic_related`, not official equivalence.
5. `ClaimConsistencyAssessment` is a future Snapshot-scoped derived comparison gated by `HealthFoodIdentity.state == verified_match` and complete V2 Claim analysis.
6. Assessment states and per-Claim relations are non-adjudicative and preserve unavailable, unresolved, zero, and mapping-gap states.
7. Mention-level regulatory attention is a separate expression-scoped contract. Its production dataset remains pending manual source governance.
8. V2-6A changes no runtime, schema, API, frontend, Review, Sampling, Risk, Recommendation, or frozen history.

## Alternatives rejected

- Comparing raw Registry strings only, because official transition names would create false differences.
- Fuzzy, embedding, edit-distance, or LLM normalization, because similarity is not official identity.
- Treating `claim_type == function_id`, because a marketing topic is not an official framework identity.
- Calling `topic_related` equivalent, approved, compliant, or legal.
- Applying transition aliases to page ClaimMentions.
- Classifying all Mentions in one ClaimSignal as disease/treatment wording through substring or topic rules.
- Using assessment output to create RiskSignal, a substance, a method, or an InspectionRecommendation.

## Consequences

- Governed knowledge consists of independent Claim taxonomy, HealthFunction framework, Claim↔HealthFunction topic mapping, and future assessment versions.
- Forty source-backed official transition aliases normalize historical Registry names without rewriting their raw values.
- Four current Claim types have explicit topic mappings; `male_function_related` remains an explicit no-mapping gap.
- Unknown framework/function strings remain visible and can block a comparison rather than being guessed.
- V2-6B must add runtime/artifact/storage/API behavior under a separate gate and record every dataset and Registry version used.

## Related canonical docs

- [HealthFunction Framework V2](../HEALTH_FUNCTION_FRAMEWORK_V2.md)
- [Claim Consistency V2](../CLAIM_CONSISTENCY_V2.md)
- [Domain Model V2](../DOMAIN_MODEL_V2.md)
- [Knowledge Governance](../KNOWLEDGE_GOVERNANCE.md)
- [Claim Taxonomy V2](../CLAIM_TAXONOMY_V2.md)
