(function () {
  "use strict";

  var MCP_URL = "https://api.liquilens.in/mcp";

  function pulse(button, label) {
    var old = button.textContent;
    button.textContent = label;
    window.setTimeout(function () { button.textContent = old; }, 1400);
  }

  document.querySelectorAll("[data-copy]").forEach(function (button) {
    button.addEventListener("click", function () {
      navigator.clipboard.writeText(button.getAttribute("data-copy") || "")
        .then(function () { pulse(button, "copied"); })
        .catch(function () { pulse(button, "select + copy"); });
    });
  });

  fetch("https://api.liquilens.in/api/health?source=developers")
    .then(function (response) {
      if (!response.ok) throw new Error("HTTP " + response.status);
      return response.json();
    })
    .then(function () {
      document.getElementById("healthDot").classList.add("ok");
      document.getElementById("healthText").textContent = "public API live";
    })
    .catch(function () {
      document.getElementById("healthText").textContent =
        "status check unavailable · endpoint details remain below";
    });

  document.getElementById("runTool").addEventListener("click", function () {
    var button = this;
    var output = document.getElementById("toolResult");
    button.disabled = true;
    output.textContent = "Calling failure_radar_board…";
    fetch(MCP_URL, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({jsonrpc: "2.0", id: 1, method: "tools/call",
        params: {name: "failure_radar_board", arguments: {}}})
    })
      .then(function (response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (message) {
        var result = message.result || {};
        var value = result.structuredContent ||
          ((result.content || [])[0] || {}).text || message;
        output.textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
      })
      .catch(function (error) { output.textContent = "Live call failed: " + error.message; })
      .finally(function () { button.disabled = false; });
  });
}());
