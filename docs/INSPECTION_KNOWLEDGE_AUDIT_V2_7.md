# Inspection Knowledge Audit V2-7

> Status: V2-7A AUDIT BASELINE + V2-7B2 BOUNDED PROMOTION UPDATE
> Repository baseline: `5a8368fcb8b46fed9f5cb2714a32df52c0f377d0`
> Audit contract: `v2.7b2-1`
> Inputs: `inspection-reference@2026.09-b7`, `inspection-method-candidates-v2@2026.09-b2`, `risk-substance-reference@2026.09-c3`, `phase3-effect-risk-bridge@2026.09-d2`
> Audit mode: deterministic and offline

## 1. Scope and result

V2-7A inventories the governed inspection knowledge and freezes the coverage contract. V2-7B1 established the depth/lifecycle/runtime boundary. V2-7B2 verifies exactly the two approved candidates from first-party records and promotes them as lower-depth Method identities: current BJS 202405 and revoked GB/T 5009.170-2003 are both `reference_only`. It adds no analyte, applicability, Risk/group mapping or group member and changes no API/frontend or Recommendation semantics.

The Wide Reference Index now contains seven methods: five `recommendation_ready` methods in the Deep Verified Subset and two `reference_only` identities. Only two methods are used by the present operational bridge path. This remains a bounded project index, not national coverage. Group mappings remain unresolved and are not expanded from method analytes.

Reproduce the facts with:

```powershell
python scripts/audit_inspection_knowledge.py --format json
python scripts/audit_inspection_knowledge.py --format markdown
```

## 2. Current inventory

| Fact | Actual governed count |
|---|---:|
| Inspection datasets | 1 |
| Risk-mapping datasets | 1 |
| Effect/Risk bridge datasets | 1 |
| Inspection methods | 7 |
| Pending candidate methods / promoted trace records | 0 / 2 |
| Regulatory documents / linked methods | 7 / 7 |
| `supplementary_bjs` / `rapid_kj` / `national_standard_gbt` | 4 / 1 / 2 |
| `current` / `superseded` / `revoked` / `verification_pending` | 6 / 0 / 1 / 0 |
| Deprecated methods | 0; `deprecated` is not a current enum value |
| Unique Substances | 117 |
| Substances with a populated `substance_group` | 0 |
| Method→Substance relations | 132 |
| Method applicability records | 37 |
| Substance regulatory contexts | 1 |
| Risk→Substance mappings | 5 |
| Risk→SubstanceGroup mappings | 3 |
| Unique Risk categories / group labels | 3 / 2 |
| Governed group-membership relations | 0 |
| Evidence→Risk bridge mappings | 3 |

These values match the approximate canonical status. The audit makes the previously combined eight Risk mappings explicit as five Substance and three Group mappings.

## 3. Dataset provenance

| Dataset | Status | Version | Authority retained | Role |
|---|---|---|---|---|
| `inspection-reference` | `verified_reference` | `2026.09-b7` | SAMR method pages / National Standards public system | Seven Method/RegulatoryDocument identities, plus unchanged Substance, MethodSubstance, applicability, explicit group membership and one context. |
| `inspection-method-candidates-v2` | `non_runtime_candidate_manifest` | `2026.09-b2` | First-party discovery and verification locators | Two completed promotion traces; the manifest itself is never imported by DataStore or Recommendation. |
| `risk-substance-reference` | `verified_reference` | `2026.09-c3` | SAMR current official guidance | Independent Risk→Substance/Group facts. |
| `phase3-effect-risk-bridge` | governed bridge | `2026.09-d2` | References exact current Risk mapping IDs | Three exact legacy Effect/keyword pairs; no Claim input. |

All seven methods retain a first-party HTTPS locator, publisher, publication/source date and method identity. All eight Risk mappings retain source name, first-party locator, source date and basis text. The audit does not claim that the repo contains downloaded official documents.

## 4. Method-by-method audit

The `knowledge_depth` column is now an explicit governed field and schema 13 projection. The audit independently recomputes static depth and fails when the declaration and facts disagree.

