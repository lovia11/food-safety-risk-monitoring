# Knowledge Base UI V2

> Status: CANONICAL DESIGN BASELINE
> Applies to: V2-8
> Last verified phase: V2-8B
> Owner: Project

## 1. Purpose and boundary

The Knowledge Base is a read-only view over the same governed knowledge used by runtime analysis. It is not a new source of truth, an editing console, a compliance engine, or a place to reconstruct relationships in the browser.

V2-8A implements the read model, GET API, TypeScript DTOs and presentation-mapper contract. V2-8B implements the visible Sidebar route, six tabs, server-driven list controls and read-only detail Drawer. Neither phase adds a knowledge mutation path.

The future page has exactly six tabs:

1. 食药物质目录
2. 保健功能
3. 风险物质
4. 风险映射
5. 检验方法
6. 官方文件

Every displayed record must map back to a current governed config or its schema-13 rebuildable SQLite projection. Frontend code must not hardcode a second catalog, infer a relation, or turn a missing fact into a negative fact.

## 2. Authorities and read path

| Domain | Authority | Read path |
|---|---|---|
| 食药物质目录 | `config/monitor_targets.reference.json` / Monitor Reference | Schema-13 `monitor_*` projection used by task discovery policy |
| 保健功能 | `config/health_functions_v2.json` (`health-functions-v2.0`) | Existing strict HealthFunction loader used by Claim Consistency |
| 风险物质 | `config/inspection_reference.json` Substance facts | Schema-13 Inspection projection |
| 风险映射 | `config/risk_substance_reference.json` | Schema-13 Risk mapping projection used by Recommendation |
| 检验方法 | `config/inspection_reference.json` Method, analyte and applicability facts | Schema-13 Inspection projection used by Recommendation |
| 官方文件 | Inspection `RegulatoryDocument` records | Schema-13 normalized document projection |

SQLite remains a rebuildable query index. The HealthFunction catalog is not duplicated into SQLite merely for display. `KnowledgeReadService` validates and reads the same governed JSON used by its production consumer.

## 3. Read-only API contract

All endpoints are GET-only:

```text
GET /api/knowledge/summary
GET /api/knowledge/monitor-targets
GET /api/knowledge/health-functions
GET /api/knowledge/substances
GET /api/knowledge/risk-mappings
GET /api/knowledge/inspection-methods
GET /api/knowledge/regulatory-documents
```

There are no Knowledge POST, PUT or DELETE operations. Reads do not modify Discovery, Claim, HealthFoodIdentity, ClaimConsistency, Risk, Recommendation, Review or Sampling state.

### 3.1 Pagination and search

Every collection accepts:

- `query`: deterministic case-insensitive substring match over the domain's named identity fields;
- `limit`: 1–100, default 50;
- `offset`: zero or greater, default 0.

Every collection returns:

```text
items
count
total
limit
offset
hasMore
```

Filters are applied on the server before pagination. Invalid bounded-enum filters or pagination return `400 invalid_knowledge_query`.

### 3.2 Domain filters

| Endpoint | Additional filters |
|---|---|
| monitor-targets | `availability=operational|query_pending|paused` |
| health-functions | `framework=<framework_id>`, `status=<function status>` |
| substances | none beyond `query` |
| risk-mappings | `target_type=substance|substance_group`, `status=current|historical` |
| inspection-methods | `status=current|superseded|revoked|verification_pending`, `knowledge_depth=reference_only|analyte_verified|applicability_verified|recommendation_ready` |
| regulatory-documents | `status=current|superseded|revoked|verification_pending`, `document_type=official_method_page|official_announcement|national_standard_record` |

No endpoint implements fuzzy, semantic or full-text inference.

## 4. Summary contract

`/api/knowledge/summary` reports separate counts with explicit domain denominators:

- `referenceMonitorTargets`
- `operationalMonitorTargets`
- `queryPendingMonitorTargets`
- `pausedMonitorTargets`
- `healthFunctions`
- `inspectionMethods`
- `recommendationReadyMethods`
- `referenceOnlyMethods`
- `substances`
- `riskMappings`
- `groupMappings`
- `regulatoryDocuments`

It also returns the governing dataset identities/versions. It never emits a blended “知识库完整度”, accuracy, national coverage or risk-recognition percentage.

At the V2-8 baseline the separate facts are 106 Reference MonitorTargets, 16 operational targets, 88 query-pending targets, 2 paused targets, 25 HealthFunction records (24 non-nutrient current functions plus one separately governed nutrient-supplement catalog root), 7 InspectionMethods, 6 `recommendation_ready`, 1 `reference_only`, 201 Substances, 8 Risk mappings, 3 group mappings and 7 RegulatoryDocuments.

## 5. Tab contracts

### 5.1 食药物质目录

- **List fields:** standard name, availability, validated SearchQuery availability, dataset/version.
- **Detail fields:** `targetId`, target type, governed SearchQueries, target source and availability reason.
- **Filter:** query and availability.
- **Empty state:** “当前筛选下没有食药物质目录记录。”
- **Knowledge Gaps:** no validated query; paused operational strategy.
- **Source trace:** target-level official source plus Monitor Reference dataset/version.
- **Forbidden reading:** Reference membership is not Operational Search readiness. Never present “106/106 已监测”.

### 5.2 保健功能

