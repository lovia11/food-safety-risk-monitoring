# Project Status

## Baseline

- Branch: `ux-redesign-v1`
- V2-2 starting commit: `e6acc4345d3ef4c702c40d78c9fb2e2a179fe75d`
- SQLite schema: 9
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

## Current Coverage

- 106 Reference MonitorTargets; 5 enabled Reference targets and 8 enabled validated queries
- Separate development seed: 1 target / 2 queries
- Legacy/current Phase3 clues: 5 categories / 26 keywords
- 3 Evidence-to-risk Bridge mappings; 8 Risk-to-substance/group mappings
- 5 Inspection methods, 117 substances, 132 method-substance links, 37 applicability records

## Current Validation

V2-2 validation: Python 414 discovered / 413 passed / 1 skipped; frontend workflow 19/19; frontend typecheck and production build passed. It includes A–L extraction fixtures, schema 8→9 preservation, idempotent import/API coverage, Historical Validation generation, and offline 1440px/1080px source-trace inspection. The five-product set produced six provenance-bearing facts, including one explicit conflict.

## Known Limitations

HealthFoodIdentity/official lookup, additional ProductFact types, human fact editing, final Claim Taxonomy, claim-consistency assessment, Analytics, Knowledge Base UI, and broad Operational Search coverage are Future V2 work. The system does not make legality, efficacy, laboratory-detection, enforcement, geographic-verification, or risk-probability conclusions.

## Current Development Phase

V2-2 — ProductFact Foundation + Declared Origin implemented and validated.

## Next Gate

V2-3 HealthFoodIdentity remains a separate gate and has not started. Do not begin it without explicit approval and an official-registry acquisition contract.

See [Current System Status](docs/CURRENT_SYSTEM_STATUS.md) and the [V2 Roadmap](docs/IMPLEMENTATION_ROADMAP_V2.md).
