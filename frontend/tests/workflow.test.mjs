import assert from "node:assert/strict";
import test from "node:test";

import {
  analysisStatePresentation,
  productCluePresentation,
} from "../src/domain/analysis.ts";
import {
  groupEvidence,
  partitionEvidenceGroups,
} from "../src/domain/evidence.ts";
import { clampLightboxZoom, moveLightboxIndex } from "../src/domain/media.ts";
import {
  QUERY_PENDING_MESSAGE,
  canCreateMonitorTask,
  filterMonitorTargets,
  monitorAvailabilityLabel,
  monitorAvailabilityMessage,
} from "../src/domain/monitorTargets.ts";
import {
  healthFoodArtifactPath,
  healthFoodIdentityPresentation,
  healthFoodSourceLabel,
  isVerifiedHealthFoodIdentity,
} from "../src/domain/healthFoodIdentity.ts";
import { readFileSync } from "node:fs";
import {
  isProductRowActivationKey,
  productAnalysisPresentation,
  productThumbnailSource,
  snapshotTimelineMode,
} from "../src/domain/product.ts";
import { productQueryString } from "../src/domain/productQuery.ts";
import { reviewPresentation } from "../src/domain/presentation.ts";
import {
  declaredOriginText,
  productFactArtifactPath,
  productFactSourceLabel,
  productFactSourcesForValue,
} from "../src/domain/productFacts.ts";
import { queueMatches } from "../src/domain/reviewQueue.ts";
import {
  evidenceQualificationLabel,
  samplingMethodGroups,
  suggestedSamplingMethods,
} from "../src/domain/sampling.ts";
import {
  buildWebTaskRequest,
  shouldResumeTask,
  taskFlowSteps,
} from "../src/domain/task.ts";

test("product query serializes every current server-side filter and pagination field", () => {
  const query = Object.fromEntries(new URLSearchParams(productQueryString({
    query: "酸枣仁",
    targetId: "target-1",
    taskId: "task-1",
    reviewStatus: "recommend_follow_up",
    effect: "助眠",
    samplingStatus: "historical_only",
    collectedFrom: "2026-09-01",
    collectedTo: "2026-09-12",
    page: 2,
    pageSize: 50,
  })));

  assert.deepEqual(query, {
    query: "酸枣仁",
    target_id: "target-1",
    task_id: "task-1",
    review_status: "recommend_follow_up",
    effect: "助眠",
    sampling_status: "historical_only",
    collected_from: "2026-09-01",
    collected_to: "2026-09-12",
    page: "2",
    page_size: "50",
  });
});

test("review statuses use the current product language", () => {
  assert.equal(reviewPresentation.pending.label, "待复核");
  assert.equal(reviewPresentation.recommend_follow_up.label, "建议跟进");
  assert.equal(reviewPresentation.no_further_action.label, "暂不纳入");
});

test("pending snapshot remains in pending queue when product has a membership", () => {
  const item = {
    readiness: { reviewEligible: true },
    sampling: {
      decisionStatus: "pending",
      inCurrentList: true,
      sourceSnapshotId: "older-snapshot",
    },
  };

  assert.equal(queueMatches(item, "pending"), true);
  assert.equal(queueMatches(item, "current"), false);
});

test("non-analysis-ready snapshots never enter the review queue", () => {
  const item = {
    readiness: { reviewEligible: false },
    sampling: {
      decisionStatus: "not_eligible",
      inCurrentList: false,
      sourceSnapshotId: null,
    },
  };

  assert.equal(queueMatches(item, "all"), false);
  assert.equal(queueMatches(item, "pending"), false);
});

test("archive resumes only interrupted resumable tasks", () => {
  assert.equal(
    shouldResumeTask({ businessStatus: "interrupted", resumable: true }),
    true,
  );
  assert.equal(
    shouldResumeTask({ businessStatus: "interrupted", resumable: false }),
    false,
  );
  assert.equal(
    shouldResumeTask({ businessStatus: "partial_error", resumable: true }),
    false,
  );
});

test("workflow renders backend step outcomes without inferring from terminal stage", () => {
  const flow = [
    { key: "search", label: "搜索商品", state: "done", completed: 4, target: 4 },
    { key: "detail", label: "采集详情", state: "partial", completed: 2, target: 3 },
    { key: "analysis", label: "线索识别", state: "failed", completed: 0, target: 1 },
    { key: "review", label: "人工复核", state: "future", completed: 0, target: 0 },
  ];
  assert.deepEqual(taskFlowSteps({ flow }), flow);
});

