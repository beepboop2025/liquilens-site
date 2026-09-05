export const API = "https://api.liquilens.in/api/experimental/v1/banking";
const STATUSES = new Set(["observed", "stale", "historical", "unavailable"]);
const LABELS = {observed: "Accepted filing evidence", stale: "Stale evidence", historical: "Historical evidence", unavailable: "Evidence unavailable"};
const CORE_METRICS = ["gnpa_pct", "nnpa_pct", "crar_pct"];
const METRICS = [...CORE_METRICS, "cet1_pct", "tier1_pct", "pcr_reported_pct", "pcr_including_technical_writeoffs_pct", "pcr_excluding_technical_writeoffs_pct", "casa_pct", "lcr_pct", "top20_depositors_pct", "top20_npa_pct", "deposits", "advances", "gross_loan_portfolio"];
const sourceLinks = values => (Array.isArray(values) ? values : []).filter(url => {try {const u = new URL(url); return u.protocol === "https:" && !u.username && !u.password;} catch {return false;}});

export function amount(value, unit) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "Not disclosed";
  const number = new Intl.NumberFormat("en-IN", {maximumFractionDigits: 6}).format(value);
  return unit === "percent" ? `${number}%` : `${number} ${String(unit || "unit unavailable").replaceAll("_", " ")}`;
}

export function reviewModel(data) {
  if (data?.schema !== "liquilens.bank-specialisation.v1" || !STATUSES.has(data.status) || typeof data.name !== "string") throw new Error("The API returned an unrecognised evidence contract.");
  if (data.score_authority !== false || data.can_authorize_credit !== false) throw new Error("The response does not confirm the public research boundary.");
  return {
    name: data.name,
    status: LABELS[data.status],
    clock: `Reporting period: ${data.period_end || "unavailable"}. Evidence cutoff: ${data.as_of || "unavailable"}. Captured: ${data.retrieved_at || data.available_at || "not recorded"}.`,
    metrics: METRICS.filter(key => CORE_METRICS.includes(key) || data.metrics?.[key]?.value != null).map(key => {
      const metric = data.metrics?.[key];
      return {label: metric?.label || key.replaceAll("_", " "), value: metric?.status === "observed" ? amount(metric.value, metric.unit) : "Not disclosed", basis: metric?.basis || ""};
    }),
    movement: data.npa_movement || {status: "unavailable", reason: "No complete movement table in this record."},
    regulatory: `Regulatory comparison: ${String(data.regulatory_comparison?.status || "unavailable").replaceAll("_", " ")}. ${data.regulatory_comparison?.note || "This review does not establish an RBI supervisory decision."}`,
    limits: [...(data.interpretation_limits || []), ...(data.comparability_notes || []), ...(data.next_disclosures || []).map(item => `Next disclosure to check: ${item}`)],
    sources: sourceLinks(data.sources),
    history: (Array.isArray(data.history) ? data.history : []).slice(-8).map(row => ({
      period: row.period_end || "Not recorded", available: row.available_at || "Not recorded", source: sourceLinks(row.sources)[0],
      values: CORE_METRICS.map(key => row.metrics?.[key]?.status === "observed" ? amount(row.metrics[key].value, row.metrics[key].unit) : "Not disclosed"),
    })),
  };
}

export async function readBounded(response, limit = 1024 * 1024) {
  if (!response.ok) throw new Error(response.status === 429 ? "The free rate limit was reached. Wait a minute and try again." : `Evidence is unavailable (HTTP ${response.status}).`);
  const reader = response.body?.getReader();
  if (!reader) throw new Error("This browser cannot safely read the response.");
  const chunks = []; let size = 0;
  try {
    while (true) {
      const part = await reader.read(); if (part.done) break;
      size += part.value.byteLength;
      if (size > limit) {await reader.cancel(); throw new Error("The evidence response exceeds the display limit.");}
      chunks.push(part.value);
    }
  } finally {reader.releaseLock();}
  const bytes = new Uint8Array(size); let offset = 0;
  for (const chunk of chunks) {bytes.set(chunk, offset); offset += chunk.byteLength;}
  return JSON.parse(new TextDecoder("utf-8", {fatal: true}).decode(bytes));
}
