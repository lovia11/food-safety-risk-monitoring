# Product Requirements V2

> Status: CANONICAL
> Applies to: V2
> Last verified against commit: `bbe992e54f9fc583b312f919f32f91f43e53fb06`
> Owner: Project

## 1. Product position

The product name is **网络食品风险线索发现与抽检辅助筛查系统**.

It supports network-food regulatory or enterprise analysis through page-level risk-clue discovery, evidence preservation, human judgment, and sampling assistance. It is not an automated enforcement system, legality adjudicator, efficacy-verification system, laboratory test system, or risk-probability model.

Every user-visible conclusion must preserve the distinction between observed page content, derived clues, verified knowledge, human decisions, and laboratory work that has not occurred.

## 2. Core business paths

### Path A — Ordinary food and food-medicine material page clues

```text
Monitor Target
→ Search Discovery
→ Product Detail
→ OCR / DOM / Image Evidence
→ Product Facts
→ Claim Signal
→ Risk Knowledge (only with a reliable mapping)
→ Inspection Recommendation
→ Human Review
→ Sampling
```

The target scope includes objects in the national food-medicine material catalog, ordinary foods featuring them as ingredients or marketing subjects, secondary processed foods, and related online food listings.

`Reference Target ≠ Operational Query Coverage`: a governed reference object may be visible before it has a production-ready SearchQuery.

### Path B — Health-food identity and claim consistency

```text
Page product
→ identity clues such as blue-hat imagery or registration/filing number
→ HealthFoodIdentity candidate
→ official registration/filing verification
→ Official Health Functions
→ actual Page Claims
→ Claim Consistency Assessment
```

Required assessment states are:

- `consistent`
- `possible_out_of_scope_claim`
- `disease_treatment_expression`
- `identity_unverified`
- `official_record_unavailable`
- `insufficient_evidence`
- `manual_review_required`

The system must not emit automatic `合法` or `违法` results. A logo or OCR identifier is an identity clue, not official verification.

### Path C — Illegal-addition clue and sampling assistance

```text
Evidence
+ Product Context
+ Verified Risk Knowledge
→ Risk Signal
→ Substance / Substance Group
→ Method
→ Applicability
→ Inspection Recommendation
```

This path may apply to both ordinary food and health food. It expresses a supported inspection direction, not the presence of a substance.

## 3. Users and responsibilities

The current primary role is a regulatory or enterprise analyst. The analyst can create an inspection task, inspect products and Evidence, examine knowledge bases and gaps, review a Snapshot, manage a current sampling list, freeze/export a list, and eventually inspect analytics and governed knowledge.

V2 does not currently require multi-role authorization, approval workflows, or multi-organization tenancy.

## 4. Information architecture

Current implemented navigation:

```text
商品总览
排查档案
抽检清单
```

Future target navigation:

```text
商品总览
排查档案
抽检清单
统计分析
知识库
```

统计分析 and 知识库 are Future V2 scope; their presence in this requirement does not mean they are implemented.

## 5. Monitoring objects and query coverage

The current Reference contains 106 MonitorTargets. Only a small, validated operational subset is enabled. V2 must make all 106 reference objects inspectable in the Knowledge Base while validating Operational SearchQueries in batches.

Each operational query requires provenance, validation state, and a documented retrieval assessment. An unvalidated query must not be labeled production-ready. V2 explicitly rejects enabling all 106 objects in one unvalidated expansion.

## 6. Claim scope

V2 separates four concepts:

- **Page Claim:** language actually observed on the page.
- **Official Health Function:** a normalized function from an official health-food framework.
- **Risk-related Claim:** a page expression that may connect through verified knowledge to an illegal-addition or sampling-risk direction.
- **Disease/Treatment Claim:** disease prevention, treatment, or clearly medicalized expression.

These concepts must not be compressed into one `Effect` field. The five categories in `config/effect_keywords.json` are the **Legacy/current Phase3 operational clue vocabulary**, not the final Claim Taxonomy.

## 7. Product Facts

**FUTURE CHANGE:** V2 will introduce provenance-bearing ProductFacts, initially including:

- `declared_origin`
- `product_category`
- `product_form`
- `ingredients`
- `health_food_registration_no`

Each fact must retain normalized value, raw value, source, source path, exact source text or image, extraction method, confidence or verification state where meaningful, Snapshot scope, and review status where needed.

No value may be filled without explicit page support. Missing declared origin is displayed as `—`, never stored or displayed as `待采集`. Search-page region, seller address, manufacturer address, and declared product origin remain independent facts and must not be inferred from one another.

## 8. Review and Sampling

- Review is a human decision scoped to one ProductSnapshot.
- Sampling Membership is Product-scoped membership in the current working list and records the source Snapshot.
- Current Review statuses remain `pending`, `recommend_follow_up`, and `no_further_action`.
- Recommendation availability does not determine Review eligibility; successful Phase3 analysis does.
- Adding to the sampling list is an application-level atomic decision: save `recommend_follow_up` Review and its note, then create or confirm current Membership.
- `no_further_action` saves the Snapshot Review and removes current Product Membership in the same business transaction.
- Removing an item from the current list alone never changes Review.
- A later pending Snapshot may coexist with a Membership sourced from an earlier Snapshot and still requires its own Review.

## 9. Evidence and non-adjudication

Seller-managed and UGC Evidence remain distinguishable. Evidence from another product must be excluded from the current product's primary-evidence path. OCR, DOM, image, and screenshot observations must preserve their source artifacts.

Where verified knowledge cannot bridge an observed clue, show a Knowledge Gap. Do not invent an ingredient, mapping, method, identity, origin, or regulatory conclusion.

## 10. Terminology registry

| Term | Canonical meaning |
|---|---|
| MonitorTarget | Governed object that may be monitored; reference presence does not imply an operational query. |
| SearchQuery | Versioned, validated or developmental query associated with a MonitorTarget. |
| Candidate | User-facing shorthand for the `CandidateHit` domain entity: a Search result observed during discovery; not yet necessarily Detail-collected or reviewable. |
| Product | Stable marketplace item identity. |
| ProductSnapshot | One time-scoped observation of a Product. |
| Evidence | Source-preserving observation derived from a Snapshot artifact. |
| Seller-managed Evidence | Evidence controlled by the seller or product page. |
| UGC Evidence | User-generated evidence, presented as auxiliary context. |
| Excluded Evidence | Evidence assigned to another product/context and barred from current primary evidence. |
| ProductFact | Future provenance-bearing normalized fact derived from a Snapshot. |
| ClaimSignal | Page expression classified as a claim clue; not an official function or risk conclusion. |
| Official Health Function | Function verified from the applicable official health-food record/framework. |
| HealthFoodIdentity | Multi-state identity resolution, not a boolean inferred from imagery. |
| RiskSignal | Risk direction reached through explicit, governed knowledge. |
| InspectionRecommendation | Derived inspection-method assistance under recorded knowledge/context. |
| Review | Snapshot-scoped human decision. |
| SamplingMembership | Product membership in the mutable current sampling list, sourced to a Snapshot. |
| FrozenList | User-facing shorthand for the `SamplingFrozenList` domain entity: an immutable historical sampling-list export and its frozen items. |
| Knowledge Gap | Explicit absence of a reliable mapping, identity, fact, or applicable method. |

## 11. Acceptance principles

A V2 capability is not complete merely because a UI can display it. It needs a domain contract, provenance, deterministic tests, explicit empty/error states, and real-world validation appropriate to its risk. Phase-specific gates are defined in [TEST_ACCEPTANCE_V2.md](TEST_ACCEPTANCE_V2.md).
