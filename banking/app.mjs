import {API, amount, readBounded, reviewModel} from "./model.mjs";
import {readInstitutionContext, syncInstitutionContext} from "../research-ui/context.js";
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
  byId("history-summary").textContent = `Disclosed history (${model.history.length} periods)`;
  byId("history-table").replaceChildren(...model.history.map(row => {
    const tr = node("tr", ""); const date = node("th", ""); date.scope = "row";
    if (row.source) {const link = node("a", row.period); link.href = row.source; link.target = "_blank"; link.rel = "noopener noreferrer"; date.append(link);}
    else date.append(node("span", row.period));
    date.append(node("small", `Known from ${row.available}`));
    tr.append(date, ...row.values.map(value => node("td", value))); return tr;
  }));
  byId("history").hidden = !model.history.length;
  byId("regulatory-status").textContent = model.regulatory;
  byId("limits").replaceChildren(...model.limits.map(item => node("li", item)));
  byId("sources").replaceChildren(...model.sources.map((url, i) => {
    const li = node("li", ""); const link = node("a", `Source ${i + 1}: ${new URL(url).hostname}`);
    link.href = url; link.target = "_blank"; link.rel = "noopener noreferrer"; li.append(link); return li;
  }));
  if (!model.sources.length) byId("sources").append(node("li", "No source link was supplied by this record."));
  result.hidden = false;
}
function rememberBank() {
  const url = new URL(location.href);
  url.searchParams.set("institution", byId("bank").value);
  history.replaceState(null, "", url);
  syncInstitutionContext();
}
async function loadReview(trackRun = false) {
  if (busy) return;
  rememberBank();
  setBusy(true); result.hidden = true; status.textContent = "Reading the latest accepted filing record…";
  const url = `${API}/institutions/${encodeURIComponent(byId("bank").value)}?include_history=true`;
  try {render(await request(url), url); status.textContent = "Review loaded. Check the reporting date and evidence state below."; if (trackRun) track("live_tool_run");}
  catch (error) {status.textContent = error.name === "AbortError" ? "The evidence request timed out. Try again shortly." : error.message === "Failed to fetch" ? "The evidence service could not be reached. Try again shortly." : error.message;}
  finally {setBusy(false);}
}
byId("bank-form").addEventListener("submit", event => {event.preventDefault(); void loadReview(true);});
byId("bank").addEventListener("change", () => {rememberBank(); result.hidden = true; status.textContent = "Choose Read evidence to load this bank.";});
async function loadCoverage(openSelection = false) {
  if (busy) return; setBusy(true); status.textContent = "Reading the coverage list…";
  let openReview = false;
  try {
    const data = await request(`${API}/coverage`);
    const states = new Set(["observed", "stale", "historical", "unavailable"]);
    if (data.schema !== "liquilens.bank-specialisation.v1" || !Array.isArray(data.rows) || !data.rows.length || data.rows.length > 1000
        || !data.rows.every(row => typeof row.slug === "string" && row.slug.length <= 96 && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(row.slug)
          && typeof row.name === "string" && row.name.length <= 240 && states.has(row.status))
        || new Set(data.rows.map(row => row.slug)).size !== data.rows.length) throw new Error("The coverage list could not be verified.");
    const selected = readInstitutionContext(location.href) || byId("bank").value;
    const preferred = data.rows.some(row => row.slug === selected) ? selected : (data.rows.find(row => row.status === "observed") || data.rows[0]).slug;
    const current = data.rows.filter(row => row.status === "observed");
    const other = data.rows.filter(row => row.status !== "observed");
    byId("bank").replaceChildren(...[["Current filing evidence", current], ["Historical and other evidence", other]].filter(([, rows]) => rows.length).map(([label, rows]) => {
      const group = node("optgroup", ""); group.label = label;
      group.append(...rows.map(row => {
        const option = node("option", `${row.name} · ${row.period_end || "no reporting date"}${row.status === "observed" ? "" : " · " + row.status}`);
        option.value = row.slug; option.selected = row.slug === preferred; return option;
      })); return group;
    }));
    result.hidden = true;
    status.textContent = `${current.length} current records · ${other.length} historical or other dossiers. Choose a bank to read its filing evidence.`;
    openReview = openSelection && readInstitutionContext(location.href) === preferred;
  } catch (error) {status.textContent = error.name === "AbortError" ? "Coverage request timed out. Try again shortly." : error.message;}
  finally {setBusy(false);}
  if (openReview) await loadReview();
}
byId("coverage-button").addEventListener("click", () => void loadCoverage());
void loadCoverage(true);
byId("copy-mcp").addEventListener("click", async () => {
  try {await navigator.clipboard.writeText(byId("mcp-url").textContent); byId("copy-status").textContent = "Endpoint copied. Add it to your MCP client."; track("mcp_endpoint_copied");}
  catch {byId("copy-status").textContent = "Select and copy the endpoint above.";}
});
