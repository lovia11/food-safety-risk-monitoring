# Project Status

## Baseline

- Branch: `ux-redesign-v1`
- V2-1 starting commit: `a5be2ed9ff07ddc9b347812f281d9d9e638fc6c6`
- SQLite schema: 8
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

## Current Coverage

- 106 Reference MonitorTargets; 5 enabled Reference targets and 8 enabled validated queries
- Separate development seed: 1 target / 2 queries
- Legacy/current Phase3 clues: 5 categories / 26 keywords
- 3 Evidence-to-risk Bridge mappings; 8 Risk-to-substance/group mappings
- 5 Inspection methods, 117 substances, 132 method-substance links, 37 applicability records

## Current Validation

V2-1 validation: affected Python suites 40 discovered / 39 passed / 1 skipped; frontend workflow 18/18; frontend typecheck and production build passed. Five historical real products were inspected at 1440px and 1080px without live collection.

## Known Limitations

ProductFact/declared origin, HealthFoodIdentity/official lookup, final Claim Taxonomy, claim-consistency assessment, Analytics, Knowledge Base UI, and broad Operational Search coverage are Future V2 work. The system does not make legality, efficacy, laboratory-detection, enforcement, or risk-probability conclusions.

## Current Development Phase

V2-1 — Core UX implemented and validated.

## Next Gate

V2-2 ProductFact and declared origin. It remains a separate gate and has not started.

See [Current System Status](docs/CURRENT_SYSTEM_STATUS.md) and the [V2 Roadmap](docs/IMPLEMENTATION_ROADMAP_V2.md).
