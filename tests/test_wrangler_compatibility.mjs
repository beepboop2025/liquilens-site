// `wrangler deploy --dry-run` packages a Worker without starting the runtime, so a
// compatibility_date newer than the pinned workerd passes that check and fails
// later, at `wrangler dev` or at deploy time. Keep every Worker within the
// runtime this repository pins.
import assert from "node:assert/strict";
import { readdir, readFile } from "node:fs/promises";
import test from "node:test";
import { compatibilityDate as pinnedRuntimeDate } from "workerd";

const ROOT = new URL("../", import.meta.url);
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
const KNOWN_WORKERS = [
  "wrangler.catalog.jsonc",
  "wrangler.financial-evidence.jsonc",
  "wrangler.payments.jsonc",
];

test("every Worker compatibility date is supported by the pinned workerd", async () => {
  assert.match(pinnedRuntimeDate, ISO_DATE);
  const configs = (await readdir(ROOT)).filter((name) => /^wrangler\..+\.jsonc$/.test(name)).sort();
  for (const name of KNOWN_WORKERS) assert.ok(configs.includes(name), `${name} is missing`);
  for (const name of configs) {
    const { compatibility_date: date } = JSON.parse(await readFile(new URL(name, ROOT), "utf8"));
    assert.match(date, ISO_DATE, name);
    assert.ok(
      date <= pinnedRuntimeDate,
      `${name} requests ${date}, but the pinned workerd supports dates through ` +
        `${pinnedRuntimeDate}. Use an earlier date, or upgrade Wrangler first.`,
    );
  }
});
