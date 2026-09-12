# System V2 Architecture

> Status: CANONICAL
> Applies to: V2
> Last verified against commit: `bbe992e54f9fc583b312f919f32f91f43e53fb06`
> Owner: Project

This document deliberately separates current implementation from target V2 design. Items under Target Architecture are `FUTURE CHANGE` until implemented and accepted.

## 1. Current architecture

```text
React / Vite
    ↓ HTTP /api
Local API (ThreadingHTTPServer)
    ↓
TaskManager
    ↓
StandalonePipeline
    ├─ Search / Discovery
    ├─ Product Detail collection
    ├─ OCR
    ├─ Phase3 analysis
    └─ Inspection Recommendation
    ↓
output/<run_id>/ artifacts
    ↓ import/index
DataStore (SQLite schema 8)
    ↓
ReviewDecisionService / SamplingStore / SamplingExportService
```

### 1.1 Runtime ownership

- The React frontend consumes typed JSON contracts; it must not reconstruct cross-artifact business conclusions.
- `LocalApiApplication` composes stores and services and serves `frontend/dist` in the production-style local run.
- `TaskManager` owns task lifecycle and starts pipeline workers.
- The pipeline worker owns its Playwright page. HTTP request threads never manipulate the page.
- `ManualActionGate` and the web adapter coordinate verification acknowledgement and worker-side rechecking. CLI execution without an adapter may use terminal confirmation.
- One OCR runtime is shared across products in a run. Runtime initialization failures are recorded per affected product without making those products reviewable.

### 1.2 Current pipeline artifacts and stage contract

Search writes run/task state and Candidate facts. Successful Detail collection produces a product directory with `meta.json` and captured source artifacts, including original images when available. OCR preserves `ocr/run_info.json`, `ocr/manifest.json`, diagnostic errors, and combined text as appropriate. Phase3 writes `analysis.json`. InspectionRuntime may write `inspection_recommendation.json`.

The authoritative predicate in `src/pipeline_contract.py` distinguishes:

- `detailCollected`: Detail success is represented by an eligible product status and a real `meta_path`.
- `ocrInputReady`: Detail is collected and at least one original image is available.
- `ocrReady`: OCR input is ready and at least one image succeeded.
- `analysisReady`: product processing succeeded, OCR is ready, and `analysis_path` exists.
- `reviewEligible`: equal to the current successful-analysis readiness requirement.

The conceptual flow is:

```text
DetailCollected
→ OcrInputReady
→ OcrReady
→ AnalysisReady
→ RecommendationAvailable (degradable)
→ ReviewEligible
```

Recommendation is not a Review gate. A successful analysis with zero Evidence is valid and counts as analysis-complete. Search-only, Detail-failed, and OCR-failed snapshots may remain visible as product/run facts but do not enter the pending Review queue.

### 1.3 Current storage and authority

| Store | Current role |
|---|---|
| `output/<run_id>/` | Raw and processed run facts, evidence inputs, analysis and recommendation artifacts. |
| `data/app.db` | Query/read index, imported run relationships, human Review, mutable current Sampling Membership, frozen-list index. |
| Frozen JSON/XLSX/evidence export | Immutable historical sampling-list fact at export time. |
| Governed `config/*.json` | Versioned operational/reference knowledge loaded by current runtime. |

SQLite run-derived data can be re-imported, but the database also contains human business mutations. Rebuilding it without preserving Review and Sampling state may lose decisions. The term “index” therefore does not mean “always safe to delete.”

### 1.4 Current API responsibilities

The Local API provides products, filter options, Snapshot workspaces, inspection context, task/archive operations, Review decisions, current/historical Sampling queries, and export/download operations. Old contract compatibility retained by the backend does not make an old frontend current.

Workspace DTOs combine Snapshot, Evidence, Review, assets, inspection, readiness, and Sampling presentation so React does not read filesystem artifacts or infer eligibility independently.

## 2. Current domain separation

- Product is stable marketplace identity; ProductSnapshot is one observed state.
- Evidence and Review are Snapshot-scoped.
- Current Sampling Membership is Product-scoped and records a source Snapshot.
- Inspection Recommendation is derived from Evidence, Product Context, and versioned knowledge.
- Review repositories do not write Membership; Sampling repositories do not write Review. Application services own compound transactions.
- Historical Sampling item identifiers are frozen identifiers; they need not retain foreign keys to live ProductSnapshots or Tasks.

## 3. Target V2 architecture — FUTURE CHANGE

The following components are target design, not current implementation:

```text
Current artifact pipeline
    ├─ ProductFact Extractor
    ├─ HealthFood Identity Resolver
    ├─ Claim Analyzer
    ├─ Claim Consistency Assessor
    └─ Knowledge Resolver
              ↓
       provenance-bearing domain records
              ↓
       DataStore / domain read models
          ├─ Current product workspace
          ├─ Analytics Read Model
          └─ Knowledge API
```

### 3.1 ProductFact Extractor

Extracts structured facts only from identifiable Snapshot artifacts. It preserves raw value, normalized value, exact source, extraction method, and verification state. It must not infer origin from search region or addresses.

### 3.2 HealthFood Identity Resolver

Creates an identity candidate from page clues, then compares it with official registration/filing data. Candidate, verified, conflict, not-found, and insufficient states remain distinct.

### 3.3 Claim Analyzer and consistency assessor

The Claim Analyzer classifies actual page language. It does not turn a marketing paraphrase into an Official Health Function without an explicit mapping. The consistency assessor compares verified identity, official functions, and page claims and emits evidence-bearing assessment details, never a legal verdict.

### 3.4 Knowledge Resolver

Resolves only versioned, lifecycle-valid, provenance-bearing links across claims, risk categories, substances/groups, methods, applicability, regulatory documents, and health-food records. Missing links remain Knowledge Gaps.

### 3.5 Analytics Read Model and Knowledge API

Analytics will expose governed metric definitions and denominators, not ad hoc frontend counts. The Knowledge API will serve the same runtime datasets used by analysis; no parallel UI-only knowledge copy is permitted.

## 4. Provenance architecture

Every future automatically extracted ProductFact, ClaimSignal, or identity clue must support this trace:

```text
ProductSnapshot
→ source artifact path and content origin
→ exact text or image region
→ extraction/classification method
→ derived record and verification state
→ downstream assessment or recommendation
```

Derived records record the applicable dataset/version. Re-running with new knowledge may create a new derived result; it must not rewrite historical source Evidence or a frozen export.

## 5. Reliability boundaries

- Browser security challenges stay human-mediated and worker-rechecked.
- Artifact paths exposed through APIs require path containment checks.
- OCR diagnostics survive top-level failure where possible.
- Stage projections use explicit success/failure counts, not terminal-task shortcuts.
- Review mutations reject non-eligible Snapshots on the server.
- Recommendation failure degrades the recommendation panel only.
- Knowledge updates cannot silently broaden mappings or retroactively mutate frozen history.

## 6. Change discipline

Any target component that requires a schema or API change must first update the domain contract and receive its phase gate. This document does not authorize implementation. See [IMPLEMENTATION_ROADMAP_V2.md](IMPLEMENTATION_ROADMAP_V2.md) and [TEST_ACCEPTANCE_V2.md](TEST_ACCEPTANCE_V2.md).
