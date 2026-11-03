"""Site consumers of the paused Failure Radar board fail closed.

tests/fixtures/failure-radar-board-paused.json is GET /api/failure-radar/board
as LiquiLens #201 serves it at 4e868c6, computed with the backend's own route
function (the same method reproduces production's board for main apart from
its market_layer.source string). While tiers are paused the board carries a
tier_publication block, no tier, grade, tier count or tier rule, and hazards
marked research only.

Every consumer here reads that block, never reads a missing tier as green or
as any other tier, ranks by the research-only 12-month PD as #201's editorial
desk does, names the pause, and never reads as calm. An older payload that
still carries tiers, or one without the block, must fail closed the same way.
"""
import copy
import html
import json
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

import daily_article  # noqa: E402
import social_cards  # noqa: E402
from test_daily_articles import datasets  # noqa: E402

WITHHELD = {"tier", "tiers", "grade", "quadrant_rule", "tier_counts"}
COLOUR = re.compile(r"\b(?:red|orange|yellow|green)\b", re.I)
GRADE = re.compile(r"\bgrade\b|\b(?:AAA|AA|BBB|BB|CCC|CC)\b")
CALM = re.compile(r"\b(?:calm|quiet|safe|benign|reassur\w*|all[- ]green|clean bill)\b", re.I)
NEGATION = re.compile(r"\b(?:not|never|no|nor|cannot|can't|isn't|aren't|without|neither)\b", re.I)


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def paused_board():
    return json.loads(read("tests/fixtures/failure-radar-board-paused.json"))


def with_tiers(board):
    """An older or partial response: tiers, grades, counts, no pause block."""
    old = copy.deepcopy(board)
    old.pop("tier_publication", None)
    for row in old["rows"]:
        row["tier"] = "green"
        row["grade"] = "AA"
        row["hazard"]["grade"] = "AA"
    old["tiers"] = {"red": 0, "orange": 0, "yellow": 0, "green": len(old["rows"])}
    old["quadrant_rule"] = "green unless a level or deterioration rule fires"
    return old


def find_withheld(value, path=""):
    hits = []
    if isinstance(value, dict):
        for key, child in value.items():
            here = f"{path}.{key}" if path else key
            if key in WITHHELD:
                hits.append(here)
            hits += find_withheld(child, here)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            hits += find_withheld(child, f"{path}[{i}]")
    return hits


def calm_readings(text):
    """Affirmative calm, quiet or safe readings; negated ones are boundaries."""
    hits = []
    for match in CALM.finditer(text):
        before = text[max(0, match.start() - 45):match.start()]
        if not NEGATION.search(before):
            hits.append(text[max(0, match.start() - 45):match.end() + 15])
    return hits


def tier_words(text, allowed=()):
    """Tier words, colours, grade letters or counts outside the pause naming.

    Regulatory capital tiers (Tier-1 leverage, tier one capital) are not
    Failure Radar tiers and are not counted."""
    text = html.unescape(text)
    for phrase in sorted(allowed, key=len, reverse=True):
        if phrase:
            text = text.replace(phrase, " ")
    hits = [m.group(0) for m in COLOUR.finditer(text)]
    hits += [m.group(0) for m in GRADE.finditer(text)]
    hits += [m.group(0) for m in re.finditer(
        r"\btiers?\b(?![- ]?(?:1|2|I|II|one|two)\b)", text, re.I)]
    return hits


def test_the_fixture_is_the_paused_board_201_serves():
    board = paused_board()
    block = board["tier_publication"]
    assert block["state"] == "paused" and block["since"] == "2026-11-03"
    assert block["label"] and block["reason"] and block["revalidation_condition"]
    assert find_withheld(board) == []
    assert all(row["hazard"]["research_only"] is True for row in board["rows"])
    assert board["method_note"].startswith("Review tiers are paused")


# --- daily article publisher -------------------------------------------------

def article_text(article):
    return "\n".join([article["headline"], article["dek"], article["body_md"]])


def pause_phrases(block):
    return (daily_article.tier_pause_sentence(block), block.get("reason") or "",
            f"review tiers are paused pending re-validation{daily_article.tier_pause_since(block)}",
            "no tier or tier count is given here", "no tier count is given here",
            "no grade letter is published while tiers are paused",
            "an absent tier is not a calm reading")


def assert_publishable(article, block):
    text = article_text(article)
    assert daily_article.tier_leaks(article["headline"], article["dek"], article["body_md"]) == []
    assert tier_words(text, pause_phrases(block)) == []
    assert calm_readings(text) == []
    assert f"paused pending re-validation since {block['since']}" in text
    assert find_withheld(article["subject"]) == []
    assert article["quality_gate"]["status"] == "PASS"


