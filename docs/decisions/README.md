# Architecture Decision Records

> Status: CANONICAL
> Applies to: V2
> Last verified against commit: `bbe992e54f9fc583b312f919f32f91f43e53fb06`
> Owner: Project

ADRs freeze cross-phase decisions that should not be changed incidentally. A newer ADR may supersede an older one only by naming it explicitly and explaining migration consequences.

| ADR | Status | Decision |
|---|---|---|
| [ADR-001](ADR-001-evidence-first-non-adjudication.md) | Accepted | Evidence-first, non-adjudicative product boundary |
| [ADR-002](ADR-002-data-authority-and-provenance.md) | Accepted | Data authority and provenance chain |
| [ADR-003](ADR-003-review-and-sampling-separation.md) | Accepted | Snapshot Review and Product Sampling separation |
| [ADR-004](ADR-004-claim-health-function-risk-separation.md) | Accepted | ClaimSignal, HealthFunction, and RiskSignal separation |
| [ADR-005](ADR-005-product-fact-provenance-model.md) | Accepted | Snapshot-scoped ProductFact provenance model |
| [ADR-006](ADR-006-health-food-identity-verification.md) | Accepted | Multi-state official health-food identity verification |

## ADR format

Every record contains Status, Date, Context, Decision, Consequences, Rejected Alternatives, and Related canonical docs. Proposed changes require a new record; do not rewrite accepted historical reasoning to disguise a changed decision.
