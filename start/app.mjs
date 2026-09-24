import {TASKS, SERVERS, configuration, runTask, safeUrl} from "./core.mjs";
import {acquisitionSource, questionLink, telegramLink, TELEGRAM_DESKS} from "./acquisition.mjs";
import {captureReview, reviewPacket, reviewMarkdown} from "./review.mjs";
import {applyAgentNavigation, browserNavigationContext} from "../agents/navigation.mjs";

const $ = id => document.getElementById(id);
const params = new URLSearchParams(location.search);
const navigation = browserNavigationContext(location, navigator, window);
const {verification, privacyOptOut} = navigation;
applyAgentNavigation(document, location.href, navigation);
const source = acquisitionSource(location.search);
let task = Object.hasOwn(TASKS, params.get("task")) ? params.get("task") : "bank";
let selectedIds = [task === "bank" ? "liquilens" : task === "funding" ? "seiche" : "undertow"];
let activeRequest = null, activeResult = null, resultTask = null;
const review = new Map();
const size = Number(params.get("size"));
if ([1000, 10000, 100000, 1000000].includes(size)) $("size").value = String(size);

function announce(message, state = "idle") {$("notice").textContent = message; $("notice").dataset.state = state;}
function track(action, product = task) {
  if (verification || privacyOptOut) return Promise.resolve(false);
  // Closed enums only: never send queries, prompts, identities or source data.
  return fetch("https://api.liquilens.in/api/events", {method: "POST", headers: {"Content-Type": "application/json"}, credentials: "omit", keepalive: true,
    body: JSON.stringify({surface: "mcp_start", event: `${product}_${action}`, source})}).then(response => response.status === 202).catch(() => false);
}
async function copy(value, button, event) {
  try {await navigator.clipboard.writeText(value); const old = button.textContent; button.textContent = "Copied"; setTimeout(() => {button.textContent = old;}, 1500); if (event) track(event);}
  catch {announce("Clipboard access is unavailable. Select and copy the text shown on the page.");}
}
function download(text, name, type = "application/json") {
  const url = URL.createObjectURL(new Blob([text], {type})); const a = document.createElement("a"); a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function definitionList(id, rows) {
  $(id).replaceChildren(...rows.map(([label, value]) => {const row = document.createElement("div"), dt = document.createElement("dt"), dd = document.createElement("dd"); dt.textContent = label; dd.textContent = value; row.append(dt, dd); return row;}));
}
function renderReview() {
  $("review-count").textContent = review.size ? `${review.size} of 3 product snapshots kept in this tab.` : "No snapshots kept yet.";
  $("review-items").replaceChildren(...[...review.values()].map(entry => {
    const item = document.createElement("li"), text = document.createElement("p"), button = document.createElement("button");
    text.textContent = `${entry.product} — retrieved ${entry.retrieved_at}${entry.task === "exit" ? `; requested size $${entry.arguments.size_usd.toLocaleString("en-US")}` : ""}`;
    button.type = "button"; button.textContent = `Remove ${entry.product}`;
    button.addEventListener("click", () => {review.delete(entry.task); renderReview();});
    item.append(text, button); return item;
  }));
  for (const id of ["download-brief", "download-review", "clear-review"]) $(id).disabled = review.size === 0;
}
function renderResult(result) {
  const v = result.view;
  $("result-state").textContent = `Returned state: ${v.state}`;
  $("result-title").textContent = v.title; $("result-note").textContent = v.note;
  definitionList("facts", v.facts); definitionList("details", v.details);
  $("limits").replaceChildren(...v.limits.map(value => {const li = document.createElement("li"); li.textContent = value; return li;}));
  $("sources").replaceChildren(...v.sources.filter(safeUrl).map(value => {const li = document.createElement("li"), a = document.createElement("a"); a.href = safeUrl(value); a.textContent = value; a.target = "_blank"; a.rel = "noopener noreferrer"; li.append(a); return li;}));
  $("raw").textContent = JSON.stringify(result.evidence, null, 2);
  $("result").hidden = false; $("useful").disabled = ["unavailable", "not_covered", "restricted", "failed", "error"].includes(v.state);
  $("useful").textContent = "This helped my research";
  $("next").href = TASKS[task].next; $("next").textContent = TASKS[task].nextLabel;
  $("telegram-next").href = telegramLink(task, source);
  $("telegram-next").textContent = TELEGRAM_DESKS[task].label;
  $("telegram-note").textContent = TELEGRAM_DESKS[task].note;
}
function setup() {
  $("config").textContent = configuration($("client").value, selectedIds);
  const server = SERVERS.find(s => s.id === $("server").value);
  $("prompt").value = server.prompt;
  $("config-help").textContent = ({codex: "Run in your terminal. Your existing configured servers are preserved.", claude: "Run in your terminal. The command adds the server in Claude Code’s default scope.", cursor: "Merge into .cursor/mcp.json in your project. Keep existing server entries.", vscode: "Merge into .vscode/mcp.json in your project. Keep existing server entries.", openclaw: "Merge these mcp.servers entries into ~/.openclaw/openclaw.json. Keep your existing settings and review discovered tools. Requires an OpenClaw version with native MCP support.", hermes: "Merge these mcp_servers entries into ~/.hermes/config.yaml. Keep existing settings, then start a new session or use /reload-mcp."})[$("client").value];
}
function chooseTask(value, updateUrl = true) {
  activeRequest?.abort(); activeRequest = null; activeResult = null; resultTask = null; task = value;
  $("result").hidden = true; $("run").disabled = false;
  document.querySelectorAll("[data-task]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.task === task)));
  $("task-title").textContent = TASKS[task].title; $("task-description").textContent = TASKS[task].description; $("task-product").textContent = TASKS[task].product;
  $("size-field").hidden = task !== "exit";
  $("run-note").textContent = task === "bank" ? "Nothing is fetched until you click. Each run makes one research-tool call. The bank example names Cosmos Co-operative Bank." : "Nothing is fetched until you click. Each run makes one research-tool call; there is no automatic refresh.";
  selectedIds = [task === "bank" ? "liquilens" : task === "funding" ? "seiche" : "undertow"];
  $("server").value = selectedIds[0]; setup(); announce(verification ? "Operator verification mode: interaction beacons are disabled." : "Ready. Get the evidence when you want to run this question.");
  if (updateUrl) {const u = new URL(location.href); u.searchParams.set("task", task); u.searchParams.delete("size"); history.replaceState(null, "", u);}
}
for (const server of SERVERS) {
  const option = document.createElement("option"); option.value = server.id; option.textContent = server.name; $("server").append(option);
  const row = document.createElement("article"); row.className = "server-row";
  const title = document.createElement("h3"), link = document.createElement("a"); link.href = server.docs; link.textContent = server.name; title.append(link);
  const description = document.createElement("p"); description.textContent = server.role;
  const button = document.createElement("button"); button.type = "button"; button.textContent = `Connect ${server.name}`;
  button.addEventListener("click", () => {$("server").value = server.id; selectedIds = [server.id]; setup(); $("connect").scrollIntoView(); $("server").focus();});
  row.append(title, description, button); $("server-list").append(row);
}
document.querySelectorAll("[data-task]").forEach(button => button.addEventListener("click", () => chooseTask(button.dataset.task)));
$("server").addEventListener("change", () => {selectedIds = [$("server").value]; setup();});
$("client").addEventListener("change", setup);
$("size").addEventListener("change", () => {if (task === "exit") chooseTask("exit");});
$("bundle").addEventListener("click", () => {selectedIds = ["liquilens", "seiche", "undertow"]; setup(); $("config-help").textContent += " This setup adds all three public MCPs.";});
$("copy-config").addEventListener("click", function () {copy($("config").textContent, this, "setup_copied");});
$("copy-prompt").addEventListener("click", function () {copy($("prompt").value, this, "prompt_copied");});
$("download-config").addEventListener("click", () => {const client = $("client").value, cli = ["codex", "claude"].includes(client), yaml = client === "hermes"; download($("config").textContent + "\n", `${client}-financial-mcp.${cli ? "txt" : yaml ? "yaml" : "json"}`, cli || yaml ? "text/plain" : "application/json"); track("setup_downloaded");});
$("share").addEventListener("click", function () {copy(questionLink(task, "shared", $("size").value), this, "question_shared");});
$("run").addEventListener("click", async () => {
  if (activeRequest) return;
  const controller = new AbortController(), requestedTask = task; activeRequest = controller; activeResult = null; $("result").hidden = true; $("run").disabled = true;
  const timeout = setTimeout(() => controller.abort(), 30000); track("started", requestedTask); announce(`Reading ${TASKS[task].product}…`, "loading");
  try {
    const result = await runTask(requestedTask, {size: Number($("size").value), verification, signal: controller.signal});
    if (activeRequest !== controller) return;
    activeResult = result; resultTask = requestedTask; renderResult(result);
    const unavailable = ["unavailable", "not_covered", "restricted", "failed", "error"].includes(result.view.state);
    announce(unavailable ? "The service returned an unavailable evidence state. Read its reason below." : "Response received. Check the source dates and limits below.", unavailable ? "unavailable" : "received");
    track(unavailable ? "unavailable" : "received", requestedTask);
  } catch (error) {
    if (activeRequest !== controller) return;
    announce(error.name === "AbortError" ? "The request reached its 30-second limit. You can try again manually or use the setup instructions." : error.message, "error"); track("failed", requestedTask);
  } finally {clearTimeout(timeout); if (activeRequest === controller) {activeRequest = null; $("run").disabled = false;}}
});
$("download").addEventListener("click", () => {if (!activeResult) return; download(JSON.stringify({schema: "liquilens.browser-research.v1", task: resultTask, retrieved_at: activeResult.retrievedAt, endpoint: TASKS[resultTask].endpoint, tool: TASKS[resultTask].tool, evidence: activeResult.evidence}, null, 2), `${resultTask}-evidence.json`); track("evidence_downloaded", resultTask);});
$("keep-review").addEventListener("click", () => {
  if (!activeResult) return;
  try {
    review.set(resultTask, captureReview(resultTask, activeResult, {size: Number($("size").value)}));
    renderReview(); announce(`${TASKS[resultTask].product} snapshot kept. A later selection for this product replaces it in the brief.`);
  } catch (error) {announce(error.message, "error");}
});
$("download-brief").addEventListener("click", () => {if (review.size) download(reviewMarkdown([...review.values()]), "financial-evidence-review.md", "text/markdown;charset=utf-8");});
$("download-review").addEventListener("click", () => {if (review.size) download(JSON.stringify(reviewPacket([...review.values()]), null, 2), "financial-evidence-review.json");});
$("clear-review").addEventListener("click", () => {review.clear(); renderReview();});
$("useful").addEventListener("click", async function () {
  if (!activeResult || this.disabled) return;
  const submitted = activeResult; this.disabled = true; this.textContent = "Sending feedback…";
  const accepted = await track("helpful_clicked", resultTask);
  if (activeResult !== submitted) return;
  this.textContent = accepted ? "Feedback recorded" : verification ? "Verification: feedback not sent" : privacyOptOut ? "Privacy preference: feedback not sent" : "Feedback could not be sent";
  this.disabled = accepted || verification || privacyOptOut;
});
chooseTask(task, false);
renderReview();
