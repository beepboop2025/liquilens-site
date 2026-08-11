(function () {
  "use strict";

  const SOURCES = [
    { product: "liquilens", label: "LiquiLens", url: "https://api.liquilens.in/api/experimental/v1/desk/bits", load: loadLiquiLens },
    { product: "seiche", label: "Seiche", url: "https://seiche.info/dispatches/news.json", load: loadSeiche },
    { product: "palimpsest", label: "Palimpsest", url: "https://palimpsest.info/readings/newsroom-latest.json", load: loadPalimpsest },
    { product: "liquilens-undertow", label: "LiquiLens—Undertow", url: "https://api.seiche.info/undertow/dispatch.json", load: loadUndertow }
  ];
  const ALLOWED_HOSTS = new Set(["liquilens.in", "api.liquilens.in", "seiche.info", "api.seiche.info", "palimpsest.info", "liquilens-undertow.com"]);

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function safeUrl(value, fallback) {
    try {
      const url = new URL(value || fallback);
      if (url.protocol === "https:" && ALLOWED_HOSTS.has(url.hostname)) return url.href;
    } catch (_) { /* A malformed source becomes the known product fallback. */ }
    return fallback;
  }

  async function json(url) {
    const response = await fetch(url, { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error("HTTP " + response.status);
    const payload = await response.json();
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) throw new Error("invalid JSON root");
    return payload;
  }

  function array(value) { return Array.isArray(value) ? value : []; }
  function firstString() {
    for (let i = 0; i < arguments.length; i += 1) {
      if (typeof arguments[i] === "string" && arguments[i].trim()) return arguments[i].trim();
    }
    return "";
  }

  function normalise(raw, product, fallbackUrl) {
    const clocks = raw.clocks || {};
    const evidence = raw.evidence || {};
    const contribution = raw.original_contribution || {};
    const kinds = array(contribution.kinds);
    const limitations = array(raw.limitations);
    return {
      id: firstString(raw.id, raw.slug, product + ":latest"),
      product: product,
      headline: firstString(raw.headline, raw.title, "Untitled evidence record"),
      dek: firstString(raw.dek, raw.summary, raw.lede, raw.method && raw.method.summary, "The source published no standfirst."),
      url: safeUrl(firstString(raw.canonical_url, raw.url, raw.source_url), fallbackUrl),
      editorialClass: firstString(raw.editorial_class, raw.type, raw.status, "evidence_record"),
      published: firstString(raw.published_at, raw.generated, raw.modified_at, raw.date, evidence.source_timestamp),
      eventTime: firstString(clocks.event_time, evidence.source_timestamp, raw.date, raw.published_at),
      knowledgeTime: firstString(clocks.knowledge_time, raw.published_at, raw.generated),
      publicationTime: firstString(clocks.publication_time, raw.published_at, raw.generated),
      contribution: kinds.length ? kinds.join(" · ") : firstString(contribution.statement, "evidence-backed desk finding"),
      evidenceStatus: firstString(raw.evidence_status, raw.status, array(raw.claims)[0] && array(raw.claims)[0].evidence_status, "DECLARED"),
      limitation: firstString(limitations[0], raw.honesty, "Read the source record for its evidence boundary."),
      sealed: raw.sealed_call || null
    };
  }

  async function loadLiquiLens(source) {
    const payload = await json(source.url);
    return array(payload.bits).map(function (row) { return normalise(row, source.product, "https://liquilens.in/desk/"); });
  }

  async function loadSeiche(source) {
    const payload = await json(source.url);
    return array(payload.entries).map(function (row) { return normalise(row, source.product, "https://seiche.info/dispatches/"); });
  }

  async function loadPalimpsest(source) {
    const payload = await json(source.url);
    let rows = array(payload.stories);
    if (!rows.length) rows = array(payload.entries);
    if (!rows.length && payload.story) rows = [payload.story];
    if (!rows.length && payload.headline) rows = [payload];
    if (!rows.length) throw new Error("no newsroom stories in feed");
    return rows.map(function (row) { return normalise(row, source.product, "https://palimpsest.info/news/"); });
  }

  async function loadUndertow(source) {
    const pack = await json(source.url);
    const letters = pack.letters && typeof pack.letters === "object" ? pack.letters : {};
    const dates = array(pack.entries).length ? array(pack.entries) : Object.keys(letters).sort().reverse();
    if (!dates.length) throw new Error("dispatch pack has no letters");
    return dates.map(function (date) {
      const letter = letters[date];
      if (!letter || typeof letter !== "object") throw new Error("dispatch pack is missing " + date);
      const record = letter.story || Object.assign({ id: "liquilens-undertow:" + date }, letter);
      const datedRecord = "https://liquilens-undertow.com/dispatch/" + encodeURIComponent(date) + ".json";
      return normalise(record, source.product, datedRecord);
    });
  }

  function sourceState(product, ok, detail) {
    const node = document.querySelector('[data-source-state="' + product + '"]');
    if (!node) return;
    node.textContent = ok ? "LIVE / " + detail : "COVERAGE GAP / " + detail;
    node.dataset.status = ok ? "live" : "gap";
  }

  function productLabel(product) {
    const source = SOURCES.find(function (item) { return item.product === product; });
    return source ? source.label : product;
  }

  function dateValue(value) {
    const date = new Date(value || 0);
    return Number.isNaN(date.getTime()) ? new Date(0) : date;
  }

  function shortDate(value) {
    const date = dateValue(value);
    if (!date.getTime()) return "clock unavailable";
    return new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" }).format(date);
  }

  function clockLine(label, value) {
    return label + " / " + (value ? shortDate(value) : "not collected");
  }

  function renderLead(story) {
    const body = document.querySelector(".lead-body");
    body.replaceChildren();
    body.className = "lead-body product-" + story.product;
    body.appendChild(element("span", "lead-product", productLabel(story.product) + " / " + story.editorialClass));
    body.appendChild(element("h2", "", story.headline));
    body.appendChild(element("p", "lead-dek", story.dek));
    const meta = element("div", "meta-row");
    [story.evidenceStatus, story.contribution, clockLine("published", story.publicationTime || story.published)].forEach(function (text) {
      meta.appendChild(element("span", "", text));
    });
    body.appendChild(meta);
    const link = element("a", "read-link", "Open the underlying record ↗");
    link.href = story.url;
    link.target = "_blank";
    link.rel = "noopener";
    body.appendChild(link);
  }

  function renderEntry(story) {
    const item = element("li", "wire-entry product-" + story.product);
    item.id = story.id.replace(/[^a-zA-Z0-9_-]/g, "-");
    const timing = element("div", "entry-time");
    timing.appendChild(element("span", "entry-product", productLabel(story.product)));
    const time = element("time", "", shortDate(story.publicationTime || story.published));
    if (story.publicationTime || story.published) time.dateTime = story.publicationTime || story.published;
    timing.appendChild(time);
    timing.appendChild(element("span", "", story.editorialClass));

    const main = element("div", "entry-main");
    main.appendChild(element("h3", "", story.headline));
    main.appendChild(element("p", "", story.dek));
    const meta = element("div", "meta-row");
    meta.appendChild(element("span", "", story.evidenceStatus));
    meta.appendChild(element("span", "", story.contribution));
    main.appendChild(meta);

    const side = element("div", "entry-side");
    side.appendChild(element("b", "", "THREE-CLOCK RAIL"));
    side.appendChild(element("p", "", clockLine("event", story.eventTime) + "\n" + clockLine("desk knew", story.knowledgeTime) + "\n" + clockLine("published", story.publicationTime)));
    side.appendChild(element("b", "", "BOUNDARY"));
    side.appendChild(element("p", "", story.limitation));
    const link = element("a", "", "Evidence record ↗");
    link.href = story.url;
    link.target = "_blank";
    link.rel = "noopener";
    side.appendChild(link);

    item.append(timing, main, side);
    return item;
  }

  function renderGap(source, reason) {
    const item = element("li", "coverage-gap product-" + source.product);
    item.textContent = productLabel(source.product) + " coverage gap: " + reason + ". No calm state inferred.";
    return item;
  }

  async function start() {
    const wire = document.getElementById("wire");
    const settled = await Promise.allSettled(SOURCES.map(function (source) { return source.load(source); }));
    const stories = [];
    const gaps = [];
    settled.forEach(function (result, index) {
      const source = SOURCES[index];
      if (result.status === "fulfilled" && result.value.length) {
        stories.push.apply(stories, result.value);
        sourceState(source.product, true, result.value.length + " record" + (result.value.length === 1 ? "" : "s"));
      } else {
        const reason = result.status === "rejected" ? result.reason.message : "empty feed";
        sourceState(source.product, false, reason);
        gaps.push({ source: source, reason: reason });
      }
    });
    stories.sort(function (a, b) { return dateValue(b.publicationTime || b.published) - dateValue(a.publicationTime || a.published); });
    wire.replaceChildren();
    // The source feeds own retention and pagination. This desk renders every
    // entry they supplied; it must not quietly drop a qualifying item behind
    // a local presentation cap.
    stories.forEach(function (story) { wire.appendChild(renderEntry(story)); });
    gaps.forEach(function (gap) { wire.appendChild(renderGap(gap.source, gap.reason)); });
    if (!stories.length && !gaps.length) wire.appendChild(element("li", "coverage-gap", "No records arrived. No calm state inferred."));
    wire.setAttribute("aria-busy", "false");
    document.getElementById("lastChecked").textContent = "checked " + new Date().toISOString().replace("T", " ").slice(0, 16) + " UTC";
    if (stories.length) {
      const leadEligible = function (story) {
        return !/(missing|stale|degraded|corrupt)/i.test(story.evidenceStatus) &&
          !/no current finding/i.test(story.headline);
      };
      const lead = stories.find(function (story) {
        return leadEligible(story) && /full_story/.test(story.editorialClass);
      }) || stories.find(leadEligible) || stories[0];
      document.getElementById("leadNumber").textContent = String(stories.indexOf(lead) + 1).padStart(2, "0");
      renderLead(lead);
    } else {
      document.getElementById("leadLoading").textContent = "Every feed is presently a coverage gap. No headline has been manufactured.";
    }
  }

  start();
}());
