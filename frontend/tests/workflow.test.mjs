import assert from "node:assert/strict";
import test from "node:test";

import { queueMatches } from "../src/domain/reviewQueue.ts";
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
