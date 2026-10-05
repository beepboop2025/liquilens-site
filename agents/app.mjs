import {topicProfiles, defaultProfile, selectConfiguration} from "./profile-config.mjs";
import {createTracker, entryEvent} from "./metrics.mjs";
import {applyAgentNavigation, browserNavigationContext} from "./navigation.mjs";
const navigation = browserNavigationContext(location, navigator, window);
applyAgentNavigation(document, location.href, navigation);
const track = createTracker({
  verification: navigation.verification,
  privacyOptOut: navigation.privacyOptOut,
});
const help = {
  hermes: "Merge hermes.yaml into ~/.hermes/config.yaml. Keep existing settings, then start a new session or use /reload-mcp.",
  openclaw: "Merge openclaw.json into ~/.openclaw/openclaw.json. Native MCP support is required. Keep existing settings and review the discovered tools.",
  claude: "Run these commands in your terminal. They add the public servers to Claude Code's default scope.",
  codex: "Run these commands in your terminal. Existing configured servers are preserved.",
  cursor: "Merge these entries into .cursor/mcp.json in your project, keeping existing servers.",
  vscode: "Merge these entries into .vscode/mcp.json in your project, keeping existing servers.",
  gemini: "Merge gemini.json into .gemini/settings.json in your project, keeping existing settings. Run gemini mcp list to check connections, then review /mcp in a Gemini CLI session.",
};
const $ = id => document.getElementById(id);
for (const [id, profile] of Object.entries(topicProfiles)) {
  const option = document.createElement("option");
  option.value = id;
  option.textContent = profile.label;
  $("topic-profile").append(option);
}
$("topic-profile").value = defaultProfile;
function update() {
  const client = $("client").value;
  const selection = selectConfiguration(client, $("topic-profile").value);
  $("configuration").textContent = selection.configuration.trim();
  $("client-help").textContent = help[client];
  $("config-download").href = selection.download;
  $("profile-description").textContent = selection.description;
  $("profile-scope").textContent = selection.scope;
  $("task-prompt").textContent = selection.prompt;
  $("copy-status").textContent = "";
}
async function copy(id, action) {
  const event = entryEvent(action, $("client").value);
  try {await navigator.clipboard.writeText($(id).textContent); $("copy-status").textContent = "Copied."; track(event);}
  catch {$("copy-status").textContent = "Select and copy the text, or download the configuration.";}
}
$("client").addEventListener("change", update);
$("topic-profile").addEventListener("change", update);
$("copy-config").addEventListener("click", () => copy("configuration", "config_copied"));
$("copy-prompt").addEventListener("click", () => copy("task-prompt", "research_prompt_copied"));
$("config-download").addEventListener("click", () => track(entryEvent("config_download_requested", $("client").value)));
for (const [id, action] of [["kit-download", "kit_download_requested"], ["n8n-download", "n8n_download_requested"], ["agent-skill", "skill_opened"]]) {
  $(id).addEventListener("click", () => track(entryEvent(action)));
}
update();
