import test from "node:test";
import assert from "node:assert/strict";
import {SOURCES} from "../start/acquisition.mjs";
import {navigationContext, browserNavigationContext, agentNavigationLink, applyAgentNavigation} from "../agents/navigation.mjs";
import {topicProfiles, selectConfiguration} from "../agents/profile-config.mjs";
import {readFileSync} from "node:fs";

const currentUrl = "https://liquilens.in/agents/?utm_source=telegram";
const context = navigationContext({search: "?utm_source=telegram"});
const link = (href, options = {}) => agentNavigationLink(href, {currentUrl, context, ...options});

test("topic selection copies the downloaded configuration and the matching research prompt", () => {
  for (const id of Object.keys(topicProfiles)) {
    for (const client of ["hermes", "openclaw", "claude", "codex", "cursor", "vscode"]) {
      const selected = selectConfiguration(client, id);
      const downloaded = readFileSync(new URL(".." + selected.download, import.meta.url), "utf8");
      assert.equal(selected.configuration, downloaded);
      assert.equal(selected.prompt, topicProfiles[id].prompt);
      assert.match(selected.scope, client === "hermes" || client === "openclaw" ? /selects the listed tools/ : /does not apply a tool allowlist/);
    }
  }
  const gold = selectConfiguration("openclaw", "gold");
  assert.match(gold.configuration, /gold_inventory_carry/);
  assert.match(gold.configuration, /gold_cash_realisation/);
  assert.doesNotMatch(gold.configuration, /exit_schedule|board_full/);
  assert.match(gold.prompt, /ask for every required/);
  assert.match(gold.prompt, /future settlement as current cash/);
});

test("unknown topic or client cannot create a configuration or download path", () => {
  for (const bad of ["__proto__", "constructor", "../gold", "https://other.example", ""]) {
    assert.throws(() => selectConfiguration("hermes", bad), /supported research topic/);
    assert.throws(() => selectConfiguration(bad, "gold"), /supported research topic/);
  }
});

test("each first-result task survives local navigation with its bounded source", () => {
  for (const source of SOURCES) for (const task of ["funding", "bank", "exit"]) {
    const result = new URL(link(`/start/?task=${task}&size=100000`, {context: navigationContext({search: `?utm_source=${source}`})}), currentUrl);
    assert.equal(result.searchParams.get("task"), task);
    assert.equal(result.searchParams.get("utm_source"), source);
    assert.equal(result.searchParams.get("size"), task === "exit" ? "100000" : null);
  }
  assert.equal(link("/start/#connect"), "/start/?utm_source=telegram#connect");
});

test("source labels survive multiple local guide hops without carrying other query data", () => {
  const first = new URL(link("/agents/hermes/?email=private&prompt=secret#connect"), currentUrl);
  assert.equal(first.pathname + first.search + first.hash, "/agents/hermes/?utm_source=telegram#connect");
  const second = agentNavigationLink("/agents/openclaw/", {currentUrl: first.href, context: navigationContext({search: first.search})});
  assert.equal(second, "/agents/openclaw/?utm_source=telegram");
  const third = agentNavigationLink("/start/?task=bank", {currentUrl: new URL(second, currentUrl).href, context: navigationContext({search: first.search})});
  assert.equal(third, "/start/?task=bank&utm_source=telegram");
});

test("ambiguous or arbitrary sources, tasks and sizes cannot propagate", () => {
  for (const search of ["?utm_source=x&utm_source=telegram", "?utm_source=x&utm_source=x", "?utm_source=X", "?utm_source=private@example.com"]) {
    const normalized = navigationContext({search});
    assert.equal(normalized.source, "unknown");
    assert.equal(link("/start/?task=funding", {context: normalized}), "/start/?task=funding&utm_source=unknown");
  }
  assert.equal(link("/start/?task=bank&task=exit&prompt=secret&user_id=123"), "/start/?utm_source=telegram");
  assert.equal(link("/start/?task=secret&size=100000"), "/start/?utm_source=telegram");
  assert.equal(link("/start/?task=exit&size=1000&size=10000"), "/start/?task=exit&utm_source=telegram");
  assert.equal(link("/start/?task=exit&size=private"), "/start/?task=exit&utm_source=telegram");
  assert.equal(link("/start/?task=exit", {context: {...context, source: "private"}}), "/start/?task=exit&utm_source=unknown");
});

test("external, non-navigation and download URLs remain byte-for-byte unchanged", () => {
  for (const href of ["#connect", "#questions", "https://clawhub.ai/beepboop2025/skills/liquilens-trading-research", "https://other.example/start/?task=funding", "//other.example/agents/", "https://user:secret@liquilens.in/agents/", "javascript:alert(1)", "mailto:person@example.com", "/agents/hermes.yaml", "/agents/trading-research-kit.zip", "/agents/trading-research/SKILL.md", "/developers/", "/start/not-a-page"]) assert.equal(link(href), href);
  assert.equal(link("/start/?task=funding", {download: true}), "/start/?task=funding");
});

test("verification and explicit privacy suppression survive navigation and duplicate flags", () => {
  const suppressed = navigationContext({search: "?utm_source=x&verification=0&verification=1&privacy_opt_out=0&privacy_opt_out=1"});
  assert.equal(link("/start/?task=funding", {context: suppressed}), "/start/?task=funding&utm_source=x&verification=1&privacy_opt_out=1");
  const destination = new URL(link("/agents/openclaw/", {context: suppressed}), currentUrl);
  assert.deepEqual(navigationContext({search: destination.search}), suppressed);
  for (const value of [{hostname: "localhost"}, {webdriver: true}]) assert.equal(navigationContext(value).verification, true);
  for (const value of [{globalPrivacyControl: true}, {doNotTrack: "1"}, {windowDoNotTrack: "1"}]) {
    assert.equal(navigationContext(value).privacyOptOut, true);
    assert.equal(navigationContext(value).verification, false);
  }
  assert.deepEqual(navigationContext({search: "?verification=true&privacy_opt_out=yes"}), {source: "unknown", verification: false, privacyOptOut: false});
});

test("browser privacy values are read without writing storage or adding identity", () => {
  assert.deepEqual(browserNavigationContext({search: "?utm_source=x", hostname: "liquilens.in"}, {globalPrivacyControl: true, webdriver: false}, {}), {source: "x", verification: false, privacyOptOut: true});
});

test("DOM wiring rewrites only eligible anchors and respects the download attribute", () => {
  const anchor = (href, download = false) => ({href, getAttribute(name) {assert.equal(name, "href"); return this.href;}, hasAttribute(name) {assert.equal(name, "download"); return download;}, setAttribute(name, next) {assert.equal(name, "href"); this.href = next;}});
  const anchors = [anchor("/start/?task=bank"), anchor("/agents/hermes/"), anchor("/agents/trading-research-kit.zip", true), anchor("https://clawhub.ai/"), anchor("/start/?task=exit", true)];
  applyAgentNavigation({querySelectorAll(selector) {assert.equal(selector, "a[href]"); return anchors;}}, currentUrl, context);
  assert.deepEqual(anchors.map(a => a.href), ["/start/?task=bank&utm_source=telegram", "/agents/hermes/?utm_source=telegram", "/agents/trading-research-kit.zip", "https://clawhub.ai/", "/start/?task=exit"]);
});
