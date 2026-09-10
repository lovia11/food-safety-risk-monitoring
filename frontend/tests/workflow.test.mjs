import assert from "node:assert/strict";
import test from "node:test";

import { queueMatches } from "../src/domain/reviewQueue.ts";
import {
  evidenceQualificationLabel,
  samplingMethodGroups,
  suggestedSamplingMethods,
} from "../src/domain/sampling.ts";
import { shouldResumeTask } from "../src/domain/task.ts";

test("pending snapshot remains in pending queue when product has a membership", () => {
  const item = {
    sampling: {
      decisionStatus: "pending",
      inCurrentList: true,
      sourceSnapshotId: "older-snapshot",
    },
  };

  assert.equal(queueMatches(item, "pending"), true);
  assert.equal(queueMatches(item, "current"), false);
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
