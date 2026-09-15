# Inspection Knowledge Audit V2-7A

> Status: AUDIT BASELINE
> Repository baseline: `5a8368fcb8b46fed9f5cb2714a32df52c0f377d0`
> Audit contract: `v2.7a-1`
> Inputs: `inspection-reference@2026.09-b5`, `risk-substance-reference@2026.09-c3`, `phase3-effect-risk-bridge@2026.09-d2`
> Audit mode: deterministic and offline

## 1. Scope and result

V2-7A inventories the current governed inspection knowledge and freezes the coverage contract. It does not promote a candidate, edit a knowledge record, migrate schema, change API/frontend behavior, or change Recommendation semantics.

The current five methods form a small, deep-parsed corpus rather than a wide national index. All five pass the current static Recommendation-depth gate for their explicitly recorded analyte relations, but only two are used by the present operational bridge path. Group mappings remain unresolved and are not expanded from method analytes.

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
| Inspection methods | 5 |
| `supplementary_bjs` / `rapid_kj` / `national_standard_gbt` | 3 / 1 / 1 |
| `current` / `superseded` / `revoked` / `verification_pending` | 5 / 0 / 0 / 0 |
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
| `inspection-reference` | `verified_reference` | `2026.09-b5` | SAMR method pages / National Standards public system | Method, Substance, MethodSubstance, applicability and one context. |
| `risk-substance-reference` | `verified_reference` | `2026.09-c3` | SAMR current official guidance | Independent Risk→Substance/Group facts. |
| `phase3-effect-risk-bridge` | governed bridge | `2026.09-d2` | References exact current Risk mapping IDs | Three exact legacy Effect/keyword pairs; no Claim input. |

All five methods retain a first-party HTTPS locator, publisher, publication/source date and method identity. All eight Risk mappings retain source name, first-party locator, source date and basis text. The audit does not dereference these URLs or claim that the repo contains downloaded official documents.

## 4. Method-by-method audit

The `knowledge_depth` column is an audit projection, not a stored field and not a runtime change.

| Method | Lifecycle | Reference / formal basis | Analyte parsing | Applicability parsing | Lifecycle / regulatory context gaps | Audit depth |
|---|---|---|---|---|---|---|
| BJS 202209 | `current`; published 2022-09-10; effective date not separately recorded | SAMR method-database page; note records official full-text PDF basis | 19/19 numbered target relations, quantitative, source labels/CAS retained | 9 method-level `include` categories | No supersession edge or separate context record; absence is not “none required” | `recommendation_ready` for the 19 explicit relations |
| BJS 201701 | `current`; published 2017-02-28; effective date not separately recorded | SAMR method-database page and source scope | 33 source-backed qualitative target relations | 4 method-level scopes plus 3 substance-scoped rules: 2 `exclude`, 1 `conditional` | No supersession edge or separate context record; negative facts are correctly retained | `recommendation_ready` for the 33 explicit relations |
| BJS 201710 | `current`; published 2017-11-17; effective date not separately recorded | SAMR method-database page; official appendix recorded item by item | 75/75 qualitative target relations with normalization notes where needed | 8 method-level `include` category/form scopes | No supersession edge; only melatonin has a separate regulatory context | `recommendation_ready` for the 75 explicit relations |
| KJ201903 | `current`; published 2019-09-27; effective date not separately recorded | SAMR 2019 No. 41 announcement | 4 explicit rapid-screen reference/performance substances | 6 method-level `include` product forms | The four relations are not an exhaustive claim about every barbiturate response; positive screening requires confirmation; no context records | `recommendation_ready` only for the four explicit relations, never for an inferred class |
| GB/T 45443-2025 | `current`; published 2025-03-28; effective 2025-10-01 | National Standards public system entry | 1 quantitative melatonin relation | 7 method-level `include` forms | Replaces GB/T 5009.170-2003, but the predecessor has no normalized Method/Document record; one melatonin context exists | `recommendation_ready` for the explicit melatonin relation |

Why all five reach the static top depth: the current `verified_reference` validator already requires every method to have official identity/source/date, at least one MethodSubstance relation, at least one method-level applicability record, and source scope text. That is a property of this small curated corpus, not evidence of broad external coverage.

## 5. Schema, importer and runtime audit

Schema 12 stores `inspection_datasets`, `inspection_methods`, `inspection_substances`, `inspection_method_substances`, `inspection_method_applicabilities`, `substance_regulatory_contexts`, `risk_mapping_datasets`, and `risk_substance_mappings`. SQLite is a rebuildable read index for the committed JSON authorities.

Current limitations relevant to V2-7B:

1. `inspection_methods` has lifecycle status but no independent `knowledge_depth`.
2. `validate_inspection_config()` rejects a method in a `verified_reference` dataset unless it already has analytes and method-level applicability. The current contract therefore cannot represent a verified `reference_only` row in that dataset.
3. `list_substance_methods()` returns explicit relations and D5 later separates non-current methods, but there is no future depth gate. A reference-only import must not become runtime-visible by accident.
4. RegulatoryDocument is not normalized; source and lifecycle fields are inline strings.
5. Supersession uses method-number strings. The GB/T predecessor is not a first-class record, so the reverse edge cannot be validated.

