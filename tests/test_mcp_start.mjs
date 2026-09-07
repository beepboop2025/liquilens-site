import test from "node:test";
import assert from "node:assert/strict";
import {TASKS, SERVERS, configuration, project, safeUrl, boundedJson, runTask} from "../start/core.mjs";

const fixtures = {
  bank: {schema: "liquilens.bank-specialisation.v1", slug: "cosmos-ucb", name: "Cosmos", status: "stale", period_end: "2026-03-31", metrics: {gnpa_pct: {value: 0}, nnpa_pct: {value: null}}, npa_movement: {amount_unit: "INR_crore", reductions: {cash_recoveries: 1, write_offs: 4}}, sources: ["https://example.org/filing", "javascript:alert(1)"], interpretation_limits: ["No credit authority"]},
  funding: {schema: "seiche.public.v2", generated_at: "2026-09-07T00:00:00Z", editorial: {thesis: "Context", confidence: "guarded", evidence: [{claim: "Observation", source: "FRED", asof: "2026-09-02"}], countercase: [{claim: "Counterexample", source: "Source", asof: "2026-09-03"}]}, data_quality: {status_counts: {fresh: 1, stale: 2}, headline_ages: [{series: "iorb", asof: "2026-09-08"}]}, proof: {historical_evidence: {reason: "Not validated"}}},
  exit: {asset: "BTC", requested_size_usd: 100000, published_rung_used_usd: 100000, sell_cost_bp_by_venue: {z: 0, a: null}, method: "Estimated", disclaimer: "Not executable"},
};

function fixtureFetch(task, mutate = x => x) {
  const calls = [];
  const fetcher = async (url, options) => {
    const body = JSON.parse(options.body); calls.push({url, options, body});
    if (body.method === "notifications/initialized") return new Response(null, {status: 202});
    const result = body.method === "initialize" ? {protocolVersion: "2025-11-25"} : {structuredContent: fixtures[task]};
    return Response.json(mutate({jsonrpc: "2.0", id: body.id, result}, body));
  };
  return {fetcher, calls};
}

test("all supported clients produce fixed-endpoint configurations for nine servers", () => {
  assert.equal(SERVERS.length, 9);
  const ids = SERVERS.map(s => s.id);
  assert.equal(Object.keys(JSON.parse(configuration("cursor", ids)).mcpServers).length, 9);
  assert.equal(Object.keys(JSON.parse(configuration("vscode", ids)).servers).length, 9);
  assert.equal(configuration("codex", ids).split("\n").length, 9);
  assert.match(configuration("claude", ["undertow"]), /^claude mcp add --transport http undertow https:\/\/api.seiche.info\/undertow\/mcp$/);
  assert.throws(() => configuration("cursor", ["evil"]));
  assert.throws(() => configuration("unknown", ids));
});

for (const task of Object.keys(TASKS)) test(`${task}: one explicit research call with a bounded, fixed endpoint`, async () => {
  const {fetcher, calls} = fixtureFetch(task);
  const result = await runTask(task, {fetcher, verification: true});
  assert.deepEqual(result.evidence, fixtures[task]);
  assert.deepEqual(calls.map(x => x.body.method), ["initialize", "notifications/initialized", "tools/call"]);
  assert.equal(calls[2].body.params.name, TASKS[task].tool);
  assert.match(calls[0].body.params.clientInfo.name, /operator-verification$/);
  for (const call of calls) {
    assert.equal(call.url, TASKS[task].endpoint);
    assert.equal(call.options.redirect, "error");
    assert.equal(call.options.credentials, "omit");
  }
});

test("projections retain zeros, missingness, source dates, stale state and counterevidence", () => {
  const bank = project("bank", fixtures.bank);
  assert.equal(bank.state, "stale");
  assert.equal(bank.facts[2][1], "0%");
  assert.equal(bank.facts[3][1], "Not reported");
  assert.deepEqual(bank.sources, ["https://example.org/filing"]);
  assert.ok(bank.details.some(([k, v]) => k === "Write-offs" && v === "4"));
  const funding = project("funding", fixtures.funding);
  assert.ok(funding.details.some(([k, v]) => k === "Counterevidence" && v.includes("2026-09-03")));
  assert.ok(funding.limits.some(v => v.includes("2 stale")));
  assert.ok(funding.limits.some(v => v.includes("future source date (2026-09-08)")));
  assert.deepEqual(project("exit", fixtures.exit).details, [["a", "Not reported"], ["z", "0 bp"]]);
});

test("unavailable evidence never becomes a zero or a research conclusion", () => {
  for (const task of Object.keys(TASKS)) {
    const view = project(task, {status: "observed", available: false, reason: "No data"});
    assert.equal(view.state, "unavailable"); assert.deepEqual(view.facts, []);
  }
  assert.throws(() => project("bank", {...fixtures.bank, slug: "different"}));
  assert.throws(() => project("exit", {...fixtures.exit, sell_cost_bp_by_venue: []}));
});

test("mismatched response IDs, protocol negotiation, tool errors and sizes fail without retries", async () => {
  for (const mutate of [x => ({...x, id: 999}), x => ({...x, error: {code: -1}}), x => ({...x, result: {...x.result, protocolVersion: "bad"}})]) {
    const t = fixtureFetch("bank", mutate);
    await assert.rejects(runTask("bank", t)); assert.equal(t.calls.length, 1);
  }
  const toolError = fixtureFetch("exit", (x, b) => b.method === "tools/call" ? {...x, result: {isError: true}} : x);
  await assert.rejects(runTask("exit", toolError)); assert.equal(toolError.calls.length, 3);
  const wrongSize = fixtureFetch("exit");
  await assert.rejects(runTask("exit", {...wrongSize, size: 1000}), /different requested/);
  const invalid = fixtureFetch("exit");
  await assert.rejects(runTask("exit", {...invalid, size: -1})); assert.equal(invalid.calls.length, 0);
});

test("legacy text responses work and protocol HTTP failures surface once", async () => {
  const t = fixtureFetch("bank", (x, b) => b.method === "tools/call" ? {...x, result: {content: [{type: "text", text: JSON.stringify(fixtures.bank)}]}} : x);
  assert.deepEqual((await runTask("bank", t)).evidence, fixtures.bank);
  let count = 0;
  await assert.rejects(runTask("bank", {fetcher: async () => {count++; return new Response(null, {status: 429});}}), /429/);
  assert.equal(count, 1);
});

test("response size and source URL policies reject unsafe values", async () => {
  await assert.rejects(boundedJson(new Response('"12345"'), 4), /display limit/);
  await assert.rejects(boundedJson(new Response("{}", {headers: {"Content-Length": "999"}}), 4));
  await assert.rejects(boundedJson(new Response(new Uint8Array([255]))));
  assert.deepEqual(await boundedJson(Response.json({ok: true})), {ok: true});
  for (const url of ["javascript:alert(1)", "http://example.org", "https://user:pass@example.org"]) assert.equal(safeUrl(url), null);
});