test("web quick task analyzes every selected candidate up to the user limit", () => {
  assert.deepEqual(
    buildWebTaskRequest({
      mode: "quick",
      name: "十件商品排查",
      keyword: "酸枣仁",
      targetId: "",
      analysisLimit: 10,
    }),
    {
      name: "十件商品排查",
      task_type: "quick",
      keyword: "酸枣仁",
      candidate_limit: 10,
      detail_limit: 10,
    },
  );
});

test("web monitor task keeps a global analysis cap across queries", () => {
  assert.deepEqual(
    buildWebTaskRequest({
      mode: "monitor",
      name: "监测对象排查",
      keyword: "",
      targetId: "target-1",
      analysisLimit: 10,
    }),
    {
      name: "监测对象排查",
      task_type: "monitor",
      target_id: "target-1",
      per_query_candidate_limit: 10,
      detail_limit: 10,
    },
  );
});

function monitorTarget(name, availability, validatedQueries = []) {
  return {
    target_id: `target-${name}`,
    dataset_id: "food-medicine-reference",
    dataset_status: "verified_reference",
    standard_name: name,
    target_type: "food_medicine",
    source_name: "官方目录",
    source_reference: "https://example.test/reference",
    source_date: "2002-02-28",
    enabled: availability === "operational",
    queries: validatedQueries,
    availability,
    availability_reason: availability === "paused" ? "基础词搜索结果主要为中药材，暂未启用" : null,
    validated_query_count: validatedQueries.length,
    candidate_query_count: availability === "query_pending" ? 1 : 0,
    validated_queries: validatedQueries,
  };
}

test("monitor reference picker searches all availability states and exposes validated chips", () => {
  const longyanQueries = [
    { query_id: "longyan", query_text: "龙眼肉" },
    { query_id: "guiyuan", query_text: "桂圆" },
  ];
  const targets = [
    monitorTarget("酸枣仁", "operational", [{ query_id: "suanzaoren", query_text: "酸枣仁" }]),
    monitorTarget("龙眼肉（桂圆）", "operational", longyanQueries),
    monitorTarget("山药", "query_pending"),
    monitorTarget("当归", "paused"),
  ];
  assert.equal(filterMonitorTargets(targets, "酸枣仁", "all")[0].availability, "operational");
  assert.deepEqual(
    filterMonitorTargets(targets, "桂圆", "all")[0].validated_queries.map((item) => item.query_text),
    ["龙眼肉", "桂圆"],
  );
  assert.equal(filterMonitorTargets(targets, "山药", "query_pending").length, 1);
  assert.equal(filterMonitorTargets(targets, "当归", "paused").length, 1);
});

test("lily remains the target identity while its refined strategy is executable", () => {
  const base = {
    query_id: "lily-base",
    query_text: "百合",
    validation_status: "rejected_low_relevance",
    enabled: false,
  };
  const refined = {
    query_id: "lily-edible",
    query_text: "食用百合",
    query_source: "manually_curated",
    validation_status: "search_validated",
    enabled: true,
  };
  const lily = {
    ...monitorTarget("百合", "operational", [refined]),
    queries: [base, refined],
  };
  assert.equal(lily.standard_name, "百合");
  assert.equal(canCreateMonitorTask(lily), true);
  assert.deepEqual(lily.validated_queries.map((item) => item.query_text), ["食用百合"]);
  assert.equal(filterMonitorTargets([lily], "食用百合", "operational")[0], lily);
});

test("monitor picker labels operational queries as governed search strategies", () => {
  const source = readFileSync(
    new URL("../src/pages/inspections/NewInspectionPage.tsx", import.meta.url),
    "utf8",
  );
  assert.match(source, /官方目录/);
  assert.match(source, /当前可排查/);
  assert.match(source, /已验证搜索策略/);
  assert.doesNotMatch(source, /已验证搜索词/);
});

