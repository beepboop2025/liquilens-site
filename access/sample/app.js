(function () {
  "use strict";

  var BOARD_URL = "https://api.liquilens.in/api/failure-radar/board";
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

  function watchRows(board) {
    var rows = Array.isArray(board.rows) ? board.rows : [];
    return rows.filter(function (row) {
      return WATCH_TIERS[row.tier] === true;
    }).slice(0, 8);
  }

  function coverLine(board, watch) {
    var asOf = board.as_of || "an unknown as-of date";
    var n = Array.isArray(board.rows) ? board.rows.length : 0;
    return "As of " + asOf + ", " + n + " public names were on the served India board; "
      + watch.length + " sit yellow or worse.";
  }

  function renderWatch(rows) {
    var list = document.getElementById("watchList");
    list.innerHTML = "";
    if (!rows.length) {
      text("watchFine", "No red, orange or yellow names on the served board. Quiet is a reading too.");
      return;
    }
    rows.forEach(function (row) {
      var item = document.createElement("li");
      var tier = document.createElement("span");
      tier.className = "tier";
      tier.textContent = String(row.tier || "n/a");
      var body = document.createElement("span");
      var signals = Array.isArray(row.signals_fired) ? row.signals_fired.join(", ") : "";
      body.textContent = (row.name || row.slug || "unnamed")
        + (signals ? " · " + signals : "");
      item.appendChild(tier);
      item.appendChild(body);
      list.appendChild(item);
    });
    text("watchFine", "Copied from the public board. The pack does not re-score.");
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
      empty.textContent = "No dark-lens rows returned on the fetched packets.";
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

  Promise.allSettled([json(BOARD_URL), json(GAUGE_URL)]).then(function (results) {
    var board = results[0].status === "fulfilled" ? results[0].value : null;
    var gauge = results[1].status === "fulfilled" ? results[1].value : null;
    if (!board || !Array.isArray(board.rows)) {
      text("packStatus", "The Failure Radar did not answer. No stale pack is shown.");
      return;
    }
    var watch = watchRows(board);
    text("packStatus", "Served as of " + (board.as_of || "?") + " · " + board.rows.length + " institutions.");
    text("coverLine", coverLine(board, watch));
    renderWatch(watch);
    renderGauge(gauge);
    var slugs = watch.map(function (row) { return row.slug; }).filter(Boolean).slice(0, 5);
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
