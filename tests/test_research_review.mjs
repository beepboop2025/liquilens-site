import test from "node:test";
import assert from "node:assert/strict";
import {captureReview, reviewPacket, reviewMarkdown} from "../start/review.mjs";

const retrievedAt = "2026-09-23T12:00:00Z";
const preparedAt = "2026-09-23T13:00:00Z";
const bank = {schema: "liquilens.bank-specialisation.v1", slug: "cosmos-ucb", name: "Example bank", status: "stale", period_end: "2025-03-31", metrics: {gnpa_pct: {value: 0}}, npa_movement: {amount_unit: "INR_crore", reductions: {write_offs: 4}}, sources: ["https://example.org/filing"], interpretation_limits: ["Historical filing only"]};
const captureBank = () => captureReview("bank", {evidence: bank, retrievedAt});

test("a brief retains historical, zero, missing, unit and stale-state evidence", () => {
  const markdown = reviewMarkdown([captureBank()], preparedAt);
  for (const value of ["2025-03-31", "Gross NPA ratio: 0%", "Net NPA ratio: Not reported", "Returned state: stale", "Write-offs: 4", "INR\\_crore", "Historical filing only", "https://example.org/filing", "Not included: Seiche, Undertow"]) assert.ok(markdown.includes(value), value);
  assert.ok(markdown.includes("2026-09-23T12:00:00.000Z"));
  assert.ok(markdown.includes("2026-09-23T13:00:00.000Z"));
});

test("keeping a response detaches it from later response or caller mutations", () => {
  const source = structuredClone(bank);
  const entry = captureReview("bank", {evidence: source, retrievedAt});
  source.metrics.gnpa_pct.value = 99;
  assert.equal(entry.evidence.metrics.gnpa_pct.value, 0);
  assert.throws(() => {entry.evidence.metrics.gnpa_pct.value = 50;}, TypeError);
});

test("unavailable products remain explicit in a combined document", () => {
  const unavailable = captureReview("funding", {evidence: {available: false, reason: "No current observations"}, retrievedAt});
  const markdown = reviewMarkdown([unavailable, captureBank()], preparedAt);
  assert.match(markdown, /Returned state: unavailable/);
  assert.match(markdown, /No current observations/);
  assert.match(markdown, /No conclusion has been substituted/);
  assert.ok(markdown.indexOf("## LiquiLens") < markdown.indexOf("## Seiche"));
  assert.deepEqual(reviewPacket([unavailable], preparedAt).not_included, ["LiquiLens", "Undertow"]);
});

test("exit requests retain the chosen size even when evidence is unavailable", () => {
  const result = {evidence: {available: false, reason: "No depth"}, retrievedAt};
  const entry = captureReview("exit", result, {size: 10000});
  assert.equal(reviewPacket([entry], preparedAt).snapshots[0].arguments.size_usd, 10000);
  assert.throws(() => captureReview("exit", result, {size: 7}));
  const wrong = {evidence: {asset: "BTC", requested_size_usd: 1000, sell_cost_bp_by_venue: {a: 2}}, retrievedAt};
  assert.throws(() => captureReview("exit", wrong, {size: 10000}), /different position size/);
});

test("a brief cannot silently change the source, request or question identity", () => {
  const entry = captureBank();
  assert.throws(() => reviewPacket([entry, entry], preparedAt), /one snapshot/);
  assert.throws(() => reviewPacket([], preparedAt));
  assert.throws(() => reviewPacket([{...entry, endpoint: "https://example.org/mcp"}], preparedAt));
  assert.throws(() => reviewPacket([{...entry, arguments: {slug: "other-bank"}}], preparedAt));
  assert.throws(() => captureReview("unknown", {evidence: bank, retrievedAt}));
  assert.throws(() => captureReview("bank", {evidence: bank, retrievedAt: "today"}));
  assert.throws(() => reviewPacket([entry], "today"));
});

test("source prose cannot inject HTML, headings or Markdown links into the brief", () => {
  const evidence = {...bank, name: "<img src=x onerror=alert(1)>\n# forged", interpretation_limits: ["[open](javascript:alert(1))"], sources: ["javascript:alert(1)", "https://user:pass@example.org", "https://example.org/source"]};
  const output = reviewMarkdown([captureReview("bank", {evidence, retrievedAt})], preparedAt);
  assert.ok(!output.includes("<img"));
  assert.ok(!output.includes("\n# forged"));
  assert.ok(!output.includes("[open](javascript:"));
  assert.ok(!output.includes("user:pass"));
  assert.ok(output.includes("https://example.org/source"));
});
