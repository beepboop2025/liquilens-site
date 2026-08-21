(function () {
  "use strict";

  if (window.__liquilensAiReferralSent || !document.referrer) return;

  var host;
  try {
    host = new URL(document.referrer).hostname.toLowerCase().replace(/\.$/, "");
  } catch (_error) {
    return;
  }

  function isHost(domain) {
    return host === domain || host.endsWith("." + domain);
  }

  var source = null;
  if (isHost("chatgpt.com") || isHost("chat.openai.com")) {
    source = "chatgpt";
  } else if (isHost("perplexity.ai")) {
    source = "perplexity";
  } else if (isHost("claude.ai")) {
    source = "claude";
  } else if (isHost("gemini.google.com")) {
    source = "gemini";
  } else if (isHost("copilot.microsoft.com")) {
    source = "copilot";
  } else if (
    isHost("meta.ai") ||
    isHost("mistral.ai") ||
    isHost("phind.com") ||
    isHost("poe.com") ||
    isHost("you.com")
  ) {
    source = "other_ai";
  }

  if (!source) return;
  window.__liquilensAiReferralSent = true;

  fetch("https://api.liquilens.in/api/events", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({surface: "ai_referral", event: source}),
    keepalive: true
  }).catch(function () {
    // Attribution must never affect the page or navigation.
  });
}());
