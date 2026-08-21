(function () {
  "use strict";

  var EVENT_ENDPOINT = "https://api.liquilens.in/api/events";
  var controls = Array.prototype.slice.call(
    document.querySelectorAll('input[name="control"]')
  );
  var labels = {};
  controls.forEach(function (control) {
    labels[control.value] = control.closest("label").querySelector("strong").textContent;
  });

  function track(eventName) {
    fetch(EVENT_ENDPOINT, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({surface: "coverage_check", event: eventName}),
      keepalive: true
    }).catch(function () {
      // The assessment must remain usable when measurement is unavailable.
    });
  }

  function resultFor(count) {
    if (count <= 3) {
      return {
        title: "Fragmented evidence",
        summary: "The process may find useful signals, but it will be hard to reconstruct what was knowable or distinguish a dark lens from a calm one."
      };
    }
    if (count <= 7) {
      return {
        title: "Partly controlled",
        summary: "Core monitoring exists. The unchecked controls are where false calm, hindsight leakage or avoidable review work can enter."
      };
    }
    if (count <= 10) {
      return {
        title: "Review-ready foundation",
        summary: "The workflow covers most of the evidence chain. Close the remaining gaps before treating it as a repeatable control."
      };
    }
    return {
      title: "Checklist-complete",
      summary: "All twelve workflow controls are represented. This is still not evidence that the data, model or policy is valid—test those separately."
    };
  }

  function uncheckedLabels() {
    return controls.filter(function (control) {
      return !control.checked;
    }).map(function (control) {
      return labels[control.value];
    });
  }

  function render() {
    var count = controls.filter(function (control) { return control.checked; }).length;
    var result = resultFor(count);
    var gaps = uncheckedLabels();
    document.getElementById("score").textContent = String(count);
    document.getElementById("resultTitle").textContent = result.title;
    document.getElementById("summary").textContent = result.summary;
    document.getElementById("meter").style.width = String((count / controls.length) * 100) + "%";

    var gapList = document.getElementById("gapList");
    gapList.textContent = "";
    (gaps.length ? gaps.slice(0, 3) : ["No checklist gaps. Validate data quality, performance and local policy next."])
      .forEach(function (gap) {
        var item = document.createElement("li");
        item.textContent = gap;
        gapList.appendChild(item);
      });
  }

  function reportText() {
    var count = controls.filter(function (control) { return control.checked; }).length;
    var result = resultFor(count);
    var gaps = uncheckedLabels();
    var priority = gaps.length ? gaps.slice(0, 3) : [
      "No checklist gaps; validate data quality, performance and local policy next."
    ];
    return [
      "LiquiLens — Bank Early-Warning System Coverage Check",
      "Coverage: " + count + "/12 — " + result.title,
      "",
      result.summary,
      "",
      "Priority gaps:",
      priority.map(function (gap, index) { return (index + 1) + ". " + gap; }).join("\n"),
      "",
      "Boundary: process self-assessment only; not a credit rating, model validation or prediction of failure.",
      "https://liquilens.in/tools/ews-coverage-check/"
    ].join("\n");
  }

  function say(message) {
    var status = document.getElementById("status");
    status.textContent = message;
    window.setTimeout(function () { status.textContent = ""; }, 2200);
  }

  controls.forEach(function (control) {
    control.addEventListener("change", render);
  });

  document.getElementById("copyReport").addEventListener("click", function () {
    navigator.clipboard.writeText(reportText()).then(function () {
      track("report_copied");
      say("Gap report copied");
    }).catch(function () {
      say("Copy blocked — use Print instead");
    });
  });

  document.getElementById("printReport").addEventListener("click", function () {
    track("report_printed");
    window.print();
  });

  document.getElementById("accessCta").addEventListener("click", function () {
    track("access_cta_clicked");
  });

  track("tool_viewed");
  render();
}());
