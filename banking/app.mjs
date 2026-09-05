import {API, amount, readBounded, reviewModel} from "./model.mjs";
const byId = id => document.getElementById(id);
const status = byId("request-status");
const result = byId("review-result");
let busy = false;

function node(tag, text, className) {
  const el = document.createElement(tag); el.textContent = text;
  if (className) el.className = className;
  return el;
}
function track(event) {
  fetch("https://api.liquilens.in/api/events", {method: "POST", credentials: "omit", headers: {"Content-Type": "application/json"}, body: JSON.stringify({surface: "developers", event}), keepalive: true}).catch(() => {});
}
async function request(url) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);
  try {return await readBounded(await fetch(url, {credentials: "omit", signal: controller.signal}));}
  finally {clearTimeout(timer);}
}
function setBusy(value) {
  busy = value;
  for (const id of ["review-button", "coverage-button", "bank"]) byId(id).disabled = value;
}
function render(data, url) {
  const model = reviewModel(data);
  byId("bank-name").textContent = model.name;
  byId("evidence-state").textContent = model.status;
  byId("evidence-clock").textContent = model.clock;
  byId("raw-link").href = url;
  byId("metric-cards").replaceChildren(...model.metrics.map(metric => {
    const el = node("div", "", "metric");
    el.append(node("small", metric.label), node("strong", metric.value));
    if (metric.basis) el.append(node("small", metric.basis));
    return el;
  }));
  const movement = model.movement;
  byId("movement-status").textContent = movement.status === "unavailable" ? movement.reason : `Arithmetic: ${String(movement.status).replaceAll("_", " ")}. Period ${movement.period_start} to ${movement.period_end}. ${movement.interpretation || ""}`;
  const rows = movement.status === "unavailable" ? [] : [
    ["Opening gross NPAs", movement.opening_gnpa], ["Additions", movement.additions],
    ...Object.entries(movement.reductions || {}).map(([key, value]) => [`Less: ${key.replaceAll("_", " ")}`, value]),
    ["Closing gross NPAs", movement.closing_gnpa], ["Residual", movement.residual], ["Rounding tolerance", movement.rounding_tolerance],
  ];
  byId("movement").replaceChildren(...rows.flatMap(([label, value]) => [node("dt", label), node("dd", amount(value, movement.amount_unit))]));
  byId("regulatory-status").textContent = model.regulatory;
  byId("limits").replaceChildren(...model.limits.map(item => node("li", item)));
  byId("sources").replaceChildren(...model.sources.map((url, i) => {
    const li = node("li", ""); const link = node("a", `Source ${i + 1}: ${new URL(url).hostname}`);
    link.href = url; link.target = "_blank"; link.rel = "noopener noreferrer"; li.append(link); return li;
  }));
  if (!model.sources.length) byId("sources").append(node("li", "No source link was supplied by this record."));
  result.hidden = false;
}
byId("bank-form").addEventListener("submit", async event => {
  event.preventDefault(); if (busy) return;
  setBusy(true); result.hidden = true; status.textContent = "Reading the latest accepted filing record…";
  const url = `${API}/institutions/${encodeURIComponent(byId("bank").value)}?include_history=true`;
  try {render(await request(url), url); status.textContent = "Review loaded. Check the reporting date and evidence state below."; track("live_tool_run");}
  catch (error) {status.textContent = error.name === "AbortError" ? "The evidence request timed out. Try again shortly." : error.message;}
  finally {setBusy(false);}
});
byId("bank").addEventListener("change", () => {result.hidden = true; status.textContent = "Choose Read evidence to load this bank.";});
byId("coverage-button").addEventListener("click", async () => {
  if (busy) return; setBusy(true); status.textContent = "Reading the coverage list…";
  try {
    const data = await request(`${API}/coverage`);
    if (data.schema !== "liquilens.bank-specialisation.v1" || !Array.isArray(data.rows) || data.rows.length > 1000) throw new Error("The coverage list could not be verified.");
    const selected = byId("bank").value;
    byId("bank").replaceChildren(...data.rows.map(row => {
      const option = node("option", `${row.name} · ${row.status} · ${row.period_end || "no date"}`);
      option.value = row.slug; option.selected = row.slug === selected; return option;
    }));
    result.hidden = true; status.textContent = `${data.rows.length} covered dossiers, including stale and historical evidence. Choose a bank to read its record.`;
  } catch (error) {status.textContent = error.name === "AbortError" ? "Coverage request timed out. Try again shortly." : error.message;}
  finally {setBusy(false);}
});
byId("copy-mcp").addEventListener("click", async () => {
  try {await navigator.clipboard.writeText(byId("mcp-url").textContent); byId("copy-status").textContent = "Endpoint copied. Add it to your MCP client."; track("mcp_endpoint_copied");}
  catch {byId("copy-status").textContent = "Select and copy the endpoint above.";}
});
