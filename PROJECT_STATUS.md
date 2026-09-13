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

- Official directory 106 / 106; 18 targets have governed Query records; 14 / 106 are operational
- 17 enabled and validated Reference queries; 2 disabled candidate queries; 2 paused targets
- Separate development seed: 1 target / 2 queries
- Legacy/current Phase3 clues: 5 categories / 26 keywords
- 3 Evidence-to-risk Bridge mappings; 8 Risk-to-substance/group mappings
- 5 Inspection methods, 117 substances, 132 method-substance links, 37 applicability records

## Current Validation

V2-4A validation passed at its recorded baseline. Wave 1 completed bounded search-only collection and human review for six standard-name Queries: five were promoted and 乌梅 was held for systematic scope mixing. Wave 2A then promoted the standard-name Queries for 山药、赤小豆、枸杞子、莲子. V2-4B4 validation passed with 46/46 targeted Monitor tests, 460 Python tests discovered / 459 passed / 1 skipped, Historical Validation builder 6/6, frontend workflow 24/24, and passing typecheck/production build. Offline local UI acceptance confirmed the four promoted Wave 2A targets are runnable, while 乌梅 remains paused and 百合、菊花 remain in the `待验证` state. Deterministic coverage includes program-calculated metrics, Chinese label normalization, immutable manifest hashing, ledger integrity, operational/reference API scopes and server-side execution guards. The Historical Validation Set remains unmodified.

## Known Limitations

Additional ProductFact types, human fact editing, final Claim Taxonomy, claim-consistency assessment, Analytics, Knowledge Base UI, and further validated Operational Search expansion are Future V2 work. V2-4 Wave 1 and Wave 2A are governed; 百合 and 菊花 remain unvalidated Wave 2B candidates. Official registry lookup remains a low-frequency, cached, best-effort integration because the public site exposes no API stability or availability contract. The system does not make legality, efficacy, laboratory-detection, enforcement, geographic-verification, or risk-probability conclusions.

## Current Development Phase

V2-4 — IN PROGRESS. Wave 1 and Wave 2A collection/governance complete; Wave 2B pending.

## Next Gate

V2-4 Wave 2B may begin only after an explicit human Gate for 百合 and 菊花. Do not start a new live batch or promote candidates before reviewed artifacts pass the frozen Gate.

See [Current System Status](docs/CURRENT_SYSTEM_STATUS.md) and the [V2 Roadmap](docs/IMPLEMENTATION_ROADMAP_V2.md).