| Method | Lifecycle | Reference / formal basis | Analyte parsing | Applicability parsing | Lifecycle / regulatory context gaps | Audit depth |
|---|---|---|---|---|---|---|
| BJS 202209 | `current`; published 2022-09-10; effective date not separately recorded | SAMR method-database page; note records official full-text PDF basis | 19/19 numbered target relations, quantitative, source labels/CAS retained | 9 method-level `include` categories | No supersession edge or separate context record; absence is not “none required” | `recommendation_ready` for the 19 explicit relations |
| BJS 201701 | `current`; published 2017-02-28; effective date not separately recorded | SAMR method-database page and source scope | 33 source-backed qualitative target relations | 4 method-level scopes plus 3 substance-scoped rules: 2 `exclude`, 1 `conditional` | No supersession edge or separate context record; negative facts are correctly retained | `recommendation_ready` for the 33 explicit relations |
| BJS 201710 | `current`; published 2017-11-17; effective date not separately recorded | SAMR method-database page; official appendix recorded item by item | 75/75 qualitative target relations with normalization notes where needed | 8 method-level `include` category/form scopes | No supersession edge; only melatonin has a separate regulatory context | `recommendation_ready` for the 75 explicit relations |
| KJ201903 | `current`; published 2019-09-27; effective date not separately recorded | SAMR 2019 No. 41 announcement | 4 explicit rapid-screen reference/performance substances | 6 method-level `include` product forms | The four relations are not an exhaustive claim about every barbiturate response; positive screening requires confirmation; no context records | `recommendation_ready` only for the four explicit relations, never for an inferred class |
| GB/T 45443-2025 | `current`; published 2025-03-28; effective 2025-10-01 | National Standards public system entry | 1 quantitative melatonin relation | 7 method-level `include` forms | Fully replaces the separately indexed GB/T 5009.170-2003; one melatonin context exists | `recommendation_ready` for the explicit melatonin relation |
| BJS 202405 | `current`; published 2024-12-22 | SAMR 2024 No. 51 announcement and official method database | Not parsed in this release | Not parsed in this release | Official identity is verified; no Risk relevance is inferred from the title | `reference_only`; excluded from Recommendation |
| GB/T 5009.170-2003 | `revoked` on 2025-10-01; published 2003-08-11; effective 2004-01-01 | National Standards public/open system entries | Not parsed in this release | Not parsed in this release | Fully replaced by GB/T 45443-2025; predecessor and successor retain distinct official titles | `reference_only`; excluded from Recommendation by depth and lifecycle |

The existing five deep methods still reach the static top depth because each passes its conditional gate: official identity/source/date, current lifecycle, a linked RegulatoryDocument, at least one MethodSubstance relation, method-level applicability, and source scope text. The two B2 methods deliberately stop at `reference_only`; identity verification is not analyte/scope verification.

## 5. Schema, importer and runtime audit

Schema 13 retains the existing inspection/risk tables and adds normalized `inspection_regulatory_documents`, explicit `knowledge_depth` and `regulatory_document_id` on methods, plus `substance_group_memberships`. SQLite remains a rebuildable read index for committed JSON authorities.

The V2-7B boundary is enforced at four independent points:

1. `validate_inspection_config()` applies conditional facts by declared depth rather than requiring every indexed method to be deep.
2. Schema 12→13 migration defaults pre-existing rows to `reference_only`; it never silently declares historical methods Recommendation-ready.
3. Reference queries can return every indexed depth, while the operational Recommendation resolver explicitly requests only `recommendation_ready` methods and still applies lifecycle separately.
4. `config/inspection_method_candidates_v2.json` is validated by a non-runtime loader, records pending/promotion lifecycle and has no DataStore importer or Recommendation call path. A promoted Method enters SQLite only from `inspection_reference.json` and is counted once.

Seven normalized RegulatoryDocument rows retain method provenance and all seven indexed methods link to one. The GB/T predecessor/successor documents and methods now have bidirectional lifecycle references, leaving zero unresolved lifecycle/document edges. The group-membership schema/validator contract exists, but the governed membership count remains zero.

## 6. Substance→Method and applicability quality

- All 117 indexed Substances have at least one explicit Method relation.
- All 132 Method→Substance paths inherit at least one relevant method-level or substance-scoped applicability record.
- The 37 source records comprise 33 `include`, 2 `conditional`, and 2 `exclude` facts.
- The two negative records and two conditional records belong to BJS 201701 and are preserved by the product-context evaluator.
- Zero currently committed relation paths lack an applicability record. This does not mean every product matches a method scope; unknown Product Context still produces `insufficient_context`, and nonmatching context can produce `not_applicable`.
- Only melatonin has a governed SubstanceRegulatoryContext. The other 116 are “no context recorded in this dataset,” not “no regulatory context exists.”

## 7. Risk mapping audit

All eight mappings are A-grade, `current_official_guidance`, `current` and source-backed. Grade describes source strength, not probability or risk severity.

