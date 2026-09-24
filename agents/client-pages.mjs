import {createTracker, entryEvent} from "./metrics.mjs";
import {applyAgentNavigation, browserNavigationContext} from "./navigation.mjs";

const client = document.body.dataset.agentClient;
const navigation = browserNavigationContext(location, navigator, window);
applyAgentNavigation(document, location.href, navigation);
const track = createTracker({
  verification: navigation.verification,
  privacyOptOut: navigation.privacyOptOut,
});
const status = document.getElementById("copy-status");
for (const button of document.querySelectorAll("[data-copy]")) {
  button.addEventListener("click", async () => {
    const content = document.getElementById(button.dataset.copy);
    try {
      await navigator.clipboard.writeText(content.textContent);
      status.textContent = "Copied.";
      track(entryEvent(button.dataset.action, client));
    } catch {
      status.textContent = "Select and copy the text, or download the configuration.";
    }
  });
}
for (const link of document.querySelectorAll("[data-config-download]")) {
  link.addEventListener("click", () => track(entryEvent("config_download_requested", client)));
}
