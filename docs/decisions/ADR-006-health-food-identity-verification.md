# ADR-006: Officially verified, multi-state HealthFoodIdentity

> Status: CANONICAL
> Applies to: V2
> Last verified against commit: `bbe992e54f9fc583b312f919f32f91f43e53fb06`
> Owner: Project
> ADR Status: Accepted
> Date: 2026-09-12

## Context

Pages may show blue-hat imagery, registration/filing numbers, and names that are missing, misleading, stale, or inconsistent. A boolean identity inferred from one clue cannot express these cases.

## Decision

HealthFoodIdentity uses at least `candidate`, `verified`, `conflict`, `not_found`, and `insufficient`. A page clue creates a candidate. `verified` requires authoritative registry evidence and documented matching. Source unavailability, number mismatch, ambiguous name, and insufficient evidence remain explicit. Identity resolution does not decide legality.

## Consequences

V2-3 requires versioned official records, matching rules, negative/ambiguous fixtures, and source provenance. Claim consistency runs only with the identity state and official evidence made visible.

## Rejected alternatives

- Boolean `is_health_food` inferred from a logo.
- Accepting an OCR number without authoritative lookup.
- Conflating record-not-found with ordinary food or illegality.

## Related canonical docs

- [Product Requirements](../PRODUCT_REQUIREMENTS_V2.md)
- [Domain Model](../DOMAIN_MODEL_V2.md)
- [Test Acceptance](../TEST_ACCEPTANCE_V2.md)