| Mapping | Risk | Target | Type | Scope / boundary |
|---|---|---|---|---|
| `weight-loss-sibutramine-group-cn-2025` | `weight_loss` | 西布曲明及其系列衍生物 | Group | Source-native group; unresolved. |
| `weight-loss-sibutramine-cn-2025` | `weight_loss` | 西布曲明 | Substance | Explicit source-named target. |
| `male-function-nafei-lafei-group-cn-2025` | `male_function` | 那非类、拉非类物质 | Group | Source-native group; unresolved. |
| `male-function-sildenafil-cn-2025` | `male_function` | 西地那非 | Substance | Explicit source-named target. |
| `male-function-tadalafil-cn-2025` | `male_function` | 他达拉非 | Substance | Explicit source-named target. |
| `anti-fatigue-nafei-lafei-group-cn-2025` | `anti_fatigue` | 那非类、拉非类物质 | Group | Source-native group; unresolved. |
| `anti-fatigue-sildenafil-cn-2025` | `anti_fatigue` | 西地那非 | Substance | Explicit source-named target. |
| `anti-fatigue-tadalafil-cn-2025` | `anti_fatigue` | 他达拉非 | Substance | Explicit source-named target. |

The same concrete Substance may be independently mapped to two Risk categories because the official source explicitly names both directions. No relation is derived from BJS 201710 analytes.

## 8. Recommendation reachability

“Applicability present” below means the knowledge path is evaluable; the final product-level state still depends on confirmed context.

| Risk | Target | Explicit Substance | Current deep Method | Applicability present | End-to-end reachable | Gap |
|---|---|---:|---|---:|---:|---|
| `weight_loss` | 西布曲明及其系列衍生物 | No | — | No | No | Group is not expanded. |
| `weight_loss` | 西布曲明 | Yes | BJS 201701; BJS 201710 | Yes | Yes | None at static chain level. |
| `male_function` | 那非类、拉非类物质 | No | — | No | No | Group is not expanded. |
| `male_function` | 西地那非 | Yes | BJS 201710 | Yes | Yes | None at static chain level. |
| `male_function` | 他达拉非 | Yes | BJS 201710 | Yes | Yes | None at static chain level. |
| `anti_fatigue` | 那非类、拉非类物质 | No | — | No | No | Group is not expanded; no Evidence→Risk bridge. |
| `anti_fatigue` | 西地那非 | Yes | BJS 201710 | Yes | No | No governed Evidence→`anti_fatigue` bridge. |
| `anti_fatigue` | 他达拉非 | Yes | BJS 201710 | Yes | No | No governed Evidence→`anti_fatigue` bridge. |

At category level, all three Risk categories have at least one structurally ready explicit Substance path. Only `weight_loss` and `male_function` are reachable from the current legacy Effect/Risk bridge. V2-7A does not create the missing `anti_fatigue` bridge and does not use V2 ClaimSignal as a Risk source.

The Recommendation runtime's currently reachable governed universe uses:

- 2 Risk categories: `male_function`, `weight_loss`;
- 5 Risk mapping rows (three explicit and two unresolved group rows);
- 3 explicit Substances: 西布曲明、西地那非、他达拉非;
- 2 Methods: BJS 201701 and BJS 201710;
- 12 unique relevant applicability records (four BJS 201701 method-level records and eight BJS 201710 records).

## 9. Denominator-defined coverage

| Metric | Numerator | Denominator | Result | Interpretation |
|---|---:|---:|---:|---|
| Method Reference Coverage | 7 | 7 indexed methods | 100% | Reference completeness inside this repository index only. |
| Method Deep-Verification Coverage | 5 | 7 indexed methods | 71.4% | Two B2 identities intentionally remain `reference_only`. |
| Substance→Method Coverage | 117 | 117 indexed Substances | 100% | At least one explicit relation; not presence or universal applicability. |
| Applicability Coverage | 132 | 132 relation paths | 100% | At least one relevant scope record; product context still required. |
| Risk→Substance Coverage | 5 | 8 current Risk target mappings | 62.5% | Three rows remain group-only. |
| Group Resolution Coverage | 0 | 3 current group mappings | 0% | No governed membership relation exists. |
| Recommendation Structural Reachability | 5 | 5 explicit Risk→Substance mappings | 100% | Static method/applicability chain only. |
| Recommendation End-to-End Reachability | 3 | 5 explicit mappings | 60% | Adds current Evidence→Risk category bridge. |
| Risk-category End-to-End Reachability | 2 | 3 governed categories | 66.7% | `anti_fatigue` is not bridged. |

No metric uses “all possible risks,” “all substances,” or “all official methods” as an unstated denominator.

## 10. Priority gaps

Priority is knowledge-engineering order, not product risk probability.

