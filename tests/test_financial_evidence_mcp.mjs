import assert from "node:assert/strict";
import test from "node:test";

import worker, {
  FINANCIAL_EVIDENCE_MCP_PATH,
  createFinancialEvidenceServer,
} from "../edge/catalog-worker.mjs";

const ENDPOINT = `https://liquilens.in${FINANCIAL_EVIDENCE_MCP_PATH}`;

function request(body, headers = {}) {
  return new Request(ENDPOINT, {
    method: "POST",
    headers: {
      Accept: "application/json, text/event-stream",
      "Content-Type": "application/json",
      Host: "liquilens.in",
      ...headers,
    },
    body: JSON.stringify(body),
  });
}

async function responsePayload(response) {
  const body = await response.text();
  if (response.headers.get("content-type")?.startsWith("text/event-stream")) {
    const data = body
      .split("\n")
      .find((line) => line.startsWith("data: "));
    assert.ok(data, "SSE response must include one data event");
    return JSON.parse(data.slice("data: ".length));
  }
  return JSON.parse(body);
}

test("legacy initialize and tool listing expose the read-only contract", async () => {
  const initialized = await worker.fetch(
    request({
      jsonrpc: "2.0",
      id: 1,
      method: "initialize",
      params: {
        protocolVersion: "2025-11-25",
        capabilities: {},
        clientInfo: { name: "edge-test", version: "1.0.0" },
      },
    }),
  );
  assert.equal(initialized.status, 200);
  const initialization = await responsePayload(initialized);
  assert.equal(initialization.result.protocolVersion, "2025-11-25");
  assert.equal(initialization.result.serverInfo.name, "financial-evidence");
  assert.equal(initialization.result.serverInfo.version, "0.1.2");

  const listed = await worker.fetch(
    request({ jsonrpc: "2.0", id: 2, method: "tools/list", params: {} }),
  );
  assert.equal(listed.status, 200);
  const payload = await responsePayload(listed);
  assert.deepEqual(
    payload.result.tools.map((tool) => tool.name),
    [
      "financial_evidence_topics",
      "financial_evidence_route",
      "financial_evidence_fetch",
    ],
  );
  for (const tool of payload.result.tools) {
    assert.equal(tool.annotations.readOnlyHint, true);
    assert.equal(tool.annotations.destructiveHint, false);
    assert.equal(tool.annotations.idempotentHint, true);
  }
});

test("modern discovery is stateless and advertises the same server", async () => {
  const response = await worker.fetch(
    request(
      {
        jsonrpc: "2.0",
        id: 3,
        method: "server/discover",
        params: {
          _meta: {
            "io.modelcontextprotocol/clientInfo": {
              name: "edge-test",
              version: "1.0.0",
            },
            "io.modelcontextprotocol/protocolVersion": "2026-07-28",
            "io.modelcontextprotocol/clientCapabilities": {},
          },
        },
      },
      {
        "MCP-Protocol-Version": "2026-07-28",
        "Mcp-Method": "server/discover",
      },
    ),
  );
  assert.equal(response.status, 200);
  const payload = await responsePayload(response);
  assert.equal(
    payload.result._meta["io.modelcontextprotocol/serverInfo"].name,
    "financial-evidence",
  );
  assert.equal(payload.result.resultType, "complete");
});

test("route calls preserve separate products and never fetch", async () => {
  const response = await worker.fetch(
    request({
      jsonrpc: "2.0",
      id: 4,
      method: "tools/call",
      params: {
        name: "financial_evidence_route",
        arguments: { topics: ["china-economy", "market-liquidity"] },
      },
    }),
  );
  assert.equal(response.status, 200);
  const payload = await responsePayload(response);
  assert.equal(payload.result.isError, false);
  assert.deepEqual(Object.keys(payload.result.structuredContent.topics), [
    "china-economy",
    "market-liquidity",
  ]);
  assert.deepEqual(
    payload.result.structuredContent.topics["china-economy"].map(
      (source) => source.product,
    ),
    ["Palimpsest", "Seiche"],
  );
});

test("fetch calls are allowlisted, bounded, hashed, and kept product-separate", async () => {
  const originalFetch = globalThis.fetch;
  const requested = [];
  globalThis.fetch = async (url, options) => {
    requested.push({ url, options });
    return new Response(JSON.stringify({ fixture: url }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };
  try {
    const response = await worker.fetch(
      request({
        jsonrpc: "2.0",
        id: 5,
        method: "tools/call",
        params: {
          name: "financial_evidence_fetch",
          arguments: { topics: ["china-economy"] },
        },
      }),
    );
    assert.equal(response.status, 200);
    const payload = await responsePayload(response);
    const packet = payload.result.structuredContent;
    assert.equal(packet.status, "complete");
    assert.deepEqual(
      packet.sources.map((source) => source.product),
      ["Palimpsest", "Seiche"],
    );
    assert.equal(packet.sources.every((source) => source.ok), true);
    assert.equal(
      packet.sources.every((source) =>
        /^sha256:[0-9a-f]{64}$/.test(source.content_sha256),
      ),
      true,
    );
    assert.equal(requested.length, 2);
    assert.equal(
      requested.every(({ url }) => new URL(url).protocol === "https:"),
      true,
    );
    assert.equal(
      requested.every(({ options }) => options.redirect === "manual"),
      true,
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("a body over the byte cap is explicit unavailable evidence", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ larger: "than one byte" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  try {
    const response = await worker.fetch(
      request({
        jsonrpc: "2.0",
        id: 6,
        method: "tools/call",
        params: {
          name: "financial_evidence_fetch",
          arguments: { topics: ["market-liquidity"], max_bytes: 1 },
        },
      }),
    );
    const payload = await responsePayload(response);
    assert.equal(payload.result.isError, true);
    assert.equal(payload.result.structuredContent.status, "unavailable");
    assert.match(
      payload.result.structuredContent.sources[0].error,
      /response exceeds 1 bytes/,
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("the server factory is lazy about network access", () => {
  let calls = 0;
  const fetchImpl = async () => {
    calls += 1;
    throw new Error("not expected");
  };
  const server = createFinancialEvidenceServer({ fetchImpl });
  assert.ok(server);
  assert.equal(calls, 0);
});

test("CORS preflight is public but unknown paths stay closed", async () => {
  const options = await worker.fetch(
    new Request(ENDPOINT, {
      method: "OPTIONS",
      headers: {
        Host: "liquilens.in",
        Origin: "https://example.net",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type,mcp-protocol-version",
      },
    }),
  );
  assert.equal(options.status, 200);
  assert.equal(options.headers.get("access-control-allow-origin"), "*");

  const unknown = await worker.fetch(
    new Request("https://liquilens.in/mcp/not-financial-evidence"),
  );
  assert.equal(unknown.status, 404);
});
