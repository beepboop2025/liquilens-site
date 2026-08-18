(function () {
  "use strict";

  var INDIA_BOARD_URL = "https://api.liquilens.in/api/failure-radar/board";
  var US_BOARD_URL = "https://api.liquilens.in/api/us-radar/board";
  var REVIEW_URL = "https://api.liquilens.in/api/failure-radar/review/";
  var GAUGE_URL = "https://api.seiche.info/api/gauge";
  var WATCH_TIERS = {red: true, orange: true, yellow: true};

  function text(id, value) {
    var node = document.getElementById(id);
    if (node) node.textContent = value;
  }

  function json(url) {
    return fetch(url, {headers: {Accept: "application/json"}}).then(function (res) {
      if (!res.ok) throw new Error("HTTP " + res.status);
      return res.json();
    });
  }

  function indiaWatch(board) {
    var rows = Array.isArray(board && board.rows) ? board.rows : [];
    return rows.filter(function (row) {
      return WATCH_TIERS[row.tier] === true;
    }).slice(0, 8);
  }

  function usWatch(board) {
    var rows = Array.isArray(board && board.board) ? board.board : [];
    return rows.slice(0, 8);
  }

  function coverLine(india, us, indiaWatchRows, usWatchRows) {
    var parts = [];
    if (india && Array.isArray(india.rows)) {
      parts.push(india.rows.length + " India names as of " + (india.as_of || "?"));
    }
    if (us && Array.isArray(us.board)) {
      var scored = us.universe && us.universe.banks_scored
        ? us.universe.banks_scored + " FDIC banks scored"
        : "US board";
      parts.push(scored + ", " + us.board.length + " served as of " + (us.as_of || "?"));
    }
    var watch = (indiaWatchRows ? indiaWatchRows.length : 0)
      + (usWatchRows ? usWatchRows.length : 0);
    if (!parts.length) {
      return "Neither public board answered. No stale pack is shown.";
    }
    return parts.join("; ") + ". " + watch + " names sit on the sample watch slice.";
  }

  function addName(list, market, label, detail) {
    var item = document.createElement("li");
    var tier = document.createElement("span");
    tier.className = "tier";
    tier.textContent = market;
    var body = document.createElement("span");
    body.textContent = label + (detail ? " · " + detail : "");
    item.appendChild(tier);
    item.appendChild(body);
    list.appendChild(item);
  }

  function renderWatch(indiaRows, usRows) {
    var list = document.getElementById("watchList");
    list.innerHTML = "";
    indiaRows.forEach(function (row) {
      var signals = Array.isArray(row.signals_fired) ? row.signals_fired.join(", ") : "";
      addName(list, "IN " + (row.tier || "n/a"), row.name || row.slug || "unnamed", signals);
    });
    usRows.forEach(function (row) {
      var score = row.undertow_score_v02 == null ? "" : "score " + row.undertow_score_v02;
      addName(list, "US cert " + (row.cert || "?"), row.bank || "unnamed", score);
    });
    if (!indiaRows.length && !usRows.length) {
      text("watchFine", "No watch names returned. Quiet is a reading too.");
      return;
    }
    text("watchFine", "Copied from the public boards. The pack does not re-score.");
  }

  function renderDark(packets) {
    var list = document.getElementById("darkList");
    list.innerHTML = "";
    var shown = 0;
    packets.forEach(function (packet) {
      if (!packet || packet.status !== "covered") return;
      var dark = packet.coverage && Array.isArray(packet.coverage.dark_lenses)
        ? packet.coverage.dark_lenses : [];
      dark.slice(0, 2).forEach(function (lens) {
        var item = document.createElement("li");
        var name = packet.entity && packet.entity.name ? packet.entity.name : "name";
        item.textContent = name + ": " + (lens.lens || "lens") + " · " + (lens.reason || "unspecified");
        list.appendChild(item);
        shown += 1;
      });
    });
    if (!shown) {
      var empty = document.createElement("li");
      empty.textContent = "No dark-lens rows returned on the fetched India packets. US rows have no review-packet dark lenses.";
      list.appendChild(empty);
    }
  }

  function renderGauge(gauge) {
    if (!gauge || !gauge.regime) {
      text("plumbingLine", "Seiche did not answer. Absence is not calm.");
      return;
    }
    var tell = typeof gauge.tell === "number" ? " · Tell " + (gauge.tell > 0 ? "+" : "") + Math.round(gauge.tell) : "";
    text("plumbingLine", "Seiche " + gauge.regime + " " + (gauge.index == null ? "?" : gauge.index) + "/100" + tell + ".");
  }

  Promise.allSettled([
    json(INDIA_BOARD_URL),
    json(US_BOARD_URL),
    json(GAUGE_URL)
  ]).then(function (results) {
    var india = results[0].status === "fulfilled" ? results[0].value : null;
    var us = results[1].status === "fulfilled" ? results[1].value : null;
    var gauge = results[2].status === "fulfilled" ? results[2].value : null;
    if ((!india || !Array.isArray(india.rows)) && (!us || !Array.isArray(us.board))) {
      text("packStatus", "The public boards did not answer. No stale pack is shown.");
      return;
    }
    var indiaRows = indiaWatch(india);
    var usRows = usWatch(us);
    var indiaCount = india && Array.isArray(india.rows) ? india.rows.length : 0;
    var usCount = us && Array.isArray(us.board) ? us.board.length : 0;
    text("packStatus", "India " + indiaCount + " · US served " + usCount + ".");
    text("coverLine", coverLine(india, us, indiaRows, usRows));
    renderWatch(indiaRows, usRows);
    renderGauge(gauge);
    var slugs = indiaRows.map(function (row) { return row.slug; }).filter(Boolean).slice(0, 5);
    return Promise.allSettled(slugs.map(function (slug) {
      return json(REVIEW_URL + encodeURIComponent(slug));
    })).then(function (packetResults) {
      renderDark(packetResults.map(function (item) {
        return item.status === "fulfilled" ? item.value : null;
      }));
    });
  }).catch(function () {
    text("packStatus", "The public feeds did not answer. Nothing was reconstructed.");
  });
}());
