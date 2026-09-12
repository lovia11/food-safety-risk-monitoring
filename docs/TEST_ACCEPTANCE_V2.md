# Test and Acceptance V2

> Status: CANONICAL
> Applies to: V2
> Last verified against commit: `bbe992e54f9fc583b312f919f32f91f43e53fb06`
> Owner: Project

Testing is proportional to changed risk. A phase must pass targeted checks before broad regression. Real-world validation supplements deterministic tests; it never replaces them.

## 1. Universal gate

Every implementation report states the starting commit, changed files, schema/API/domain impact, targeted tests, broad tests required by the phase, real validation performed, known gaps, new commit, and git status. Do not change historical fixture hashes to force a pass.

## 2. Documentation gate

- All canonical files declare `Status: CANONICAL`, `Applies to: V2`, verified commit, and `Owner: Project`.
- Links resolve and canonical documents link to the right authority.
- Terminology matches the registry in Product Requirements.
- Current implementation and Future changes are distinguishable.
- Active docs identify schema 8 as the sole current schema; prior-version details remain only in archived or explicit migration history.
- Retired IA and `web/` do not appear as current.
- Archived material is marked non-normative and is never cited as a higher authority.
- A cold-start reader can answer the 16 canonical baseline questions without chat context.

## 3. Baseline regression commands

Run from repository root with the intended Python interpreter:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

Run frontend checks from `frontend/`:

```powershell
npm run test:workflow
npm run typecheck
npm run build
```

Historical Validation builder changes additionally run their dedicated test module(s). The exact targeted command should be reported from the current test filename, not copied from an obsolete handoff.

## 4. UX gate

Required deterministic coverage:

- product-list/filter/query and Snapshot selection workflows;
- Evidence Source Group presentation while preserving distinct Evidence records;
- sidebar session state and keyboard focus;
- lightbox open/close, `Esc`, zoom, previous/next and active evidence;
- recommendation failure that leaves Evidence/Review usable;
- one-Snapshot compressed and multi-Snapshot timeline behavior;
- loading, API error, true empty, missing image, long title, zero Evidence, unmapped Evidence, and historical Snapshot.

Required visual acceptance at 1440px and 1080px includes list-only and split-detail modes. Typecheck and production build are mandatory. Do not loop indefinitely for minor pixel differences.

## 5. ProductFact gate — Future V2-2

At minimum test:

- every fact has an explicit Snapshot and reconstructable source;
- missing origin remains absent and presents `—`;
- conflicting origins remain separate/conflicted rather than arbitrarily selected;
- OCR-derived and DOM-derived facts retain distinct methods and paths;
- exact source text/image is available;
- normalization does not overwrite raw value;
- search-page region, seller location and manufacturer location are never inferred as declared origin;
- re-import and historical Snapshot behavior preserve scope and provenance.

Real validation includes clear-origin, missing-origin and conflicting-origin pages reviewed against the artifact.

## 6. HealthFoodIdentity gate — Future V2-3

At minimum test:

- real positive with authoritative record match;
- logo-only negative/insufficient case;
- registration number mismatch;
- official record not found or source unavailable;
- ambiguous product name;
- conflicting page clues;
- record version/effective-state behavior;
- no boolean collapse and no automatic legal conclusion.

Real validation compares a bounded set with official records and preserves the lookup source/time.

## 7. Claim gate — Future V2-5/V2-6

At minimum test:

- exact official claim;
- marketing paraphrase with and without a verified mapping;
- disease/treatment wording;
- ambiguous expression;
- UGC-only expression;
- seller-managed and UGC occurrences kept distinct;
- unmatched claim/Knowledge Gap;
- ClaimSignal, HealthFunction and RiskSignal stored and presented independently;
- consistency assessment exposes compared claims, functions, matched/unmatched items, evidence, source and gaps rather than pass/fail.

## 8. Knowledge gate

Every governed dataset change tests:

- required provenance and dataset/version identity;
- stable unique IDs and referential integrity;
- lifecycle and supersession behavior;
- temporal/jurisdiction fields where supplied;
- only eligible lifecycle records drive runtime results;
- no implicit Claim, Risk, Substance, Method, applicability, origin, or identity mapping;
- group mappings are not silently expanded;
- UI/API reads the same runtime dataset;
- per-layer coverage metrics use correct denominators.

## 9. Pipeline and Review gate

- Search Candidate is not Detail success or Review eligibility.
- Detail, OCR input, OCR, analysis, recommendation and Review readiness are independently tested.
- No OCR inputs and zero successful OCR images are failures; partial success preserves failed manifest items.
- Analysis success with zero Evidence still counts as analysis-complete and Review-eligible.
- Recommendation error does not block an otherwise eligible Review.
- Detail/OCR/analysis failure cannot enter business pendingReview or accept Review mutation.
- Mixed-result integration contains successful, Detail-failed, OCR-failed, and search-only products and validates task-flow counts/states.
- Current Product Membership based on an old Snapshot does not mark a new pending Snapshot as reviewed.

## 10. Data migration/API gate

Any future schema change requires forward migration from the current schema, old-data preservation, invariant tests, import/rebuild behavior, transaction rollback tests, and an explicit downgrade/backup statement. API changes require DTO contract tests, compatibility decisions, filter/pagination tests, path containment, and N+1 review.

No roadmap entry by itself authorizes schema/API work.

## 11. Real collection gate

Live Taobao access requires explicit user authorization and a minimal bounded run. Never bypass CAPTCHA or verification. Record run ID, environment, task parameters, first failure, diagnostic artifacts, Detail/OCR/analysis/recommendation counts, and whether each acceptance artifact exists. Stop at the first new contract blocker rather than mass-retrying products.

## 12. Acceptance result

Use only:

```text
PASS — <phase-specific accepted baseline>
```

or:

```text
FAIL — <remaining contradictions or blockers>
```

A partial test run cannot support a full PASS unless the approved phase gate explicitly limits scope.
