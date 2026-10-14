import {test} from "node:test";
import assert from "node:assert/strict";
import {amount, readBounded, reviewModel} from "../banking/model.mjs";

const record = () => ({schema: "liquilens.bank-specialisation.v1", status: "stale", name: "Test Bank", score_authority: false, can_authorize_credit: false, period_end: "2021-03-31", as_of: "2026-09-05", metrics: {gnpa_pct: {label: "Gross NPA", value: 0, unit: "percent", status: "observed"}}, sources: ["https://example.org/report.pdf", "javascript:alert(1)", "https://user:pass@example.org/private"], regulatory_comparison: {status: "scope_unverified"}});
const provisional = () => ({status: "provisional", period_end: "2026-09-30", publication_date: "2026-10-03", retrieved_at: "2026-10-14T08:38:45Z", full_financial_results: false, asset_quality_period_refreshed: false, score_authority: false, training_eligible: false,
  metrics: {deposits: {value: 170460, unit: "INR_crore", status: "observed"}, casa_pct: {value: 0, unit: "percent", status: "observed"}, gnpa_pct: {value: 99, unit: "percent", status: "observed"}}, sources: ["https://example.org/provisional.pdf", "javascript:alert(1)"]});

test("provisional business figures retain a separate period without replacing NPA evidence", () => {
  const data = {...record(), period_end: "2026-06-30", as_of: "2026-10-14", provisional_update: provisional()};
  const model = reviewModel(data);
  assert.match(model.clock, /2026-06-30/);
  assert.equal(model.metrics[0].value, "0%");
  assert.match(model.provisional.clock, /2026-09-30.*2026-10-03.*2026-10-14/);
  assert.match(model.provisional.note, /NPA and capital figures above remain dated 2026-06-30/);
  assert.deepEqual(model.provisional.metrics.map(m => m.value), ["1,70,460 INR crore", "Not disclosed", "Not disclosed", "0%"]);
  assert.deepEqual(model.provisional.sources, ["https://example.org/provisional.pdf"]);
  assert.match(reviewModel({...data, provisional_update: {...provisional(), status: "stale"}}).provisional.title, /^Stale provisional/);
  assert.equal(reviewModel(record()).provisional, null);
  assert.equal(reviewModel({...data, provisional_update: {status: "unavailable"}}).provisional, null);
});

test("unverified provisional boundaries and superseded periods fail closed", () => {
  for (const patch of [{status: "observed"}, {full_financial_results: true}, {asset_quality_period_refreshed: true}, {score_authority: true}, {training_eligible: true}, {period_end: "2021-03-31"}, {publication_date: "today"}, {retrieved_at: null}]) {
    assert.throws(() => reviewModel({...record(), provisional_update: {...provisional(), ...patch}}), /provisional disclosure/);
  }
});
test("old evidence and zero measurements retain their meanings", () => {
  const model = reviewModel(record());
  assert.equal(model.status, "Stale evidence");
  assert.match(model.clock, /2021-03-31/);
  assert.equal(model.metrics[0].value, "0%");
  assert.equal(model.metrics[1].value, "Not disclosed");
  assert.equal(model.movement.status, "unavailable");
  assert.match(model.regulatory, /scope unverified/);
  assert.deepEqual(model.sources, ["https://example.org/report.pdf"]);
});
test("unverified authority and malformed responses fail closed", () => {
  assert.throws(() => reviewModel({...record(), can_authorize_credit: true}));
  assert.throws(() => reviewModel({...record(), schema: "different"}));
  assert.equal(amount(NaN, "percent"), "Not disclosed");
  assert.equal(amount(null, "percent"), "Not disclosed");
  assert.equal(amount(-2, "INR_thousand"), "-2 INR thousand");
});
test("transport errors and oversized bodies never become displayed evidence", async () => {
  await assert.rejects(readBounded(new Response("{}", {status: 429})), /rate limit/);
  await assert.rejects(readBounded(new Response("x".repeat(25)), 20), /display limit/);
  assert.deepEqual(await readBounded(new Response('{"status":"unavailable"}')), {status: "unavailable"});
});
test("funding disclosures keep their units, basis and missing denominators", () => {
  const data = record();
  data.metrics.gross_loan_portfolio = {label: "Gross loan portfolio", value: 140327, unit: "INR_crore", status: "observed", basis: "Disclosed portfolio; not advances"};
  data.metrics.lcr_pct = {label: "Liquidity coverage", value: 119, unit: "percent", status: "observed", basis: "Quarterly average"};
  data.metrics.casa_pct = {label: "CASA", value: 0, unit: "percent", status: "observed"};
  data.metrics.advances = {value: null, status: "not_disclosed"};
  const metrics = reviewModel(data).metrics;
  assert.ok(metrics.some(m => m.label === "Gross loan portfolio" && m.value === "1,40,327 INR crore" && /not advances/.test(m.basis)));
  assert.ok(metrics.some(m => m.label === "Liquidity coverage" && m.basis === "Quarterly average"));
  assert.ok(metrics.some(m => m.label === "CASA" && m.value === "0%"));
  assert.ok(!metrics.some(m => m.label === "advances"));
});
test("history preserves knowledge dates, missing ratios and safe filing links", () => {
  const data = record();
  data.history = [{period_end: "2020-03-31", available_at: "2026-09-05", sources: ["javascript:alert(1)", "https://example.org/filing.pdf"], metrics: {gnpa_pct: {value: 0, unit: "percent", status: "observed"}}}];
  assert.deepEqual(reviewModel(data).history, [{period: "2020-03-31", available: "2026-09-05", source: "https://example.org/filing.pdf", values: ["0%", "Not disclosed", "Not disclosed"]}]);
});
