import {test} from "node:test";
import assert from "node:assert/strict";
import {amount, readBounded, reviewModel} from "../banking/model.mjs";

const record = () => ({schema: "liquilens.bank-specialisation.v1", status: "stale", name: "Test Bank", score_authority: false, can_authorize_credit: false, period_end: "2021-03-31", as_of: "2026-09-05", metrics: {gnpa_pct: {label: "Gross NPA", value: 0, unit: "percent", status: "observed"}}, sources: ["https://example.org/report.pdf", "javascript:alert(1)", "https://user:pass@example.org/private"], regulatory_comparison: {status: "scope_unverified"}});
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
