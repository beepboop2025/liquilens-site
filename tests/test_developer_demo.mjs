import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import test from "node:test";
import vm from "node:vm";

const script = readFileSync(new URL("../developers/app.js", import.meta.url), "utf8");
const flush = () => new Promise(resolve => setImmediate(resolve));

function environment({message, copyFails = false, httpFails = false} = {}) {
  const events = [];
  const elements = {};
  function element(attributes = {}) {
    return {textContent: "", dataset: {}, disabled: false, classList: {add() {}},
      getAttribute(name) {return attributes[name];},
      addEventListener(name, fn) {this[name] = fn;}};
  }
  for (const id of ["runTool", "toolResult", "healthDot", "healthText"]) elements[id] = element();
  const copy = element({"data-copy": "https://api.liquilens.in/mcp", "data-event": "mcp_endpoint_copied"});
  const context = {
    document: {querySelectorAll(selector) {return selector === "[data-copy]" ? [copy] : [];},
      getElementById(id) {return elements[id];}},
    navigator: {clipboard: {writeText: () => copyFails ? Promise.reject(new Error("denied")) : Promise.resolve()}},
    window: {setTimeout() {return 1;}, clearTimeout() {}},
    AbortController, TextDecoder, Uint8Array, Promise, JSON,
    async fetch(url, options = {}) {
      if (url.endsWith("/api/events")) {events.push(JSON.parse(options.body)); return {};}
      if (url.includes("/api/health")) return {ok: true, json: async () => ({})};
      const raw = new TextEncoder().encode(JSON.stringify(message));
      let supplied = false;
      return {ok: !httpFails, status: httpFails ? 429 : 200,
        headers: {get() {return null;}}, body: {getReader() {return {
          async read() {if (supplied) return {done: true}; supplied = true; return {done: false, value: raw};},
          async cancel() {},
        };}}};
    },
  };
  vm.runInNewContext(script, context);
  return {elements, copy, events};
}

test("copy events require a successful clipboard write", async () => {
  for (const copyFails of [false, true]) {
    const env = environment({copyFails});
    env.copy.click();
    assert.equal(env.events.length, 0);
    await flush();
    assert.equal(env.events.length, copyFails ? 0 : 1);
    assert.equal(env.copy.textContent, copyFails ? "select + copy" : "copied");
  }
});

test("RPC, tool, HTTP and malformed result failures are visibly errors", async () => {
  for (const options of [
    {message: {jsonrpc: "2.0", id: 1, error: {code: -32000}}},
    {message: {jsonrpc: "2.0", id: 1, result: {isError: true, structuredContent: {value: 42}}}},
    {message: {jsonrpc: "2.0", id: 7, result: {structuredContent: {value: 42}}}},
    {message: {jsonrpc: "2.0", id: 1, result: {content: []}}},
    {message: {jsonrpc: "2.0", id: 1, result: {structuredContent: {status: "FAILED"}}}},
    {message: {}, httpFails: true},
  ]) {
    const env = environment(options);
    env.elements.runTool.click();
    await flush();
    assert.equal(env.elements.toolResult.dataset.state, "error");
    assert.match(env.elements.toolResult.textContent, /^Live call failed:/);
    assert.equal(env.elements.runTool.disabled, false);
    assert.deepEqual(env.events, [{surface: "developers", event: "live_tool_run"}]);
  }
});

test("received and unavailable evidence retain their dates and limits", async () => {
  for (const ok of [true, false]) {
    const evidence = {ok, asof: "2026-01-02", caveats: ["Historical evidence"]};
    const env = environment({message: {jsonrpc: "2.0", id: 1, result: {structuredContent: evidence}}});
    env.elements.runTool.click();
    await flush();
    assert.equal(env.elements.toolResult.dataset.state, ok ? "received" : "unavailable");
    assert.match(env.elements.toolResult.textContent, /2026-01-02/);
    assert.match(env.elements.toolResult.textContent, /Historical evidence/);
  }
});
