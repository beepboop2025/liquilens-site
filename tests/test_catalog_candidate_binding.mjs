import assert from "node:assert/strict";
import test from "node:test";

import {
  bindCatalogCandidate,
  extractCandidateId,
} from "../scripts/bind_catalog_candidate.mjs";

const SHA = "d118150cdd95815edd742d61dbc3fd82381b33bf";
const VERSION_ID = "e422cb90-cb39-428c-a421-9f755fea9d76";

function upload(overrides = {}) {
  return {
    type: "version-upload",
    version_id: VERSION_ID,
    worker_name: "liquilens-ai-catalog",
    worker_name_overridden: false,
    worker_tag: "6ec80a4c5f04482aafbbaf5a5708edfa",
    ...overrides,
  };
}

function receipt(...uploads) {
  return [
    JSON.stringify({ type: "wrangler-session", wrangler_version: "4.125.0" }),
    ...uploads.map((row) => JSON.stringify(row)),
  ].join("\n");
}

function version(overrides = {}) {
  return {
    id: VERSION_ID,
    metadata: { source: "wrangler" },
    annotations: {
      "workers/tag": SHA,
      "workers/message": `GitHub-${SHA}`,
      "workers/triggered_by": "version_upload",
    },
    ...overrides,
  };
}

test("binds Wrangler's internal receipt tag through immutable Cloudflare metadata", () => {
  const actual = bindCatalogCandidate({
    receiptText: receipt(upload()),
    versionText: JSON.stringify(version()),
    expectedSha: SHA,
  });
  assert.equal(actual, VERSION_ID);
});

test("rejects empty, malformed, duplicate, and ambiguously named upload receipts", () => {
  assert.throws(() => extractCandidateId(""), /receipt is empty/u);
  assert.throws(() => extractCandidateId("not-json"), /not valid JSON/u);
  assert.throws(() => extractCandidateId(receipt()), /emitted 0/u);
  assert.throws(
    () => extractCandidateId(receipt(upload(), upload())),
    /emitted 2/u,
  );
  assert.throws(
    () => extractCandidateId(receipt(upload({ version_id: "not-a-uuid" }))),
    /canonical lowercase UUID/u,
  );
  assert.throws(
    () => extractCandidateId(receipt(upload({ worker_name: "other-worker" }))),
    /wrong or overridden Worker/u,
  );
  assert.throws(
    () => extractCandidateId(receipt(upload({ worker_name_overridden: true }))),
    /wrong or overridden Worker/u,
  );
});

test("rejects every cross-layer candidate identity mismatch", () => {
  const cases = [
    ["id", { id: "00000000-0000-0000-0000-000000000000" }, /metadata ID differs/u],
    ["source", { metadata: { source: "dashboard" } }, /unexpected source/u],
    [
      "tag",
      { annotations: { ...version().annotations, "workers/tag": "0".repeat(40) } },
      /tag differs/u,
    ],
    [
      "message",
      { annotations: { ...version().annotations, "workers/message": "wrong" } },
      /message differs/u,
    ],
    [
      "trigger",
      { annotations: { ...version().annotations, "workers/triggered_by": "deployment" } },
      /not created by a version upload/u,
    ],
  ];
  for (const [label, overrides, expected] of cases) {
    assert.throws(
      () =>
        bindCatalogCandidate({
          receiptText: receipt(upload()),
          versionText: JSON.stringify(version(overrides)),
          expectedSha: SHA,
        }),
      expected,
      label,
    );
  }
  assert.throws(
    () =>
      bindCatalogCandidate({
        receiptText: receipt(upload()),
        versionText: JSON.stringify(version()),
        expectedSha: SHA.toUpperCase(),
      }),
    /40 lowercase hexadecimal/u,
  );
});
