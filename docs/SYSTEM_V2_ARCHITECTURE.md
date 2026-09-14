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
    ├─ Health-food identity enrichment
    ├─ Phase3 analysis
    ├─ Claim analysis sidecar
    └─ Inspection Recommendation
    ↓
output/<run_id>/ artifacts
    ↓ import/index
DataStore (SQLite schema 11)
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

Search writes run/task state and Candidate facts. Successful Detail collection produces a product directory with `meta.json` and captured source artifacts, including original images when available. OCR preserves `ocr/run_info.json`, `ocr/manifest.json`, diagnostic errors, and combined text as appropriate. Phase3 writes `analysis.json`. The V2 Claim analyzer then consumes the stable, ID-bearing Evidence records represented by Phase3 evidence details and writes `claim_analysis.json`; it never scans Discovery inputs or raw collector sources directly. InspectionRuntime may write `inspection_recommendation.json` through the unchanged legacy compatibility path.

After OCR artifacts are available, the independent ProductFact extractor reads existing DOM/OCR artifacts and writes `product_facts.json`. The HealthFood Identity enrichment then reads the same bounded seller-managed sources, optionally queries the official registry through a cached provider, and writes `health_food_identity.json`. Claim analysis is also degradable: a taxonomy/derivation failure writes `claim_analysis_error.json` and never changes Phase3 success, Analysis readiness, Review, Sampling, Recommendation readiness, or Product status. Existing successful products can derive a missing Claim sidecar from their stable analysis Evidence without re-running collection, OCR, or Phase3.

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
| `output/<run_id>/` | Raw and processed run facts, evidence inputs, `product_facts.json`, `health_food_identity.json`, `claim_analysis.json`, analysis and recommendation artifacts. |
| `output/_registry_cache/health_food/` | Best-effort official query cache with raw JSON, hash, retrieval time and normalized result; never committed. |
| `data/app.db` | Schema 11 query/read index including ProductFact, HealthFoodIdentity, ClaimMention/ClaimSignal, normalized registry projections, imported run relationships, human Review, mutable current Sampling Membership, and frozen-list index. |
| Frozen JSON/XLSX/evidence export | Immutable historical sampling-list fact at export time. |
| Governed `config/*.json` | Versioned operational/reference knowledge loaded by current runtime. |

`config/claim_taxonomy_v2.json` remains the governed **design baseline** and is now the sole runtime Claim taxonomy. Product-Snapshot `claim_analysis.json` is the derived ClaimMention/ClaimSignal authority; SQLite `claim_mentions`, `claim_signals`, and `claim_signal_mentions` are rebuildable projections. A complete artifact with empty arrays means zero Claims; a missing artifact projects `not_generated`, and an invalid/failed sidecar projects `error`. Raw OCR/DOM/title artifacts remain source facts and Evidence remains the source-preserving observation layer; neither is replaced by a Claim record.

SQLite run-derived data can be re-imported, but the database also contains human business mutations. Rebuilding it without preserving Review and Sampling state may lose decisions. The term “index” therefore does not mean “always safe to delete.”

### 1.4 Current API responsibilities

The Local API provides products, filter options, Snapshot workspaces, inspection context, task/archive operations, Review decisions, current/historical Sampling queries, and export/download operations. `GET /api/monitor-targets` defaults to the operational set for compatibility; `scope=reference` exposes all 106 formal Reference objects with `operational`, `query_pending`, or `paused` availability and derived coverage counts. Monitor task creation enforces the same operational predicate server-side. Old contract compatibility retained by the backend does not make an old frontend current.

Workspace DTOs combine Snapshot, Evidence, additive Claim analysis status/Mentions/Signals, ProductFacts/declared-origin presentation, HealthFoodIdentity presentation, Review, assets, inspection, readiness, and Sampling presentation so React does not read filesystem artifacts or infer eligibility/identity independently. V2-5B1 adds only frontend types; user-visible Claim presentation remains a V2-5B2 concern.

## 2. Current domain separation

- Product is stable marketplace identity; ProductSnapshot is one observed state.
- Evidence and Review are Snapshot-scoped.
- ProductFact is Snapshot-scoped derived data with exact artifact provenance. The current implementation supports only `declared_origin`.
- HealthFoodIdentity is Snapshot-scoped; HealthFoodRegistryRecord is an official identifier-keyed reusable projection. Neither rewrites Product, Review, Sampling, Evidence or Risk.
- ClaimMention is Evidence- and Snapshot-scoped; ClaimSignal aggregates same-Snapshot Mentions by governed marketing topic. Neither creates HealthFunction, RiskSignal, Recommendation, Review, or Sampling state.
- Current Sampling Membership is Product-scoped and records a source Snapshot.
- Inspection Recommendation is derived from Evidence, Product Context, and versioned knowledge.
- Review repositories do not write Membership; Sampling repositories do not write Review. Application services own compound transactions.
- Historical Sampling item identifiers are frozen identifiers; they need not retain foreign keys to live ProductSnapshots or Tasks.

