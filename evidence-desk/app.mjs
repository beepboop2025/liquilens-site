const ENDPOINT = "/mcp/financial-evidence";
const MAX_RESPONSE_BYTES = 4_194_304;
const REQUEST_TIMEOUT_MS = 35_000;

const TOPIC_LABELS = Object.freeze({
  "money-market": "Money markets",
  "capital-market": "Capital markets",
  "china-economy": "China economy",
  "bank-risk": "Bank risk",
  "market-liquidity": "Market liquidity",
});

function plainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function textValue(value, fallback = "not reported") {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function parseSse(body) {
  const dataLines = body
    .split(/\r?\n/)
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trim());
  if (!dataLines.length) {
    throw new Error("The MCP response did not contain a data event.");
  }
  return JSON.parse(dataLines.join("\n"));
}

export function parseMcpEnvelope(body, contentType = "application/json") {
  if (typeof body !== "string" || !body.trim()) {
    throw new Error("The MCP response was empty.");
  }
  const envelope = contentType.toLowerCase().includes("text/event-stream")
    ? parseSse(body)
    : JSON.parse(body);
  if (!plainObject(envelope)) {
    throw new Error("The MCP response root was not an object.");
  }
  if (plainObject(envelope.error)) {
    throw new Error(textValue(envelope.error.message, "The MCP request failed."));
  }
  if (!plainObject(envelope.result)) {
    throw new Error("The MCP response did not include a result.");
  }
  return envelope;
}

export function extractPacket(envelope) {
  const result = envelope?.result;
  const textBlock = Array.isArray(result?.content)
    ? result.content.find((item) => item?.type === "text" && typeof item.text === "string")
    : undefined;
  let packet;
  if (textBlock) {
    packet = JSON.parse(textBlock.text);
  } else if (plainObject(result?.structuredContent)) {
    packet = result.structuredContent;
  }
  if (!plainObject(packet) || !Array.isArray(packet.sources)) {
    throw new Error("The MCP tool did not return a financial-evidence packet.");
  }
  requireUsableOutput(packet, result?.isError === true);
  return packet;
}

function requireUsableOutput(packet, toolError = false) {
  const outputStatus = textValue(packet?.output_status, "complete");
  if (toolError || outputStatus !== "complete") {
    throw new Error(
      textValue(
        packet?.output_error,
        "The MCP tool reported an unavailable evidence output.",
      ),
    );
  }
}

function sourceReported(source) {
  if (!plainObject(source.source_reported)) {
    return { state: "not reported", clocks: "not reported" };
  }
  const format = (value) => {
    if (!Array.isArray(value) || !value.length) return textValue(value);
    return value
      .filter((item) => plainObject(item) && typeof item.name === "string")
      .map((item) => `${item.name}: ${String(item.value)}`)
      .join(" · ") || "not reported";
  };
  return {
    state: format(source.source_reported.state),
    clocks: format(source.source_reported.clocks),
  };
}

export function packetToView(packet) {
  requireUsableOutput(packet);
  const transport = textValue(packet.transport_status ?? packet.status, "unavailable");
  const evidence = textValue(packet.evidence_status, "not_evaluated");
  const carrier = textValue(packet.carrier_verification, "not_performed");
  return {
    schema: textValue(packet.schema),
    transport,
    evidence,
    carrier,
    topics: Array.isArray(packet.topics) ? packet.topics : [],
    sources: packet.sources.map((source) => {
      const reported = sourceReported(source);
      return {
        product: textValue(source.product, "Unknown product"),
        topic: textValue(source.topic, "unknown-topic"),
        ok: source.ok === true,
        sourceUrl: textValue(source.source_url, ""),
        humanScopeUrl: textValue(source.human_scope_url, ""),
        retrievedAt: textValue(source.retrieved_at),
        hash: textValue(source.content_sha256),
        bytes: Number.isInteger(source.bytes) ? source.bytes : null,
        evidenceClass: textValue(source.evidence_class),
        reportedState: reported.state,
        reportedClocks: reported.clocks,
        error: textValue(source.error, ""),
      };
    }),
  };
}

export function buildToolRequest(topics, id = 1) {
  const unique = [...new Set(topics)].filter((topic) => topic in TOPIC_LABELS);
  if (!unique.length) throw new Error("Select at least one evidence topic.");
  return {
    jsonrpc: "2.0",
    id,
    method: "tools/call",
    params: {
      name: "financial_evidence_fetch",
      arguments: { topics: unique, timeout: 10, max_bytes: 500_000 },
    },
  };
}

export async function fetchEvidence(topics, fetchImpl = fetch) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetchImpl(ENDPOINT, {
      method: "POST",
      credentials: "omit",
      referrerPolicy: "no-referrer",
      headers: {
        Accept: "application/json, text/event-stream",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(buildToolRequest(topics, Date.now())),
      signal: controller.signal,
    });
    const declaredLength = Number(response.headers.get("content-length"));
    if (Number.isFinite(declaredLength) && declaredLength > MAX_RESPONSE_BYTES) {
      throw new Error("The evidence response exceeded the browser safety limit.");
    }
    const body = await response.text();
    if (new TextEncoder().encode(body).byteLength > MAX_RESPONSE_BYTES) {
      throw new Error("The evidence response exceeded the browser safety limit.");
    }
    if (!response.ok) throw new Error(`The evidence endpoint returned HTTP ${response.status}.`);
    return extractPacket(parseMcpEnvelope(body, response.headers.get("content-type") || ""));
  } finally {
    clearTimeout(timeout);
  }
}

