# ADR-008: Separate inspection-method lifecycle, knowledge depth, and recommendation reachability

> Status: CANONICAL
> Applies to: V2-7
> Design starting baseline: `5a8368fcb8b46fed9f5cb2714a32df52c0f377d0`
> Owner: Project
> ADR Status: Accepted
> Date: 2026-09-15

## Context

The current Inspection Reference contains five source-backed methods with deeply parsed analytes and applicability, while the broader official-method universe is neither indexed nor defined. The current `method_status` describes lifecycle, and the `verified_reference` validator requires analyte and applicability records for every method. Reusing those concepts for a future wide index would falsely imply that every current official method is Recommendation-capable.

Risk mappings also include source-native groups. Method analyte lists contain some concrete compounds whose names may appear related to those groups, but a method relation is not an independent Risk mapping or a complete group-membership authority.

## Decision

1. Maintain a Wide Reference Index and a Deep Verified Subset.
2. Keep official method lifecycle independent from project `knowledge_depth`.
3. Use `reference_only`, `analyte_verified`, `applicability_verified`, and `recommendation_ready` as the design depth progression; V2-7A does not persist it.
4. Require official identity/source, source-backed analytes, parsed scope, applicability handling, lifecycle and provenance before deep promotion.
5. Require an independent Risk→explicit Substance mapping and product-context applicability before a method can contribute to Recommendation.
6. Never derive Risk mapping or group membership from Method→Substance.
7. Report multiple denominator-defined metrics rather than one “knowledge coverage” percentage.
8. Normalize RegulatoryDocument identity and supersession in a future additive gate; retain current inline sources until then.
9. Keep V2-7B candidates outside runtime import until a depth-aware resolver boundary exists.

## Alternatives rejected

- Treat every `current` method as verified and applicable.
- Add reference-only rows to the current verified dataset and rely on missing joins accidentally suppressing them.
- Expand Risk groups from method analyte lists or model knowledge.
- Define method coverage against an unstated universe of all official methods.
- Use one score that mixes source strength, knowledge depth, product risk and Recommendation reachability.
- Add a ClaimSignal→Risk bridge during Inspection knowledge expansion.

## Consequences

- The current five-method corpus audits as deep verified for its explicit relations, while still being narrow.
- The three group mappings remain unresolved; explicit sibling Substance mappings can still support the existing path.
- V2-7B needs an additive depth/candidate boundary before widening runtime data.
- Coverage reports carry input versions, numerators and denominators.
- Existing D2–D6 output, schema 12, API, frontend and governed records remain unchanged in V2-7A.

## Related canonical docs

- [Inspection Knowledge Coverage V2](../INSPECTION_KNOWLEDGE_COVERAGE_V2.md)
- [Inspection Knowledge Audit V2-7A](../INSPECTION_KNOWLEDGE_AUDIT_V2_7.md)
- [Domain Model V2](../DOMAIN_MODEL_V2.md)
- [Knowledge Governance](../KNOWLEDGE_GOVERNANCE.md)
- [Implementation Roadmap V2](../IMPLEMENTATION_ROADMAP_V2.md)