- **List fields:** official name, framework, ordinal, status, version.
- **Detail fields:** framework identity/type/coverage, exact official transition aliases and alias provenance.
- **Filter:** query, framework ID and status.
- **Empty state:** “当前筛选下没有保健功能记录。”
- **Knowledge Gaps:** incomplete framework catalog detail remains explicit, including the nutrient-supplement root boundary.
- **Source trace:** function-level official source plus `health-functions-v2.0`.
- **Forbidden reading:** HealthFunction is not ClaimSignal. An official transition alias is not a page-marketing synonym.

### 5.3 风险物质

- **List fields:** canonical name, CAS when recorded, method coverage count, regulatory-context availability.
- **Detail fields:** English name, governed group-membership metadata, regulatory contexts with provenance, source dataset/version and note.
- **Filter:** deterministic query over ID/name/English name/CAS.
- **Empty state:** “当前筛选下没有已治理物质记录。”
- **Knowledge Gaps:** `regulatory_context_not_recorded`; group membership `not_recorded`.
- **Source trace:** Inspection Reference dataset/version and context-level source when present.
- **Forbidden reading:** method coverage is not evidence that a product contains the Substance. `not_recorded` does not mean “none exists”.

### 5.4 风险映射

- **List fields:** Risk category/label, target type, target label, evidence grade, basis type and temporal status.
- **Detail fields:** product scope, exact source basis text, mapping provenance and group-resolution state.
- **Filter:** query, target type and temporal status.
- **Empty state:** “当前筛选下没有风险映射记录。”
- **Knowledge Gaps:** unresolved or partial group membership.
- **Source trace:** mapping-level official source and Risk dataset/version.
- **Forbidden reading:** a group mapping is not a list of members; Method analytes never create Risk mappings; a mapping is not evidence of product content.

### 5.5 检验方法

- **List fields:** method number/name, lifecycle, knowledge depth, publisher, dates, analyte count and applicability count.
- **Detail fields:** method type, replacement links, applicability include/conditional/exclude counts, RegulatoryDocument, note and source/version.
- **Filter:** query, independent lifecycle status and independent `knowledgeDepth`.
- **Empty state:** “当前筛选下没有检验方法记录。”
- **Knowledge Gaps:** unverified analyte depth, unverified/unknown applicability or missing document link.
- **Source trace:** Method source, Inspection dataset/version and linked RegulatoryDocument.
- **Forbidden reading:** `current` is not `recommendation_ready`; `reference_only` remains visible but cannot drive Recommendation. A Method detects an analyte; it does not prove product content or create a Risk relation.

### 5.6 官方文件

- **List fields:** document number/title, type, publisher, lifecycle and dates.
- **Detail fields:** official source link, jurisdiction, supersedes/superseded-by links, linked Method count and dataset/version.
- **Filter:** query, lifecycle status and document type.
- **Empty state:** “当前筛选下没有官方文件记录。”
- **Knowledge Gaps:** missing effective date is “尚未记录”, never “无生效日期”. Unresolved source/lifecycle facts remain explicit.
- **Source trace:** only the governed `sourceReference`; the frontend must not fabricate a locator.
- **Forbidden reading:** supersession does not merge two document identities or rewrite historical derivations.

## 6. Knowledge Gap and presentation semantics

Knowledge Gaps are stable machine-readable codes mapped to user-facing language in `frontend/src/domain/knowledge.ts`. Absence is represented as `not_recorded`, `unresolved`, `partial` or a specific gap code. It is never silently converted to false, nonexistence, suitability or inapplicability.

The future page must visually separate:

- lifecycle (`current`, `revoked`, `superseded`, and so on);
- project knowledge depth;
- operational availability;
- missing or unresolved knowledge;
- source/provenance.

Color alone cannot carry these meanings. Source links require accessible labels and must use the governed URL.

## 7. Frontend implementation

V2-8A established:

- typed DTOs in `frontend/src/api/contracts.ts`;
- GET client functions in `frontend/src/api/knowledge.ts`;
- stable depth/gap/source presentation mappings in `frontend/src/domain/knowledge.ts`.

V2-8B consumes only those DTOs and adds `#/knowledge`, a first-level 知识库 Sidebar item, the six governed tabs, explicit-submit search, relevant server filters, offset pagination and a shared accessible Drawer. Query, active tab, filters and offset are encoded in the hash URL. The page never imports governed config JSON or constructs a Risk, group-member, Claim or HealthFunction relation.

Every tab shares loading, filtered-empty, API-error and content states. Tables scroll within their card at constrained widths; the page itself does not gain horizontal overflow. Source links accept only governed HTTP(S) references and open with `noopener noreferrer`. The Drawer traps focus through the existing shared component, opens from keyboard-operable row actions and restores focus when closed.

## 8. Acceptance result

V2-8A passes when all seven GET endpoints are deterministic and traceable, all seven indexed Methods including the revoked `reference_only` Method are visible, shallow/non-current Methods remain excluded from operational Recommendation, groups remain unexpanded, server-side filters/pagination work, TypeScript contracts typecheck, and requests leave business state unchanged.

V2-8B passes with the six API-backed tabs, independent lifecycle/depth/availability/gap states, governed source links, URL-stable filters/pagination, keyboard-operable tabs/actions/Drawer, and explicit no-inference boundaries. Offline validation passed targeted Knowledge regression 168/168, Python full regression discovered 564 / passed 563 / skipped 1, frontend workflow 43/43, typecheck and production build. Local 1440px and 1080px acceptance found no page-level horizontal overflow and covered long titles, 201-Substance pagination, filtered empty, API error, Drawer, revoked/reference-only Method, unresolved group mapping and missing regulatory context.

V2-8 is **COMPLETE**. V2-9 Analytics is the next planned independent Gate.
