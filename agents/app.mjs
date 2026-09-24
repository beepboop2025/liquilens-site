import {configuration} from "../start/core.mjs";
const ids = ["seiche", "liquilens", "undertow"];
const help = {
  hermes: "Merge hermes.yaml into ~/.hermes/config.yaml. Keep existing settings, then start a new session or use /reload-mcp.",
  openclaw: "Merge openclaw.json into ~/.openclaw/openclaw.json. Native MCP support is required. Keep existing settings and review the discovered tools.",
  claude: "Run these commands in your terminal. They add the public servers to Claude Code's default scope.",
  codex: "Run these commands in your terminal. Existing configured servers are preserved.",
  cursor: "Merge these entries into .cursor/mcp.json in your project, keeping existing servers.",
  vscode: "Merge these entries into .vscode/mcp.json in your project, keeping existing servers.",
};
const $ = id => document.getElementById(id);
const files = {hermes: "hermes.yaml", openclaw: "openclaw.json", claude: "claude.txt", codex: "codex.txt", cursor: "cursor.json", vscode: "vscode.json"};
async function update() {
  const client = $("client").value;
  $("configuration").textContent = configuration(client, ids);
  $("client-help").textContent = help[client];
  $("config-download").href = "/agents/" + files[client];
  // Use the same focused files as the downloadable kit. No MCP call is made.
  if (["hermes", "openclaw"].includes(client)) {
    try {
      const response = await fetch("/agents/" + files[client], {redirect: "error", credentials: "omit"});
      if (!response.ok) return;
      const text = await response.text();
      if ($("client").value === client && text.length < 12000) $("configuration").textContent = text.trim();
    } catch { /* The native configuration above remains usable. */ }
  }
}
async function copy(id) {
  try {await navigator.clipboard.writeText($(id).textContent); $("copy-status").textContent = "Copied.";}
  catch {$("copy-status").textContent = "Select and copy the text, or download the configuration.";}
}
$("client").addEventListener("change", update);
$("copy-config").addEventListener("click", () => copy("configuration"));
$("copy-prompt").addEventListener("click", () => copy("task-prompt"));
update();
