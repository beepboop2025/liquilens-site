import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";


const SCRIPT = await readFile(new URL("../go/x/app.js", import.meta.url), "utf8");


async function runBridge(search) {
  let posted;
  let redirected;
  const elements = {
    continue: { href: "", textContent: "" },
    detail: { textContent: "" },
  };
  const window = {
    location: {
      search,
      replace(destination) { redirected = destination; },
    },
    setTimeout(callback, milliseconds) {
      queueMicrotask(callback);
      return milliseconds;
    },
  };
  const context = vm.createContext({
    URL,
    URLSearchParams,
    Promise,
    window,
    document: {
      getElementById(id) { return elements[id]; },
    },
    fetch: async (url, options) => {
      posted = { url, options };
      return { status: 202 };
    },
  });

  vm.runInContext(SCRIPT, context);
  await new Promise((resolve) => setImmediate(resolve));
  return { elements, posted, redirected };
}


test("Nicegram profile handoff sends one bounded event then opens @LiquiLens", async () => {
  const result = await runBridge("?from=nicegram&action=profile");

  assert.equal(result.redirected, "https://x.com/LiquiLens");
  assert.equal(result.posted.url, "https://api.liquilens.in/api/events");
  assert.deepEqual(JSON.parse(result.posted.options.body), {
    surface: "community_growth",
    event: "nicegram_x_profile_redirect",
  });
  assert.equal(result.posted.options.keepalive, true);
});


test("channel share handoff opens a user-controlled X draft", async () => {
  const result = await runBridge("?from=crypto_channel&action=share");
  const destination = new URL(result.redirected);

  assert.equal(destination.origin + destination.pathname, "https://twitter.com/intent/tweet");
  assert.match(destination.searchParams.get("text"), /@LiquiLens/);
  assert.equal(
    destination.searchParams.get("url"),
    "https://t.me/liquilens_crypto_bot?start=x26_crypto_share_market",
  );
  assert.deepEqual(JSON.parse(result.posted.options.body), {
    surface: "community_growth",
    event: "crypto_channel_x_share_composer_redirect",
  });
  assert.match(result.elements.detail.textContent, /Nothing is posted automatically/);
});


test("unknown input is organic and operator rehearsals do not emit events", async () => {
  const unknown = await runBridge("?from=unbounded-user-input&action=anything");
  assert.deepEqual(JSON.parse(unknown.posted.options.body), {
    surface: "community_growth",
    event: "organic_x_profile_redirect",
  });

  const rehearsal = await runBridge("?from=operator_rehearsal&action=profile");
  assert.equal(rehearsal.posted, undefined);
  assert.equal(rehearsal.redirected, "https://x.com/LiquiLens");
});


test("every reviewed source and action resolves to the API allowlist shape", async () => {
  const sources = new Map([
    ["nicegram", "nicegram"],
    ["adsgram", "adsgram"],
    ["telegram_ads", "telegram_ads"],
    ["x", "x_return"],
    ["web", "web"],
    ["organic", "organic"],
    ["crypto_channel", "crypto_channel"],
  ]);
  for (const [source, eventPrefix] of sources) {
    for (const [action, eventAction] of [
      ["profile", "profile"],
      ["share", "share_composer"],
    ]) {
      const result = await runBridge(`?from=${source}&action=${action}`);
      const body = JSON.parse(result.posted.options.body);
      assert.equal(body.surface, "community_growth");
      assert.equal(body.event, `${eventPrefix}_x_${eventAction}_redirect`);
    }
  }
});
