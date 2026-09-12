# ADR-002: Data authority and provenance

> Status: CANONICAL
> Applies to: V2
> Last verified against commit: `bbe992e54f9fc583b312f919f32f91f43e53fb06`
> Owner: Project
> ADR Status: Accepted
> Date: 2026-09-12

## Context

The system has run artifacts, a SQLite index/business store, derived recommendations, governed config, and frozen exports. Treating them as interchangeable risks losing human decisions or rewriting historical facts.

## Decision

`output/<run_id>/` is authoritative for raw collection and processing facts. `data/app.db` is the query index and current Review/Sampling business store; run-derived content can be re-imported, but human mutations require backup/migration care. `inspection_recommendation.json` is a derived result under recorded context and knowledge versions. A frozen Sampling export is immutable historical list fact. Historical Validation data is test/demo support, not production coverage.

Every derived fact must trace to a ProductSnapshot, exact artifact/content, extraction method, and relevant knowledge version.

## Consequences

Rebuild procedures cannot casually discard Review/Sampling state. New derived versions do not alter source Evidence or frozen exports. APIs enforce safe artifact-path containment.

## Rejected alternatives

- Declaring SQLite wholly disposable.
- Treating derived recommendations as raw facts.
- Reconstructing frozen history through mandatory live foreign keys.

## Related canonical docs

- [System Architecture](../SYSTEM_V2_ARCHITECTURE.md)
- [Domain Model](../DOMAIN_MODEL_V2.md)
- [Test Acceptance](../TEST_ACCEPTANCE_V2.md)
