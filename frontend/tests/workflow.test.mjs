import assert from "node:assert/strict";
import test from "node:test";

import {
  analysisStatePresentation,
} from "../src/domain/analysis.ts";
import {
  claimConsistencyCountSummary,
  claimConsistencyPresentation,
  claimConsistencyRelationPresentation,
  claimConsistencyRelationViewModels,
  hasClaimAttentionGovernanceGap,
  healthFunctionFrameworkLabel,
  officialFunctionViewModels,
} from "../src/domain/claimConsistency.ts";
import {
  claimMentionEvidence,
  claimPresentation,
  claimSignalLabels,
  claimSignalViewModels,
  claimSourceLabel,
} from "../src/domain/claims.ts";
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
  healthFoodIdentityAnchorId,
  healthFoodIdentityPresentation,
  healthFoodOfficialSourceControlId,
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
    claimType: "sleep_related",
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
    claim_type: "sleep_related",
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
    inspection: inspection({ available: false, recommendationStatus: "unavailable" }),
  });
  const zeroEvidence = analysisStatePresentation({
    readiness: eligibleReadiness,
    evidence: [],
    inspection: inspection(),
  });
  const unavailable = analysisStatePresentation({
    readiness: eligibleReadiness,
    evidence: [evidence("e1")],
    inspection: inspection({ available: false, recommendationStatus: "unavailable" }),
  });

  assert.equal(notAnalyzed.code, "NOT_ANALYZED");
  assert.equal(zeroEvidence.code, "ANALYZED_ZERO_EVIDENCE");
  assert.equal(unavailable.code, "RECOMMENDATION_UNAVAILABLE");
});

