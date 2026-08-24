#!/usr/bin/env python3
"""Build per-institution replay pages from the construction-PIT diagnostic.

Source of truth: GET https://api.liquilens.in/api/failure-radar/validation,
the same payload the research page cites. Every number rendered here is that
payload's, verbatim; institutions absent from it get no page. Fail-loud: any
fetch or schema problem aborts the build with no partial output.

Output:
  replay/index.html            the replay index (all institutions)
  replay/<slug>/index.html     one page per institution
  replay/index.json            machine-readable historical case-file feed
  sitemap.xml                  regenerated: base pages + replay pages

Run from the repo root:  python3 scripts/build_replay_pages.py
"""
from __future__ import annotations

import datetime
import json
import pathlib
import re
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET

API = "https://api.liquilens.in/api/failure-radar/validation"
SITE = "https://liquilens.in"
ROOT = pathlib.Path(__file__).resolve().parent.parent

# Display names derive from the record's slugs only, titleised, with
# initialisms restored. Nothing is appended that the slug does not carry.
ACRONYMS = {"ilfs": "IL&FS", "pmc": "PMC", "ckp": "CKP"}
TYPE_GLOSS = {
    "ucb": "urban co-operative bank",
    "nbfc": "non-banking financial company (NBFC)",
    "mfi": "microfinance institution (MFI)",
    "bank": "bank",
}
STATUS_GLOSS = {
    "saf_triggered": "SAF trigger zone (UCB supervisory action framework)",
    "pca_triggered": "PCA trigger zone",
    "threshold_1": "first PCA threshold zone",
    "threshold_2": "second PCA threshold zone",
}


def name_from_slug(slug: str) -> str:
    if slug in ACRONYMS:
        return ACRONYMS[slug]
    words = []
    for w in slug.split("-"):
        words.append(ACRONYMS.get(w, w.capitalize() if w != "of" and w != "the" else w))
    return " ".join(words).replace("Co Operative", "Co-operative")


def esc(s) -> str:
    # Em and en dashes are normalised to a plain hyphen on the way out. The
    # house rule is that no published page carries them, and prose arriving
    # from the historical diagnostic payload is outside this repo's control: three of its
    # fields carry em dashes today, and one of them renders on the index. A
    # substitution here holds the line whatever upstream does next. It is
    # typographic only, so no quoted number or claim changes meaning.
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;")
            .replace("—", "-").replace("–", "-"))


def complementarity_note(d: dict) -> str:
    """Build the public note from structured replay rows, never upstream prose.

    The API's free-text note can lag its structured replay fields.  Deriving the
    examples here keeps generated pages consistent with the numbers they print.
    """
    pca = {row["slug"]: row for row in d["pca_replay"]["failures"]}
    funding = {row["slug"]: row for row in d["funding_replay"]["failures"]}

    def lead(rows: dict, slug: str) -> str:
        value = rows.get(slug, {}).get("lead_months")
        return "a miss" if value is None else f"{value} months early"

    return (
        "The four engines catch different failure physics on the same corpus: "
        f"PCA/score tripwires catch ratio-visible deterioration (GTB {lead(pca, 'global-trust-bank')}, "
        f"Abhyudaya {lead(pca, 'abhyudaya-co-operative-bank')}); the funding lens catches "
        f"rollover/run failures the ratios miss (Altico {lead(funding, 'altico')} on CP reliance, "
        f"IL&FS {lead(funding, 'ilfs')}, Sambandh {lead(funding, 'sambandh-finserve')}); "
        "the forensic screen owns fabricated reporting; the market layer reprices daily "
        "between filings for listed names."
    )


def fetch() -> dict:
    req = urllib.request.Request(API, headers={"User-Agent": "liquilens-site-replay-build"})
    with urllib.request.urlopen(req, timeout=45) as r:
        if r.status != 200:
            sys.exit(f"validation endpoint answered {r.status}, aborting, no pages written")
        d = json.load(r)
    for key in ("pca_replay", "funding_replay", "hazard"):
        if key not in d:
            sys.exit(f"payload missing {key}: schema drift, aborting")
    return d


