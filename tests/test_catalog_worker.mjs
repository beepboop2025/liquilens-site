import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import worker, { CATALOG_PATH } from "../edge/catalog-worker.mjs";


test("GET returns the committed ARD catalog with discovery headers", async () => {
  const response = await worker.fetch(
    new Request(`https://liquilens.in${CATALOG_PATH}`),
  );
  const catalog = await response.json();
  const expected = JSON.parse(
    await readFile(new URL("../.well-known/ai-catalog.json", import.meta.url), "utf8"),
  );

  assert.equal(response.status, 200);
  assert.deepEqual(catalog, expected);
  assert.equal(catalog.specVersion, "1.0");
  assert.equal(catalog.entries.length, 11);
  const carrier = catalog.entries.find(
    (entry) => entry.identifier === "urn:air:liquilens.in:protocol:evidence-carrier",
  );
  assert.equal(carrier.version, "0.14.0");
  assert.equal(
    carrier.metadata.mcpBundleSha256,
    "e57e3039d7ae53b6feb3638dbc2f7ba413ff437e5c3a1b62172cad6f3b98e6ea",
  );
  assert.equal(
    carrier.metadata.browserVerifier,
    "https://beepboop2025.github.io/liquilens-evidence-carrier/",
  );
  assert.match(response.headers.get("content-type"), /^application\/ai-catalog\+json/);
  assert.equal(response.headers.get("access-control-allow-origin"), "*");
});


test("HEAD and OPTIONS are bodyless, and mutation methods are rejected", async () => {
  const url = `https://liquilens.in${CATALOG_PATH}`;
  const head = await worker.fetch(new Request(url, { method: "HEAD" }));
  const options = await worker.fetch(new Request(url, { method: "OPTIONS" }));
  const post = await worker.fetch(new Request(url, { method: "POST" }));

  assert.equal(head.status, 200);
  assert.equal(await head.text(), "");
  assert.equal(options.status, 204);
  assert.equal(options.headers.get("access-control-max-age"), "86400");
  assert.equal(post.status, 405);
  assert.equal(post.headers.get("allow"), "GET, HEAD, OPTIONS");
});


test("the handler refuses paths outside its exact route", async () => {
  const response = await worker.fetch(
    new Request("https://liquilens.in/.well-known/not-the-catalog.json"),
  );
  assert.equal(response.status, 404);
});
