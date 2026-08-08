(function () {
  "use strict";

  function track(eventName) {
    fetch("https://api.liquilens.in/api/events", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({surface: "pilot", event: eventName}),
      keepalive: true
    }).catch(function () {
      // Measurement must never delay or block the buyer's action.
    });
  }

  track("offer_viewed");
  document.querySelectorAll("[data-event]").forEach(function (element) {
    element.addEventListener("click", function () {
      track(element.getAttribute("data-event"));
    });
  });
}());
