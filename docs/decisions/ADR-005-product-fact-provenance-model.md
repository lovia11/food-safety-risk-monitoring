# ADR-005: Provenance-bearing ProductFact model

> Status: CANONICAL
> Applies to: V2
> Last verified against commit: `bbe992e54f9fc583b312f919f32f91f43e53fb06`
> Owner: Project
> ADR Status: Accepted
> Date: 2026-09-12

## Context

Structured page facts such as declared origin, ingredients, form, category, and health-food registration number can vary over time and may be extracted from conflicting DOM, OCR, or image sources.

## Decision

ProductFact is a future Snapshot-scoped derived entity. It retains normalized and raw values, source type and content origin, exact source path/text or image, extraction method, verification state, and creation/version context. Absence and conflict are explicit. Search region and business addresses never infer declared origin.

The documented field list is a domain proposal, not authorization for a schema migration.

## Consequences

V2-2 must design cardinality, conflicts, typed values, review and supersession before migration. UI missing origin is `—`; `待采集` is not stored as data.

## Rejected alternatives

- Adding unproven columns directly to Product.
- Storing only normalized values without source.
- Filling missing facts from nearby geographic fields.

## Related canonical docs

- [Domain Model](../DOMAIN_MODEL_V2.md)
- [Product Requirements](../PRODUCT_REQUIREMENTS_V2.md)
- [V2 Roadmap](../IMPLEMENTATION_ROADMAP_V2.md)
