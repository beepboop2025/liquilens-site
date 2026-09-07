// Display source fields; never turn missing evidence into a score or recommendation.
export const TASKS = Object.freeze({
  bank: {name: "Bank and credit research", product: "LiquiLens", endpoint: "https://api.liquilens.in/mcp", tool: "bank_asset_quality_review", title: "What changed in Cosmos Bank’s NPAs?", description: "Read the disclosed movement in bad loans, with cash recoveries and write-offs kept separate.", args: {slug: "cosmos-ucb", include_history: true}, prompt: "Review Cosmos Co-operative Bank’s disclosed NPAs using LiquiLens. Show the reporting period, filing source, cash recoveries, upgrades and write-offs separately. State missing disclosures and evidence limits. Do not infer deposit safety.", next: "/banking/", nextLabel: "Choose another covered bank"},
  funding: {name: "Agent and macro research", product: "Seiche", endpoint: "https://api.seiche.info/mcp", tool: "funding_stress_now", title: "What is driving dollar funding stress?", description: "Get the funding desk’s conclusion, its supporting observations and the evidence that disagrees.", args: {}, prompt: "Use Seiche to explain the current dollar-funding regime. Separate the source-dated evidence from modelled context, show the strongest counterevidence, and state freshness and historical-validation limits. Cite the returned sources.", next: "https://seiche.info/money-markets/", nextLabel: "Explore the money-market desk"},
  exit: {name: "Crypto market research", product: "Undertow", endpoint: "https://api.seiche.info/undertow/mcp", tool: "exit_cost", title: "What does a BTC exit cost across venues?", description: "Compare published depth-based estimates at your selected dollar size. This is a research estimate, not an executable quote.", args: {size_usd: 100000}, prompt: "Use Undertow to compare estimated BTC sell costs for a $100,000 position across the available venues. Show basis points, snapshot time, the published size rung and methodology. Do not recommend a venue or treat the estimates as executable quotes.", next: "https://liquilens-undertow.com/developers/", nextLabel: "Explore depth and exit research"},
});

export const SERVERS = Object.freeze([
  {id: "liquilens", name: "LiquiLens", url: TASKS.bank.endpoint, role: "Bank filings, NPA movements and institution evidence", docs: "https://liquilens.in/developers/", prompt: TASKS.bank.prompt},
  {id: "seiche", name: "Seiche", url: TASKS.funding.endpoint, role: "Dollar funding, money markets and macro context", docs: "https://seiche.info/developers", prompt: TASKS.funding.prompt},
  {id: "undertow", name: "Undertow", url: TASKS.exit.endpoint, role: "Market depth and position-sized exit estimates", docs: "https://liquilens-undertow.com/developers/", prompt: TASKS.exit.prompt},
  {id: "financial-evidence", name: "Financial Evidence", url: "https://liquilens.in/mcp/financial-evidence", role: "Route a question and collect source-separated evidence", docs: "https://github.com/beepboop2025/financial-evidence-skills", prompt: "List the supported financial-evidence topics, then fetch the funding and institution context. Keep each source’s dates, rights and unavailable states separate. Do not infer Carrier verification from a successful fetch."},
  {id: "palimpsest", name: "Palimpsest", url: "https://api.seiche.info/palimpsest/mcp", role: "OONI network measurements and information-control evidence; China economic values are restricted", docs: "https://palimpsest.info/", prompt: "Use Palimpsest get_signal with name ooni-gfw to explain its published OONI measurements for China. Keep the measurement window, generation time, sample counts, source and missing tests attached. Anomalous measurements are not confirmed censorship or a representative measure of every connection. China economic values are currently restricted/unavailable; preserve that state without substituting zero or an economic conclusion."},
  {id: "riptide", name: "Riptide", url: "https://api.seiche.info/riptide/mcp", role: "Scenario research and recorded paper results", docs: "https://github.com/beepboop2025/riptide-mcp", prompt: "Read Riptide’s overview and paper record. Distinguish recorded simulated results from live performance, and state dates, costs, missing evidence and research limits."},
  {id: "myquant-editorial", name: "MyQuant editorial", url: "https://myquantdoesntspeakenglish.com/mcp", role: "Find and read the available editorial briefing", docs: "https://myquantdoesntspeakenglish.com/", prompt: "Find MyQuant’s available stories. Summarize one relevant story with its actual publication date, source links and limitations. Do not assume the briefing is from today."},
  {id: "narcoscope", name: "NarcoScope", url: "https://www.narcoscope.com/mcp", role: "Official drug-market and illicit-economy evidence", docs: "https://narcoscope.com/", prompt: "Use NarcoScope to retrieve official illicit-economy research. Give the source, observation period, coverage gaps and uncertainty. Keep indicators distinct from causal claims."},
  {id: "trade-safety", name: "Trade Safety", url: "https://trade-safety.liquilens.in/mcp", role: "Inspect the read-only assessment contract", docs: "https://liquilens.in/protocol/trade-safety/", prompt: "Read the Trade Safety capabilities and explain its evidence and policy requirements. It is a read-only sandbox: do not submit an order or treat an assessment as execution authority."},
]);

