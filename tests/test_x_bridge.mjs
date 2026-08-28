import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";


const X_SCRIPT = await readFile(new URL("../go/x/app.js", import.meta.url), "utf8");
const TELEGRAM_SCRIPT = await readFile(
  new URL("../go/telegram/app.js", import.meta.url),
  "utf8",
);
const SOURCES = [
  "nicegram",
  "adsgram",
  "telegram_ads",
  "x",
  "web",
  "organic",
  "crypto_channel",
];
const TOPICS = ["market", "movers", "funding", "defi", "pump", "rails", "paper"];


async function runBridge(script, search, fetchMode = "resolve") {
  const posts = [];
  const redirects = [];
  const timers = [];
  const elements = {
    continue: { href: "", textContent: "" },
    detail: { textContent: "" },
  };

  function mockFetch(url, options) {
    posts.push({ url, options });
    if (fetchMode === "throw") throw new Error("synchronous analytics failure");
    if (fetchMode === "reject") return Promise.reject(new Error("analytics rejected"));
    if (fetchMode === "hang") return new Promise(() => {});
    return Promise.resolve({ status: 202 });
  }

  const window = {
    location: {
      search,
      replace(destination) { redirects.push(destination); },
    },
    setTimeout(callback, milliseconds) {
      timers.push(callback);
      return milliseconds;
    },
  };
  const context = vm.createContext({
    URL,
    URLSearchParams,
    window,
    document: {
      getElementById(id) { return elements[id]; },
    },
    fetch: mockFetch,
  });

  vm.runInContext(script, context);
  await new Promise((resolve) => setImmediate(resolve));
  return {
    elements,
    posts,
    redirects,
    runTimers() { timers.forEach((callback) => callback()); },
  };
}


function postedEvent(result) {
  assert.equal(result.posts.length, 1);
  const post = result.posts[0];
  assert.equal(post.url, "https://api.liquilens.in/api/events");
  assert.equal(post.options.method, "POST");
  assert.equal(post.options.headers["Content-Type"], "text/plain;charset=UTF-8");
  assert.equal(post.options.keepalive, true);
  assert.ok(Buffer.byteLength(post.options.body, "utf8") <= 512);
  return JSON.parse(post.options.body);
}


test("follow uses the official X intent and emits one bounded event", async () => {
  const result = await runBridge(
    X_SCRIPT,
    "?from=nicegram&topic=market&action=follow",
  );

  assert.deepEqual(result.redirects, ["https://x.com/intent/follow?screen_name=LiquiLens"]);
  assert.equal(result.elements.continue.href, result.redirects[0]);
  assert.deepEqual(postedEvent(result), {
    surface: "community_growth",
    event: "nicegram_x_market_follow_intent_redirect",
  });
  result.runTimers();
  result.runTimers();
  assert.equal(result.redirects.length, 1);
});


test("every share topic gets fixed truthful copy and a first-party return URL", async () => {
  const copySignals = new Map([
    ["market", "public-data market desk"],
    ["movers", "market-movers view"],
    ["funding", "perpetual funding and positioning"],
    ["defi", "DeFi liquidity view"],
    ["pump", "not a trading call"],
    ["rails", "stablecoin rail, peg, supply, and tripwire"],
    ["paper", "public-board paper-risk frame"],
  ]);

  for (const topic of TOPICS) {
    const result = await runBridge(
      X_SCRIPT,
      `?from=crypto_channel&topic=${topic}&action=share`,
    );
    const destination = new URL(result.redirects[0]);
    assert.equal(destination.origin + destination.pathname, "https://x.com/intent/tweet");
    assert.match(destination.searchParams.get("text"), /@LiquiLens/);
    assert.ok(destination.searchParams.get("text").includes(copySignals.get(topic)));
    assert.equal(
      destination.searchParams.get("url"),
      `https://liquilens.in/go/telegram/?from=crypto_channel&topic=${topic}`,
    );
    assert.deepEqual(postedEvent(result), {
      surface: "community_growth",
      event: `crypto_channel_x_${topic}_share_composer_redirect`,
    });
    assert.match(result.elements.detail.textContent, /Nothing is posted automatically/);
  }
});


test("all reviewed outbound enums resolve to the API allowlist contract", async () => {
  for (const source of SOURCES) {
    for (const topic of TOPICS) {
      for (const [action, eventAction] of [
        ["follow", "follow_intent"],
        ["share", "share_composer"],
      ]) {
        const result = await runBridge(
          X_SCRIPT,
          `?from=${source}&topic=${topic}&action=${action}`,
        );
        assert.deepEqual(postedEvent(result), {
          surface: "community_growth",
          event: `${source}_x_${topic}_${eventAction}_redirect`,
        });
      }
    }
  }
});