def build(board, *, previous=()):
    data = datasets()
    data["board"] = board
    return daily_article.build_article(
        data, date="2026-11-04", recent_index=list(previous), configured_model=None)


def test_the_publisher_on_the_paused_board_names_the_pause_and_no_tier():
    board = paused_board()
    article = build(board)
    # No row is material on today's paused board, so the desk opens a replay.
    assert article["article_type"] == "historical_replay"
    assert_publishable(article, board["tier_publication"])
    assert "The board states why:" in article["body_md"]


def test_a_current_article_ranks_material_rows_by_research_pd():
    board = paused_board()
    ranked = sorted(board["rows"], key=lambda r: (-r["hazard"]["pd_12m"], r["slug"]))
    lower, higher = ranked[4], ranked[1]
    for row in (lower, higher):
        next(r for r in board["rows"] if r["slug"] == row["slug"])["signals_fired"] = ["market_dd_below_2"]
    article = build(board)
    assert article["article_type"] == "current_analysis"
    assert article["topic"] == higher["slug"]
    assert_publishable(article, board["tier_publication"])
    spec = social_cards.article_card_spec(article)
    assert spec.metric_detail == "TIERS PAUSED / SCREEN, NOT RATING"
    assert not COLOUR.search(social_cards._card_alt(spec))


def test_an_older_board_that_still_carries_tiers_fails_closed():
    old = with_tiers(paused_board())
    stripped = daily_article.without_tier_publication(old)
    assert find_withheld(stripped) == []
    assert stripped["tier_publication"] == daily_article.SITE_TIER_PAUSE
    article = build(old)
    text = article_text(article)
    assert daily_article.tier_leaks(article["headline"], article["dek"], article["body_md"]) == []
    assert "34 green" not in text and "all green" not in text.lower()
    assert calm_readings(text) == []
    assert "paused pending re-validation" in text


def test_a_missing_tier_is_never_ranked_as_green(monkeypatch):
    rows = [
        {"slug": "b-bank", "hazard": {"pd_12m": 0.0020}},
        {"slug": "a-bank", "hazard": {"pd_12m": 0.0020}},
        {"slug": "c-bank", "hazard": {"pd_12m": 0.0031}},
        {"slug": "d-bank", "hazard": {}},
    ]
    expected = ["c-bank", "a-bank", "b-bank", "d-bank"]
    paused = {"rows": rows}
    assert [r["slug"] for r in daily_article.ranked_rows(paused, rows)] == expected
    # Even with tiers published, one row without a known tier sends the whole
    # ranking to the research-only PD instead of defaulting that row to green.
    monkeypatch.setattr(daily_article, "TIER_PUBLICATION_PAUSED", False)
    published = {"tier_publication": {"state": "published"}, "rows": rows}
    mixed = copy.deepcopy(rows)
    for row in mixed[:3]:
        row["tier"] = "yellow"
    assert daily_article.tiers_published(published)
    assert [r["slug"] for r in daily_article.ranked_rows(published, mixed)] == expected
    with pytest.raises(KeyError):
        daily_article.row_interest({"slug": "no-tier"})


def test_the_served_block_is_kept_not_overwritten():
    board = paused_board()
    held = daily_article.without_tier_publication(board)
    assert held["tier_publication"] == board["tier_publication"]
    dossier_board = daily_article.compact_board(held, "none")
    assert dossier_board["tier_publication"] == board["tier_publication"]
    assert dossier_board["screened_count"] == len(board["rows"])
    order = [row["slug"] for row in dossier_board["comparison_rows"]]
    ranked = sorted(board["rows"], key=lambda r: (-r["hazard"]["pd_12m"], r["slug"]))
    assert order == [row["slug"] for row in ranked[:3]]


# --- browser consumers, run in node against the same payloads ----------------

