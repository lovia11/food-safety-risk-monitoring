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

## Current Coverage

- Official directory 106 / 106; 18 targets have governed Query records; 15 / 106 are operational
- 18 enabled and validated Reference queries; 1 disabled rejected query; 1 disabled candidate query; 3 paused targets
- Separate development seed: 1 target / 2 queries
- Legacy/current Phase3 clues: 5 categories / 26 keywords
- 3 Evidence-to-risk Bridge mappings; 8 Risk-to-substance/group mappings
- 5 Inspection methods, 117 substances, 132 method-substance links, 37 applicability records

## Current Validation

V2-4A validation passed at its recorded baseline. Wave 1 promoted five standard-name Queries and held 乌梅; Wave 2A promoted 山药、赤小豆、枸杞子、莲子. Wave 2B promoted 菊花 and rejected the standard-name 百合 Query at 50% observed relevance. 百合 remains a Reference MonitorTarget but has no executable search strategy. Its disabled `manually_curated` candidate `食用百合` completed bounded search-only Batch `v2-4b-batch-02c` and awaits final human review. V2-4B6 passed 56/56 final Monitor/Query tests, 461 Python tests discovered / 460 passed / 1 skipped, frontend workflow 24/24, typecheck and production build. Deterministic coverage includes program-calculated metrics, Chinese label normalization, immutable manifest hashing, ledger integrity, operational/reference API scopes and server-side execution guards. The Historical Validation Set remains unmodified.

## Known Limitations

Additional ProductFact types, human fact editing, final Claim Taxonomy, claim-consistency assessment, Analytics, Knowledge Base UI, and further validated Operational Search expansion are Future V2 work. All planned V2-4 standard-name waves are governed; only final human review of the collected `食用百合` candidate remains. Official registry lookup remains a low-frequency, cached, best-effort integration because the public site exposes no API stability or availability contract. The system does not make legality, efficacy, laboratory-detection, enforcement, geographic-verification, or risk-probability conclusions.

## Current Development Phase

V2-4 — IN PROGRESS. Planned standard-name waves are governed; `食用百合` collection is complete and human review remains.

## Next Gate

Finalize the `食用百合` review artifact under an explicit human Gate. Do not enable the Query or mark 百合 operational before that decision.

See [Current System Status](docs/CURRENT_SYSTEM_STATUS.md) and the [V2 Roadmap](docs/IMPLEMENTATION_ROADMAP_V2.md).
