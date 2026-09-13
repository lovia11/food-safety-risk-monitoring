# Project Status

## Baseline

- Branch: `ux-redesign-v1`
- V2-3 starting commit: `0c597dd51ac577dd5d1b35fe90c0bc5a9a2495ca`
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

## Current Coverage

- 106 Reference MonitorTargets; 5 enabled Reference targets and 8 enabled validated queries
- Separate development seed: 1 target / 2 queries
- Legacy/current Phase3 clues: 5 categories / 26 keywords
- 3 Evidence-to-risk Bridge mappings; 8 Risk-to-substance/group mappings
- 5 Inspection methods, 117 substances, 132 method-substance links, 37 applicability records

## Current Validation

V2-3 validation: Python 441 discovered / 440 passed / 1 skipped; Historical Validation builder 6/6; frontend workflow 22/22; frontend typecheck and production build passed. It includes identifier/source/provider/matching fixtures, schema 9→10 preservation, idempotent import/rebuild/API coverage, degradable pipeline integration, a recorded official positive response, and local 1440px/1080px detail/modal inspection without page-level horizontal overflow or new console errors. The five-product Historical Validation Set remains unmodified and all five products resolve to `no_indicator`.

## Known Limitations

Additional ProductFact types, human fact editing, final Claim Taxonomy, claim-consistency assessment, Analytics, Knowledge Base UI, and broad Operational Search coverage are Future V2 work. Official registry lookup remains a low-frequency, cached, best-effort integration because the public site exposes no API stability or availability contract. The system does not make legality, efficacy, laboratory-detection, enforcement, geographic-verification, or risk-probability conclusions.

## Current Development Phase

V2-3 — HealthFood Identity & Official Registry Verification implemented and validated; awaiting acceptance.

## Next Gate

V2-4 Monitor coverage remains a separate gate. Do not begin it before V2-3 is accepted.

See [Current System Status](docs/CURRENT_SYSTEM_STATUS.md) and the [V2 Roadmap](docs/IMPLEMENTATION_ROADMAP_V2.md).