test("non-operational monitor targets cannot create tasks", () => {
  const pending = monitorTarget("山药", "query_pending");
  const rejectedStrategy = {
    ...monitorTarget("百合", "paused"),
    availability_reason: "标准名称‘百合’已完成真实搜索验证，但药材语境混入较高，当前未启用。可继续验证更精确的食品搜索策略。",
    queries: [{ query_id: "lily-base", query_text: "百合", validation_status: "rejected_low_relevance" }],
  };
  const paused = monitorTarget("当归", "paused");
  assert.equal(canCreateMonitorTask(pending), false);
  assert.equal(canCreateMonitorTask(rejectedStrategy), false);
  assert.equal(canCreateMonitorTask(paused), false);
  assert.equal(monitorAvailabilityMessage(pending), QUERY_PENDING_MESSAGE);
  assert.equal(monitorAvailabilityLabel(rejectedStrategy), "搜索策略待完善");
  assert.match(monitorAvailabilityMessage(rejectedStrategy), /标准名称‘百合’已完成真实搜索验证/);
  assert.match(monitorAvailabilityMessage(paused), /中药材/);
});

test("product overview distinguishes search-only candidates from analyzed products", () => {
  assert.equal(
    productAnalysisPresentation("pending_detail_collection").label,
    "仅搜索发现，尚未分析",
  );
  assert.equal(
    productAnalysisPresentation("success").label,
    "已完成详情和线索分析",
  );
});

const eligibleReadiness = {
  detailCollected: true,
  ocrInputReady: true,
  ocrReady: true,
  analysisReady: true,
  reviewEligible: true,
  reason: "eligible",
};

function inspection(overrides = {}) {
  return {
    available: true,
    recommendationStatus: "available",
    context: {
      product_category: null,
      product_form: null,
      confirmed_ingredient_contexts: [],
      context_evidence: [],
    },
    riskFindings: [],
    unmappedEvidence: [],
    compositionGaps: [],
    knowledgeGaps: [],
    disclaimer: "",
    recommendationPath: null,
    contextPath: null,
    error: null,
    ...overrides,
  };
}

function evidence(id, overrides = {}) {
  return {
    evidenceId: id,
    effect: "助眠",
    text: "深度睡眠",
    matchedKeywords: ["睡眠"],
    sourceType: "ocr",
    sourceLabel: "详情图 OCR",
    contentOrigin: "seller_managed",
    sourcePath: "ocr/original_001.txt",
    lineNumber: 1,
    ...overrides,
  };
}

test("analysis presentation distinguishes not analyzed, zero evidence, and unavailable recommendation", () => {
  const notAnalyzed = analysisStatePresentation({
    readiness: { ...eligibleReadiness, analysisReady: false, reviewEligible: false },
    evidence: [],
    detectedEffects: [],
    inspection: inspection({ available: false, recommendationStatus: "unavailable" }),
  });
  const zeroEvidence = analysisStatePresentation({
    readiness: eligibleReadiness,
    evidence: [],
    detectedEffects: [],
    inspection: inspection(),
  });
  const unavailable = analysisStatePresentation({
    readiness: eligibleReadiness,
    evidence: [evidence("e1")],
    detectedEffects: ["助眠"],
    inspection: inspection({ available: false, recommendationStatus: "unavailable" }),
  });

  assert.equal(notAnalyzed.code, "NOT_ANALYZED");
  assert.equal(zeroEvidence.code, "ANALYZED_ZERO_EVIDENCE");
  assert.equal(unavailable.code, "RECOMMENDATION_UNAVAILABLE");
  assert.equal(
    productCluePresentation({
      readiness: { ...eligibleReadiness, analysisReady: false },
      detectedEffects: [],
    }),
    "尚未完成线索分析",
  );
  assert.equal(
    productCluePresentation({ readiness: eligibleReadiness, detectedEffects: [] }),
    "已分析，未发现当前规则线索",
  );
});

test("analysis presentation distinguishes unmapped evidence and recommendation errors", () => {
  const unmapped = analysisStatePresentation({
    readiness: eligibleReadiness,
    evidence: [evidence("e1")],
    detectedEffects: ["助眠"],
    inspection: inspection(),
  });
  const errored = analysisStatePresentation({
    readiness: eligibleReadiness,
    evidence: [evidence("e1")],
    detectedEffects: ["助眠"],
    inspection: inspection({ recommendationStatus: "error", error: { message: "boom" } }),
  });

  assert.equal(unmapped.code, "EVIDENCE_UNMAPPED");
  assert.match(unmapped.message, /尚未建立.*映射/);
  assert.equal(errored.code, "RECOMMENDATION_ERROR");
  assert.match(errored.message, /人工复核仍然可用/);
});

