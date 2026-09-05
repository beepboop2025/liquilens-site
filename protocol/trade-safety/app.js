(function () {
  "use strict";

  var EVENT_SURFACES = {
    mcp_endpoint_copied: "developers",
    openapi_opened: "developers",
    offer_viewed: "pilot",
    email_clicked: "pilot"
  };

  function track(eventName) {
    var surface = EVENT_SURFACES[eventName];
    if (!surface) return;
    fetch("https://api.liquilens.in/api/events", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({surface: surface, event: eventName}),
      keepalive: true
    }).catch(function () {
      // Free evaluation and the optional contact action never depend on measurement.
    });
  }

  document.querySelectorAll("[data-free-copy]").forEach(function (button) {
    button.addEventListener("click", function () {
      navigator.clipboard.writeText(button.getAttribute("data-free-copy") || "")
        .then(function () {
          track(button.getAttribute("data-free-event"));
          button.textContent = "Copied";
        })
        .catch(function () {
          button.textContent = "Select and copy the endpoint below";
        });
    });
  });

  document.querySelectorAll("a[data-free-event]").forEach(function (link) {
    link.addEventListener("click", function () {
      track(link.getAttribute("data-free-event"));
    });
  });

  document.querySelectorAll("[data-pilot-event]").forEach(function (element) {
    element.addEventListener("click", function () {
      track(element.getAttribute("data-pilot-event"));
    });
  });

  var offer = document.getElementById("protected-route-pilot");
  if (offer && "IntersectionObserver" in window) {
    var observer = new IntersectionObserver(function (entries) {
      if (entries.some(function (entry) { return entry.isIntersecting; })) {
        track("offer_viewed");
        observer.disconnect();
      }
    });
    observer.observe(offer);
  }
}());