export function configuration(client, ids) {
  const chosen = SERVERS.filter(server => ids.includes(server.id));
  if (!chosen.length || chosen.length !== new Set(ids).size) throw new Error("Choose supported servers.");
  if (client === "codex") return chosen.map(s => `codex mcp add ${s.id} --url ${s.url}`).join("\n");
  if (client === "claude") return chosen.map(s => `claude mcp add --transport http ${s.id} ${s.url}`).join("\n");
  if (client === "vscode") return JSON.stringify({servers: Object.fromEntries(chosen.map(s => [s.id, {type: "http", url: s.url}]))}, null, 2);
  if (client === "cursor") return JSON.stringify({mcpServers: Object.fromEntries(chosen.map(s => [s.id, {url: s.url}]))}, null, 2);
  throw new Error("Unsupported client.");
}

const text = value => typeof value === "string" ? value : "Not reported";
const number = (value, unit = "") => typeof value === "number" && Number.isFinite(value) ? `${value.toLocaleString("en-US", {maximumFractionDigits: 3})}${unit}` : "Not reported";
const list = value => Array.isArray(value) ? value : [];
export function safeUrl(value) {
  try { const u = new URL(value); return u.protocol === "https:" && !u.username && !u.password ? u.href : null; } catch { return null; }
}
export function project(task, data) {
  if (!data || typeof data !== "object" || Array.isArray(data)) throw new Error("No evidence object was returned.");
  const state = String(data.status || "").toLowerCase();
  if (data.ok === false || data.available === false || ["unavailable", "not_covered", "restricted", "failed", "error"].includes(state)) {
    return {state: ["unavailable", "not_covered", "restricted", "failed", "error"].includes(state) ? state : "unavailable", title: "This evidence is unavailable", note: text(data.reason || data.message), facts: [], details: [], limits: ["No conclusion has been substituted for the missing evidence."], sources: []};
  }
  if (task === "bank") {
    if (data.schema !== "liquilens.bank-specialisation.v1" || data.slug !== "cosmos-ucb") throw new Error("The bank response did not match the requested record.");
    const n = data.npa_movement || {}, m = data.metrics || {}, reductions = n.reductions || {};
    return {state: text(data.status), title: text(data.name), note: "Amounts below are the filing’s disclosed components. An arithmetic reconciliation does not independently verify the filing.",
      facts: [["Reporting period ends", text(data.period_end)], ["Available to this service", text(data.available_at)], ["Gross NPA ratio", number(m.gnpa_pct?.value, "%")], ["Net NPA ratio", number(m.nnpa_pct?.value, "%")]],
      details: [["Opening gross NPAs", number(n.opening_gnpa)], ["New additions", number(n.additions)], ["Cash recoveries", number(reductions.cash_recoveries)], ["Upgrades", number(reductions.upgrades)], ["Write-offs", number(reductions.write_offs)], ["Closing gross NPAs", number(n.closing_gnpa)], ["Reported amount unit", text(n.amount_unit)], ["Reconciliation status", text(n.status)]],
      limits: [...list(data.interpretation_limits), ...list(data.comparability_notes)].filter(x => typeof x === "string"), sources: list(data.sources).filter(safeUrl)};
  }
  if (task === "funding") {
    if (data.schema !== "seiche.public.v2") throw new Error("The funding response did not match the expected contract.");
    const e = data.editorial || {}, c = data.conclusion || {}, q = data.data_quality || {};
    const futureDates = list(q.headline_ages).filter(x => typeof x.asof === "string" && x.asof.slice(0, 10) > String(data.generated_at).slice(0, 10));
    return {state: "source-reported research", title: text(e.thesis || c.line), note: text(e.confidence_note),
      facts: [["Board regime", text(c.regime)], ["Board value (0–100)", number(c.value)], ["Generated at", text(data.generated_at)], ["Editorial confidence", text(e.confidence)]],
      details: [...list(e.evidence).slice(0, 4).map(x => [text(x.label), `${text(x.claim)} Source: ${text(x.source)}. Observation: ${text(x.asof)}.`]), ...list(e.countercase).slice(0, 3).map(x => ["Counterevidence", `${text(x.claim)} Source: ${text(x.source)}. Observation: ${text(x.asof)}.`])],
      limits: ["Generation time is not the date of every underlying observation.", `Service-wide source states: ${number(q.status_counts?.fresh)} fresh; ${number(q.status_counts?.aging)} aging; ${number(q.status_counts?.stale)} stale; ${number(q.status_counts?.dead)} dead; ${number(q.status_counts?.unknown)} unknown.`, ...futureDates.map(x => `${text(x.series)} carries a future source date (${text(x.asof)}). Do not treat that date as an already observed print.`), text(q.publication_note), text(data.proof?.historical_evidence?.reason), "A funding regime is research context, not an instruction to trade."], sources: ["https://api.seiche.info/api/gauge", "https://seiche.info/money-markets/"]};
  }
  if (task === "exit") {
    if (data.asset !== "BTC" || !data.sell_cost_bp_by_venue || typeof data.sell_cost_bp_by_venue !== "object" || Array.isArray(data.sell_cost_bp_by_venue)) throw new Error("The exit response did not contain the requested BTC venue estimates.");
    return {state: "depth-based estimate", title: `BTC sell-cost estimates at ${number(data.published_rung_used_usd, " USD")}`, note: text(data.method),
      facts: [["Requested size", number(data.requested_size_usd, " USD")], ["Published size rung", number(data.published_rung_used_usd, " USD")], ["Snapshot generated", text(data.generated_at)], ["Observation date", text(data.asof)]],
      details: Object.entries(data.sell_cost_bp_by_venue).sort(([a], [b]) => a.localeCompare(b)).map(([venue, value]) => [venue, number(value, " bp")]),
      limits: [text(data.note_on_rung), "1 basis point is 0.01%. Estimates do not guarantee executable prices, fees, venue access or withdrawal availability.", text(data.disclaimer)], sources: ["https://api.seiche.info/undertow/calibration.json"]};
  }
  throw new Error("Unknown research task.");
}

