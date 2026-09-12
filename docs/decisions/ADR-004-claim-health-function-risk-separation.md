# ADR-004: Separate ClaimSignal, HealthFunction, and RiskSignal

> Status: CANONICAL
> Applies to: V2
> Last verified against commit: `bbe992e54f9fc583b312f919f32f91f43e53fb06`
> Owner: Project
> ADR Status: Accepted
> Date: 2026-09-12

## Context

The current Phase3 Effect vocabulary detects a limited set of page clues. Future health-food consistency and inspection-risk workflows require meanings that cannot safely share one Effect field.

## Decision

ClaimSignal records an observed page expression. HealthFunction records an official normalized function under a verified record/framework. RiskSignal records a risk direction reached through an explicit governed bridge. They are separate entities. Marketing expressions, official functions, risk claims, and disease/treatment expressions use distinct taxonomy layers and explicit mappings.

## Consequences

The current five Effect categories remain labeled legacy/current Phase3 operational clue vocabulary. Future APIs and UI must preserve actual expression, mapping status, source, and gaps. Similar wording is insufficient for equivalence.

## Rejected alternatives

- Expanding the existing Effect enum into a universal taxonomy.
- Automatically equating marketing synonyms with official functions.
- Treating every ClaimSignal as a RiskSignal.

## Related canonical docs

- [Product Requirements](../PRODUCT_REQUIREMENTS_V2.md)
- [Domain Model](../DOMAIN_MODEL_V2.md)
- [Knowledge Governance](../KNOWLEDGE_GOVERNANCE.md)
