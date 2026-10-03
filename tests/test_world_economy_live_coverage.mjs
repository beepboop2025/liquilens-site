import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import test from "node:test";

const source = await readFile(new URL("../world-economy/coverage.js", import.meta.url), "utf8");
const {coverageSummary, startCoverage} = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
const settle = () => new Promise(resolve => setImmediate(resolve));
const jsonResponse = data => new Response(JSON.stringify(data), {status: 200});

function catalog() {
  return {service: "liquilens-market-corpus", schema_version: "1.0.0", release_id: "corpus-abcd",
    knowledge_time: "2026-08-11T01:00:00Z", generated_at: "2026-10-04T00:00:00Z",
    corpora: {bis: {flows: 3, bulk_flat: 2, api_only: 1, registry_only: 0, inventory_sha256: "a".repeat(64),
      materialization: {schema: "liquilens-bis-live-materialization-v1", release_id: "corpus-abcd",
        inventory_sha256: "a".repeat(64), error_count: 0, expected_count: 2, materialized_count: 2,
        aggregate_row_count: 30, generated_at: "2026-10-03T23:00:00Z", expected_flow_ids: ["WS_A", "WS_B"],
        flows: [10, 20].map((rows, i) => ({flow_id: i ? "WS_B" : "WS_A", row_count: rows,
          capture_id: i + 1, normalized_sha256: "b".repeat(64), manifest_sha256: "c".repeat(64)}))}}}};
}

function harness(fetcher) {
  const nodes = new Map();
  const root = {querySelector(key) {
    if (!nodes.has(key)) nodes.set(key, {textContent: "", hidden: true});
    return nodes.get(key);
  }};
  const docEvents = new Map(), winEvents = new Map(), scheduled = new Map();
  const document = {hidden: false, addEventListener: (k, f) => docEvents.set(k, f),
    removeEventListener: k => docEvents.delete(k)};
  const window = {addEventListener: (k, f) => winEvents.set(k, f), removeEventListener: k => winEvents.delete(k)};
  let id = 0;
  const timers = {setTimeout: (f, delay) => { scheduled.set(++id, {f, delay}); return id; },
    clearTimeout: k => scheduled.delete(k)};
  const app = startCoverage(root, {document, window, timers, fetch: fetcher});
  return {app, nodes, document, docEvents, winEvents, scheduled,
    node: name => root.querySelector(`[data-coverage-${name}]`)};
}

test("coverage preserves independent clocks and takes counts from the admitted census", () => {
  const summary = coverageSummary(catalog());
  assert.equal(summary.flows, 2);
  assert.equal(summary.records, 30);
  assert.equal(summary.catalogKnowledgeAt, "2026-08-11T01:00:00.000Z");
  assert.equal(summary.materializedAt, "2026-10-03T23:00:00.000Z");
  assert.equal(summary.responseAt, "2026-10-04T00:00:00.000Z");
});

for (const [label, mutation] of [
  ["missing source", data => delete data.corpora],
  ["failed materialization", data => data.corpora.bis.materialization.error_count++],
  ["wrong count", data => data.corpora.bis.materialization.aggregate_row_count++],
  ["duplicate flow", data => data.corpora.bis.materialization.flows[1].flow_id = "WS_A"],
  ["partial census", data => data.corpora.bis.materialization.flows.pop()],
  ["wrong release", data => data.corpora.bis.materialization.release_id = "corpus-ffff"],
  ["bad source clock", data => data.knowledge_time = "yesterday"],
  ["naive clock", data => data.knowledge_time = "2026-08-11T00:00:00"],
]) {
  test(`${label} cannot become a live count or a fake zero`, () => {
    const data = catalog(); mutation(data);
    assert.throws(() => coverageSummary(data));
  });
}

test("render uses canonical source, exact counts, accessible status and one refresh timer", async () => {
  let options;
  const h = harness(async (url, init) => { assert.equal(url, "https://api.seiche.info/api/v2/corpus/v1/catalog"); options = init; return jsonResponse(catalog()); });
  await settle();
  assert.equal(h.node("records").textContent, "30");
  assert.equal(h.node("values").hidden, false);
  assert.equal(options.cache, "no-store");
  assert.equal(options.credentials, "omit");
  assert.deepEqual([...h.scheduled.values()].map(t => t.delay), [60_000]);
  h.app.dispose();
});

test("failed refresh hides previous numbers and never substitutes dated counts", async () => {
  let fail = false;
  const h = harness(async () => { if (fail) throw new Error("offline"); return jsonResponse(catalog()); });
  await settle(); fail = true;
  await h.app.refresh();
  assert.equal(h.node("values").hidden, true);
  assert.match(h.node("status").textContent, /unavailable/);
  h.app.dispose();
});

test("hidden page aborts pending request and ignores late response; visibility resumes", async () => {
  let resolve, signal;
  const h = harness((url, init) => { signal = init.signal; return new Promise(r => { resolve = r; }); });
  h.document.hidden = true;
  h.docEvents.get("visibilitychange")();
  assert.equal(signal.aborted, true);
  resolve(jsonResponse(catalog()));
  await settle();
  assert.equal(h.node("values").hidden, true);
  assert.equal(h.scheduled.size, 0);
  h.document.hidden = false;
  h.docEvents.get("visibilitychange")();
  resolve(jsonResponse(catalog()));
  await settle();
  assert.equal(h.node("values").hidden, false);
  h.app.dispose();
});

test("late old response cannot overwrite a newer generation", async () => {
  const requests = [];
  const h = harness(() => new Promise(resolve => requests.push(resolve)));
  const newer = catalog(); newer.corpora.bis.materialization.flows[0].row_count = 11;
  newer.corpora.bis.materialization.aggregate_row_count = 31;
  const pending = h.app.refresh();
  requests[1](jsonResponse(newer)); await pending;
  requests[0](jsonResponse(catalog())); await settle();
  assert.equal(h.node("records").textContent, "31");
  h.app.dispose();
});

test("pagehide aborts work and pageshow resumes a restored page", async () => {
  const h = harness(async () => jsonResponse(catalog()));
  await settle(); h.winEvents.get("pagehide")();
  assert.equal(h.scheduled.size, 0);
  assert.equal(h.node("values").hidden, true);
  h.winEvents.get("pageshow")(); await settle();
  assert.equal(h.node("values").hidden, false);
  h.app.dispose(); assert.equal(h.winEvents.size, 0);
});

test("timeout aborts the network and oversized catalogs are rejected", async () => {
  const h = harness((url, {signal}) => new Promise((resolve, reject) => {
    signal.addEventListener("abort", () => reject(new Error("timeout")));
  }));
  [...h.scheduled.values()].find(t => t.delay === 10_000).f(); await settle();
  assert.match(h.node("status").textContent, /unavailable/);
  h.app.dispose();
  const large = harness(async () => new Response(" ".repeat(128 * 1024 + 1)));
  await settle();
  assert.equal(large.node("values").hidden, true);
  assert.match(large.node("status").textContent, /unavailable/);
  large.app.dispose();
});

test("HTML retains a labeled historical snapshot and useful no-script links", async () => {
  const html = await readFile(new URL("../world-economy/index.html", import.meta.url), "utf8");
  assert.match(html, /role="status" aria-live="polite"/);
  assert.match(html, /Historical discovery snapshot · 21 August 2026/);
  assert.match(html, /src="\/world-economy\/coverage.js"/);
  assert.match(html, /<noscript>/);
  assert.match(html, /https:\/\/api.seiche.info\/api\/v2\/corpus\/mcp/);
  assert.ok(!html.includes("76,660,996"));
});
