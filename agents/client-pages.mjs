import {createTracker, entryEvent} from "./metrics.mjs";

const client = document.body.dataset.agentClient;
const track = createTracker({
  verification: location.hostname !== "liquilens.in" || new URLSearchParams(location.search).get("verification") === "1" || navigator.webdriver === true,
  privacyOptOut: navigator.globalPrivacyControl === true || navigator.doNotTrack === "1" || window.doNotTrack === "1",
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