V2-7A does not change these structures. V2-7B must first choose an additive safe representation or keep candidates outside runtime import until their deep promotion is complete.

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
| Method Reference Coverage | 5 | 5 indexed methods | 100% | Reference completeness inside this repository index only. |
| Method Deep-Verification Coverage | 5 | 5 indexed methods | 100% | The current index is small and already deep parsed. |
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
| P0 | Wide index cannot safely represent `reference_only` separately from runtime-ready methods | No `knowledge_depth`; verified dataset validation requires analyte/applicability; resolver has no depth filter | Before importing wide candidates, add an explicit additive depth/candidate boundary and Recommendation gate, or keep candidates non-importable. |
| P0 | Group mappings have no governed membership contract | 3 group rows, 0 membership relations; runtime correctly reports partial/unresolved | Define source-backed partial/complete group membership and explicit unknown remainder; never derive members from MethodSubstance. |
| P0 | RegulatoryDocument and supersession are not first-class | Inline URLs and method-number strings; GB/T predecessor absent | Normalize document identity/lifecycle design before bulk expansion; preserve current URLs during migration. |
| P1 | BJS 202405 is source-discovered but not verified in Inspection Reference | Current official weight-loss guidance mentions the method; repo has no verified method/analyte/scope record | V2-7B must retrieve and verify the official method page/full text before any promotion or Risk shortcut. |
| P1 | GB/T 5009.170-2003 predecessor is not indexed | GB/T 45443-2025 declares full replacement | Add a superseded reference record/document only after first-party identity and lifecycle verification; never recommend it as current. |
| P1 | `anti_fatigue` has structural knowledge but no Evidence→Risk bridge | Two explicit Substance paths are ready; bridge count is zero | Treat as a separate future Risk-bridge governance decision, not as an Inspection-method expansion or automatic Claim mapping. |
| P1 | Regulatory context coverage is sparse and nonabsence cannot be inferred | 1 record across 117 Substances | Expand only from authoritative context sources when operationally needed; keep missing as unknown. |

## 11. V2-7B candidate official-method list

Candidates are planning records only. They are not added to `config/inspection_reference.json`, SQLite or Recommendation runtime.

| Candidate ID | Method number / title | Official discovery source | Source type | Existing governed direction | Why prioritized | Expected depth | Verification status |
|---|---|---|---|---|---|---|---|
| `candidate-bjs-202405` | BJS 202405 / **official title not yet verified** | Current SAMR notice retained by `weight-loss-sibutramine-group-cn-2025` | First-party official notice; method full text still required | `weight_loss` / 西布曲明及其系列衍生物 | Directly named by the current operational gap; may clarify the 2025 method and analyte/scope facts | Target `recommendation_ready` only after all gates | `candidate` |
| `candidate-gbt-5009-170-2003` | GB/T 5009.170-2003 / 保健食品中褪黑素的测定 | Current National Standards entry for GB/T 45443-2025 records replacement | First-party national-standard lifecycle entry; predecessor record/full text still required | Existing melatonin Method/Substance lifecycle | Completes the explicit predecessor edge and historical derivation trace | `reference_only` or `applicability_verified`; never current Recommendation | `candidate` |

The audit deliberately does not invent further titles from third-party lists. V2-7B may widen the candidate corpus only through SAMR, the National Standards public system, NHC or another first-party authority, recording rejected and pending candidates separately.

## 12. V2-7B plan — Wide Official Method Reference Expansion

1. Establish a non-runtime candidate manifest and explicit depth field/contract.
2. Re-verify candidate identity, exact title, publisher, dates, status, official locator and document relationship.
3. Import reference-only candidates only after queries and D5 exclude them by construction.
4. Start with BJS 202405 and the GB/T predecessor lifecycle record because both arise from existing governed paths.
5. Record candidates rejected, superseded or unavailable; do not force them into `verified_reference`.
6. Recompute the same denominator-defined audit after each versioned release.

## 13. V2-7C plan — Deep Verified Subset and exit gate

1. Select deep-verification work from existing governed Risk→explicit Substance paths and observed Recommendation gaps, not popularity lists.
2. Parse analytes, source labels/CAS, determination role and normalization notes from official full text.
3. Parse positive, conditional and negative scope without turning missing facts into `not_applicable`.
4. Normalize RegulatoryDocument and lifecycle/supersession links or explicitly defer them with a gap.
5. Promote only records passing the full gate; verify D5 ignores every lower-depth method.
6. Test a defined Product Context corpus for context-applicable reachability; keep that metric separate from static coverage.
7. Preserve exact existing Recommendation fixtures and frozen historical artifacts.

## 14. Explicitly unchanged

- `config/inspection_reference.json`, `config/risk_substance_reference.json`, and `config/effect_risk_bridge.json` knowledge records;
- Phase3, D2–D6 and Recommendation output;
- ClaimSignal, Claim consistency, Review and Sampling semantics;
- schema 12, API and frontend;
- historical Evidence and frozen Sampling exports;
- live collection and network behavior.
