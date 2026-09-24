// Aggregate setup intent; no visitor identifier, query or research content.
const clients = new Set(["hermes", "openclaw", "claude", "codex", "cursor", "vscode"]);
const general = new Set(["kit_download_requested", "n8n_download_requested", "research_prompt_copied", "skill_opened"]);
const clientActions = new Set(["config_copied", "config_download_requested"]);
const events = new Set([...general, ...[...clients].flatMap(client => [...clientActions].map(action => `${client}_${action}`))]);

export function entryEvent(action, client) {
  if (general.has(action)) return action;
  return clients.has(client) && clientActions.has(action) ? `${client}_${action}` : null;
}

export function createTracker({verification = false, privacyOptOut = false, send = globalThis.fetch} = {}) {
  const sent = new Set();
  return async event => {
    if (verification || privacyOptOut || !events.has(event) || sent.has(event)) return false;
    sent.add(event); // No retries or repeated clicks counted within this page view.
    try {
      const response = await send("https://api.liquilens.in/api/events", {
        method: "POST", headers: {"Content-Type": "application/json"},
        credentials: "omit", redirect: "error", referrerPolicy: "no-referrer",
        keepalive: true, body: JSON.stringify({surface: "agent_starter", event}),
      });
      return response.status === 202;
    } catch { return false; }
  };
}
