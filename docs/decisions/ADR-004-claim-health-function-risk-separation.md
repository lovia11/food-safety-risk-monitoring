# ADR-004: Separate ClaimSignal from HealthFunction and RiskSignal

> Status: CANONICAL
> Applies to: V2
> Last verified against commit: `bbe992e54f9fc583b312f919f32f91f43e53fb06`
> Owner: Project
> ADR Status: Accepted
> Date: 2026-09-12

## Context

The current Phase3 Effect vocabulary detects a limited set of page expressions, stores the expression occurrence and normalized Effect label together, and supplies an exact Effect/keyword bridge into Risk and inspection knowledge. Future health-food consistency and inspection-risk workflows require meanings that cannot safely share one overloaded Effect field.

An observed marketing phrase is neither proof that a product has the claimed effect nor an Official Health Function. A normalized marketing topic is also not, by itself, a supported regulatory RiskSignal or an inspection recommendation. The source occurrence must remain reconstructable rather than being reduced to a category boolean.

## Decision

Introduce two separate Claim layers:

- ClaimMention records one Snapshot-specific, Evidence-backed occurrence, including raw text, exact matched expression and seller-managed source trace.
- ClaimSignal groups one or more same-Snapshot ClaimMentions into a governed page-marketing topic while retaining every mention/Evidence identity.

HealthFunction records an official function under a verified record/framework. RiskSignal records a risk direction reached through an explicit governed bridge. ClaimSignal, HealthFunction, and RiskSignal are separate entities and enums. Marketing expressions, official functions, risk vocabulary, and disease/treatment vocabulary use distinct governed layers; any cross-layer relation is an explicit provenance-bearing mapping.

Formal Claim input is seller-managed Evidence only. UGC remains auxiliary and excluded-other-product content is forbidden. `config/claim_taxonomy_v2.json` contains no HealthFunction, Risk, substance, method, legality, or inspection mapping.

## Alternatives rejected

- Expanding the existing Effect enum into a universal taxonomy.
- Treating a keyword or ClaimSignal as verified product efficacy.
- Automatically equating marketing synonyms with Official Health Functions.
- Treating every ClaimSignal as a RiskSignal or direct inspection trigger.
- Allowing UGC or recommendation-area text to create a formal current-product ClaimSignal.
- Keeping only `claim_type=true` and dropping source occurrences.

## Consequences

- The current five Effect categories remain explicitly legacy/current Phase3 operational clue vocabulary.
- Future artifacts and APIs carry `claimMentions[]` and `claimSignals[]`, including raw expression, Evidence/source trace, taxonomy version and gaps.
- The official 2023 health-function framework cannot be represented as these five Claim types.
- Missing cross-layer knowledge remains unmapped; similar wording is insufficient for equivalence.
- Claim consistency and Risk/inspection bridging require later independent gates.

## Migration impact

V2-5A maps all 26 current exact expressions into five page-marketing topics without expanding the lexicon. It changes no runtime, API, SQLite schema, historical artifact, frozen Sampling export, Phase3 logic, or D2–D6 behavior.

The three current exact Effect/keyword-to-Risk mappings remain a separately governed legacy compatibility bridge. V2-5B must produce seller-managed ClaimMention/ClaimSignal records and keep UGC auxiliary. A later gate may replace the legacy bridge only with an explicit ClaimSignal-to-Risk mapping and must preserve historical derivations. Future SQLite Claim tables are additive rebuildable projections; the derived Claim artifact and source Evidence retain authority.

## Related canonical docs

- [Product Requirements](../PRODUCT_REQUIREMENTS_V2.md)
- [Domain Model](../DOMAIN_MODEL_V2.md)
- [Knowledge Governance](../KNOWLEDGE_GOVERNANCE.md)
- [Claim Taxonomy V2](../CLAIM_TAXONOMY_V2.md)
