# ADR-001: Evidence-first, non-adjudicative system boundary

> Status: CANONICAL
> Applies to: V2
> Last verified against commit: `bbe992e54f9fc583b312f919f32f91f43e53fb06`
> Owner: Project
> ADR Status: Accepted
> Date: 2026-09-12

## Context

The pipeline observes marketplace pages and derives clues from DOM, images, OCR, and governed knowledge. Those observations cannot establish laboratory content, efficacy truth, legality, or enforcement outcome.

## Decision

The product is evidence-first and non-adjudicative. It reports page-level clues, sources, knowledge bridges, gaps, and inspection assistance. OCR hits are not laboratory results; recommendations are neither risk probabilities nor enforcement conclusions. Seller-managed, UGC, and excluded-other-product Evidence remain distinguishable. Unknown or unsupported conclusions remain explicit.

## Consequences

UI and APIs must expose provenance and uncertainty. Testing includes wording and source-origin boundaries. Human Review records an operational decision, not an automated legal judgment.

## Rejected alternatives

- Labeling products legal/illegal from page content.
- Treating OCR hits as detected substances.
- Hiding Knowledge Gaps behind generated recommendations.

## Related canonical docs

- [Product Requirements](../PRODUCT_REQUIREMENTS_V2.md)
- [UX Specification](../UX_SPEC_V2.md)
- [Knowledge Governance](../KNOWLEDGE_GOVERNANCE.md)
