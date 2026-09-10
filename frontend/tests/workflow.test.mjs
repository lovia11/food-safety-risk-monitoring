import assert from "node:assert/strict";
import test from "node:test";

import { queueMatches } from "../src/domain/reviewQueue.ts";
import {
  evidenceQualificationLabel,
  samplingMethods,
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

test("sampling presentation uses only frozen method facts", () => {
  const item = {
    summary: {
      methods: [
        { methodId: "m1", methodNo: "BJS TEST", methodName: "已核验方法" },
        { methodId: "empty", methodNo: "", methodName: "" },
      ],
    },
  };
  assert.deepEqual(samplingMethods(item), [item.summary.methods[0]]);
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
});
