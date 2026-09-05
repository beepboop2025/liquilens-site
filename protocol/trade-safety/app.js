(function () {
  "use strict";

  var ALLOWED_EVENTS = {offer_viewed: true, email_clicked: true};

  function track(eventName) {
    if (!Object.prototype.hasOwnProperty.call(ALLOWED_EVENTS, eventName)) return;
    fetch("https://api.liquilens.in/api/events", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({surface: "pilot", event: eventName}),
      keepalive: true
    }).catch(function () {
      // The offer and contact action never depend on measurement succeeding.
    });
  }

  track("offer_viewed");
  document.querySelectorAll("[data-pilot-event]").forEach(function (element) {
    element.addEventListener("click", function () {
      track(element.getAttribute("data-pilot-event"));
    });
  });
}());
