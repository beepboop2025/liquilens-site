import aiCatalog from "../.well-known/ai-catalog.json" with { type: "json" };
import protocolCatalog from "../protocol/catalog.json" with { type: "json" };

export const AI_CATALOG_PATH = "/.well-known/ai-catalog.json";
export const PROTOCOL_CATALOG_PATH = "/protocol/catalog.json";
// Preserve the original export for callers that consume the ARD catalog.
export const CATALOG_PATH = AI_CATALOG_PATH;

const SHARED_HEADERS = {
  "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
  "Access-Control-Allow-Origin": "*",
  "Cache-Control": "public, max-age=300, s-maxage=3600, stale-while-revalidate=86400",
  "X-Content-Type-Options": "nosniff",
};
const CATALOGS = new Map([
  [AI_CATALOG_PATH, {
    body: JSON.stringify(aiCatalog),
    headers: {
      ...SHARED_HEADERS,
      "Content-Type": "application/ai-catalog+json; charset=utf-8",
      Link: '<https://liquilens.in/protocol/catalog.json>; rel="alternate"; type="application/json"',
    },
  }],
  [PROTOCOL_CATALOG_PATH, {
    body: JSON.stringify(protocolCatalog),
    headers: {
      ...SHARED_HEADERS,
      "Content-Type": "application/json; charset=utf-8",
      Link: [
        '<https://liquilens.in/protocol/liquilens-evidence-carrier-v1.schema.json>; rel="describedby"; type="application/schema+json"',
        '<https://liquilens.in/.well-known/ai-catalog.json>; rel="alternate"; type="application/ai-catalog+json"',
      ].join(", "),
    },
  }],
]);

export function handleCatalogRequest(request) {
  const url = new URL(request.url);
  const catalog = CATALOGS.get(url.pathname);
  if (!catalog) {
    return new Response("Not found", { status: 404 });
  }

  if (request.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: {
        ...catalog.headers,
        "Access-Control-Max-Age": "86400",
      },
    });
  }

  if (request.method !== "GET" && request.method !== "HEAD") {
    return new Response("Method not allowed", {
      status: 405,
      headers: { ...catalog.headers, Allow: "GET, HEAD, OPTIONS" },
    });
  }

  return new Response(request.method === "HEAD" ? null : catalog.body, {
    status: 200,
    headers: catalog.headers,
  });
}

export default {
  fetch(request) {
    return handleCatalogRequest(request);
  },
};
