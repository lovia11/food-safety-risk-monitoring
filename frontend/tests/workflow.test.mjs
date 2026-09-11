import assert from "node:assert/strict";
import test from "node:test";

import { productAnalysisPresentation } from "../src/domain/product.ts";
import { productQueryString } from "../src/domain/productQuery.ts";
import { reviewPresentation } from "../src/domain/presentation.ts";
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
