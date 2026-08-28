(function () {
  "use strict";

  var SOURCES = Object.freeze({
    nicegram: true,
    adsgram: true,
    telegram_ads: true,
    x: true,
    web: true,
    organic: true,
    crypto_channel: true,
    operator_rehearsal: true
  });
  var TOPICS = Object.freeze({
    market: true,
    movers: true,
    funding: true,
    defi: true,
    pump: true,
    rails: true,
    paper: true
  });
  var ACTIONS = Object.freeze({ follow: true, share: true });
  var SHARE_COPY = Object.freeze({
    market: "A useful public-data market desk from @LiquiLens: sourced liquidity and financial-stress research, with timestamps and evidence limits.",
    movers: "A useful market-movers view from @LiquiLens: sourced moves with timestamps, context, and clear evidence limits.",
    funding: "Review perpetual funding and positioning context with @LiquiLens: sourced observations, timestamps, and evidence limits.",
    defi: "A sourced DeFi liquidity view from @LiquiLens, with timestamps, context, and explicit evidence limits.",
    pump: "A sober pump-risk research view from @LiquiLens: public signals, timestamps, and evidence limits—not a trading call.",
    rails: "Review stablecoin rail, peg, supply, and tripwire context with @LiquiLens: sourced observations with explicit evidence limits.",
    paper: "Use a public-board paper-risk frame from @LiquiLens: reduce-only context with explicit invalidation, not a trading call."
  });
  var API = "https://api.liquilens.in/api/events";
  var params = new URLSearchParams(window.location.search);

  function select(name, allowed, fallback) {
    var candidates = params.getAll(name);
    var valid = candidates.length === 1 &&
      Object.prototype.hasOwnProperty.call(allowed, candidates[0]);
    return { value: valid ? candidates[0] : fallback, valid: valid };
  }

  var selectedSource = select("from", SOURCES, "operator_rehearsal");
  var selectedTopic = select("topic", TOPICS, "market");
  var selectedAction = select("action", ACTIONS, "follow");
  var source = selectedSource.value;
  var topic = selectedTopic.value;
  var action = selectedAction.value;
  var allInputValid = selectedSource.valid && selectedTopic.valid && selectedAction.valid;
  var returnSource = allInputValid ? source : "operator_rehearsal";

  var followIntent = new URL("https://x.com/intent/follow");
  followIntent.searchParams.set("screen_name", "LiquiLens");

  var telegramReturn = new URL("https://liquilens.in/go/telegram/");
  telegramReturn.searchParams.set("from", returnSource);
  telegramReturn.searchParams.set("topic", topic);

  var shareIntent = new URL("https://x.com/intent/tweet");
  shareIntent.searchParams.set("text", SHARE_COPY[topic]);
  shareIntent.searchParams.set("url", telegramReturn.toString());

  var destination = action === "share" ? shareIntent.toString() : followIntent.toString();
  var link = document.getElementById("continue");
  var detail = document.getElementById("detail");
  link.href = destination;
  link.textContent = action === "share" ? "Open the X composer" : "Open @LiquiLens on X";
  detail.textContent = action === "share"
    ? "Opening a topic-matched draft you control. Nothing is posted automatically."
    : "Opening the official @LiquiLens follow screen. Following remains your choice.";

  var navigated = false;
  function navigate() {
    if (navigated) return;
    navigated = true;
    window.location.replace(destination);
  }

  function deliver(eventName) {
    try {
      var request = fetch(API, {
        method: "POST",
        headers: { "Content-Type": "text/plain;charset=UTF-8" },
        body: JSON.stringify({ surface: "community_growth", event: eventName }),
        keepalive: true
      });
      if (request && typeof request.catch === "function") {
        request.catch(function () {});
      }
    } catch (ignored) {
      // A measurement failure must never interrupt the handoff.
    }
  }

  if (allInputValid && source !== "operator_rehearsal") {
    var eventAction = action === "share" ? "share_composer" : "follow_intent";
    deliver(source + "_x_" + topic + "_" + eventAction + "_redirect");
  }

  window.setTimeout(navigate, 700);
  navigate();
}());
