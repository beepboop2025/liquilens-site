import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import worker, {
  AI_CATALOG_PATH,
  CATALOG_PATH,
  OPENAI_APPS_CHALLENGE_PATH,
  PROTOCOL_CATALOG_PATH,
} from "../edge/catalog-worker.mjs";


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
  assert.equal(catalog.entries.length, 13);
  const carrier = catalog.entries.find(
    (entry) => entry.identifier === "urn:air:liquilens.in:protocol:evidence-carrier",
  );
  assert.equal(carrier.version, "0.15.0");
  assert.equal(
    carrier.metadata.mcpBundleSha256,
    "c3cad6d894ed0b8b36017f8349188a9854c20d48a50536af8b256e079b92de9d",
  );
  assert.equal(
    carrier.metadata.browserVerifier,
    "https://beepboop2025.github.io/liquilens-evidence-carrier/",
  );
  assert.match(response.headers.get("content-type"), /^application\/ai-catalog\+json/);
  assert.equal(response.headers.get("access-control-allow-origin"), "*");
  assert.equal(
    response.headers.get("link"),
    '<https://liquilens.in/protocol/catalog.json>; rel="alternate"; type="application/json"',
  );
});


test("GET returns the exact protocol catalog with standards-based discovery", async () => {
  const response = await worker.fetch(
    new Request(`https://liquilens.in${PROTOCOL_CATALOG_PATH}`),
  );
  const actual = await response.json();
  const expected = JSON.parse(
    await readFile(new URL("../protocol/catalog.json", import.meta.url), "utf8"),
  );

  assert.equal(response.status, 200);
  assert.deepEqual(actual, expected);
  assert.equal(response.headers.get("content-type"), "application/json; charset=utf-8");
  assert.equal(response.headers.get("access-control-allow-origin"), "*");
  assert.equal(response.headers.get("x-content-type-options"), "nosniff");
  assert.equal(
    response.headers.get("link"),
    [
      '<https://liquilens.in/protocol/liquilens-evidence-carrier-v1.schema.json>; rel="describedby"; type="application/schema+json"',
      '<https://liquilens.in/.well-known/ai-catalog.json>; rel="alternate"; type="application/ai-catalog+json"',
    ].join(", "),
  );
});


test("HEAD and OPTIONS are bodyless, and mutation methods are rejected", async () => {
  for (const path of [AI_CATALOG_PATH, PROTOCOL_CATALOG_PATH]) {
    const url = `https://liquilens.in${path}`;
    const head = await worker.fetch(new Request(url, { method: "HEAD" }));
    const options = await worker.fetch(new Request(url, { method: "OPTIONS" }));
    const post = await worker.fetch(new Request(url, { method: "POST" }));

    assert.equal(head.status, 200);
    assert.equal(await head.text(), "");
    assert.equal(options.status, 204);
    assert.equal(options.headers.get("access-control-max-age"), "86400");
    assert.equal(post.status, 405);
    assert.equal(post.headers.get("allow"), "GET, HEAD, OPTIONS");
  }
});


test("the handler refuses paths outside its exact route", async () => {
  const response = await worker.fetch(
    new Request("https://liquilens.in/.well-known/not-the-catalog.json"),
  );
  assert.equal(response.status, 404);
});


test("OpenAI Apps challenge stays absent until its exact token is configured", async () => {
  const url = `https://liquilens.in${OPENAI_APPS_CHALLENGE_PATH}`;
  for (const env of [undefined, {}, { OPENAI_APPS_CHALLENGE_TOKEN: "" }]) {
    const response = await worker.fetch(new Request(url), env);
    assert.equal(response.status, 404);
    assert.equal(await response.text(), "Not found");
  }
});


test("OpenAI Apps challenge returns the configured token byte-for-byte", async () => {
  const token = "issued-token-Δ";
  const tokenBytes = new TextEncoder().encode(token).byteLength;
  const env = { OPENAI_APPS_CHALLENGE_TOKEN: token };
  const url = `https://liquilens.in${OPENAI_APPS_CHALLENGE_PATH}`;

  const get = await worker.fetch(new Request(url), env);
  const head = await worker.fetch(new Request(url, { method: "HEAD" }), env);

  assert.equal(get.status, 200);
  assert.equal(await get.text(), token);
  assert.equal(get.headers.get("content-type"), "text/plain; charset=utf-8");
  assert.equal(get.headers.get("cache-control"), "no-store");
  assert.equal(get.headers.get("x-content-type-options"), "nosniff");
  assert.equal(get.headers.get("content-length"), String(tokenBytes));
  assert.equal(head.status, 200);
  assert.equal(await head.text(), "");
  assert.equal(head.headers.get("content-length"), String(tokenBytes));
});


test("OpenAI Apps challenge rejects non-read methods when configured", async () => {
  const env = { OPENAI_APPS_CHALLENGE_TOKEN: "issued-token" };
  const url = `https://liquilens.in${OPENAI_APPS_CHALLENGE_PATH}`;

  for (const method of ["POST", "PUT", "PATCH", "DELETE", "OPTIONS"]) {
    const response = await worker.fetch(new Request(url, { method }), env);
    assert.equal(response.status, 405);
    assert.equal(response.headers.get("allow"), "GET, HEAD");
  }
});


test("the deployed Worker declares the fail-closed MCP fetch limiter", async () => {
  const config = JSON.parse(
    await readFile(new URL("../wrangler.catalog.jsonc", import.meta.url), "utf8"),
  );
  assert.deepEqual(config.ratelimits, [
    {
      name: "FINANCIAL_EVIDENCE_RATE_LIMITER",
      namespace_id: "24082401",
      simple: { limit: 60, period: 60 },
    },
  ]);
  assert.deepEqual(config.version_metadata, { binding: "CF_VERSION_METADATA" });
  assert.equal(config.limits, undefined);
  assert.equal(
    config.routes.some(
      (route) =>
        route.pattern === "https://liquilens.in/mcp/financial-evidence*",
    ),
    true,
  );
  assert.equal(
    config.routes.some(
      (route) =>
        route.pattern ===
        "https://liquilens.in/.well-known/openai-apps-challenge*",
    ),
    true,
  );
});


test("runtime responses expose exact Cloudflare version metadata", async () => {
  const response = await worker.fetch(
    new Request(`https://liquilens.in${AI_CATALOG_PATH}`),
    {
      CF_VERSION_METADATA: {
        id: "00000000-0000-0000-0000-000000000040",
        tag: "0123456789abcdef0123456789abcdef01234567",
      },
    },
  );
  assert.equal(
    response.headers.get("x-liquilens-worker-version"),
    "00000000-0000-0000-0000-000000000040",
  );
  assert.equal(
    response.headers.get("x-liquilens-worker-tag"),
    "0123456789abcdef0123456789abcdef01234567",
  );
});
