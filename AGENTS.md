# Repository Agent Rules

> Status: CANONICAL
> Applies to: V2
> Last verified against commit: `bbe992e54f9fc583b312f919f32f91f43e53fb06`
> Owner: Project

## Current technical baseline

- Backend: Python 3.10.x (stable validation environment: 3.10.0), `ThreadingHTTPServer`, SQLite, Playwright with visible Chrome/CDP, `ManualActionGate`, raw run artifacts, and a `DataStore` business index.
- OCR: `paddlepaddle==3.2.0`, `paddleocr==3.7.0`, `paddlex==3.7.2`, PP-OCRv6, BOS model source, CPU.
- Frontend: React 19.2.8, TypeScript 7.0.2, Vite 8.2.2, Tailwind CSS 4.3.3, Lucide React 1.43.0.
- Current SQLite schema: 8. Current production UI: `frontend/`; current backend entry: `python -m src.local_api`.

## Source priority

Resolve conflicts in this order:

1. Current code, tests, and governed configuration.
2. `docs/CURRENT_SYSTEM_STATUS.md`.
3. `docs/PRODUCT_REQUIREMENTS_V2.md`.
4. `docs/SYSTEM_V2_ARCHITECTURE.md`.
5. `docs/DOMAIN_MODEL_V2.md`.
6. `docs/UX_SPEC_V2.md`.
7. `docs/KNOWLEDGE_GOVERNANCE.md`.
8. `docs/IMPLEMENTATION_ROADMAP_V2.md`.
9. Accepted ADRs that have not been superseded.
10. `docs/archive/**` is never a current specification.

If code clearly conflicts with Product Requirements, do not silently assume the code is the correct product behavior. Report the conflict and wait for a design decision.

## Permanent product boundaries

- The system discovers page-level risk clues; it does not determine that a product is illegal.
- It does not verify whether a claimed benefit is true, declare that a drug was detected, perform laboratory testing, or predict a risk probability.
- OCR hits are not laboratory results. Recommendations are neither risk probabilities nor enforcement conclusions.
- Keep seller-managed evidence separate from UGC evidence.
- Evidence classified as `excluded_other_product` must not become primary evidence for the current product.
- Preserve Knowledge Gaps explicitly. When reliable support is absent, use `unknown`, `insufficient`, or `unmapped`; never infer a convenient result.

## Data authority

- `output/<run_id>/`: raw collection and processing facts.
- `data/app.db`: query index plus current Review and Sampling business state. Run-derived rows are rebuildable; human decisions require backup/migration care.
- `inspection_recommendation.json`: a derived result under the recorded knowledge and context versions.
- Frozen Sampling export: immutable historical sampling-list fact.
- Historical Validation Set: real test/demo samples; it is not production coverage.

## Forbidden autonomous changes

Without explicit user approval, do not:

- change SQLite schema, entity identity, or entity scope;
- infer or expand regulatory mappings, or create official Claim equivalence from synonyms;
- fabricate a Recommendation to satisfy UI needs;
- treat search-page region, seller address, or manufacturer address as product origin;
- confirm health-food identity from a blue-hat logo alone or from an OCR registration number without official verification;
- change Phase3 or D2-D6 semantics;
- bypass CAPTCHA or security verification;
- alter frozen historical exports or historical Evidence;
- use `git add .`.

## Work discipline

Before each phase:

1. Read the canonical documents relevant to the phase.
2. State the Goal and Non-goals.
3. List files expected to change.
4. Check schema, API, and domain impact.
5. Implement only that phase.
6. Run the required validation from `docs/TEST_ACCEPTANCE_V2.md`.
7. Report gaps and evidence.
8. Do not start the next phase opportunistically.

Use explicit file paths for staging. Preserve unrelated user changes and local runtime data.

## Validation map

- Backend/domain: targeted tests, then `python -m unittest discover -s tests -p "test_*.py"` when the gate requires full coverage.
- Frontend: workflow tests, `npm run typecheck`, and `npm run build` from `frontend/`.
- Knowledge/config: provenance, lifecycle, referential-integrity, and no-implicit-mapping checks.
- Historical validation: use the dedicated builder/tests; do not edit the frozen fixture to make a test pass.
- Real collection: only when the user explicitly authorizes it; never bypass manual verification.
