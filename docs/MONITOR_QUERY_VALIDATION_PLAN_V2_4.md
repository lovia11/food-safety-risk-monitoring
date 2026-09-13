# Monitor Query Validation Plan V2-4

> Status: **IN PROGRESS — planned standard-name waves reviewed; 食用百合 collection complete and human review pending**
>
> Completed collection batches: Wave 1 `v2-4b-batch-01a`, Wave 2A `v2-4b-batch-02a`, Wave 2B `v2-4b-batch-02b`, Lily refinement `v2-4b-batch-02c`; only the `食用百合` human-review gate remains
>
> Collection ceiling: first 15 unique Search Result cards per Query
>
> Promotion evaluation sample: first 10 unique assessable Search Results per Query, in original search order
>
> Scope: search-only; no Detail, OCR, Phase3, Review, or Sampling

## Selection rule

This first bounded batch uses only the official standard name. It prioritizes query-pending Reference objects with plausible food/processed-food results while retaining likely ambiguity for explicit review. It does not pre-create product-form combinations. A later product-form candidate is allowed only when the base-query artifact repeatedly demonstrates that form.

All official sources below are the 2002 Ministry of Health notice recorded on each governed MonitorTarget. Wave 1 reviewed six standard-name Query records: five are enabled `search_validated`, while 乌梅 is disabled `paused_scope_issue`. Wave 2A reviewed and enabled the standard-name Queries for 山药、赤小豆、枸杞子、莲子. Wave 2B enabled 菊花 after review and rejected the standard-name 百合 Query for 50% observed relevance. The 百合 MonitorTarget remains in the Reference and may receive a separately governed refined candidate.

| Target | Target ID | Proposed Query | Why selected | Known ambiguity / risk |
|---|---|---|---|---|
| 山药 | `food-medicine-2002-006` | 山药 | Common edible ingredient with processed-food relevance. | Fresh produce and raw medicinal slices may dominate. |
| 山楂 | `food-medicine-2002-007` | 山楂 | Strong association with snacks and processed foods. | Raw fruit and medicinal-slice results may mix with food. |
| 乌梅 | `food-medicine-2002-010` | 乌梅 | Plausible preserved-fruit and beverage products. | Raw medicinal material/decoction-piece context may be substantial. |
| 百合 | `food-medicine-2002-022` | 百合 | Edible bulb and processed-food use are established candidate contexts. | Ornamental flowers and broad non-food naming can create noise. |
| 沙棘 | `food-medicine-2002-028` | 沙棘 | Likely juice, powder, and processed-food discovery value. | Supplements, raw ingredients, or low-information cards may be ambiguous. |
| 赤小豆 | `food-medicine-2002-032` | 赤小豆 | Clear staple-food and processed-food use. | May be confused with generic red-bean products that do not identify the target precisely. |
| 罗汉果 | `food-medicine-2002-038` | 罗汉果 | Likely beverage and edible processed-product results. | Whole raw fruit and medicinal context may dominate. |
| 枸杞子 | `food-medicine-2002-045` | 枸杞子 | Strong edible dried-fruit and processed-food association. | Raw medicinal-material framing may overlap with food sales. |
| 莲子 | `food-medicine-2002-060` | 莲子 | Clear ingredient/staple and processed-food use. | Seeds, planting products, and low-information raw listings require labeling. |
| 菊花 | `food-medicine-2002-064` | 菊花 | Food/tea use provides monitoring value. | Ornamental flowers and raw medicinal-material results may be high. |
| 黑芝麻 | `food-medicine-2002-071` | 黑芝麻 | Strong ordinary-food and processed-food association. | Broad marketing claims and mixed-ingredient products may reduce target importance. |
| 蜂蜜 | `food-medicine-2002-076` | 蜂蜜 | Clear food identity and broad marketplace presence. | Very broad result set and containing-products may reduce Target specificity. |

Official source: `https://www.nhc.gov.cn/wjw/gfxwj/200203/5e9768a72af64db89acb45fe30a810af.shtml` (source date `2002-02-28`).

## Wave 1 collection command

```powershell
python tools/validate_monitor_queries.py `
  --batch v2-4b-batch-01a `
  --dry-run `
  --max-results 15 `
  --target food-medicine-2002-007 `
  --target food-medicine-2002-010 `
  --target food-medicine-2002-028 `
  --target food-medicine-2002-038 `
  --target food-medicine-2002-071 `
  --target food-medicine-2002-076 `
  --output output/query_validation
```

At the V2-4A baseline, the unfiltered dry run resolved all 12 disabled candidates. Wave 1 was intentionally narrowed to six separately authorized Targets, Wave 2A reviewed four, and Wave 2B reviewed 百合 and 菊花. No unreviewed standard-name candidate remains after Wave 2B governance. A dry run only resolves configuration and prints Targets/Queries, limits, and destination; it must not import Playwright, launch a browser, or contact Taobao.

The collection ceiling and promotion evaluation sample are deliberately different. A bounded live run stops after at most 15 unique Search Result cards (or natural exhaustion/blocker). Human review then evaluates the first 10 unique assessable results in original search order. If fewer than 10 assessable results remain after the 15-card ceiling, the decision is `hold`; collection must not continue through unbounded pagination to fill the sample. The fixed `70%`, five-relevant-result, ten-assessable-result, and systematic-scope-issue gates remain unchanged.

Wave 1 decisions and immutable manifest evidence are recorded in [MONITOR_QUERY_VALIDATION_RESULTS_V2_4_BATCH_01A.md](MONITOR_QUERY_VALIDATION_RESULTS_V2_4_BATCH_01A.md). Wave 2A is recorded in [MONITOR_QUERY_VALIDATION_RESULTS_V2_4_BATCH_02A.md](MONITOR_QUERY_VALIDATION_RESULTS_V2_4_BATCH_02A.md), and Wave 2B in [MONITOR_QUERY_VALIDATION_RESULTS_V2_4_BATCH_02B.md](MONITOR_QUERY_VALIDATION_RESULTS_V2_4_BATCH_02B.md). A refined 百合 candidate must retain explicit provenance to the rejected standard-name artifact and pass the same unchanged gate.

## Lily refinement candidate

The standard-name `百合` Query produced only 50% observed relevance because half of its first ten assessable Search Result cards were explicitly framed as medicinal-material or medicinal-use sales. The separately governed candidate `食用百合` therefore adds a direct food-scope disambiguator without restricting processing form: it can still retrieve fresh edible lily bulbs, dried lily and other food forms rather than locking the strategy to `百合干`.

- Target: `food-medicine-2002-022`
- Query ID: `food-medicine-2002-022-edible-candidate`
- Query source: `manually_curated`
- Provenance: `derived_from_validation_batch=v2-4b-batch-02b`
- Lifecycle: disabled `candidate_unvalidated`
- Collection batch: `v2-4b-batch-02c`
- Collection status: complete, 15 unique Search Result cards, human review pending

The `食用百合` collection does not change target availability, does not constitute promotion, and must not be treated as a final relevance result until explicit human labels are finalized.
