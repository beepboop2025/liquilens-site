import {acquisitionSource, questionLink} from "../start/acquisition.mjs";

const pages = new Set(["/agents/", "/agents/hermes/", "/agents/openclaw/", "/start/"]);
const tasks = new Set(["funding", "bank", "exit"]);

// Suppression is monotonic: a duplicate flag cannot turn an existing opt-out off.
export function navigationContext({search = "", hostname = "liquilens.in", webdriver = false,
  globalPrivacyControl = false, doNotTrack, windowDoNotTrack} = {}) {
  const params = new URLSearchParams(search);
  return {
    source: acquisitionSource(search),
    verification: hostname !== "liquilens.in" || webdriver === true || params.getAll("verification").includes("1"),
    privacyOptOut: globalPrivacyControl === true || doNotTrack === "1" || windowDoNotTrack === "1" || params.getAll("privacy_opt_out").includes("1"),
  };
}

export function browserNavigationContext(location, navigator, window) {
  return navigationContext({search: location.search, hostname: location.hostname,
    webdriver: navigator.webdriver, globalPrivacyControl: navigator.globalPrivacyControl,
    doNotTrack: navigator.doNotTrack, windowDoNotTrack: window.doNotTrack});
}

// Only these local HTML journeys receive the finite acquisition label. Files,
// third-party links and arbitrary input query values are never propagated.
export function agentNavigationLink(href, {currentUrl, context, download = false}) {
  // Fragment-only links stay in the current document, including after a task
  // selector updates its URL. Rewriting them would freeze an earlier task.
  if (download || href.startsWith("#")) return href;
  let url, current;
  try {current = new URL(currentUrl); url = new URL(href, current);} catch {return href;}
  if (!new Set(["http:", "https:"]).has(url.protocol) || url.origin !== current.origin || url.username || url.password || !pages.has(url.pathname)) return href;
  const taskValues = url.searchParams.getAll("task");
  const task = taskValues.length === 1 && tasks.has(taskValues[0]) ? taskValues[0] : null;
  const sizeValues = url.searchParams.getAll("size");
  const size = sizeValues.length === 1 ? sizeValues[0] : undefined;
  // Normalize again at the boundary, including callers constructing a context.
  const source = acquisitionSource(new URLSearchParams({utm_source: context.source}).toString());
  url.search = url.pathname === "/start/" && task ? new URL(questionLink(task, source, size)).search : new URLSearchParams({utm_source: source}).toString();
  if (context.verification) url.searchParams.set("verification", "1");
  if (context.privacyOptOut) url.searchParams.set("privacy_opt_out", "1");
  return url.pathname + url.search + url.hash;
}

export function applyAgentNavigation(root, currentUrl, context) {
  for (const link of root.querySelectorAll("a[href]")) {
    const href = link.getAttribute("href");
    const next = agentNavigationLink(href, {currentUrl, context, download: link.hasAttribute("download")});
    if (next !== href) link.setAttribute("href", next);
  }
}