test("operator and malformed outbound input navigate but never count", async () => {
  const cases = [
    "",
    "?from=nicegram&topic=market",
    "?from=nicegram&topic=market&action=unknown",
    "?from=unknown&topic=market&action=share",
    "?from=nicegram&topic=unknown&action=share",
    "?from=nicegram&from=web&topic=market&action=share",
    "?from=nicegram&topic=market&topic=movers&action=share",
    "?from=nicegram&topic=market&action=share&action=follow",
    "?from=operator_rehearsal&topic=market&action=share",
  ];

  for (const search of cases) {
    const result = await runBridge(X_SCRIPT, search);
    assert.equal(result.posts.length, 0, search);
    assert.equal(result.redirects.length, 1, search);
    const destination = new URL(result.redirects[0]);
    if (destination.pathname === "/intent/tweet") {
      const returnUrl = new URL(destination.searchParams.get("url"));
      assert.equal(returnUrl.searchParams.get("from"), "operator_rehearsal", search);
    } else {
      assert.equal(destination.toString(), "https://x.com/intent/follow?screen_name=LiquiLens");
    }
  }
});


test("analytics failure or latency cannot delay or duplicate X navigation", async () => {
  for (const fetchMode of ["resolve", "reject", "hang", "throw"]) {
    const result = await runBridge(
      X_SCRIPT,
      "?from=organic&topic=paper&action=follow",
      fetchMode,
    );
    assert.equal(result.redirects.length, 1, fetchMode);
    result.runTimers();
    result.runTimers();
    assert.equal(result.redirects.length, 1, fetchMode);
  }
});


test("every X return maps to the exact useful Telegram start reference", async () => {
  const shortSource = new Map([
    ["nicegram", "ng"],
    ["adsgram", "ag"],
    ["telegram_ads", "tg"],
    ["x", "xr"],
    ["web", "wb"],
    ["organic", "or"],
    ["crypto_channel", "ch"],
  ]);
  const intent = new Map([
    ["market", "market"],
    ["movers", "movers"],
    ["funding", "derivatives"],
    ["defi", "defi"],
    ["pump", "pump"],
    ["rails", "rails"],
    ["paper", "paper"],
  ]);

  for (const source of SOURCES) {
    for (const topic of TOPICS) {
      const result = await runBridge(
        TELEGRAM_SCRIPT,
        `?from=${source}&topic=${topic}`,
      );
      const destination = new URL(result.redirects[0]);
      const start = destination.searchParams.get("start");
      assert.equal(destination.origin + destination.pathname, "https://t.me/liquilens_crypto_bot");
      assert.equal(start, `x26_crypto_${shortSource.get(source)}_${intent.get(topic)}`);
      assert.ok(Buffer.byteLength(start, "utf8") <= 64);
      assert.deepEqual(postedEvent(result), {
        surface: "community_growth",
        event: `x_return_telegram_${source}_${topic}_redirect`,
      });
    }
  }
});


test("operator and malformed returns fall closed to qa without an event", async () => {
  const cases = [
    ["", "x26_crypto_qa_market"],
    ["?from=nicegram", "x26_crypto_qa_market"],
    ["?topic=funding", "x26_crypto_qa_derivatives"],
    ["?from=unknown&topic=funding", "x26_crypto_qa_derivatives"],
    ["?from=nicegram&topic=unknown", "x26_crypto_qa_market"],
    ["?from=nicegram&from=web&topic=market", "x26_crypto_qa_market"],
    ["?from=nicegram&topic=market&topic=paper", "x26_crypto_qa_market"],
    ["?from=operator_rehearsal&topic=paper", "x26_crypto_qa_paper"],
  ];

  for (const [search, expectedStart] of cases) {
    const result = await runBridge(TELEGRAM_SCRIPT, search);
    assert.equal(result.posts.length, 0, search);
    const start = new URL(result.redirects[0]).searchParams.get("start");
    assert.equal(start, expectedStart, search);
    assert.ok(Buffer.byteLength(start, "utf8") <= 64, search);
  }
});


test("analytics failure or latency cannot delay or duplicate Telegram navigation", async () => {
  for (const fetchMode of ["resolve", "reject", "hang", "throw"]) {
    const result = await runBridge(
      TELEGRAM_SCRIPT,
      "?from=x&topic=movers",
      fetchMode,
    );
    assert.equal(result.redirects.length, 1, fetchMode);
    result.runTimers();
    result.runTimers();
    assert.equal(result.redirects.length, 1, fetchMode);
  }
});