| Priority | Gap | Evidence from current chain | Required next action |
|---|---|---|---|
| Resolved in B1 | Wide index could not safely represent `reference_only` separately from runtime-ready methods | Schema 13 depth, conditional validation, non-runtime candidates and an explicit operational resolver filter now enforce the boundary | Keep these gates mandatory during B2 expansion. |
| Resolved contract / data gap remains | Group mappings had no governed membership contract | Schema 13 and config validation now support explicit source-backed membership; actual membership count remains 0 | Add no member without source evidence; all three group mappings remain unresolved. |
| Resolved in B2 | BJS 202405 identity and title were unverified; the B1 planning rationale incorrectly associated it with `weight_loss`/sibutramine | SAMR announcement and method database confirm `食品中西地那非、他达拉非等化合物的测定` | The old association is explicitly invalidated; keep the method `reference_only` until official analyte/scope facts are separately parsed. |
| Resolved in B2 | GB/T 5009.170-2003 predecessor identity/lifecycle was absent | First-party standards records confirm title, dates, revoked status and full replacement by GB/T 45443-2025 | Keep predecessor and successor as distinct identities; the revoked predecessor never enters Recommendation. |
| P1 | `anti_fatigue` has structural knowledge but no Evidence→Risk bridge | Two explicit Substance paths are ready; bridge count is zero | Treat as a separate future Risk-bridge governance decision, not as an Inspection-method expansion or automatic Claim mapping. |
| P1 | Regulatory context coverage is sparse and nonabsence cannot be inferred | 1 record across 117 Substances | Expand only from authoritative context sources when operationally needed; keep missing as unknown. |

## 11. V2-7B candidate promotion trace

The candidate manifest remains a non-runtime provenance ledger. Both approved records are now `promoted` traces. Their corresponding formal Methods exist only in `config/inspection_reference.json`; the manifest does not double-import or enlarge coverage denominators.

| Candidate ID | Method number / title | Official discovery source | Source type | Existing governed direction | Why prioritized | Expected depth | Verification status |
|---|---|---|---|---|---|---|---|
| `candidate-bjs-202405` | BJS 202405 / 食品中西地那非、他达拉非等化合物的测定 | SAMR 2024 No. 51 announcement and official method database | Identity, title, issuer and publication identity verified; analyte/scope not parsed | None inferred | Corrects and invalidates the B1 `weight_loss`/sibutramine rationale | `reference_only` | `promoted` → `bjs-202405` |
| `candidate-gbt-5009-170-2003` | GB/T 5009.170-2003 / 保健食品中褪黑素含量的测定 | National Standards public and open-system records | Identity, distinct predecessor title, dates, revoked status and full-replacement edge verified | Historical melatonin-method lifecycle only | Closes the normalized predecessor/document edge without making it current | `reference_only`; never Recommendation | `promoted` → `gbt-5009-170-2003` |

No other method was searched for or promoted. The audit deliberately does not invent titles, analytes, scope or Risk relevance from third-party lists or method names.

## 12. V2-7B plan — Wide Official Method Reference Expansion

1. **B1 complete:** non-runtime candidate manifest, explicit depth field/validator, schema 13 projection, RegulatoryDocument baseline, group-membership contract and Recommendation-ready resolver gate.
2. **B2 complete:** the two approved identities/documents were verified from first-party sources and promoted only as `reference_only`; BJS 202405 remains current, while GB/T 5009.170-2003 is revoked and linked to its current successor.
3. D5 excludes both promoted records by construction; existing Recommendation reachability and output semantics are unchanged.
4. The BJS planning-association error and the predecessor-title error are retained as explicit corrections rather than silently rewritten history.
5. Recompute the same denominator-defined audit after each versioned release.

## 13. V2-7C plan — Deep Verified Subset and exit gate

1. Select deep-verification work from existing governed Risk→explicit Substance paths and observed Recommendation gaps, not popularity lists.
2. Parse analytes, source labels/CAS, determination role and normalization notes from official full text.
3. Parse positive, conditional and negative scope without turning missing facts into `not_applicable`.
4. Complete candidate-specific RegulatoryDocument and lifecycle/supersession links or explicitly retain them as gaps.
5. Promote only records passing the full gate; verify D5 ignores every lower-depth method.
6. Test a defined Product Context corpus for context-applicable reachability; keep that metric separate from static coverage.
7. Preserve exact existing Recommendation fixtures and frozen historical artifacts.

## 14. Explicitly unchanged

- the five existing deep methods and their analytes/applicability, `config/risk_substance_reference.json`, and `config/effect_risk_bridge.json` knowledge semantics;
- Phase3, D2–D6 and Recommendation output;
- ClaimSignal, Claim consistency, Review and Sampling semantics;
- API and frontend behavior;
- historical Evidence and frozen Sampling exports;
- live collection and network behavior.

V2-7B2 adds exactly two official Method/RegulatoryDocument identities at `reference_only`, closes one lifecycle edge, and upgrades the candidate manifest/audit trace. It adds no analyte, applicability, Risk/group mapping, group member, schema, API, frontend or runtime business behavior.