export async function boundedJson(response, limit = 2 * 1024 * 1024) {
  const declared = response.headers.get("content-length");
  if (declared !== null && (!/^\d+$/.test(declared) || Number(declared) > limit)) throw new Error("The response exceeds the display limit.");
  const reader = response.body?.getReader();
  if (!reader) throw new Error("This browser cannot read the response safely.");
  const chunks = []; let size = 0;
  try {
    while (true) {
      const {value, done} = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > limit) throw new Error("The response exceeds the display limit.");
      chunks.push(value);
    }
  } catch (error) { await reader.cancel().catch(() => {}); throw error; }
  const bytes = new Uint8Array(size); let offset = 0;
  for (const chunk of chunks) {bytes.set(chunk, offset); offset += chunk.byteLength;}
  return JSON.parse(new TextDecoder("utf-8", {fatal: true}).decode(bytes));
}

export async function runTask(task, {size = 100000, verification = false, fetcher = fetch, signal} = {}) {
  if (!Object.hasOwn(TASKS, task)) throw new Error("Choose a supported question.");
  const spec = TASKS[task];
  if (task === "exit" && ![1000, 10000, 100000, 1000000].includes(size)) throw new Error("Choose one of the published example sizes.");
  const protocol = "2025-11-25";
  const client = {name: verification ? "liquilens-start-operator-verification" : "liquilens-start-browser", version: "1.0.0"};
  const headers = {"Content-Type": "application/json", Accept: "application/json, text/event-stream", "MCP-Protocol-Version": protocol};
  if (verification && task === "bank") headers["X-Liquilens-Traffic-Class"] = "synthetic";
  let sequence = 0;
  async function rpc(method, params, notification = false) {
    const id = ++sequence;
    const body = {jsonrpc: "2.0", method, params};
    if (!notification) body.id = id;
    const response = await fetcher(spec.endpoint, {method: "POST", headers, body: JSON.stringify(body), signal, redirect: "error", credentials: "omit"});
    if (!response.ok) throw new Error(`The service returned HTTP ${response.status}. Try again later or use the connection instructions.`);
    if (notification) {await response.body?.cancel(); return;}
    const message = await boundedJson(response);
    if (message?.jsonrpc !== "2.0" || message.id !== id || message.error || !message.result || message.result.isError) throw new Error("The service could not complete this question. No result has been inferred.");
    return message.result;
  }
  const initialized = await rpc("initialize", {protocolVersion: protocol, capabilities: {}, clientInfo: client});
  if (initialized.protocolVersion !== protocol) throw new Error("The service did not accept the supported protocol.");
  await rpc("notifications/initialized", {}, true);
  const result = await rpc("tools/call", {name: spec.tool, arguments: task === "exit" ? {size_usd: size} : spec.args, _meta: {"io.modelcontextprotocol/clientInfo": client}});
  let evidence = result.structuredContent;
  if (evidence === undefined) {
    if (result.content?.length !== 1 || result.content[0].type !== "text") throw new Error("No structured evidence was returned.");
    evidence = JSON.parse(result.content[0].text);
  }
  const view = project(task, evidence);
  if (task === "exit" && view.state === "depth-based estimate" && evidence.requested_size_usd !== size) throw new Error("The service returned a different requested position size.");
  return {evidence, view, retrievedAt: new Date().toISOString()};
}
