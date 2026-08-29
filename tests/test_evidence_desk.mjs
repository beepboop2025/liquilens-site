import assert from "node:assert/strict";
import test from "node:test";

import {
  buildToolRequest,
  extractPacket,
  packetToView,
  parseMcpEnvelope,
} from "../evidence-desk/app.mjs";


const PACKET = {
  schema: "liquidity-lab.financial-evidence-packet.v1",
  status: "complete",
  status_semantics: "transport_only",
  evidence_status: "not_evaluated",
  carrier_verification: "not_performed",
  topics: ["money-market", "china-economy"],
  sources: [
    {
      topic: "money-market",
      product: "Seiche",
      ok: true,
      source_url: "https://api.seiche.info/api/v2/money-markets",
      retrieved_at: "2026-08-26T01:02:03Z",
      content_sha256: `sha256:${"a".repeat(64)}`,
      evidence_class: "observed_or_unavailable",
      source_reported: {
        adapter: "seiche_money_markets_v1",
        state: [{ name: "response_status", value: "PARTIAL", path: "/status" }],
        clocks: [{ name: "generated_at", value: "2026-08-25T23:00:00Z", path: "/generated_at" }],
      },
      document: { status: "PARTIAL", as_of: "2026-08-25" },
    },
    {
      topic: "china-economy",
      product: "Palimpsest",
      ok: true,
      source_url: "https://palimpsest.info/readings/china-index-latest.json",
      retrieved_at: "2026-08-26T01:02:04Z",
      content_sha256: `sha256:${"b".repeat(64)}`,
      evidence_class: "observed_structural_or_unavailable",
      document: { readiness: { status: "warming_up" } },
    },
  ],
};


function envelope(packet = PACKET) {
  return {
    jsonrpc: "2.0",
    id: 1,
    result: {
      content: [{ type: "text", text: JSON.stringify(packet) }],
      structuredContent: { status: packet.status },
      isError: false,
    },
  };
}


test("JSON and SSE envelopes preserve the full packet", () => {
  const json = parseMcpEnvelope(JSON.stringify(envelope()), "application/json");
  assert.deepEqual(extractPacket(json), PACKET);

  const sseBody = `event: message\ndata: ${JSON.stringify(envelope())}\n\n`;
  const sse = parseMcpEnvelope(sseBody, "text/event-stream; charset=utf-8");
  assert.deepEqual(extractPacket(sse), PACKET);
});


test("a complete transport never becomes complete evidence", () => {
  const view = packetToView(PACKET);
  assert.equal(view.transport, "complete");
  assert.equal(view.evidence, "not_evaluated");
  assert.equal(view.carrier, "not_performed");
  assert.equal(view.sources[0].reportedState, "response_status: PARTIAL");
  assert.equal(view.sources[0].reportedClocks, "generated_at: 2026-08-25T23:00:00Z");
  assert.equal(view.sources[1].reportedState, "not reported");
  assert.equal(view.sources[1].reportedClocks, "not reported");
  assert.notEqual(view.evidence, view.transport);
});


test("missing adapter output never falls back to heuristic document fields", () => {
  const candidate = structuredClone(PACKET);
  delete candidate.sources[0].source_reported;
  candidate.sources[0].document = {
    status: "complete",
    readiness: { status: "healthy" },
    generated_at: "2099-01-01T00:00:00Z",
  };
  const source = packetToView(candidate).sources[0];
  assert.equal(source.reportedState, "not reported");
  assert.equal(source.reportedClocks, "not reported");
});


test("legacy packets fail closed for evidence and carrier state", () => {
  const legacy = structuredClone(PACKET);
  delete legacy.status_semantics;
  delete legacy.evidence_status;
  delete legacy.carrier_verification;
  const view = packetToView(legacy);
  assert.equal(view.transport, "complete");
  assert.equal(view.evidence, "not_evaluated");
  assert.equal(view.carrier, "not_performed");
});


test("the tool request deduplicates topics and rejects an empty selection", () => {
  const request = buildToolRequest(["bank-risk", "bank-risk", "not-a-topic"], 7);
  assert.equal(request.id, 7);
  assert.deepEqual(request.params.arguments.topics, ["bank-risk"]);
  assert.throws(() => buildToolRequest([]), /Select at least one/);
});


test("MCP errors and malformed packets are rejected", () => {
  assert.throws(
    () => parseMcpEnvelope(JSON.stringify({ jsonrpc: "2.0", error: { message: "nope" } })),
    /nope/,
  );
  assert.throws(
    () => extractPacket({ result: { structuredContent: { status: "complete" } } }),
    /financial-evidence packet/,
  );
});


test("tool-level and encoded-output failures cannot become downloadable evidence", () => {
  const truncated = structuredClone(PACKET);
  truncated.output_status = "unavailable";
  truncated.output_error = "The encoded MCP output exceeded the public response limit.";
  truncated.sources[0].document_disclosed = false;
  delete truncated.sources[0].document;
  const failed = envelope(truncated);
  failed.result.isError = true;
  failed.result.structuredContent = {
    output_status: truncated.output_status,
    output_error: truncated.output_error,
  };

  assert.throws(() => extractPacket(failed), /encoded MCP output exceeded/);
  assert.throws(() => packetToView(truncated), /encoded MCP output exceeded/);
});


test("the browser renderer never uses innerHTML for upstream evidence", async () => {
  const source = await (await import("node:fs/promises")).readFile(
    new URL("../evidence-desk/app.mjs", import.meta.url),
    "utf8",
  );
  assert.doesNotMatch(source, /\.innerHTML\s*=/);
  assert.match(source, /textContent =/);
  assert.match(source, /parsed\.protocol !== "https:"/);
});
