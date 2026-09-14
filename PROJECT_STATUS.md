# Project Status

## Baseline

- Branch: `ux-redesign-v1`
- V2-4 Wave 1 starting commit: `698b8ad482367ffbd20ba696799c47ebd372d2c3`
- SQLite schema: 10
- Active UI: React/Vite in `frontend/`
- Backend: Python 3.10.x local API and pipeline

## Current Capabilities

- Search/Discovery → Detail → OCR → Phase3 → degradable Inspection Recommendation
- Product Overview and Snapshot workspace with Evidence, context and Review
- Local Snapshot thumbnails, whole-row keyboard navigation, compact Snapshot summary/timeline, and source-grouped Evidence review
- In-app image Lightbox/OCR viewer and explicit analysis/knowledge/recommendation presentation states
- Snapshot-scoped Review with server-enforced analysis readiness
- Product-scoped current Sampling Membership and frozen historical list export
- Web manual-action coordination without HTTP-thread browser control
- Deterministic Historical Validation support
- Snapshot-scoped ProductFact extraction for explicit `declared_origin`, with DOM/OCR provenance, conflict presentation and source trace
- Snapshot-scoped HealthFoodIdentity with seller-managed clue/identifier provenance, degradable official lookup, conservative page-to-registry matching, verbatim official functions and separate page/official source trace
- Full 106-object Monitor Reference picker with operational/query-pending/paused presentation, server-side execution guard, governed Query lifecycle, validation ledger and search-only batch tooling
- V2 Claim design baseline with separate ClaimMention/ClaimSignal contracts, seller-managed Evidence boundary, and a governed 5-type/26-expression exact taxonomy

## Current Coverage

- Official directory 106 / 106; 18 targets have governed Query records; 16 / 106 are operational
- 19 enabled and validated Reference queries; 1 disabled rejected query; 0 disabled candidate queries; 2 paused targets
- Separate development seed: 1 target / 2 queries
- Legacy/current Phase3 clues: 5 categories / 26 keywords
- V2 Claim design baseline: 5 marketing-topic Claim types / 26 provenance-bearing exact expressions
- 3 Evidence-to-risk Bridge mappings; 8 Risk-to-substance/group mappings
- 5 Inspection methods, 117 substances, 132 method-substance links, 37 applicability records

## Current Validation

V2-4 is complete. Wave 1 promoted five standard-name Queries and held 乌梅; Wave 2A promoted 山药、赤小豆、枸杞子、莲子. Wave 2B promoted 菊花 and rejected the standard-name 百合 Query at 50% observed relevance. The separately governed `食用百合` strategy retained `manually_curated` provenance and passed independent Batch 02C review at 90%; 百合 is now operational only through that refined Query, while the naked standard name remains rejected and disabled. The governed evidence therefore includes real Promote, Hold, Reject, and Refinement paths. V2-4 exit validation passed 74/74 targeted Monitor/query/task tests, 6/6 Historical Validation builder tests, 462 Python tests discovered / 461 passed / 1 skipped, frontend workflow 26/26, typecheck, and production build. The Historical Validation Set remains unmodified.

V2-5A Claim Taxonomy & Domain Contract is complete. All 5 legacy Effect labels and 26 exact keywords were inventoried from the repository and migrated exactly once into five marketing-topic Claim types with no gap. ClaimSignal remains separate from HealthFunction, RiskSignal and InspectionRecommendation; formal Claim sources are seller-managed only. Claim taxonomy tests passed 14/14, Monitor regression passed 74/74, Python full regression discovered 476 / passed 475 / skipped 1, and frontend workflow 26/26, typecheck and build passed offline.

## Known Limitations

Production ClaimMention/ClaimSignal extraction/storage/API/UI, additional ProductFact types, human fact editing, claim-consistency assessment, Analytics, Knowledge Base UI, and further separately governed Operational Search expansion are Future V2 work. Current Phase3 still emits the legacy Effect compatibility contract; no runtime behavior changed in V2-5A. Official registry lookup remains a low-frequency, cached, best-effort integration because the public site exposes no API stability or availability contract. The system does not make legality, efficacy, laboratory-detection, enforcement, geographic-verification, or risk-probability conclusions.

## Current Development Phase

V2-5A — COMPLETE. Claim Taxonomy & Domain Contract design baseline is frozen; schema remains 10 and runtime Claim extraction is unchanged.

## Next Gate

V2-5B ClaimMention / ClaimSignal runtime implementation is NEXT and requires a separate human Gate.

See [Current System Status](docs/CURRENT_SYSTEM_STATUS.md) and the [V2 Roadmap](docs/IMPLEMENTATION_ROADMAP_V2.md).
