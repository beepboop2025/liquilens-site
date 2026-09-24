import test from "node:test";
import assert from "node:assert/strict";
import {TASKS} from "../start/core.mjs";

// Execute the real browser entry point with inert DOM/clipboard/transport seams.
// These tests make no HTTP request and never invoke a research tool.
let run = 0;
async function withStart({search = "?task=funding&utm_source=x", hostname = "liquilens.in", navigator = {}, window = {}}, check) {
  const nodes = new Map(), requests = [], copied = [];
  const node = () => ({dataset: {}, children: [], listeners: {}, value: "", textContent: "",
    append(...children) {this.children.push(...children);}, replaceChildren(...children) {this.children = children;},
    addEventListener(type, fn) {this.listeners[type] = fn;}, setAttribute() {}});
  const document = {getElementById(id) {if (!nodes.has(id)) nodes.set(id, node()); return nodes.get(id);},
    querySelectorAll() {return [];}, createElement: node};
  document.getElementById("client").value = "hermes";
  document.getElementById("size").value = "100000";
  const values = {
    document, location: {search, hostname, href: `https://${hostname}/start/${search}`},
    navigator: {clipboard: {async writeText(value) {copied.push(value);}}, ...navigator}, window,
    fetch: async (url, options) => {requests.push({url, options}); return {status: 202};},
    setTimeout: () => 1,
  };
  const prior = new Map(Object.keys(values).map(key => [key, Object.getOwnPropertyDescriptor(globalThis, key)]));
  try {
    for (const [key, value] of Object.entries(values)) Object.defineProperty(globalThis, key, {configurable: true, writable: true, value});
    await import(`../start/app.mjs?privacy-test=${++run}`);
    await check({nodes, requests, copied, async copyConfiguration() {
      const button = nodes.get("copy-config"); button.listeners.click.call(button);
      await new Promise(resolve => setImmediate(resolve));
    }});
  } finally {
    for (const [key, descriptor] of prior) {if (descriptor) Object.defineProperty(globalThis, key, descriptor); else delete globalThis[key];}
  }
}

test("start selects each question without automatic calls and attributes an explicit setup action", async () => {
  for (const task of ["funding", "bank", "exit"]) {
    await withStart({search: `?task=${task}&utm_source=telegram&private=secret`}, async ({nodes, requests, copied, copyConfiguration}) => {
      assert.equal(nodes.get("task-title").textContent, TASKS[task].title);
      assert.equal(requests.length, 0, "page loading must not request research or metrics");
      await copyConfiguration();
      assert.equal(copied.length, 1);
      assert.equal(requests.length, 1);
      assert.equal(requests[0].url, "https://api.liquilens.in/api/events");
      assert.deepEqual(JSON.parse(requests[0].options.body), {surface: "mcp_start", event: `${task}_setup_copied`, source: "telegram"});
    });
  }
});

test("start honors every verification and privacy suppression while copy remains functional", async () => {
  for (const options of [
    {search: "?task=funding&utm_source=x&verification=1"},
    {search: "?task=funding&utm_source=x&privacy_opt_out=1"},
    {search: "?task=funding&privacy_opt_out=0&privacy_opt_out=1"},
    {navigator: {globalPrivacyControl: true}}, {navigator: {doNotTrack: "1"}},
    {window: {doNotTrack: "1"}}, {navigator: {webdriver: true}}, {hostname: "localhost"},
  ]) {
    await withStart(options, async ({requests, copied, copyConfiguration}) => {
      await copyConfiguration();
      assert.equal(copied.length, 1);
      assert.equal(requests.length, 0, JSON.stringify(options));
    });
  }
});

test("start never attributes an ambiguous or arbitrary acquisition label", async () => {
  for (const search of ["?task=bank&utm_source=x&utm_source=telegram", "?task=bank&utm_source=private@example.com"]) {
    await withStart({search}, async ({requests, copyConfiguration}) => {
      await copyConfiguration();
      assert.equal(requests.length, 1);
      assert.equal(JSON.parse(requests[0].options.body).source, "unknown");
    });
  }
});
