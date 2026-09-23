import {TASKS, project, safeUrl} from "./core.mjs";

const order = Object.keys(TASKS);
const sizes = [1000, 10000, 100000, 1000000];
const copy = value => JSON.parse(JSON.stringify(value));
function freeze(value) {
  if (value && typeof value === "object") {
    Object.values(value).forEach(freeze);
    Object.freeze(value);
  }
  return value;
}
function timestamp(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}T/.test(value) || !Number.isFinite(Date.parse(value))) throw new Error("A recorded retrieval time is required.");
  return new Date(value).toISOString();
}

// Retain the response the reader chose, even when a later request changes it.
export function captureReview(task, result, {size} = {}) {
  if (!Object.hasOwn(TASKS, task)) throw new Error("Choose a supported research question.");
  if (task === "exit" && !sizes.includes(size)) throw new Error("Choose a supported exit size.");
  const evidence = copy(result.evidence);
  const view = project(task, evidence);
  if (task === "exit" && view.state === "depth-based estimate" && evidence.requested_size_usd !== size) throw new Error("The retained result belongs to a different position size.");
  return freeze({schema: "liquilens.review-entry.v1", task, product: TASKS[task].product,
    retrieved_at: timestamp(result.retrievedAt), endpoint: TASKS[task].endpoint,
    tool: TASKS[task].tool, arguments: copy(task === "exit" ? {size_usd: size} : TASKS[task].args), evidence});
}

export function reviewPacket(entries, preparedAt = new Date().toISOString()) {
  if (!Array.isArray(entries) || !entries.length || entries.length > order.length) throw new Error("Keep between one and three research snapshots.");
  if (new Set(entries.map(entry => entry.task)).size !== entries.length) throw new Error("Keep one snapshot per research question.");
  const snapshots = entries.map(entry => {
    if (!Object.hasOwn(TASKS, entry.task) || entry.schema !== "liquilens.review-entry.v1" || entry.endpoint !== TASKS[entry.task].endpoint || entry.tool !== TASKS[entry.task].tool) throw new Error("The snapshot does not match a supported source.");
    const retained = captureReview(entry.task, {evidence: entry.evidence, retrievedAt: entry.retrieved_at}, {size: entry.arguments?.size_usd});
    if (JSON.stringify(retained.arguments) !== JSON.stringify(entry.arguments)) throw new Error("The snapshot request has changed.");
    return retained;
  }).sort((a, b) => order.indexOf(a.task) - order.indexOf(b.task));
  return {schema: "liquilens.research-review.v1", prepared_at: timestamp(preparedAt),
    scope: "Independently retrieved research snapshots for human review. Source dates and evidence limits apply separately. No combined score, credit approval or trade instruction.",
    not_included: order.filter(task => !snapshots.some(entry => entry.task === task)).map(task => TASKS[task].product),
    snapshots};
}

// Returned prose is untrusted text, including when rendered as Markdown.
const plain = value => String(value).replace(/[\r\n\u2028\u2029]+/g, " ").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/[\\`*_{}\[\]()!#|~]/g, "\\$&");
export function reviewMarkdown(entries, preparedAt) {
  const packet = reviewPacket(entries, preparedAt);
  const lines = ["# Financial evidence review", "", `Prepared at: ${packet.prepared_at}`, "", packet.scope, "",
    "These are retained observations, not an automatically refreshed report. Preparation time does not change the age of any observation.", "",
    packet.not_included.length ? `Not included: ${packet.not_included.join(", ")}. No result was retained for these products.` : "Includes separately dated LiquiLens, Seiche and Undertow snapshots.", ""];
  for (const entry of packet.snapshots) {
    const view = project(entry.task, entry.evidence);
    lines.push(`## ${entry.product}`, "", `Question: ${plain(TASKS[entry.task].title)}`, "",
      `Retrieved at: ${entry.retrieved_at}`, `Source endpoint: <${entry.endpoint}>`,
      `Tool: ${plain(entry.tool)}`, `Request: ${plain(JSON.stringify(entry.arguments))}`, "",
      `Returned state: ${plain(view.state)}`, "", `### ${plain(view.title)}`, "", plain(view.note), "");
    for (const [heading, rows] of [["Source dates and measures", view.facts], ["Reported details", view.details]]) {
      if (rows.length) lines.push(`### ${heading}`, "", ...rows.map(([label, value]) => `- ${plain(label)}: ${plain(value)}`), "");
    }
    lines.push("### Evidence limits", "", ...view.limits.map(value => `- ${plain(value)}`), "", "### Sources", "");
    const urls = view.sources.map(safeUrl).filter(Boolean);
    lines.push(...(urls.length ? urls.map(url => `- <${url.replace(/</g, "%3C").replace(/>/g, "%3E")}>`) : ["No source links were returned for this snapshot."]), "");
  }
  return lines.join("\n");
}