test("analysis presentation distinguishes mapped risk without and with verified methods", () => {
  const finding = {
    risk_category: "sleep",
    risk_labels: ["助眠相关宣传线索"],
    possible_risk_summary: "",
    evidence_qualification: "seller_managed_primary",
    substance_follow_ups: [{
      substance_id: "s1",
      canonical_name: "示例物质",
      english_name: "",
      cas_no: "",
      regulatory_context_note: "",
      follow_up_status: "needs_context_review",
      suggested_methods: [],
      methods_needing_context: [],
      other_known_methods: [],
      reason: "",
    }],
  };
  const withoutMethod = analysisStatePresentation({
    readiness: eligibleReadiness,
    evidence: [evidence("e1")],
    detectedEffects: ["助眠"],
    inspection: inspection({ riskFindings: [finding] }),
  });
  const withMethod = analysisStatePresentation({
    readiness: eligibleReadiness,
    evidence: [evidence("e1")],
    detectedEffects: ["助眠"],
    inspection: inspection({
      riskFindings: [{
        ...finding,
        substance_follow_ups: [{
          ...finding.substance_follow_ups[0],
          suggested_methods: [{ method_id: "m1" }],
        }],
      }],
    }),
  });

  assert.equal(withoutMethod.code, "RISK_MAPPED_NO_METHOD");
  assert.equal(withMethod.code, "RECOMMENDATION_AVAILABLE");
});

test("evidence records group by source asset and merge duplicate snippets without losing identities", () => {
  const records = [
    evidence("e1", { matchedKeywords: ["睡眠"], lineNumber: 2 }),
    evidence("e2", { matchedKeywords: ["安神"], effect: "安神", lineNumber: 4 }),
    evidence("e3", { text: "失眠多梦易醒安神", lineNumber: 6 }),
    evidence("e4", { text: "茶养助眠膏", lineNumber: 8 }),
    evidence("e5", { text: "轻松入睡", lineNumber: 10 }),
    evidence("e6", { text: "夜间好眠", lineNumber: 12 }),
    evidence("u1", {
      sourceType: "dom_user_review",
      sourceLabel: "用户评价",
      contentOrigin: "user_generated",
      sourcePath: "page/dom_text.txt#review",
      text: "用户说睡得好",
    }),
    evidence("u2", {
      sourceType: "dom_user_review",
      sourceLabel: "用户评价",
      contentOrigin: "user_generated",
      sourcePath: "page/dom_text.txt#review",
      text: "用户说更精神",
    }),
  ];
  const groups = groupEvidence(records);
  const parts = partitionEvidenceGroups(groups);

  assert.equal(parts.seller.length, 1);
  assert.equal(parts.seller[0].recordCount, 6);
  assert.equal(parts.seller[0].snippets.length, 5);
  assert.deepEqual(parts.seller[0].snippets[0].evidenceIds, ["e1", "e2"]);
  assert.deepEqual(parts.seller[0].snippets[0].matchedKeywords, ["睡眠", "安神"]);
  assert.equal(parts.ugc.length, 1);
  assert.equal(parts.ugc[0].recordCount, 2);
});

test("excluded other-product evidence stays outside seller and UGC evidence", () => {
  const parts = partitionEvidenceGroups(groupEvidence([
    evidence("seller"),
    evidence("ugc", { contentOrigin: "user_generated", sourceType: "dom_user_review" }),
    evidence("noise", { contentOrigin: "excluded_other_product", sourceType: "ocr" }),
  ]));
  assert.equal(parts.seller.length, 1);
  assert.equal(parts.ugc.length, 1);
  assert.equal(parts.excluded.length, 1);
});

test("thumbnail, row activation, timeline, and lightbox helpers are deterministic", () => {
  assert.equal(productThumbnailSource("/local/image.png", false), "/local/image.png");
  assert.equal(productThumbnailSource("/local/image.png", true), null);
  assert.equal(productThumbnailSource(null, false), null);
  assert.equal(isProductRowActivationKey("Enter"), true);
  assert.equal(isProductRowActivationKey(" "), true);
  assert.equal(isProductRowActivationKey("Escape"), false);
  assert.equal(snapshotTimelineMode(1), "compact");
  assert.equal(snapshotTimelineMode(2), "timeline");
  assert.equal(clampLightboxZoom(0.1), 0.5);
  assert.equal(clampLightboxZoom(9), 2.5);
  assert.equal(moveLightboxIndex(0, -1, 3), 2);
  assert.equal(moveLightboxIndex(2, 1, 3), 0);
});

