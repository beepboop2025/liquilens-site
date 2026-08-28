(function () {
  "use strict";

  var SHORT_SOURCE = Object.freeze({
    nicegram: "ng",
    adsgram: "ag",
    telegram_ads: "tg",
    x: "xr",
    web: "wb",
    organic: "or",
    crypto_channel: "ch",
    operator_rehearsal: "qa"
  });
  var TOPIC_INTENT = Object.freeze({
    market: "market",
    movers: "movers",
    funding: "derivatives",
    defi: "defi",
    pump: "pump",
    rails: "rails",
    paper: "paper"
  });
  var TOPIC_LABEL = Object.freeze({
    market: "market desk",
    movers: "market movers",
    funding: "funding view",
    defi: "DeFi view",
    pump: "pump-risk view",
    rails: "stablecoin rails view",
    paper: "paper-risk frame"
  });
  var API = "https://api.liquilens.in/api/events";
  var params = new URLSearchParams(window.location.search);

  function select(name, allowed, fallback) {
    var candidates = params.getAll(name);
    var valid = candidates.length === 1 &&
      Object.prototype.hasOwnProperty.call(allowed, candidates[0]);
    return { value: valid ? candidates[0] : fallback, valid: valid };
  }

  var selectedSource = select("from", SHORT_SOURCE, "operator_rehearsal");
  var selectedTopic = select("topic", TOPIC_INTENT, "market");
  var allInputValid = selectedSource.valid && selectedTopic.valid;
  var source = allInputValid ? selectedSource.value : "operator_rehearsal";
  var topic = selectedTopic.value;
  var start = "x26_crypto_" + SHORT_SOURCE[source] + "_" + TOPIC_INTENT[topic];
  var destination = "https://t.me/liquilens_crypto_bot?start=" + encodeURIComponent(start);

  var link = document.getElementById("continue");
  var detail = document.getElementById("detail");
  link.href = destination;
  link.textContent = "Open the " + TOPIC_LABEL[topic] + " in Telegram";
  detail.textContent = "Continue to a useful, topic-matched LiquiLens bot view.";

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
    deliver("x_return_telegram_" + source + "_" + topic + "_redirect");
  }

  window.setTimeout(navigate, 700);
  navigate();
}());
