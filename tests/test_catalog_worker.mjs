import assert from "node:assert/strict";
import test from "node:test";

import worker, { CATALOG_PATH } from "../edge/catalog-worker.mjs";


test("GET returns the committed ARD catalog with discovery headers", async () => {
  const response = await worker.fetch(
    new Request(`https://liquilens.in${CATALOG_PATH}`),
  );
  const catalog = await response.json();

  assert.equal(response.status, 200);
  assert.equal(catalog.specVersion, "1.0");
  assert.ok(catalog.entries.length >= 4);
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