test("declared origin presentation keeps none, provenance, and conflicts explicit", () => {
  const dom = {
    factId: "dom",
    normalizedValue: "中国大陆",
    sourceType: "dom_parameter",
    sourcePath: "dom_text.txt#L10-L11",
  };
  const ocr = {
    factId: "ocr",
    normalizedValue: "河北邢台",
    sourceType: "ocr_detail_image",
    sourcePath: "ocr/original_003.txt#L7",
  };
  const none = { state: "none", values: [], sources: [] };
  const conflict = {
    state: "conflict",
    values: ["中国大陆", "河北邢台"],
    sources: [dom, ocr],
  };

  assert.equal(declaredOriginText(none), "—");
  assert.equal(declaredOriginText(conflict), "存在多个声明");
  assert.equal(productFactSourceLabel("dom_parameter"), "详情参数");
  assert.equal(productFactSourceLabel("ocr_detail_image"), "详情图 OCR");
  assert.equal(productFactArtifactPath(ocr), "ocr/original_003.txt");
  assert.deepEqual(productFactSourcesForValue(conflict, "河北邢台"), [ocr]);
});

test("health-food identity presents every backend state without promoting candidates", () => {
  const expected = {
    no_indicator: "—",
    candidate_indicator_only: "检测到身份线索",
    candidate_identifier: "注册信息待核验",
    identifier_ambiguous: "编号字符待确认",
    registry_lookup_unavailable: "官方查询暂不可用",
    registry_record_not_found: "官方记录未找到",
    registry_record_found_identity_unverified: "官方记录存在 · 对应关系待确认",
    verified_match: "官方记录已核验",
    identity_mismatch: "页面与官方记录存在差异",
    conflict: "身份候选存在冲突",
  };
  for (const [state, label] of Object.entries(expected)) {
    assert.equal(healthFoodIdentityPresentation[state].label, label);
    assert.equal(isVerifiedHealthFoodIdentity(state), state === "verified_match");
  }
  assert.equal(healthFoodIdentityPresentation.candidate_identifier.summary, "保健食品待核验");
  assert.equal(healthFoodIdentityPresentation.verified_match.summary, "保健食品 · 已核验");
});

test("health-food page evidence tolerates legacy sources without path metadata", () => {
  assert.equal(healthFoodSourceLabel(undefined), "页面依据");
  assert.equal(healthFoodArtifactPath(undefined), null);
  assert.equal(healthFoodArtifactPath("ocr\\original_001.txt#L2"), "ocr/original_001.txt");
});

test("health-food detail keeps page evidence, official evidence, functions and OCR lightbox explicit", () => {
  const source = readFileSync(
    new URL("../src/components/HealthFoodIdentitySection.tsx", import.meta.url),
    "utf8",
  );
  assert.match(source, /查看页面依据/);
  assert.match(source, /查看官方依据/);
  assert.match(source, /officialHealthFunctions/);
  assert.match(source, /ImageLightbox/);
  assert.match(source, /打开官方来源/);
});

test("sampling presentation keeps frozen method categories separate", () => {
  const suggested = { methodId: "m1", methodNo: "BJS TEST", methodName: "建议方法" };
  const needsContext = { methodId: "m2", methodNo: "BJS CONTEXT", methodName: "待判断方法" };
  const otherKnown = { methodId: "m3", methodNo: "BJS OTHER", methodName: "其他方法" };
  const item = {
    summary: {
      suggestedMethods: [suggested, { methodId: "empty", methodNo: "", methodName: "" }],
      methodsNeedingContext: [needsContext],
      otherKnownMethods: [otherKnown],
    },
  };
  assert.deepEqual(suggestedSamplingMethods(item), [suggested]);
  assert.deepEqual(samplingMethodGroups(item), {
    suggested: [suggested],
    needsContext: [needsContext],
    otherKnown: [otherKnown],
    legacyUnclassified: [],
  });
});

test("legacy unclassified methods are not promoted to suggested methods", () => {
  const legacy = { methodId: "legacy", methodNo: "OLD", methodName: "旧版方法" };
  const item = { summary: { methods: [legacy] } };
  assert.deepEqual(suggestedSamplingMethods(item), []);
  assert.deepEqual(samplingMethodGroups(item).legacyUnclassified, [legacy]);
});

test("sampling evidence qualification is presented in user language", () => {
  assert.equal(
    evidenceQualificationLabel("seller_managed_primary"),
    "商家管理内容主要线索",
  );
  assert.equal(
    evidenceQualificationLabel("user_generated_auxiliary_only"),
    "用户生成内容辅助线索",
  );
  assert.equal(evidenceQualificationLabel("not_recorded"), "未记录");
});