# The shared shell mirrors the hand-built site pages (privacy/, about/):
# same fonts, palette, nav, CSP (incl. the Web Analytics hosts) and beacon.
HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline' https://static.cloudflareinsights.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; img-src 'self' data: https:; connect-src 'self' https://api.liquilens.in https://cloudflareinsights.com; object-src 'none'; base-uri 'self'; form-action 'self'; upgrade-insecure-requests" />
<meta name="referrer" content="strict-origin-when-cross-origin" />
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="https://liquilens.in/og-radar.png">
<meta property="og:url" content="{canonical}">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%23E3B778'/%3E%3Ctext x='16' y='23' font-family='Georgia,serif' font-size='20' font-weight='600' fill='%231A1206' text-anchor='middle'%3EL%3C/text%3E%3C/svg%3E">
<script type="application/ld+json">{jsonld}</script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;1,9..144,400;1,9..144,500&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
:root{{--ink:#0A0F1C;--ink2:#0E1424;--line:#1E2740;--gold:#E3B778;--gold-deep:#C8954E;--teal:#5BD0C4;--red:#E06A6A;--text:#E9EBF2;--muted:#8B94AB;--muted2:#5C657E}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:var(--ink);color:var(--text);font-family:'Inter',system-ui,sans-serif;font-size:16px;line-height:1.65;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:840px;margin:0 auto;padding:0 28px}}
a{{color:var(--gold);text-decoration:none}}a:hover{{text-decoration:underline}}
.serif{{font-family:'Fraunces',Georgia,serif;font-weight:500;letter-spacing:-0.02em;line-height:1.12}}
nav{{border-bottom:1px solid var(--line);padding:20px 0;position:sticky;top:0;background:rgba(10,15,28,.92);backdrop-filter:blur(10px);z-index:9}}
nav .wrap{{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}}
.brand{{display:flex;align-items:center;gap:11px;color:var(--text);font-weight:600;font-size:18px}}
.brand:hover{{text-decoration:none}}
.mark{{width:30px;height:30px;border-radius:8px;display:grid;place-items:center;background:linear-gradient(150deg,var(--gold),var(--gold-deep));color:#1A1206;font-family:'Fraunces',serif;font-weight:600;font-size:18px}}
.brand small{{color:var(--muted2);font-weight:400;font-size:13px;margin-left:2px}}
.navlinks{{display:flex;gap:22px;font-size:14.5px}}
.navlinks a{{color:var(--muted)}}.navlinks a:hover{{color:var(--gold);text-decoration:none}}
header.hero{{padding:64px 0 10px;background:radial-gradient(70% 90% at 80% 0%,rgba(227,183,120,.07),transparent 60%)}}
.kicker{{font-family:'IBM Plex Mono',monospace;font-size:13px;letter-spacing:.22em;color:var(--gold);text-transform:uppercase;display:flex;align-items:center;gap:12px}}
.kicker::before{{content:"";width:26px;height:1px;background:var(--gold)}}
h1{{font-size:clamp(32px,4.4vw,46px);margin:20px 0 14px}}
.lede{{color:var(--muted);max-width:700px;font-size:17.5px}}
.lede b{{color:var(--text)}}
section{{padding:26px 0 60px}}
h2{{font-family:'Fraunces',Georgia,serif;font-weight:500;font-size:24px;color:var(--text);margin:30px 0 10px}}
p.body{{color:var(--muted);margin:10px 0;max-width:760px}}
p.body b{{color:var(--text)}}
.mono{{font-family:'IBM Plex Mono',monospace;font-size:13px;color:var(--muted2)}}
.factrow{{display:flex;align-items:baseline;gap:12px;padding:12px 16px;border:1px solid var(--line);border-radius:10px;margin:10px 0;background:var(--ink2);flex-wrap:wrap}}
.factrow .k{{font-family:'IBM Plex Mono',monospace;font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted2);min-width:190px}}
.factrow .v{{color:var(--text)}}
.fraud{{border-color:rgba(224,106,106,.5)}}
.miss{{color:var(--red)}}
table.rp{{border-collapse:collapse;width:100%;margin:14px 0;font-size:14.5px}}
table.rp th,table.rp td{{text-align:left;padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}}
table.rp th{{font-family:'IBM Plex Mono',monospace;font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted2)}}
table.rp td.n{{font-family:'IBM Plex Mono',monospace;white-space:nowrap}}
.tblwrap{{overflow-x:auto}}
footer{{border-top:1px solid var(--line);padding:32px 0 44px;font-family:'IBM Plex Mono',monospace;font-size:12.5px;color:var(--muted2)}}
footer a{{color:var(--muted)}}
@media (max-width:640px){{.navlinks{{display:none}}}}
</style>
<!-- Cloudflare Web Analytics --><script type='module' src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{{"token": "43b422e63bb44fb5975c7bb39bd0ba24"}}'></script><!-- End Cloudflare Web Analytics -->
</head>
<body>

<nav><div class="wrap">
  <a class="brand" href="/"><span class="mark">L</span>LiquiLens <small>failure replay</small></a>
  <div class="navlinks"><a href="/replay/">Replay index</a><a href="/research/">Research</a><a href="/us/">US layer</a><a href="/">Home</a></div>
</div></nav>
"""

FOOT = """
<footer><div class="wrap">
<p>Every number on this page is served from
<a href="https://api.liquilens.in/api/failure-radar/validation">GET /api/failure-radar/validation</a>,
the same payload the <a href="/research/">research index</a> cites. Its status is
<code>PERIOD_END_PROXY_CONSTRUCTION_PIT</code>; it is not validated-backtest or
real-money evidence, a credit rating or investment advice.
&copy; 2026 LiquiLens.</p>
</div></footer>
<script src="/ai-referral.js" defer></script>
</body>
</html>
"""


def jsonld_page(name: str, desc: str, url: str) -> str:
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": name,
        "description": desc,
        "url": url,
        "isPartOf": {"@type": "WebSite", "name": "LiquiLens", "url": SITE + "/"},
        "isBasedOn": API,
    })


def inst_page(slug: str, pca: dict | None, fund: dict | None, fraud: bool) -> str:
    name = name_from_slug(slug)
    itype = (pca or fund or {}).get("inst_type", "")
    gloss = TYPE_GLOSS.get(itype, itype)
    default_date = (pca or {}).get("default_date")

    title = f"{name} failure: construction-PIT historical replay | LiquiLens"
    desc = (f"How the LiquiLens lenses read {name} ({gloss}) before its failure"
            + (f" on {default_date}" if default_date else "")
            + ": action-zone replay, funding-fragility replay, and what was missed, from the published construction-PIT diagnostic.")
    url = f"{SITE}/replay/{slug}/"

    rows = []
    rows.append(f'<div class="factrow"><span class="k">Institution type</span><span class="v">{esc(gloss)}</span></div>')
    if default_date:
        rows.append(f'<div class="factrow"><span class="k">Failure date on record</span><span class="v mono">{esc(default_date)}</span></div>')
    if fraud:
        rows.append('<div class="factrow fraud"><span class="k">Fraud-masked books</span>'
                    '<span class="v">The record marks this failure as concealed by fraud: reported financials '
                    'did not carry the distress, which balance-sheet lenses cannot see. It is excluded from the '
                    'headline non-fraud recall and kept visible here. The record keeps its misses.</span></div>')

    # PCA / SAF action-zone replay
    pca_html = '<p class="body miss">No action-zone entry before failure on this record, shown as a miss.</p>'
    if pca and pca.get("first_action_zone"):
        z = pca["first_action_zone"]
        raw_status = z.get("status", "")
        # unknown tokens render as the recorded label in mono, never silently
        # prettified; both branches are safe HTML by construction
        status_html = (f"<b>{esc(STATUS_GLOSS[raw_status])}</b>" if raw_status in STATUS_GLOSS
                       else f'action zone the record labels <span class="mono">{esc(raw_status)}</span>')
        breaches = ", ".join(z.get("breaches", [])) or "-"
        lead = pca.get("lead_months")
        lead_txt = f'<b>{lead} months</b> before the failure date' if lead is not None else "lead not scored"
        pca_html = (f'<p class="body">First entered the {status_html} in {esc(z.get("q",""))} '
                    f'(period ending <span class="mono">{esc(z.get("period_end",""))}</span>), '
                    f'breaching: <b>{esc(breaches)}</b>. That is {lead_txt}.</p>')

    # Funding-fragility replay
    fund_html = '<p class="body miss">No funding-side signal before failure on this record, shown as a miss.</p>'
    if fund and fund.get("first_signal"):
        s = fund["first_signal"]
        flags = "; ".join(s.get("flags", [])) or "-"
        lead = fund.get("lead_months")
        lead_txt = f'<b>{lead} months</b> of lead' if lead is not None else "lead not scored"
        fund_html = (f'<p class="body">First funding-fragility signal at period ending '
                     f'<span class="mono">{esc(s.get("period_end",""))}</span>: index '
                     f'<span class="mono">{esc(s.get("index",""))}</span>, band <b>{esc(s.get("band",""))}</b>, '
                     f'flags: <b>{esc(flags)}</b>. That is {lead_txt}.</p>')
    elif fund and not fund.get("scoreable", True):
        fund_html = '<p class="body">Not scoreable on the funding lens for this record (insufficient liability-side data), disclosed rather than scored.</p>'

    body = f"""
<header class="hero"><div class="wrap">
  <p class="kicker">Failure replay · {esc(itype.upper())}</p>
  <h1 class="serif">{esc(name)}</h1>
  <p class="lede">Historical replay of <b>{esc(name)}</b> through the LiquiLens lenses,
  from the published India construction-PIT diagnostic. Filing availability is proxied rather than
  fully reconstructed, so this is not validated-backtest or real-money evidence.</p>
</div></header>

<section><div class="wrap">
  {''.join(rows)}
  <h2 class="serif">Action-zone replay (distance to PCA/SAF)</h2>
  {pca_html}
  <h2 class="serif">Funding-fragility replay (liability side)</h2>
  {fund_html}
  <p class="body">Context for these two lenses (cohort recall, leads, controls and
  the misses) is on the <a href="/replay/">replay index</a> and the
  <a href="/research/">research page</a>.</p>
</div></section>
"""
    return HEAD.format(title=esc(title), desc=esc(desc), canonical=url,
                       jsonld=jsonld_page(title, desc, url)) + body + FOOT


def index_page(d: dict, slugs: list[str], pca_by: dict, fund_by: dict, fraud_set: set) -> str:
    title = "Failure replays: every institution on the published record | LiquiLens"
    desc = ("Per-institution construction-PIT historical replays of two decades of Indian lender failures "
            "through the LiquiLens lenses: action-zone distance, funding fragility, leads in months, "
            "and the misses, from the published construction-PIT diagnostic.")
    url = f"{SITE}/replay/"
    hz = d["hazard"]

    trs = []
    for slug in slugs:
        p, f = pca_by.get(slug), fund_by.get(slug)
        name = name_from_slug(slug)
        pl = p.get("lead_months") if p else None
        fl = f.get("lead_months") if f else None
        trs.append(
            f'<tr><td><a href="/replay/{slug}/">{esc(name)}</a></td>'
            f'<td class="n">{esc((p or f or {}).get("inst_type",""))}</td>'
            f'<td class="n">{esc((p or {}).get("default_date","-"))}</td>'
            f'<td class="n">{esc(pl) if pl is not None else "<span class=miss>miss</span>"}</td>'
            f'<td class="n">{esc(fl) if fl is not None else "<span class=miss>miss</span>"}</td>'
            f'<td class="n">{"yes" if slug in fraud_set else "no"}</td></tr>')

    body = f"""
<header class="hero"><div class="wrap">
  <p class="kicker">Failure replays · the record, institution by institution</p>
  <h1 class="serif">Every failure on the published record</h1>
  <p class="lede">One page per institution: how each lens read it before it failed,
  with leads in months, and where a lens saw nothing, a <b>miss shown as a miss</b>.
  Hazard panel behind the headline: <span class="mono">{hz["panel"]["institutions"]} institutions,
  {hz["panel"]["rows"]} panel rows, {hz["panel"]["events"]} failure events</span>.</p>
</div></header>

<section><div class="wrap">
  <div class="tblwrap"><table class="rp">
  <thead><tr><th>Institution</th><th>Type</th><th>Failed</th><th>Action-zone lead (mo)</th><th>Funding lead (mo)</th><th>Fraud-masked</th></tr></thead>
  <tbody>{''.join(trs)}</tbody></table></div>
  <h2 class="serif">How to read this</h2>
  <p class="body">{esc(complementarity_note(d))}</p>
  <p class="body mono">Hazard method, as served by the payload: {esc(hz.get("method", ""))}</p>
</div></section>
"""
    return HEAD.format(title=esc(title), desc=esc(desc), canonical=url,
                       jsonld=jsonld_page(title, desc, url)) + body + FOOT


def replay_verdict(row: dict | None, field: str, *, scoreable: bool = True) -> str:
    """Grade one lens without collapsing separate model behaviours together."""
    if not scoreable:
        return "VOID"
    return "HIT" if row and row.get(field) else "MISS"


def case_file_record(
        slug: str, pca: dict | None, fund: dict | None, fraud: bool,
        published_at: str) -> dict:
    name = name_from_slug(slug)
    default_date = (pca or {}).get("default_date")
    pca_verdict = replay_verdict(pca, "first_action_zone")
    funding_verdict = replay_verdict(
        fund, "first_signal", scoreable=bool(fund and fund.get("scoreable", True)))
    pca_lead = pca.get("lead_months") if pca else None
    funding_lead = fund.get("lead_months") if fund else None

    if pca_verdict == "HIT" and funding_verdict == "HIT":
        headline = f"Two LiquiLens lenses flagged {name} before the recorded failure"
    elif pca_verdict == "HIT":
        headline = f"The action-zone lens flagged {name}; the funding lens did not"
    elif funding_verdict == "HIT":
        headline = f"The funding lens flagged {name}; the action-zone lens missed it"
    elif funding_verdict == "VOID":
        headline = f"The action-zone lens missed {name}; the funding lens was not scoreable"
    else:
        headline = f"Both published LiquiLens lenses missed {name}"

    outcomes = []
    outcomes.append(
        f"Action-zone lens: {pca_verdict}"
        + (f", first flag {pca_lead} months before the recorded failure." if pca_lead is not None
           else ", with no pre-failure action-zone entry in this record."))
    if funding_verdict == "VOID":
        outcomes.append("Funding-fragility lens: VOID because the record was not scoreable on that lens.")
    else:
        outcomes.append(
            f"Funding-fragility lens: {funding_verdict}"
            + (f", first flag {funding_lead} months before the recorded failure." if funding_lead is not None
               else ", with no pre-failure signal in this record."))
    if fraud:
        outcomes.append(
            "The source marks the case fraud-masked; reported books may not carry the hidden distress, so misses remain visible and are not reclassified.")

    return {
        "id": f"liquilens:case-file:{slug}",
        "slug": slug,
        "article_type": "case_file",
        "headline": headline,
        "dek": " ".join(outcomes),
        "beat": "historical-institution-replay",
        "editorial_class": "case_file",
        "publication_status": "PUBLISHED",
        "published_at": published_at,
        "modified_at": published_at,
        "canonical_url": f"{SITE}/replay/{slug}/",
        "clocks": {
            "event_time": default_date or published_at,
            "knowledge_time": published_at,
        },
        "evidence_as_of": "2026-08-09",
        "evidence_status": "PERIOD_END_PROXY_CONSTRUCTION_PIT",
        "point_in_time_status": "RECONSTRUCTED_LATER",
        "outcome_window": {
            "end": default_date,
            "definition": "First qualifying pre-failure signal in the published construction-PIT diagnostic.",
        },
        "verdicts": {
            "action_zone": pca_verdict,
            "funding_fragility": funding_verdict,
        },
        "fraud_masked": fraud,
        "original_contribution": {
            "kinds": ["historical_case_file", "misses_included"],
            "statement": "A per-institution comparison of two distinct historical lenses against the recorded failure date, preserving hits, misses, and unscoreable cases separately.",
        },
        "limitations": [
            "Filing availability is proxied rather than fully reconstructed, so this is reconstructed construction-PIT analysis, not a publication-vintage validated backtest or real-money evidence."
        ],
    }


def case_file_index(
        slugs: list[str], pca_by: dict, fund_by: dict, fraud_set: set,
        published_at: str = "2026-08-09T20:27:48+05:30") -> dict:
    return {
        "schema": "liquilens.case-file-index.v1",
        "publication_policy": "construction_pit_replay_misses_included",
        "articles": [
            case_file_record(
                slug, pca_by.get(slug), fund_by.get(slug),
                slug in fraud_set, published_at)
            for slug in slugs
        ],
    }


BASE_SITEMAP = [
    ("/", "2026-08-21", "weekly", "1.0"),
    ("/investigations/", "2026-08-12", "weekly", "0.9"),
    ("/investigations/the-5-64x-private-credit-concentration/",
     "2026-08-12", "monthly", "0.8"),
    ("/developers/", "2026-08-21", "monthly", "0.9"),
    ("/use-cases/", "2026-08-21", "monthly", "0.9"),
    ("/world-economy/", "2026-08-24", "weekly", "0.95"),
    ("/money-markets/", "2026-08-24", "weekly", "0.95"),
    ("/capital-markets/", "2026-08-24", "weekly", "0.95"),
    ("/china-economy/", "2026-08-24", "weekly", "0.95"),
    ("/tools/ews-coverage-check/", "2026-08-21", "monthly", "0.9"),
    ("/guides/rbi-nbfc-early-warning-system/", "2026-08-21", "monthly", "0.9"),
    ("/access/", "2026-08-18", "monthly", "0.95"),
    ("/access/sample/", "2026-08-18", "daily", "0.8"),
    ("/pilot/", "2026-08-08", "monthly", "0.8"),
    ("/us/", "2026-08-09", "weekly", "0.9"),
    ("/research/", "2026-08-21", "weekly", "0.9"),
    ("/research/lab-reviewed-status-2026-08-09.json", "2026-08-09", "never", "0.8"),
    ("/research/replay-atlas-2026-08-09.json", "2026-08-09", "never", "0.8"),
    ("/desk/", "2026-08-11", "daily", "0.9"),
    ("/replay/", "2026-08-04", "weekly", "0.8"),
    ("/replay/index.json", "2026-08-09", "weekly", "0.8"),
    ("/ship-log/", "2026-08-22", "weekly", "0.7"),
    ("/about/", "2026-08-04", None, None),
    ("/security/", "2026-08-09", None, None),
    ("/status/", "2026-08-22", None, None),
    ("/privacy/", "2026-08-21", None, None),
    ("/terms/", "2026-08-04", None, None),
]


def write_if_changed(path: pathlib.Path, content: str) -> bool:
    """Write generated content and report whether it changed."""
    if path.exists() and path.read_text() == content:
        return False
    path.write_text(content)
    return True


def differs_from_head(path: pathlib.Path) -> bool:
    """Keep today's lastmod when this worktree already changed a generated page."""
    try:
        rel = path.relative_to(ROOT)
        result = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", str(rel)],
            cwd=ROOT,
            check=False,
            capture_output=True,
        )
        return result.returncode == 1
    except (OSError, ValueError):
        return False


def committed_lastmods() -> dict[str, str]:
    """Read prior dates from the committed sitemap, falling back to the file."""
    try:
        result = subprocess.run(
            ["git", "show", "HEAD:sitemap.xml"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        source = result.stdout
    except (OSError, subprocess.CalledProcessError):
        source = (ROOT / "sitemap.xml").read_text()
    try:
        root = ET.fromstring(source)
    except ET.ParseError:
        return {}
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return {
        node.findtext("sm:loc", default="", namespaces=ns):
        node.findtext("sm:lastmod", default="", namespaces=ns)
        for node in root.findall("sm:url", ns)
    }


def write_sitemap(
        slugs: list[str], changed_slugs: set[str], replay_index_changed: bool) -> None:
    today = datetime.date.today().isoformat()
    previous = committed_lastmods()
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, configured_lastmod, freq, prio in BASE_SITEMAP:
        url = f"{SITE}{path}"
        lastmod = configured_lastmod
        if path == "/replay/":
            lastmod = today if replay_index_changed else previous.get(url, configured_lastmod)
        out.append("  <url>")
        out.append(f"    <loc>{url}</loc>")
        out.append(f"    <lastmod>{lastmod}</lastmod>")
        if freq:
            out.append(f"    <changefreq>{freq}</changefreq>")
        if prio:
            out.append(f"    <priority>{prio}</priority>")
        out.append("  </url>")
    for slug in slugs:
        url = f"{SITE}/replay/{slug}/"
        lastmod = today if slug in changed_slugs else previous.get(url, today)
        out.append(f"  <url><loc>{url}</loc><lastmod>{lastmod}</lastmod><changefreq>monthly</changefreq></url>")
    current_sitemap = ROOT / "sitemap.xml"
    if current_sitemap.exists():
        match = re.search(
            r"<!-- DAILY-ARTICLES:START -->.*?<!-- DAILY-ARTICLES:END -->",
            current_sitemap.read_text(),
            flags=re.S,
        )
        if match:
            out.append(match.group(0))
    out.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(out) + "\n")


def main() -> int:
    d = fetch()
    pca_by = {f["slug"]: f for f in d["pca_replay"]["failures"]}
    fund_by = {f["slug"]: f for f in d["funding_replay"]["failures"]}
    fraud_set = set(d["hazard"].get("fit_exclusions", {}).get("fraud_masked_failures", []))
    slugs = sorted(set(pca_by) | set(fund_by))
    if not slugs:
        sys.exit("no institutions in payload, aborting")

    outdir = ROOT / "replay"
    outdir.mkdir(exist_ok=True)
    changed_slugs = set()
    for slug in slugs:
        page_dir = outdir / slug
        page_dir.mkdir(exist_ok=True)
        page_path = page_dir / "index.html"
        changed = write_if_changed(
            page_path,
            inst_page(slug, pca_by.get(slug), fund_by.get(slug), slug in fraud_set),
        )
        if changed or differs_from_head(page_path):
            changed_slugs.add(slug)
    index_path = outdir / "index.html"
    index_changed = write_if_changed(
        index_path, index_page(d, slugs, pca_by, fund_by, fraud_set))
    index_changed = index_changed or differs_from_head(index_path)
    write_if_changed(
        outdir / "index.json",
        json.dumps(case_file_index(slugs, pca_by, fund_by, fraud_set), indent=2)
        + "\n",
    )
    write_sitemap(slugs, changed_slugs, index_changed)
    print(f"wrote {len(slugs)} institution pages + index + sitemap ({len(BASE_SITEMAP) + len(slugs)} urls)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