### 2.1 Monitor coverage boundary — CURRENT V2-4A

Governed JSON remains the authority for MonitorTarget/SearchQuery source, lifecycle, and enablement; SQLite remains the imported read model and requires no V2-4A schema change. A pure domain projection derives availability and coverage. Discovery accepts only enabled `search_validated` queries and continues to deduplicate by stable Product ID before applying one task-level Detail/analysis cap.

Search-only validation artifacts live under `output/query_validation/<batch_id>/` and are never production evidence. Reviewed decisions are summarized in the tracked validation ledger; candidates cannot become operational through runtime output alone.

## 3. Target V2 architecture

The ProductFact, HealthFood Identity, and Claim Analyzer branches below are current; the other branches and read models remain target design until their own gates are accepted:

```text
Current artifact pipeline
    ├─ ProductFact Extractor (current: declared_origin)
    ├─ HealthFood Identity Resolver (current)
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

### 3.1 ProductFact Extractor — CURRENT V2-2

Extracts structured facts only from identifiable Snapshot artifacts. It preserves raw value, normalized value, exact source, extraction method, and verification state. `product_facts.json` is the derived artifact authority; the generic SQLite `product_facts` table is a rebuildable projection. The current allowlist covers explicit declared-origin labels in seller-managed DOM parameter sections and conservative labeled detail-image OCR. It never infers origin from search region, title/UGC wording, shipping data, raw-material origin or addresses.

### 3.2 HealthFood Identity Resolver — CURRENT V2-3

Creates clues and registration/filing candidates only from current-product seller-managed DOM and detail-image OCR. UGC and recommendation-area DOM are excluded. Ambiguous OCR characters are retained without correction or lookup. A provider abstraction supports low-frequency cached official lookup and governed imported snapshots. A found record becomes `verified_match` only when an explicit page product name equals the official product name after formatting-only normalization; title-only similarity is insufficient. Candidate, unavailable, not-found, unverified relation, mismatch and conflict states remain distinct. See [HEALTH_FOOD_REGISTRY_SOURCE_AUDIT.md](HEALTH_FOOD_REGISTRY_SOURCE_AUDIT.md).

### 3.3 Claim Analyzer — CURRENT V2-5B1; consistency assessor — FUTURE

The accepted Claim contract now implements the first four nodes of this pipeline:

```text
ProductSnapshot
→ seller-managed Evidence
→ ClaimMention exact-expression extraction
→ ClaimSignal governed normalization
→ [future] Claim consistency / RiskSignal
→ [future] inspection bridge
```

ClaimMention preserves the raw observed text, matching expression, Evidence identity and source locator. ClaimSignal groups same-Snapshot mentions under a governed marketing `claim_type` while retaining every mention/Evidence identity. Only `seller_managed` Evidence enters the formal runtime; UGC is auxiliary only, `excluded_other_product` is forbidden, and SearchQuery/task keywords are not inputs. Matching is formatting-normalized deterministic literal substring matching. All overlapping governed expressions are retained. Mention order is Evidence order, taxonomy-expression order, then occurrence order; signal order is taxonomy Claim-type order.

V2-5B1 implements runtime extraction, artifact authority, schema 11 projection, and additive Snapshot API fields. The consistency assessor, Claim-to-HealthFunction mapping, Claim-to-Risk mapping, visible Claim UX, and legacy presentation migration remain future. A marketing paraphrase never becomes an Official Health Function without an explicit governed mapping, and a ClaimSignal never directly selects an inspection substance or method.

### 3.4 Knowledge Resolver

Resolves only versioned, lifecycle-valid, provenance-bearing links across claims, risk categories, substances/groups, methods, applicability, regulatory documents, and health-food records. Missing links remain Knowledge Gaps.

### 3.5 Analytics Read Model and Knowledge API

Analytics will expose governed metric definitions and denominators, not ad hoc frontend counts. The Knowledge API will serve the same runtime datasets used by analysis; no parallel UI-only knowledge copy is permitted.

## 4. Provenance architecture

Every automatically extracted ProductFact, ClaimSignal, or identity clue must support this trace:

```text
ProductSnapshot
→ source artifact path and content origin
→ exact text or image region
→ extraction/classification method
→ derived record and verification state
→ downstream assessment or recommendation
```

Derived records record the applicable dataset/version. Re-running with new knowledge may create a new derived result; it must not rewrite historical source Evidence or a frozen export.

The Snapshot/detail API now adds `claimAnalysisStatus`, `claimMentions[]`, and `claimSignals[]`. Existing `detectedEffects`/`effect` fields remain legacy compatibility fields; Product-list Claim filters and visible Claim UX remain out of scope for V2-5B1.

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
