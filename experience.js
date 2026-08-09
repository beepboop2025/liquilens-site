(function () {
  "use strict";

  var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var number = new Intl.NumberFormat("en-US");

  function siteChrome() {
    var root = document.documentElement;
    var ticker = document.querySelector(".ticker");
    var navigation = document.querySelector(".nav-shell");
    if (!ticker || !navigation) return;

    function measure() {
      var tickerHeight = Math.round(ticker.getBoundingClientRect().height);
      var chromeHeight = tickerHeight + Math.round(navigation.getBoundingClientRect().height);
      root.style.setProperty("--ticker-height", tickerHeight + "px");
      root.style.setProperty("--site-chrome-height", chromeHeight + "px");
    }
    function schedule() {
      measure();
    }

    if ("ResizeObserver" in window) {
      var observer = new ResizeObserver(schedule);
      observer.observe(ticker);
      observer.observe(navigation);
    }
    window.addEventListener("resize", schedule, { passive: true });
    measure();
    return schedule;
  }

  function setText(root, selector, value) {
    var node = root.querySelector(selector);
    if (node) node.textContent = value;
  }

  function sumClassifications(c) {
    return (c.unevaluable || 0) + (c.not_applicable || 0);
  }

  function replayAtlas() {
    var atlas = document.querySelector("[data-replay-atlas]");
    if (!atlas) return;

    var detail = atlas.querySelector(".product-detail");
    var rows = Array.prototype.slice.call(atlas.querySelectorAll(".product-row"));
    var list = atlas.querySelector(".product-list");
    var source = atlas.getAttribute("data-source");
    var products = null;

    atlas.setAttribute("aria-busy", "true");

    function outcomeSegment(className, count, total) {
      var node = document.createElement("i");
      node.className = className;
      node.style.setProperty("--share", ((count / total) * 100).toFixed(4) + "%");
      if (count > 0 && count / total < 0.015) node.style.setProperty("--min-share", "4px");
      return node;
    }

    function render(product, row, moveFocus) {
      if (!product) return;

      rows.forEach(function (candidate) {
        var selected = candidate === row;
        candidate.classList.toggle("is-active", selected);
        candidate.setAttribute("aria-selected", selected ? "true" : "false");
        candidate.tabIndex = selected ? 0 : -1;
      });

      detail.classList.remove("is-swapping");
      void detail.offsetWidth;
      detail.classList.add("is-swapping");

      setText(detail, "[data-detail-role]", product.role.toUpperCase() + " · PRODUCT " + String(product.index).padStart(2, "0"));
      setText(detail, "[data-detail-name]", product.name);
      setText(detail, "[data-detail-status]", "RETROSPECTIVE: INELIGIBLE");
      setText(detail, "[data-detail-description]", product.description);
      setText(detail, "[data-detail-establishes]", product.establishes);
      setText(detail, "[data-detail-boundary]", product.boundary);
      setText(detail, "[data-metric='evaluations']", number.format(product.evaluations));
      setText(detail, "[data-metric='scored']", number.format(product.scored));
      setText(detail, "[data-metric='captured']", number.format(product.classifications.captured));
      setText(detail, "[data-metric='missed']", number.format(product.classifications.missed));
      setText(detail, "[data-metric='falsePositive']", number.format(product.classifications.false_positive));
      setText(detail, "[data-metric='gaps']", number.format(product.gaps));

      var track = detail.querySelector("[data-outcome-track]");
      var c = product.classifications;
      var unscored = sumClassifications(c);
      if (track) {
        track.replaceChildren(
          outcomeSegment("captured", c.captured, product.evaluations),
          outcomeSegment("rejected", c.correct_rejection, product.evaluations),
          outcomeSegment("missed", c.missed, product.evaluations),
          outcomeSegment("false-positive", c.false_positive, product.evaluations),
          outcomeSegment("unscored", unscored, product.evaluations)
        );
        track.setAttribute(
          "aria-label",
          "Outcome composition: " + number.format(c.captured) + " captured, " +
          number.format(c.correct_rejection) + " correct rejections, " +
          number.format(c.missed) + " missed, " +
          number.format(c.false_positive) + " false positives, and " +
          number.format(unscored) + " not scored"
        );
      }

      var forward = detail.querySelector("[data-forward-read]");
      if (forward) {
        forward.hidden = !product.forward_records;
        setText(forward, "[data-forward-count]", number.format(product.forward_records));
        setText(forward, "[data-forward-note]", product.forward_records === 1 ? "forward score row" : "forward score rows");
      }

      detail.dataset.state = product.state;
      if (moveFocus) detail.querySelector("h3").focus({ preventScroll: true });
    }

    function revealSelection(row, smooth) {
      if (!list || list.scrollWidth <= list.clientWidth) return;
      var left = row.offsetLeft - (list.clientWidth - row.offsetWidth) / 2;
      if (smooth && "scrollTo" in list) list.scrollTo({ left: left, behavior: "smooth" });
      else list.scrollLeft = left;
    }

    function choose(row, moveFocus) {
      if (!products) return;
      var product = products[row.getAttribute("data-product")];
      render(product, row, moveFocus);
      revealSelection(row, !reducedMotion);
    }

    rows.forEach(function (row, index) {
      row.addEventListener("click", function () { choose(row, false); });
      row.addEventListener("keydown", function (event) {
        var next = null;
        if (event.key === "ArrowDown" || event.key === "ArrowRight") next = rows[(index + 1) % rows.length];
        if (event.key === "ArrowUp" || event.key === "ArrowLeft") next = rows[(index - 1 + rows.length) % rows.length];
        if (event.key === "Home") next = rows[0];
        if (event.key === "End") next = rows[rows.length - 1];
        if (!next) return;
        event.preventDefault();
        choose(next, false);
        next.focus();
      });
    });

    fetch(source, { headers: { Accept: "application/json" } })
      .then(function (response) {
        if (!response.ok) throw new Error("Replay atlas unavailable");
        return response.json();
      })
      .then(function (payload) {
        products = {};
        payload.products.forEach(function (product) { products[product.id] = product; });
        var initial = atlas.querySelector(".product-row.is-active") || rows[0];
        render(products[initial.getAttribute("data-product")], initial, false);
        revealSelection(initial, false);
        atlas.setAttribute("aria-busy", "false");
      })
      .catch(function () {
        atlas.setAttribute("aria-busy", "false");
        atlas.dataset.loadState = "static-fallback";
      });
  }

  function chapterRail() {
    var rail = document.getElementById("chapterRail");
    if (!rail || !("IntersectionObserver" in window)) return;
    var label = document.getElementById("chapterLabel");
    var links = Array.prototype.slice.call(rail.querySelectorAll("[data-chapter-link]"));
    var names = {
      top: "Opening record",
      "lab-reviewed-status": "Latest replay",
      leadtime: "Warning period",
      "evidence-status": "Evidence system",
      proof: "Historical proof",
      board: "Boards & tools",
      contact: "Run a proof"
    };

    function activate(id) {
      links.forEach(function (link) {
        var active = link.dataset.chapterLink === id;
        link.classList.toggle("is-active", active);
        if (active) link.setAttribute("aria-current", "location");
        else link.removeAttribute("aria-current");
      });
      if (label) label.textContent = names[id] || "LiquiLens";
    }

    var targets = links.map(function (link) {
      return document.getElementById(link.dataset.chapterLink);
    }).filter(Boolean);

    var observer = new IntersectionObserver(function (entries) {
      var visible = entries.filter(function (entry) { return entry.isIntersecting; })
        .sort(function (a, b) { return b.intersectionRatio - a.intersectionRatio; });
      if (visible[0]) activate(visible[0].target.id);
    }, { rootMargin: "-28% 0px -52% 0px", threshold: [0, .05, .2, .5] });

    targets.forEach(function (target) { observer.observe(target); });
    activate("top");
  }

  function tickerControl() {
    var ticker = document.querySelector(".ticker");
    var button = document.getElementById("tickerToggle");
    if (!ticker || !button) return;
    var icon = button.querySelector("span");
    var copy = button.querySelector("b");
    var paused = reducedMotion;

    try { paused = paused || sessionStorage.getItem("liquilens-tape-paused") === "true"; }
    catch (_) { /* storage can be disabled without disabling the control */ }

    function paint() {
      ticker.classList.toggle("is-paused", paused);
      button.setAttribute("aria-pressed", paused ? "true" : "false");
      if (icon) icon.textContent = paused ? "▶" : "Ⅱ";
      if (copy) copy.textContent = paused ? "Play live tape" : "Pause live tape";
    }

    button.addEventListener("click", function () {
      paused = !paused;
      try { sessionStorage.setItem("liquilens-tape-paused", String(paused)); }
      catch (_) { /* control remains functional for this page */ }
      paint();
    });
    paint();
  }

  function mobileNavigation(chromeChanged) {
    var button = document.getElementById("navMenu");
    var menu = document.getElementById("mobileNav");
    if (!button || !menu) return;

    function setOpen(open) {
      button.setAttribute("aria-expanded", open ? "true" : "false");
      menu.hidden = !open;
      var label = button.querySelector("b");
      if (label) label.textContent = open ? "Close navigation" : "Open navigation";
      if (chromeChanged) chromeChanged();
    }

    button.addEventListener("click", function () {
      setOpen(button.getAttribute("aria-expanded") !== "true");
    });
    menu.addEventListener("click", function (event) {
      if (event.target.closest("a")) setOpen(false);
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") setOpen(false);
    });
  }

  function motionGovernor() {
    var root = document.documentElement;
    var zones = document.querySelectorAll(".hero,.replay-atlas,.tminus,.board,.sei-live,.sei-board");
    root.classList.add("motion-aware");

    function visibility() {
      root.classList.toggle("is-document-hidden", document.hidden);
    }
    document.addEventListener("visibilitychange", visibility);
    visibility();

    if (reducedMotion || !("IntersectionObserver" in window)) return;
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        entry.target.classList.toggle("is-motion-active", entry.isIntersecting);
      });
    }, { rootMargin: "18% 0px", threshold: 0 });
    Array.prototype.forEach.call(zones, function (zone) { observer.observe(zone); });
  }

  var chromeChanged = siteChrome();
  motionGovernor();
  replayAtlas();
  chapterRail();
  tickerControl();
  mobileNavigation(chromeChanged);
})();
