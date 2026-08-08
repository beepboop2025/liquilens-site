(function () {
  "use strict";

  document.querySelectorAll("[data-funnel]").forEach(function (element) {
    element.addEventListener("click", function () {
      fetch("https://api.liquilens.in/api/events", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          surface: "homepage",
          event: element.getAttribute("data-funnel")
        }),
        keepalive: true
      }).catch(function () {
        // Navigation and conversion never depend on analytics.
      });
    });
  });
}());
