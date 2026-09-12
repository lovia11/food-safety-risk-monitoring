# Current System Status

> Status: CANONICAL
> Applies to: V2
> Last verified against commit: `bbe992e54f9fc583b312f919f32f91f43e53fb06`
> Owner: Project

This document describes only behavior implemented at the verified commit. Future requirements belong in the other canonical V2 documents.

## Baseline

- Branch: `ux-redesign-v1`
- Verified HEAD: `bbe992e54f9fc583b312f919f32f91f43e53fb06`
- SQLite schema: 8
- Backend entry: `python -m src.local_api`
- Production static UI: `frontend/dist`, built from `frontend/`
- Current primary navigation: 商品总览、排查档案、抽检清单
- Retired V1 `web/` frontend: absent from the active workspace

## Current runtime

The React/Vite frontend calls a local `ThreadingHTTPServer`. `TaskManager` starts `StandalonePipeline`, which performs Search/Discovery, Detail collection, OCR, Phase3 analysis, and Inspection Recommendation. Run artifacts are written under `output/<run_id>/`; `DataStore` imports queryable run facts into SQLite and supports Review and Sampling workflows.

Playwright uses a visible Chrome/CDP session. `ManualActionGate` lets a web task wait for login or verification while the worker retains browser ownership; the HTTP thread only acknowledges user action. CLI execution without a web adapter retains the terminal fallback.

## Pipeline readiness

The shared backend predicate currently projects:

```text
DetailCollected
→ OcrInputReady
→ OcrReady
→ AnalysisReady
→ RecommendationAvailable (degradable)
→ ReviewEligible
```

`ReviewEligible` is driven by successful Phase3 analysis. Recommendation generation is degradable: a Recommendation error does not invalidate Evidence or prevent Review. Search-only, Detail-failed, and OCR-failed snapshots are retained as facts but are not business-pending Reviews.

Task flow states are `future`, `active`, `done`, `partial`, and `failed`, derived from stage facts and counts rather than from terminal task stage alone.

## Current data and workflow

- One stable Product may have multiple ProductSnapshots.
- Evidence remains snapshot-scoped and preserves seller-managed, UGC, and excluded-other-product origins.
- Review is Snapshot-scoped with `pending`, `recommend_follow_up`, and `no_further_action`.
- Current Sampling Membership is Product-scoped and records its source Snapshot.
- Review and Sampling repositories do not mutate each other. Application-level decision transactions coordinate compound business actions.
- A pending Snapshot may coexist with a Product membership based on another Snapshot.
- Frozen Sampling Lists and their item indexes preserve historical export facts.

## Current OCR environment

The reproducible supported baseline is:

- Python 3.10.0 (Python 3.10.x runtime family)
- PaddlePaddle 3.2.0
- PaddleOCR 3.7.0
- PaddleX 3.7.2
- PP-OCRv6, BOS model source, CPU

OCR writes versioned run diagnostics. No input image and zero successful images are stage failures; partial image success may continue with failed items preserved in the manifest.

## Current governed coverage

Counts below are computed from the governed configuration at the verified commit:

| Area | Current coverage |
|---|---:|
| Reference MonitorTargets | 106 |
| Enabled Reference targets | 5 |
| Enabled validated Reference queries | 8 |
| Separate development-seed targets/queries | 1 / 2 |
| Legacy/current Phase3 clue categories/keywords | 5 / 26 |
| Evidence-to-risk Bridge mappings | 3 |
| Risk-to-substance/group mappings | 8 |
| Inspection methods | 5 |
| Inspection substances | 117 |
| Method-substance links | 132 |
| Method applicability records | 37 |
| Substance regulatory contexts | 1 |

The 106-object Reference is not 106-object operational search coverage. Only enabled, validated queries are operational. The separate development seed is not merged into the verified Reference count.

## Current validation support

- Historical Validation Set: five real sample products under `historical_validation_20260911`, intended for deterministic test/demo support without live collection.
- Its scope is described in `HISTORICAL_VALIDATION_CANDIDATES.md`; it is not representative production coverage.
- V2-0B validation: Python 397 discovered / 396 passed / 1 skipped; Historical Validation builder 6/6; frontend workflow 12/12; frontend typecheck and production build passed.

## Known limitations and future changes

The following are **not implemented** at this baseline:

- **FUTURE CHANGE:** ProductFact runtime and structured `declared_origin` extraction.
- **FUTURE CHANGE:** HealthFoodIdentity and official registry verification.
- **FUTURE CHANGE:** final ClaimTaxonomy and claim-consistency assessment.
- **FUTURE CHANGE:** Analytics pages and governed metric read models.
- **FUTURE CHANGE:** Knowledge Base UI and its public read APIs.
- **FUTURE CHANGE:** operational search coverage beyond the currently enabled validated subset.

The five existing Effect categories are an operational Phase3 clue vocabulary, not the final V2 Claim taxonomy.

## Canonical references

- Product boundaries: [PRODUCT_REQUIREMENTS_V2.md](PRODUCT_REQUIREMENTS_V2.md)
- Current/target architecture: [SYSTEM_V2_ARCHITECTURE.md](SYSTEM_V2_ARCHITECTURE.md)
- Domain model: [DOMAIN_MODEL_V2.md](DOMAIN_MODEL_V2.md)
- Roadmap: [IMPLEMENTATION_ROADMAP_V2.md](IMPLEMENTATION_ROADMAP_V2.md)
