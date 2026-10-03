const CATALOG_URL = "https://api.seiche.info/api/v2/corpus/v1/catalog";
const MAX_RESPONSE_BYTES = 128 * 1024;
const REFRESH_MS = 60_000;
const TIMEOUT_MS = 10_000;

function requireValue(condition, message) {
  if (!condition) throw new Error(message);
}

function clock(value) {
  requireValue(typeof value === "string" && /(?:Z|[+-]\d{2}:\d{2})$/.test(value)
    && Number.isFinite(Date.parse(value)), "Invalid catalog clock");
  return new Date(value).toISOString();
}

export function coverageSummary(catalog) {
  const bis = catalog?.corpora?.bis;
  const materialization = bis?.materialization;
  requireValue(catalog?.service === "liquilens-market-corpus" && catalog.schema_version === "1.0.0"
    && typeof catalog.release_id === "string" && /^corpus-[a-f0-9]+$/.test(catalog.release_id),
  "Invalid canonical catalog");
  requireValue(materialization?.schema === "liquilens-bis-live-materialization-v1"
    && materialization.release_id === catalog.release_id
    && materialization.inventory_sha256 === bis.inventory_sha256
    && /^[a-f0-9]{64}$/.test(bis.inventory_sha256), "Catalog generation mismatch");
  const countFields = [bis.flows, bis.bulk_flat, bis.api_only, bis.registry_only,
    materialization.expected_count, materialization.materialized_count,
    materialization.aggregate_row_count, materialization.error_count];
  requireValue(countFields.every(value => Number.isSafeInteger(value) && value >= 0), "Invalid coverage counts");
  requireValue(bis.flows === bis.bulk_flat + bis.api_only + bis.registry_only
    && bis.bulk_flat > 0 && bis.bulk_flat <= 128 && materialization.error_count === 0
    && bis.bulk_flat === materialization.expected_count
    && bis.bulk_flat === materialization.materialized_count, "Incomplete materialization");
  const flows = materialization.flows;
  requireValue(Array.isArray(flows) && flows.length === bis.bulk_flat
    && Array.isArray(materialization.expected_flow_ids), "Missing materialization census");
  const ids = flows.map(flow => flow.flow_id);
  requireValue(ids.every(id => typeof id === "string" && /^[A-Z][A-Z0-9_]{0,63}$/.test(id))
    && new Set(ids).size === ids.length
    && JSON.stringify([...ids].sort()) === JSON.stringify([...materialization.expected_flow_ids].sort()),
  "Materialization census mismatch");
  requireValue(flows.every(flow => Number.isSafeInteger(flow.row_count) && flow.row_count >= 0
    && Number.isSafeInteger(flow.capture_id) && flow.capture_id > 0
    && /^[a-f0-9]{64}$/.test(flow.normalized_sha256) && /^[a-f0-9]{64}$/.test(flow.manifest_sha256)),
  "Invalid admitted flow");
  requireValue(materialization.aggregate_row_count > 0
    && materialization.aggregate_row_count === flows.reduce((sum, flow) => sum + flow.row_count, 0),
  "Observation census mismatch");
  return {
    flows: bis.bulk_flat,
    records: materialization.aggregate_row_count,
    registered: bis.flows,
    materializedAt: clock(materialization.generated_at),
    catalogKnowledgeAt: clock(catalog.knowledge_time),
    responseAt: clock(catalog.generated_at),
    release: catalog.release_id,
  };
}

async function boundedJson(response) {
  requireValue(response.ok, "Canonical catalog request failed");
  requireValue(response.body?.getReader, "Streaming catalog response unavailable");
  const reader = response.body.getReader();
  const chunks = [];
  let length = 0;
  try {
    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      length += value.byteLength;
      requireValue(length <= MAX_RESPONSE_BYTES, "Canonical catalog is too large");
      chunks.push(value);
    }
  } catch (error) {
    await reader.cancel().catch(() => {});
    throw error;
  } finally {
    reader.releaseLock();
  }
  const bytes = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  return JSON.parse(new TextDecoder("utf-8", {fatal: true}).decode(bytes));
}

export function startCoverage(root, {document: doc = document, fetch: fetcher = fetch,
  timers = globalThis, window: win = window} = {}) {
  const status = root.querySelector("[data-coverage-status]");
  const values = root.querySelector("[data-coverage-values]");
  let sequence = 0;
  let active = null;
  let refreshTimer = null;
  let stopped = false;
  let suspended = false;
  const set = (name, value) => { root.querySelector(`[data-coverage-${name}]`).textContent = value; };
  const unavailable = (text) => { values.hidden = true; status.textContent = text; };
  function cancel() {
    sequence += 1;
    active?.abort();
    active = null;
    timers.clearTimeout(refreshTimer);
  }
  async function refresh() {
    if (stopped || suspended || doc.hidden) return;
    cancel();
    const request = sequence;
    const controller = new AbortController();
    active = controller;
    const timeout = timers.setTimeout(() => controller.abort(), TIMEOUT_MS);
    status.textContent = "Checking the canonical coverage catalog…";
    try {
      const response = await fetcher(CATALOG_URL, {signal: controller.signal, cache: "no-store",
        credentials: "omit", headers: {Accept: "application/json"}});
      const summary = coverageSummary(await boundedJson(response));
      if (request !== sequence || stopped || doc.hidden || controller.signal.aborted) return;
      const number = new Intl.NumberFormat("en");
      set("flows", number.format(summary.flows));
      set("records", number.format(summary.records));
      set("registered", number.format(summary.registered));
      set("materialized", summary.materializedAt);
      set("knowledge", summary.catalogKnowledgeAt);
      set("response", summary.responseAt);
      set("release", summary.release);
      values.hidden = false;
      status.textContent = "Loaded from the canonical API and MCP catalog. Checks every minute while this page is visible.";
    } catch {
      if (request === sequence && !stopped && !doc.hidden) {
        unavailable("Current coverage is unavailable. Use the canonical JSON or MCP links below; historical counts are not a live fallback.");
      }
    } finally {
      timers.clearTimeout(timeout);
      if (request === sequence && !stopped && !doc.hidden) {
        active = null;
        refreshTimer = timers.setTimeout(refresh, REFRESH_MS);
      }
    }
  }
  function visibility() {
    if (doc.hidden) {
      cancel();
      unavailable("Coverage checks are paused while this page is hidden.");
    } else { void refresh(); }
  }
  function dispose() {
    stopped = true;
    cancel();
    doc.removeEventListener("visibilitychange", visibility);
    win.removeEventListener("pagehide", pagehide);
    win.removeEventListener("pageshow", pageshow);
  }
  function pagehide() {
    suspended = true;
    cancel();
    unavailable("Coverage checks are paused while this page is inactive.");
  }
  function pageshow() {
    if (suspended) { suspended = false; void refresh(); }
  }
  doc.addEventListener("visibilitychange", visibility);
  win.addEventListener("pagehide", pagehide);
  win.addEventListener("pageshow", pageshow);
  void refresh();
  return {refresh, dispose};
}

if (typeof document !== "undefined") {
  const root = document.querySelector("[data-live-corpus-coverage]");
  if (root) startCoverage(root);
}
