(function () {
  "use strict";

  var MCP_URL = "https://api.liquilens.in/mcp";
  var MCP_PROTOCOL_VERSION = "2026-07-28";
  var MAX_MCP_RESPONSE_BYTES = 1024 * 1024;

  function boundedJson(response) {
    var declared = response.headers.get("content-length");
    if (declared !== null) {
      if (!/^\d+$/.test(declared) || Number(declared) > MAX_MCP_RESPONSE_BYTES) {
        throw new Error("response exceeded the 1 MiB display limit");
      }
    }
    if (!response.body || typeof response.body.getReader !== "function") {
      throw new Error("this browser cannot safely stream the response");
    }

    var reader = response.body.getReader();
    var chunks = [];
    var received = 0;

    function consume(part) {
      if (part.done) {
        var body = new Uint8Array(received);
        var offset = 0;
        chunks.forEach(function (chunk) {
          body.set(chunk, offset);
          offset += chunk.byteLength;
        });
        return JSON.parse(new TextDecoder("utf-8", {fatal: true}).decode(body));
      }
      received += part.value.byteLength;
      if (received > MAX_MCP_RESPONSE_BYTES) {
        reader.cancel().catch(function () {});
        throw new Error("response exceeded the 1 MiB display limit");
      }
      chunks.push(part.value);
      return reader.read().then(consume);
    }

    return reader.read().then(consume);
  }

  function track(eventName) {
    fetch("https://api.liquilens.in/api/events", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({surface: "developers", event: eventName}),
      keepalive: true
    }).catch(function () {
      // Product use must never depend on measurement succeeding.
    });
  }

  function pulse(button, label) {
    var old = button.textContent;
    button.textContent = label;
    window.setTimeout(function () { button.textContent = old; }, 1400);
  }

  document.querySelectorAll("[data-copy]").forEach(function (button) {
    button.addEventListener("click", function () {
      var eventName = button.getAttribute("data-event");
      Promise.resolve().then(function () {
        return navigator.clipboard.writeText(button.getAttribute("data-copy") || "");
      })
        .then(function () {
          if (eventName) track(eventName);
          pulse(button, "copied");
        })
        .catch(function () { pulse(button, "select + copy"); });
    });
  });

  document.querySelectorAll("a[data-event]").forEach(function (link) {
    link.addEventListener("click", function () {
      track(link.getAttribute("data-event"));
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
    var controller = new AbortController();
    var timeout = window.setTimeout(function () { controller.abort(); }, 12000);
    button.disabled = true;
    // This existing event records an attempt, never a completed agent call.
    track("live_tool_run");
    output.dataset.state = "loading";
    output.textContent = "Calling failure_radar_board…";
    fetch(MCP_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
        "Mcp-Method": "tools/call",
        "Mcp-Name": "failure_radar_board"
      },
      signal: controller.signal,
      body: JSON.stringify({jsonrpc: "2.0", id: 1, method: "tools/call",
        params: {
          name: "failure_radar_board",
          arguments: {},
          _meta: {
            "io.modelcontextprotocol/protocolVersion": MCP_PROTOCOL_VERSION,
            "io.modelcontextprotocol/clientInfo": {
              name: "liquilens-developer-page",
              version: "1.8.0"
            },
            "io.modelcontextprotocol/clientCapabilities": {}
          }
        }})
    })
      .then(function (response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return boundedJson(response);
      })
      .then(function (message) {
        if (!message || message.jsonrpc !== "2.0" || message.id !== 1 || message.error) {
          throw new Error("MCP rejected the request or returned an invalid response");
        }
        var result = message.result;
        if (!result || (result.isError !== undefined && result.isError !== false)) {
          throw new Error("the MCP tool returned an error");
        }
        var value = result.structuredContent;
        if (!value) {
          var content = result.content || [];
          if (content.length !== 1 || content[0].type !== "text") {
            throw new Error("the MCP tool returned no evidence object");
          }
          value = JSON.parse(content[0].text);
        }
        if (!value || typeof value !== "object" || Array.isArray(value) ||
            value.status === "FAILED" || value.status === "error") {
          throw new Error("the MCP tool returned no valid evidence object");
        }
        var unavailable = value.ok === false || value.status === "unavailable";
        output.dataset.state = unavailable ? "unavailable" : "received";
        output.textContent = (unavailable ? "Evidence unavailable — read the returned reason.\n\n" :
          "Evidence received — check its dates, coverage and limitations.\n\n") +
          JSON.stringify(value, null, 2);
      })
      .catch(function (error) {
        output.dataset.state = "error";
        output.textContent = error.name === "AbortError"
          ? "Live call timed out after 12 seconds"
          : "Live call failed: " + error.message;
      })
      .finally(function () {
        window.clearTimeout(timeout);
        button.disabled = false;
      });
  });
}());