function setText(node, value) {
  if (node) node.textContent = value;
}

function statusTone(value) {
  const token = String(value).toLowerCase();
  if (["complete", "ok", "normal", "verified"].includes(token)) return "good";
  if (["partial", "warming_up", "structural", "degraded"].includes(token)) return "warn";
  return "neutral";
}

function renderSummary(view) {
  const summary = document.querySelector("[data-summary]");
  summary.hidden = false;
  for (const [name, value] of [
    ["transport", view.transport],
    ["evidence", view.evidence],
    ["carrier", view.carrier],
  ]) {
    const node = summary.querySelector(`[data-status="${name}"]`);
    setText(node, value.replaceAll("_", " "));
    node.dataset.tone = statusTone(value);
  }
}

function appendFact(list, label, value, className = "") {
  const wrapper = document.createElement("div");
  wrapper.className = `source-fact ${className}`.trim();
  const term = document.createElement("dt");
  term.textContent = label;
  const detail = document.createElement("dd");
  detail.textContent = value;
  wrapper.append(term, detail);
  list.append(wrapper);
}

function safeHttpsLink(url, label) {
  if (!url) return null;
  let parsed;
  try {
    parsed = new URL(url);
  } catch (_error) {
    return null;
  }
  if (parsed.protocol !== "https:") return null;
  const link = document.createElement("a");
  link.href = parsed.href;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.referrerPolicy = "no-referrer";
  link.textContent = label;
  return link;
}

function renderSources(view) {
  const target = document.querySelector("[data-sources]");
  target.replaceChildren();
  for (const source of view.sources) {
    const card = document.createElement("article");
    card.className = "source-card";
    card.dataset.transport = source.ok ? "ok" : "unavailable";
    const heading = document.createElement("div");
    heading.className = "source-heading";
    const title = document.createElement("h3");
    title.textContent = source.product;
    const topic = document.createElement("span");
    topic.textContent = TOPIC_LABELS[source.topic] || source.topic;
    heading.append(title, topic);
    const facts = document.createElement("dl");
    appendFact(facts, "Retrieval", source.ok ? "succeeded" : "unavailable", source.ok ? "good" : "bad");
    appendFact(facts, "Source-reported state", source.reportedState);
    appendFact(facts, "Source-reported clocks", source.reportedClocks);
    appendFact(facts, "Retrieved", source.retrievedAt);
    appendFact(facts, "Evidence class", source.evidenceClass);
    appendFact(facts, "Payload hash", source.hash);
    if (source.bytes !== null) appendFact(facts, "Bytes", source.bytes.toLocaleString("en"));
    if (source.error) appendFact(facts, "Why unavailable", source.error, "bad");
    const actions = document.createElement("div");
    actions.className = "source-actions";
    const scopeLink = safeHttpsLink(source.humanScopeUrl, "Read scope");
    const rawLink = safeHttpsLink(source.sourceUrl, "Open raw source");
    if (scopeLink) actions.append(scopeLink);
    if (rawLink) actions.append(rawLink);
    card.append(heading, facts, actions);
    target.append(card);
  }
}

function selectedTopics() {
  return [...document.querySelectorAll('input[name="topic"]:checked')].map((input) => input.value);
}

function downloadPacket(packet) {
  const blob = new Blob([`${JSON.stringify(packet, null, 2)}\n`], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `liquilens-financial-evidence-${new Date().toISOString().slice(0, 10)}.json`;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function bindBrowser() {
  const form = document.querySelector("[data-evidence-form]");
  if (!form) return;
  const submit = form.querySelector('button[type="submit"]');
  const status = document.querySelector("[data-live-status]");
  const download = document.querySelector("[data-download]");
  let latestPacket;

  document.querySelector("[data-select-all]")?.addEventListener("click", () => {
    for (const input of form.querySelectorAll('input[name="topic"]')) input.checked = true;
    status.textContent = "All five topic routes selected.";
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    submit.disabled = true;
    download.hidden = true;
    setText(status, "Retrieving fixed public routes. This can take up to 35 seconds…");
    try {
      latestPacket = await fetchEvidence(selectedTopics());
      const view = packetToView(latestPacket);
      renderSummary(view);
      renderSources(view);
      download.hidden = false;
      setText(status, `Retrieved ${view.sources.filter((source) => source.ok).length} of ${view.sources.length} fixed sources. Review each source-reported state before citing.`);
    } catch (error) {
      latestPacket = undefined;
      document.querySelector("[data-summary]").hidden = true;
      document.querySelector("[data-sources]").replaceChildren();
      setText(status, error?.name === "AbortError" ? "The request reached its 35-second browser limit." : textValue(error?.message, "Evidence retrieval failed."));
    } finally {
      submit.disabled = false;
    }
  });

  download.addEventListener("click", () => {
    if (latestPacket) downloadPacket(latestPacket);
  });
}

if (typeof document !== "undefined") bindBrowser();
