# Project Status

## Baseline

- Branch: `ux-redesign-v1`
- Verified commit: `bbe992e54f9fc583b312f919f32f91f43e53fb06`
- SQLite schema: 8
- Active UI: React/Vite in `frontend/`
- Backend: Python 3.10.x local API and pipeline

## Current Capabilities

- Search/Discovery → Detail → OCR → Phase3 → degradable Inspection Recommendation
- Product Overview and Snapshot workspace with Evidence, context and Review
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

V2-0B validation: Python 397 discovered / 396 passed / 1 skipped; Historical Validation builder 6/6; frontend workflow 12/12; typecheck and production build passed.

## Known Limitations

ProductFact/declared origin, HealthFoodIdentity/official lookup, final Claim Taxonomy, claim-consistency assessment, Analytics, Knowledge Base UI, and broad Operational Search coverage are Future V2 work. The system does not make legality, efficacy, laboratory-detection, enforcement, or risk-probability conclusions.

## Current Development Phase

V2-0B — canonical architecture and development baseline.

## Next Gate

V2-1 Core UX: thumbnail, row click, detail summary, Evidence Source Group presentation, lightbox, compact single-Snapshot timeline, and explicit knowledge states. Do not begin it until V2-0B is approved.

See [Current System Status](docs/CURRENT_SYSTEM_STATUS.md) and the [V2 Roadmap](docs/IMPLEMENTATION_ROADMAP_V2.md).
