# Current System Status

> Status: CANONICAL
> Applies to: V2
> V2-3 starting baseline: `0c597dd51ac577dd5d1b35fe90c0bc5a9a2495ca`
> Owner: Project

This document describes implemented behavior through the V2-3 delivery. Future requirements belong in the other canonical V2 documents.

## Baseline

- Branch: `ux-redesign-v1`
- V2-3 starting HEAD: `0c597dd51ac577dd5d1b35fe90c0bc5a9a2495ca`
- SQLite schema: 10
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
- ProductFact is Snapshot-scoped. Its authority is `product_facts.json`; SQLite is a rebuildable query projection. V2-2 implements only `declared_origin`.
- HealthFoodIdentity is a separate Snapshot-scoped enrichment. Its authority is `health_food_identity.json`; SQLite schema 10 indexes the identity assessment and reusable normalized official record. Page clue, identifier candidate, official record and verified current-product match are never collapsed into one boolean.
- Review is Snapshot-scoped with `pending`, `recommend_follow_up`, and `no_further_action`.
- Current Sampling Membership is Product-scoped and records its source Snapshot.
- Review and Sampling repositories do not mutate each other. Application-level decision transactions coordinate compound business actions.
- A pending Snapshot may coexist with a Product membership based on another Snapshot.
- Frozen Sampling Lists and their item indexes preserve historical export facts.

## Current product-reading UX

- Product Overview derives a local saved-asset thumbnail URL for each representative Snapshot. Missing or unreadable assets fall back to one consistent placeholder; no remote marketplace image is required.
- Every Product row is a pointer-accessible and keyboard-accessible detail target while preserving independent-control boundaries.
- Product Detail and Inspection Workspace share a Snapshot summary for page clues, seller/UGC Evidence counts, knowledge-bridge state, and Review state.
- A single Snapshot uses a compact timestamp/source row; two or more Snapshots use the selectable timeline.
- Evidence records remain unchanged as facts. The React presentation groups them by `content_origin`, `source_type`, and source asset/context, collapses repeated snippets for reading, and retains all Evidence IDs in the group model.
- Seller-managed Evidence is primary, UGC is explicitly auxiliary, and excluded-other-product content is outside the primary counts.
- Saved images and OCR text open in an in-application modal. Image preview supports close/escape/backdrop, previous/next, zoom, viewport containment, and the Evidence associated with the active image.
- Analysis presentation distinguishes not analyzed, analyzed with zero Evidence, Evidence without a verified mapping, mapped Risk without a verified Method, available Recommendation, unavailable Recommendation, and Recommendation error.
- Search-page region and product-declared origin are independent keys. Explicit seller-managed DOM parameters and conservatively labeled detail-image OCR may supply `declared_origin`; search region, title wording, UGC, shipping, seller/manufacturer/warehouse addresses and raw-material origin never do.
- Product Detail and Inspection Workspace expose a separate 保健食品身份 section. Only a valid unambiguous identifier, a found official record, and formatting-normalized exact equality with an explicit page product name can display `保健食品 · 已核验`. Page and official sources remain separate; candidates, unavailable lookup, not-found, mismatch and conflict remain explicit.
- A missing declared origin is `—`. Equal DOM/OCR values retain both sources under one presentation value; different explicit values are displayed as a conflict without automatic arbitration.
- Origin source trace opens the exact DOM/OCR text and reuses the existing image Lightbox for OCR image provenance.

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
- V2-1 validation: affected Python suites 40 discovered / 39 passed / 1 skipped; frontend workflow 18/18; frontend typecheck and production build passed. The five-product historical set was inspected at 1440px and 1080px with no page-level horizontal overflow or browser console error.
- V2-2 validation: Python 414 discovered / 413 passed / 1 skipped; frontend workflow 19/19; frontend typecheck and production build passed. Deterministic A–L origin fixtures, schema 8→9 preservation, import/rebuild/API tests, and offline extraction against the same five-product historical set produced six source records, including one explicit conflict. The Product Detail source trace was inspected at 1440px and 1080px with no page-level horizontal overflow or browser console error.
- V2-3 source support is documented in [HEALTH_FOOD_REGISTRY_SOURCE_AUDIT.md](HEALTH_FOOD_REGISTRY_SOURCE_AUDIT.md). Ordinary tests use a governed recorded official response; live official lookup is best-effort and never a CI dependency.
- The five-product Historical Validation Set contains no valid registration/filing identifier and no positive strong identity candidate. Product `674221193698` has an explicit negative `是否保健食品…否` parameter and remains `no_indicator`; the other four also remain `no_indicator`. No historical artifact was edited or re-OCRed.
- V2-3 validation: Python 441 discovered / 440 passed / 1 skipped; Historical Validation builder 6/6; frontend workflow 22/22; frontend typecheck and production build passed. Identifier, provider, matching, degradation, schema 9→10 and artifact rebuild contracts are covered. Product Detail plus page/official evidence dialogs were inspected locally at 1440px and 1080px without page-level horizontal overflow or new browser console errors.

## Known limitations and future changes

The following are **not implemented** at this baseline:

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
