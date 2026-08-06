import catalog from "../.well-known/ai-catalog.json" with { type: "json" };

export const CATALOG_PATH = "/.well-known/ai-catalog.json";

const CATALOG_BODY = JSON.stringify(catalog);
const CATALOG_HEADERS = {
  "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
  "Access-Control-Allow-Origin": "*",
  "Cache-Control": "public, max-age=300, s-maxage=3600, stale-while-revalidate=86400",
  "Content-Type": "application/ai-catalog+json; charset=utf-8",
  "X-Content-Type-Options": "nosniff",
};

export function handleCatalogRequest(request) {
  const url = new URL(request.url);
  if (url.pathname !== CATALOG_PATH) {
    return new Response("Not found", { status: 404 });
  }

  if (request.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: {
        ...CATALOG_HEADERS,
        "Access-Control-Max-Age": "86400",
      },
    });
  }

  if (request.method !== "GET" && request.method !== "HEAD") {
    return new Response("Method not allowed", {
      status: 405,
      headers: { ...CATALOG_HEADERS, Allow: "GET, HEAD, OPTIONS" },
    });
  }

  return new Response(request.method === "HEAD" ? null : CATALOG_BODY, {
    status: 200,
    headers: CATALOG_HEADERS,
  });
}

export default {
  fetch(request) {
    return handleCatalogRequest(request);
  },
};