test("analysis presentation distinguishes unmapped evidence and recommendation errors", () => {
  const unmapped = analysisStatePresentation({
    readiness: eligibleReadiness,
    evidence: [evidence("e1")],
    inspection: inspection(),
  });
  const errored = analysisStatePresentation({
    readiness: eligibleReadiness,
    evidence: [evidence("e1")],
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
    inspection: inspection({ riskFindings: [finding] }),
  });
  const withMethod = analysisStatePresentation({
    readiness: eligibleReadiness,
    evidence: [evidence("e1")],
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

function claimMention(id, overrides = {}) {
  return {
    claimMentionId: id,
    snapshotId: "snapshot-1",
    claimType: "sleep_related",
    expressionId: "sleep-1",
    rawText: "帮助安睡，轻松入眠",
    normalizedText: "帮助安睡轻松入眠",
    matchedExpression: "安睡",
    evidenceId: "e1",
    sourceScope: "seller_managed",
    sourceAssetType: "ocr",
    sourceLocator: { sourcePath: "ocr/original_001.txt", lineNumber: 3 },
    extractionMethod: "exact_literal_occurrence",
    taxonomyVersion: "2.0.0",
    createdAt: "2026-09-14T10:00:00+08:00",
    ...overrides,
  };
}

function claimSignal(type, label, mentionIds = ["m1"]) {
  return {
    claimSignalId: `signal-${type}`,
    snapshotId: "snapshot-1",
    claimType: type,
    displayLabel: label,
    mentionIds,
    evidenceIds: ["e1"],
    taxonomyVersion: "2.0.0",
    status: "normalized",
    createdAt: "2026-09-14T10:00:00+08:00",
  };
}

function consistencyAssessment(overrides = {}) {
  const base = {
    schemaVersion: 1,
    assessmentVersion: "claim-consistency-v2.0",
    snapshotId: "snapshot-1",
    state: "assessed",
    claimTaxonomyVersion: "claim-taxonomy-v2.0",
    healthFunctionDatasetVersion: "health-functions-v2.0",
    claimHealthFunctionMappingVersion: "claim-health-function-mapping-v2.0",
    healthFoodRegistryIdentifier: "国食健注G00000000",
    healthFoodRegistryRecordReferenceOrHash: "sha256:test",
    healthFoodRegistryRetrievedAt: "2026-09-15T10:00:00+08:00",
    healthFoodRegistrySourceName: "官方登记来源",
    healthFoodRegistrySourceReference: "https://example.invalid/registry",
    healthFoodRegistryRawArtifactPath: "official/registry.json",
    registryFrameworkId: "hf-framework-non-nutrient-cn-2023",
    registryFrameworkResolutionSource: "resolved_official_functions",
    rawOfficialFunctions: ["有助于改善睡眠"],
    resolvedHealthFunctions: [{
      rawOfficialFunction: "有助于改善睡眠",
      resolutionStatus: "resolved",
      resolutionSource: "current_official_name",
      frameworkId: "hf-framework-non-nutrient-cn-2023",
      healthFunctionId: "hf-non-nutrient-cn-2023-06",
      healthFunctionOfficialName: "有助于改善睡眠",
    }],
    unresolvedOfficialFunctions: [],
    claimSignalIds: ["signal-sleep_related"],
    claimMentionIds: ["m1"],
    perClaimAssessments: [{
      claimSignalId: "signal-sleep_related",
      claimType: "sleep_related",
      claimMentionIds: ["m1"],
      evidenceIds: ["e1"],
      relation: "function_topic_recorded",
      mappingId: "sleep-map",
      healthFunctionId: "hf-non-nutrient-cn-2023-06",
      healthFunctionOfficialName: "有助于改善睡眠",
      frameworkId: "hf-framework-non-nutrient-cn-2023",
      supportingResolvedOfficialFunctions: [],
      gaps: [],
    }],
    mentionAttentions: [],
    summary: {
      claimSignalCount: 1,
      functionTopicRecordedCount: 1,
      functionTopicNotRecordedCount: 0,
      noMappingCount: 0,
      mappingUnresolvedCount: 0,
      unresolvedOfficialFunctionCount: 0,
      attentionMentionCount: 0,
    },
    gaps: ["claim_expression_attention_dataset_pending_manual_governance"],
    generatedAt: "2026-09-15T10:00:00+08:00",
  };
  return { ...base, ...overrides };
}

test("claim presentation keeps claims, governed zero, not-generated, and error distinct", () => {
  const one = claimPresentation("complete", [claimSignal("sleep_related", "睡眠相关宣传")]);
  const multiple = claimPresentation("complete", [
    claimSignal("sleep_related", "睡眠相关宣传", ["m1", "m2"]),
    claimSignal("weight_management", "体重管理相关宣传"),
  ]);
  const zero = claimPresentation("complete", []);
  const missing = claimPresentation("not_generated", []);
  const error = claimPresentation("error", []);

  assert.equal(one.summary, "检测到 1 类页面宣传线索，共 1 处表达");
  assert.equal(multiple.summary, "检测到 2 类页面宣传线索，共 3 处表达");
  assert.equal(zero.label, "未发现已治理词表中的页面宣传表达");
  assert.match(zero.description, /不表示无风险、无问题或宣传合规/);
  assert.equal(missing.label, "尚未生成页面宣传线索");
  assert.notEqual(zero.label, missing.label);
  assert.equal(error.label, "页面宣传线索分析失败");
  assert.equal(error.tone, "danger");
  assert.equal(one.tone, "info");
  assert.equal(Object.hasOwn(one, "riskLevel"), false);
});

test("claim consistency keeps operational status separate from domain state", () => {
  const missing = claimConsistencyPresentation("not_generated", null);
  const error = claimConsistencyPresentation("error", null);
  const complete = claimConsistencyPresentation("complete", consistencyAssessment());

  assert.equal(missing.label, "尚未生成保健功能一致性比较");
  assert.equal(missing.tone, "neutral");
  assert.equal(error.label, "保健功能一致性分析失败");
  assert.equal(error.tone, "danger");
  assert.equal(complete.code, "assessed");
  assert.equal(complete.tone, "info");
});

test("claim consistency presents every complete domain state without false failure", () => {
  const expected = {
    identity_not_verified: "保健食品身份尚未核验",
    claim_not_generated: "页面宣传线索尚未生成",
    claim_analysis_error: "页面宣传线索分析失败",
    framework_unresolved: "官方功能框架暂无法确定",
    official_function_unresolved: "当前比较结果不完整",
    no_page_claims: "未发现可比较的页面宣传表达",
    assessed: "逐项主题比较已生成",
  };
  for (const [state, label] of Object.entries(expected)) {
    const view = claimConsistencyPresentation(
      "complete",
      consistencyAssessment({ state }),
    );
    assert.equal(view.label, label);
    assert.notEqual(view.tone, "danger");
  }
  assert.equal(
    claimConsistencyPresentation(
      "complete",
      consistencyAssessment({ state: "identity_not_verified" }),
    ).showRelations,
    false,
  );
});

test("claim consistency relation wording and colors remain non-adjudicative", () => {
  assert.deepEqual(
    Object.fromEntries(Object.entries(claimConsistencyRelationPresentation).map(
      ([relation, item]) => [relation, item.tone],
    )),
    {
      function_topic_recorded: "info",
      function_topic_not_recorded: "warning",
      no_governed_function_mapping: "neutral",
      mapping_unresolved: "warning",
    },
  );
  assert.match(
    claimConsistencyRelationPresentation.function_topic_recorded.description,
    /不代表具体页面措辞获得官方认可/,
  );
  assert.match(
    claimConsistencyRelationPresentation.function_topic_not_recorded.description,
    /建议人工复核/,
  );
  assert.match(
    claimConsistencyRelationPresentation.no_governed_function_mapping.label,
    /暂无已治理/,
  );
  assert.match(
    claimConsistencyRelationPresentation.mapping_unresolved.description,
    /不能显示为未找到对应项/,
  );
});

test("partial unresolved keeps positive evidence and protects negative comparison", () => {
  const signal = claimSignal("sleep_related", "睡眠相关宣传");
  const unresolved = {
    rawOfficialFunction: "某个无法治理解析的官方原文",
    resolutionStatus: "unresolved",
    resolutionSource: null,
    frameworkId: null,
    healthFunctionId: null,
    healthFunctionOfficialName: null,
  };
  const partialPositive = consistencyAssessment({
    state: "official_function_unresolved",
    rawOfficialFunctions: ["有助于改善睡眠", unresolved.rawOfficialFunction],
    unresolvedOfficialFunctions: [unresolved],
    summary: {
      ...consistencyAssessment().summary,
      unresolvedOfficialFunctionCount: 1,
    },
  });
  const positiveRows = claimConsistencyRelationViewModels(
    partialPositive,
    [signal],
    [claimMention("m1")],
    [evidence("e1")],
  );
  assert.equal(positiveRows[0].assessment.relation, "function_topic_recorded");
  assert.equal(
    claimConsistencyPresentation("complete", partialPositive).label,
    "当前比较结果不完整",
  );

  const partialNegative = consistencyAssessment({
    state: "official_function_unresolved",
    rawOfficialFunctions: ["有助于增强免疫力", unresolved.rawOfficialFunction],
    unresolvedOfficialFunctions: [unresolved],
    perClaimAssessments: [{
      ...consistencyAssessment().perClaimAssessments[0],
      relation: "mapping_unresolved",
      gaps: ["unresolved_official_function_may_affect_comparison"],
    }],
    summary: {
      ...consistencyAssessment().summary,
      functionTopicRecordedCount: 0,
      mappingUnresolvedCount: 1,
      unresolvedOfficialFunctionCount: 1,
    },
  });
  const negativeRows = claimConsistencyRelationViewModels(
    partialNegative,
    [signal],
    [claimMention("m1")],
    [evidence("e1")],
  );
  assert.equal(negativeRows[0].assessment.relation, "mapping_unresolved");
  assert.doesNotMatch(negativeRows[0].presentation.label, /未找到对应项/);
  assert.equal(negativeRows[0].pageTraceAvailable, true);
  assert.equal(
    claimConsistencyRelationViewModels(partialNegative, [signal], [], [])[0]
      .pageTraceAvailable,
    false,
  );
});

test("official function presentation retains raw aliases and unresolved descriptive text", () => {
  const alias = consistencyAssessment({
    rawOfficialFunctions: ["改善睡眠"],
    resolvedHealthFunctions: [{
      ...consistencyAssessment().resolvedHealthFunctions[0],
      rawOfficialFunction: "改善睡眠",
      resolutionSource: "official_transition_alias",
    }],
  });
  const aliasView = officialFunctionViewModels(alias)[0];
  assert.equal(aliasView.currentName, "有助于改善睡眠");
  assert.equal(aliasView.rawText, "改善睡眠");
  assert.equal(aliasView.resolutionLabel, "官方新旧功能名称衔接");
  assert.equal(aliasView.showRawText, true);

  const descriptive = "本品经动物实验评价，具有对化学性肝损伤有辅助保护作用的保健功能";
  const unresolved = consistencyAssessment({
    state: "framework_unresolved",
    registryFrameworkId: null,
    rawOfficialFunctions: [descriptive],
    resolvedHealthFunctions: [],
    unresolvedOfficialFunctions: [{
      rawOfficialFunction: descriptive,
      resolutionStatus: "unresolved",
      resolutionSource: null,
      frameworkId: null,
      healthFunctionId: null,
      healthFunctionOfficialName: null,
    }],
  });
  const unresolvedView = officialFunctionViewModels(unresolved)[0];
  assert.equal(unresolvedView.rawText, descriptive);
  assert.equal(unresolvedView.currentName, null);
  assert.equal(unresolvedView.resolutionLabel, "暂无法通过已治理名称解析");
});

test("claim consistency counts are descriptive and attention absence stays a gap", () => {
  const assessment = consistencyAssessment({
    summary: {
      claimSignalCount: 4,
      functionTopicRecordedCount: 2,
      functionTopicNotRecordedCount: 1,
      noMappingCount: 1,
      mappingUnresolvedCount: 0,
      unresolvedOfficialFunctionCount: 0,
      attentionMentionCount: 0,
    },
  });
  const summary = claimConsistencyCountSummary(assessment);
  assert.equal(
    summary,
    "4 类页面宣传主题：2 类找到官方功能对应主题，1 类未在当前官方功能记录中找到对应项，1 类暂无治理映射。",
  );
  assert.doesNotMatch(summary, /%|通过率|一致率|风险分/);
  assert.equal(hasClaimAttentionGovernanceGap(assessment), true);
  assert.equal(assessment.mentionAttentions.length, 0);
  assert.equal(healthFunctionFrameworkLabel(null), "暂无法确定");
});

test("claim consistency is shared by detail and workspace with existing trace controls", () => {
  const files = {
    section: readFileSync(new URL("../src/components/ClaimConsistencySection.tsx", import.meta.url), "utf8"),
    detail: readFileSync(new URL("../src/pages/products/ProductDetailPanel.tsx", import.meta.url), "utf8"),
    workspace: readFileSync(new URL("../src/pages/inspections/InspectionWorkspaceDetail.tsx", import.meta.url), "utf8"),
    identity: readFileSync(new URL("../src/components/HealthFoodIdentitySection.tsx", import.meta.url), "utf8"),
    query: readFileSync(new URL("../src/domain/productQuery.ts", import.meta.url), "utf8"),
  };
  assert.match(files.detail, /<ClaimConsistencySection/);
  assert.match(files.workspace, /<ClaimConsistencySection/);
  assert.match(files.section, /claimSignalAnchorId/);
  assert.match(files.section, /officialSourceControlId/);
  assert.match(files.identity, /healthFoodOfficialSourceControlId/);
  assert.doesNotMatch(files.query, /claimConsistency|consistency_status/);
  assert.ok(
    files.detail.indexOf("<ClaimAnalysisSection")
      < files.detail.indexOf("<ClaimConsistencySection"),
  );
  assert.ok(
    files.detail.indexOf("<ClaimConsistencySection")
      < files.detail.indexOf("<RecommendationPanel"),
  );
  assert.ok(
    files.workspace.indexOf("<ClaimAnalysisSection")
      < files.workspace.indexOf("<ClaimConsistencySection"),
  );
  assert.equal(
    healthFoodIdentityAnchorId("snapshot:1"),
    "health-food-identity-snapshot-1",
  );
  assert.equal(
    healthFoodOfficialSourceControlId("snapshot:1"),
    "health-food-official-source-snapshot-1",
  );
});

test("claim consistency stays selected-Snapshot scoped and read-only", () => {
  const snapshotA = claimConsistencyPresentation(
    "complete",
    consistencyAssessment({ snapshotId: "snapshot-a" }),
  );
  const snapshotB = claimConsistencyPresentation("not_generated", null);
  assert.equal(snapshotA.label, "逐项主题比较已生成");
  assert.equal(snapshotB.label, "尚未生成保健功能一致性比较");

  const component = readFileSync(
    new URL("../src/components/ClaimConsistencySection.tsx", import.meta.url),
    "utf8",
  );
  const detail = readFileSync(
    new URL("../src/pages/products/ProductDetailPanel.tsx", import.meta.url),
    "utf8",
  );
  const workspace = readFileSync(
    new URL("../src/pages/inspections/InspectionWorkspaceDetail.tsx", import.meta.url),
    "utf8",
  );
  assert.match(detail, /status=\{workspace\.claimConsistencyStatus\}/);
  assert.match(detail, /assessment=\{workspace\.claimConsistency\}/);
  assert.match(workspace, /status=\{workspace\.claimConsistencyStatus\}/);
  assert.match(workspace, /assessment=\{workspace\.claimConsistency\}/);
  assert.doesNotMatch(
    component,
    /ReviewActions|SamplingStore|RecommendationPanel|fetch\(|axios|updateReview|review-decision/,
  );
});

test("legacy effects and UGC text cannot fabricate a V2 claim presentation", () => {
  const legacySnapshot = {
    claimAnalysisStatus: "not_generated",
    claimSignals: [],
    detectedEffects: ["助眠"],
  };
  const ugcOnlySnapshot = {
    claimAnalysisStatus: "complete",
    claimSignals: [],
    detectedEffects: ["助眠"],
    evidence: [evidence("ugc", {
      text: "安睡",
      contentOrigin: "user_generated",
      sourceType: "dom_user_review",
    })],
  };

  assert.equal(
    claimPresentation(legacySnapshot.claimAnalysisStatus, legacySnapshot.claimSignals).code,
    "not_generated",
  );
  assert.equal(
    claimPresentation(ugcOnlySnapshot.claimAnalysisStatus, ugcOnlySnapshot.claimSignals).code,
    "zero",
  );
});

test("claim view models preserve raw context, multiple mentions, and evidence trace fallback", () => {
  const linked = claimMention("m1");
  const unavailable = claimMention("m2", {
    rawText: "页面另一处安睡表达",
    evidenceId: "missing-evidence",
  });
  const signal = claimSignal("sleep_related", "睡眠相关宣传", ["m1", "m2"]);
  const view = claimSignalViewModels([signal], [linked, unavailable])[0];

  assert.equal(view.mentionCount, 2);
  assert.equal(view.mentions[0].rawText, "帮助安睡，轻松入眠");
  assert.equal(view.mentions[0].matchedExpression, "安睡");
  assert.equal(claimSourceLabel("ocr", evidence("e1")), "详情图片 OCR");
  assert.equal(claimMentionEvidence(linked, [evidence("e1")]).evidenceId, "e1");
  assert.equal(claimMentionEvidence(unavailable, [evidence("e1")]), null);
  assert.deepEqual(claimSignalLabels([
    signal,
    claimSignal("weight_management", "体重管理相关宣传"),
    claimSignal("blood_pressure_related", "血压相关宣传"),
  ]), { labels: ["睡眠相关宣传", "体重管理相关宣传"], remaining: 1 });
});

test("primary claim surfaces consume V2 fields and keep frozen sampling explicit", () => {
  const files = {
    detail: readFileSync(new URL("../src/components/ClaimAnalysisSection.tsx", import.meta.url), "utf8"),
    list: readFileSync(new URL("../src/pages/products/ProductTable.tsx", import.meta.url), "utf8"),
    review: readFileSync(new URL("../src/pages/inspections/ReviewQueue.tsx", import.meta.url), "utf8"),
    sampling: readFileSync(new URL("../src/pages/sampling/SamplingListTable.tsx", import.meta.url), "utf8"),
    samplingDrawer: readFileSync(new URL("../src/pages/sampling/SamplingListDrawer.tsx", import.meta.url), "utf8"),
    evidence: readFileSync(new URL("../src/components/EvidenceGroupCard.tsx", import.meta.url), "utf8"),
    productDetail: readFileSync(new URL("../src/pages/products/ProductDetailPanel.tsx", import.meta.url), "utf8"),
    claimDomain: readFileSync(new URL("../src/domain/claims.ts", import.meta.url), "utf8"),
  };

  assert.match(files.detail, /mention\.rawText/);
  assert.match(files.detail, /mention\.matchedExpression/);
  assert.match(files.detail, /来源信息不可用/);
  assert.match(files.detail, /<details/);
  assert.match(files.list, /claimSignalSummaries/);
  assert.doesNotMatch(files.list, /detectedEffects/);
  assert.match(files.review, /claimSignalSummaries/);
  assert.doesNotMatch(files.review, /detectedEffects/);
  assert.match(files.sampling, /旧版冻结分析结果/);
  assert.match(files.sampling, /claimSignals/);
  assert.match(files.samplingDrawer, /不属于 V2 页面宣传线索/);
  assert.doesNotMatch(files.evidence, /snippet\.effects|snippet\.matchedKeywords/);
  assert.doesNotMatch(files.claimDomain, /riskLevel|severity|probability|HealthFunction|RiskSignal/);
  assert.ok(
    files.productDetail.indexOf("<EvidenceReviewSection")
      < files.productDetail.indexOf("<ClaimAnalysisSection"),
  );
  assert.ok(
    files.productDetail.indexOf("<ClaimAnalysisSection")
      < files.productDetail.indexOf("<RecommendationPanel"),
  );
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
