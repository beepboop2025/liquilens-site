(function () {
  "use strict";

  var EVENT_SOURCE = Object.freeze({
    nicegram: "nicegram",
    adsgram: "adsgram",
    telegram_ads: "telegram_ads",
    x: "x_return",
    web: "web",
    organic: "organic",
    crypto_channel: "crypto_channel",
    operator_rehearsal: null
  });
  var PROFILE = "https://x.com/LiquiLens";
  var API = "https://api.liquilens.in/api/events";
  var params = new URLSearchParams(window.location.search);
  var requestedSource = params.get("from") || "organic";
  var source = Object.prototype.hasOwnProperty.call(EVENT_SOURCE, requestedSource)
    ? requestedSource
    : "organic";
  var action = params.get("action") === "share" ? "share" : "profile";

  var composer = new URL("https://twitter.com/intent/tweet");
  composer.searchParams.set(
    "text",
    "A useful public-data desk from @LiquiLens: sourced liquidity and financial-stress research, with timestamps and evidence limits."
  );
  composer.searchParams.set(
    "url",
    "https://t.me/liquilens_crypto_bot?start=x26_crypto_share_market"
  );

  var destination = action === "share" ? composer.toString() : PROFILE;
  var link = document.getElementById("continue");
  var detail = document.getElementById("detail");
  link.href = destination;
  link.textContent = action === "share" ? "Open the X composer" : "Continue to X";
  detail.textContent = action === "share"
    ? "Opening a draft you control. Nothing is posted automatically."
    : "Opening the @LiquiLens profile. Following remains your choice.";

  var navigated = false;
  function navigate() {
    if (navigated) return;
    navigated = true;
    window.location.replace(destination);
  }

  var eventPrefix = EVENT_SOURCE[source];
  var eventName = eventPrefix
    ? eventPrefix + "_x_" + (action === "share" ? "share_composer" : "profile") + "_redirect"
    : null;
  var delivery = eventName
    ? fetch(API, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ surface: "community_growth", event: eventName }),
        keepalive: true
      }).catch(function () {})
    : Promise.resolve();

  Promise.race([
    delivery,
    new Promise(function (resolve) { window.setTimeout(resolve, 180); })
  ]).then(navigate);
  window.setTimeout(navigate, 700);
}());