HARNESS = r"""
const vm = require('node:vm');
let raw = '';
process.stdin.on('data', part => raw += part);
process.stdin.on('end', async () => {
  const { library, sample, board } = JSON.parse(raw);
  const tick = () => new Promise(resolve => setTimeout(resolve, 0));

  // The radar renderer, exactly as evidence-library.js ships it.
  const els = {};
  const element = id => (els[id] = els[id] || {
    id, textContent: '', title: '', hidden: true,
    tbody: { innerHTML: '' }, querySelector() { return this.tbody; }
  });
  const start = library.indexOf('  // the failure radar: every licence type on one API-dated board');
  const end = library.indexOf('  // the Seiche desk panel');
  const fmtDate = iso => {
    const M = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    const d = new Date(iso + 'T00:00:00Z');
    return d.getUTCDate() + ' ' + M[d.getUTCMonth()] + ' ' + d.getUTCFullYear();
  };
  new Function('document', 'liveJSON', 'fmtDate', library.slice(start, end))(
    { getElementById: element }, () => Promise.resolve(board), fmtDate);
  for (let i = 0; i < 5; i++) await tick();
  const radar = {
    html: els.radarTable.tbody.innerHTML, census: els.radarCensus.textContent,
    title: els.radarCensus.title, stamp: els.radarStamp.textContent,
    order: [...els.radarTable.tbody.innerHTML.matchAll(/<td class="inst-name"[^>]*>([^<]*)<\/td>/g)].map(m => m[1]),
  };

  // The sample pack, exactly as access/sample/app.js ships it.
  const nodes = {};
  const node = tag => {
    const n = { tag, className: '', textContent: '', children: [],
      appendChild(child) { this.children.push(child); return child; } };
    Object.defineProperty(n, 'innerHTML', { get() { return ''; }, set() { n.children = []; } });
    return n;
  };
  const doc = {
    getElementById: id => (nodes[id] = nodes[id] || node('div')),
    createElement: tag => node(tag),
  };
  const fetchStub = url => {
    if (url === 'https://api.liquilens.in/api/failure-radar/board') {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(board) });
    }
    if (url === 'https://api.liquilens.in/api/us-radar/board') {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ as_of: '2026-11-03', universe: { banks_scored: 0 }, board: [] }) });
    }
    return Promise.resolve({ ok: false, status: 503, json: () => Promise.resolve(null) });
  };
  vm.runInNewContext(sample, { document: doc, fetch: fetchStub, Promise, setTimeout, console });
  for (let i = 0; i < 20; i++) await tick();
  const list = (nodes.watchList || node('ul')).children.map(li => li.children.map(c => c.textContent).join(' | '));
  const pack = {
    status: (nodes.packStatus || {}).textContent, cover: (nodes.coverLine || {}).textContent,
    list, fine: (nodes.watchFine || {}).textContent,
  };
  process.stdout.write(JSON.stringify({ radar, pack }));
});
"""


def run_consumers(board):
    payload = json.dumps({"library": read("evidence-library.js"),
                          "sample": read("access/sample/app.js"), "board": board})
    out = subprocess.run(["node", "-e", HARNESS], input=payload, text=True,
                         capture_output=True, check=True, timeout=60)
    return json.loads(out.stdout)


BROWSER_PAUSE = ("tiers paused pending re-validation", "India Failure Radar tiers are paused pending re-validation",
                 "tier authority", "tier-authorized")


def served_strings(board):
    """Explanations the API itself serves while paused, shown verbatim in
    tooltips (for example a market lens's "market tier admission incomplete")."""
    out = [str((board.get("market_layer") or {}).get("authority_reason") or ""),
           str((board.get("tier_publication") or {}).get("reason") or "")]
    for row in board["rows"]:
        out.append(str((row.get("market") or {}).get("authority_reason") or ""))
        out.append(str((row.get("movement") or {}).get("reason") or ""))
    return tuple(s for s in out if s)


def pd_order(board):
    return [row["slug"] for row in sorted(
        board["rows"], key=lambda r: (-r["hazard"]["pd_12m"], r["slug"]))]


def names_by_slug(board):
    return {row["slug"]: re.sub(r" (Limited|Private Limited|Ltd\.?)$", "", row["name"]) for row in board["rows"]}


@pytest.mark.parametrize("variant", ["served", "older_with_tiers", "no_block"])
def test_browser_consumers_never_show_a_tier_or_read_as_calm(variant):
    board = paused_board()
    if variant == "older_with_tiers":
        board = with_tiers(board)
    elif variant == "no_block":
        board.pop("tier_publication")
    shown = run_consumers(board)
    radar, pack = shown["radar"], shown["pack"]
    radar_text = " ".join([radar["html"], radar["census"], radar["stamp"]])
    pack_text = " ".join([pack["status"], pack["cover"], pack["fine"], *pack["list"]])
    for text in (radar_text, pack_text):
        assert tier_words(text, BROWSER_PAUSE + served_strings(board)) == [], text[:400]
        assert calm_readings(text) == []
        assert "research only" in text
    names = names_by_slug(board)
    assert radar["order"] == [names[slug] for slug in pd_order(board)[:12]]
    india = [line for line in pack["list"] if line.startswith("IN research")]
    assert [line.split(" | ")[1].split(" · ")[0] for line in india] == [
        next(r["name"] for r in board["rows"] if r["slug"] == slug) for slug in pd_order(board)[:5]]
    if variant == "served":
        assert "tiers paused pending re-validation since 2026-11-03" in radar["census"]
        assert radar["title"] == board["tier_publication"]["reason"]
        assert "India Failure Radar tiers are paused pending re-validation since 2026-11-03" in pack["cover"]
    else:
        assert "tiers paused pending re-validation" in radar["census"]
        assert " since " not in radar["census"].split("tiers paused pending re-validation", 1)[1][:7]
