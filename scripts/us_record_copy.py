#!/usr/bin/env python3
"""Render every US record figure on the site from captured API artifacts.

The published copy states the US failure count, recall, lead, AUC, the 2026
replay and the named misses. None of it is maintained by hand. It is rendered
from two verbatim production captures that the site gate already binds to:

  tests/fixtures/us-radar-validation.json  GET /api/us-radar/validation
  tests/fixtures/us-evidence.json          GET /api/evidence/us

    python3 scripts/us_record_copy.py --capture   refresh both captures
    python3 scripts/us_record_copy.py             rewrite the published copy
    python3 scripts/us_record_copy.py --check     fail on any drifted figure

A phrase below is a template: its figures are placeholders, everything else
is literal. --check fails when a template no longer matches its page (the
copy moved and the figure is now unmanaged) or when a matched figure differs
from the artifact (someone typed a number). Figures from the July 2026 study
cut that the API does not serve stay dated in the copy instead of being
silently presented as the current record.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
CAPTURES = {
    "us-radar-validation.json": "https://api.liquilens.in/api/us-radar/validation",
    "us-evidence.json": "https://api.liquilens.in/api/evidence/us",
}
MAX_BYTES = 8 * 1024 * 1024
WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven",
         "eight", "nine", "ten", "eleven", "twelve")

# Each placeholder's figure shape. A template matches only its own shapes, so
# a phrase about India or a different metric can never be rewritten.
SHAPES = {
    "count": r"\d{3,4}",
    "recall": r"\d{1,3}\.\d",
    "lead": r"\d{1,3}\.\d",
    "auc": r"0\.\d{3}",
    "ci_lo": r"\d{1,3}\.\d",
    "ci_hi": r"\d{1,3}\.\d",
    "lift": r"\d{1,3}\.\d",
    "bank_quarters": r"\d{1,3}(?:,\d{3})+",
    "svb_lead": r"\d{1,3}\.\d",
    "svb_flag_month": r"[A-Z][a-z]{2} \d{4}",
    "n2026": r"[a-z]+",
    "N2026": r"[A-Z][a-z]+",
    "flagged2026": r"[a-z]+",
    "Flagged2026": r"[A-Z][a-z]+",
    "misses2026": r"[a-z]+",
    "leads2026": r"\d{1,3}\.\d(?:(?:, | and )\d{1,3}\.\d)*",
    "pending2026": r"[^<.;]*",
    "misses": r"[a-z]+",
    "flagged_named": r"\d{1,3} of \d{1,3}",
    "named_tail": r"[^<]*",
}

TEMPLATES: tuple[tuple[str, str], ...] = (
    ("llms.txt",
     "- United States: CURRENT_AMENDED_CONSTRUCTION_PIT over all {count} FDIC failures since 2008. "
     "Validated-backtest eligible: false. Real-money eligible: false. The current diagnostic reports "
     "{recall} percent recall, {lead}-month median lead, and pooled 24-month AUC {auc}; misses are named."),
    ("index.html",
     '<div class="market">United States · {count} failures since 2008</div><h3>Bank-failure diagnostic</h3>'
     '<div class="truth-card__metrics"><span><b>{recall}%</b> recall</span><span><b>{auc}</b> pooled AUC</span>'
     "<span><b>{lead} mo</b> median lead</span></div>"),
    ("index.html",
     "Its public record includes {flagged2026} 2026 US failures flagged {leads2026} months in advance, "
     "with the 2026 misses named.</p>"),
    ("index.html",
     "and {recall}% recall across {count} US failures since 2008;"),
    ("index.html",
     "Of the {n2026} 2026 failures in the served record, {flagged2026} were on the watchlist beforehand "
     "({leads2026} months ahead) and {misses2026} are named misses{pending2026}, but the API classifies"),
    ("index.html", "<h3>{count} failures since 2008</h3>"),
    ("index.html",
     "Current-amended-vintage diagnostic: {recall}% recall, {lead}-month median lead and AUC {auc}, with misses named."),
    ("index.html", "48 Indian institutions, {count} US failures since 2008 and seven European case files, with misses published"),
    ("index.html", "a current-amended construction-PIT diagnostic over {count} failures since 2008."),
    ("index.html",
     "The US diagnostic covers <b>{count} failures since 2008</b>, reports {recall}% recall and AUC {auc}, and is"),
    ("index.html", "for 48 Indian institutions, {count} US failures since 2008 and seven European case files. All three"),
    ("index.html", "the US is CURRENT_AMENDED_CONSTRUCTION_PIT over {count} failures since 2008;"),
    ("research/index.html",
     "Replays, studies and method notes from LiquiLens and Seiche. {count} US bank failures since 2008, "
     "48 Indian institutions and 7 European case files, with misses named."),
    ("research/index.html", "<h3>The United States: <em>{count} failures since 2008, quarter by quarter</em></h3>"),
    ("research/index.html",
     "Of the {n2026} 2026 failures in the served record, {flagged2026} were on the watchlist beforehand "
     "({leads2026} months ahead); {misses} recent misses are named."),
    ("research/index.html",
     '<div class="stat"><b>{recall}%</b><span>recall ({ci_lo} to {ci_hi})</span></div>\n'
     '        <div class="stat"><b>{lead} mo</b><span>median lead</span></div>\n'
     '        <div class="stat"><b>{auc}</b><span>AUC</span></div>'),
    ("research/index.html", "while reporting {recall} percent recall."),
    ("research/index.html", '<p class="src">{bank_quarters} bank quarters · 9,903 institutions'),
    ("research/index.html",
     "Status-bound historical diagnostics and method notes from LiquiLens and Seiche: {count} US failures since 2008,"),
    ("research/index.html", '"name":"The United States: {count} failures since 2008, quarter by quarter"'),
    ("access/index.html",
     "current-amended construction-PIT record over {count} FDIC failures since 2008 ({recall} percent recall on the served validation)."),
    ("brand/_x-banner.html", '<div class="stat"><b>{count}</b><span>US FAILURES REPLAYED</span></div>'),
    ("brand/_x-banner.html", '<div class="stat"><b>{recall}%</b><span>RECALL, POINT IN TIME</span></div>'),
    ("brand/_x-banner.html", '<div class="stat"><b>{lead} mo</b><span>MEDIAN LEAD</span></div>'),
    ("world-economy/index.html", '<div class="number">48 · {count} · 7<small>India institutions · US failures'),
    ("use-cases/index.html", "a current-amended construction-PIT US diagnostic over {count} failures since 2008,"),
    ("us/index.html",
     "historical diagnostic over {count} failures since 2008, with misses and eligibility flags published."),
    ("us/index.html",
     "CURRENT_AMENDED_CONSTRUCTION_PIT diagnostic over {count} FDIC receiverships from 2008 to 2026. "
     "The served record reports recall {recall} percent, median lead {lead} months and named misses."),
    ("us/index.html", 'panel <span class="live">{bank_quarters} bank quarters</span>'),
    ("us/index.html",
     'construction-PIT diagnostic · recall <span class="live">{recall}%</span> of {count} failures since 2008 '
     '· median lead <span class="live">{lead} months</span>'),
    ("us/index.html", 'SVB retrospective diagnostic lead <span class="live">{svb_lead} months</span>'),
    ("us/index.html",
     '2026 diagnostic: <span class="live">{flagged2026} of {n2026} flagged retrospectively</span> · {misses2026} misses named'),
    ("us/index.html", "with a {svb_lead}-month diagnostic lead before the March 2023 failure"),
    ("us/index.html", '<text class="lbl gold" x="130" y="60">replay flag · {svb_flag_month}</text>'),
    ("us/index.html", '<text class="lead-count" x="352" y="28">{svb_lead} mo diagnostic lead</text>'),
    ("us/index.html",
     '<div class="stat"><div class="num">{recall}%</div><p>served recall among {count} failures since 2008 in the construction-PIT diagnostic</p></div>'),
    ("us/index.html", '<div class="stat"><div class="num">{lead} mo</div><p>median lead in the retrospective diagnostic</p></div>'),
    ("us/index.html",
     '<div class="stat"><div class="num">{flagged_named}</div><p>failures since 2023 in the served record flagged in the retrospective diagnostic{named_tail}</p></div>'),
    ("us/index.html", "the served record now covers {bank_quarters} bank quarters."),
    ("us/index.html", '<tr><td class="rowlab">lift over base rate, served</td><td>{lift}x</td></tr>'),
    ("us/index.html", '<tr><td class="rowlab">pooled AUC, served</td><td>{auc}</td></tr>'),
    ("us/index.html", '<tr><td class="rowlab">recall, 95% interval, served</td><td>{ci_lo}% to {ci_hi}%</td></tr>'),
    ("us/index.html", "<h3>The {misses} we missed, and why we show them</h3>"),
    ("us/index.html", "Five of the {misses} 2023 to 2026 misses were fraud driven failures;"),
)

# Phrases that legitimately repeat (meta tag triplets, the duplicated ticker
# half). Every other template must match exactly once, so a lookalike phrase
# about another market is reported instead of being rewritten.
REPEATS = {
    "Replays, studies and method notes from LiquiLens and Seiche.": 3,
    "historical diagnostic over {count} failures since 2008, with misses": 3,
    'panel <span class="live">': 2,
    "construction-PIT diagnostic · recall": 2,
    "SVB retrospective diagnostic lead": 2,
    "2026 diagnostic: <span": 2,
}


def expected_matches(template: str) -> int:
    return next((n for prefix, n in REPEATS.items() if template.startswith(prefix)), 1)


# Generated blocks: everything between the markers is rendered.
BLOCK = re.compile(r"(<!-- us-record:(?P<name>[a-z-]+) -->\n)(?P<body>.*?)(\s*<!-- /us-record:(?P=name) -->)", re.S)

# Display names and reviewed miss notes are presentation, keyed by FDIC cert.
SHORT_NAME = {24735: "Silicon Valley Bank", 57053: "Signature Bank", 59017: "First Republic",
              27332: "Republic First", 57488: "Metropolitan Capital", 25796: "CB&T West Georgia",
              28722: "Kentland Federal S&L", 25744: "Small Business Bank",
              33802: "Tioga-Franklin Savings", 58590: "Nano Banc"}
MISS_NOTE = {
    25851: "Heartland Tri State Bank, 2023 · CEO wire fraud scheme",
    8758: "Citizens Bank, Sac City, 2023 · concentrated fraudulent loans",
    4134: "First National Bank of Lindsay, 2024 · false bank records",
    28611: "Pulaski Savings Bank, 2025 · suspected fraud cited by the FDIC",
    5520: "Santa Anna National Bank, 2025 · fraud reported",
    28722: ("Kentland Federal Savings and Loan, 2026 · a $3.7M thrift, the smallest US bank. "
            "Never reached the watch decile; peak percentile 0.65 on its final filing"),
    25744: ("Small Business Bank, Lenexa, 2026 · $73M, publicly undercapitalized since a 2023 Fed order. "
            "A solvency story our run risk weights underrank; peak percentile 0.46"),
}


def _word(n: int, capital: bool = False) -> str:
    text = WORDS[n] if 0 <= n < len(WORDS) else str(n)
    return text[:1].upper() + text[1:] if capital else text


def _and(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def load(name: str) -> dict:
    with open(FIXTURES / name, encoding="utf-8") as fh:
        return json.load(fh)


def figures(validation: dict, evidence: dict) -> dict:
    """Every figure the copy states, read from the two captures only."""
    v, s = validation["validation"], evidence["summary"]
    if v["n_failure_events_with_data"] != s["failures_with_data"]:
        raise ValueError("the two captures disagree on the US failure count; recapture both")
    if f"{v['recall_overall'] * 100:.1f}" != f"{s['recall_pct']:.1f}":
        raise ValueError("the two captures disagree on recall; recapture both")
    institutions = {i["cert"]: i for i in evidence["institutions"]}
    failures = evidence["recent_failures"]
    misses = evidence["recent_misses"]["banks"]
    miss_certs = {m["cert"] for m in misses}
    flagged = [institutions[f["cert"]] for f in failures
               if institutions.get(f["cert"], {}).get("flagged_in_window") is True]
    f2026 = [f for f in failures if f["fail_date"].startswith("2026")]
    flagged2026 = [institutions[f["cert"]] for f in f2026
                   if institutions.get(f["cert"], {}).get("flagged_in_window") is True]
    misses2026 = [f for f in f2026 if f["cert"] in miss_certs]
    pending2026 = [f for f in f2026 if f not in misses2026
                   and f["cert"] not in {i["cert"] for i in flagged2026}]
    pending = [f for f in failures if f["cert"] not in miss_certs
               and f["cert"] not in {i["cert"] for i in flagged}]
    svb = institutions[24735]
    first = next(t for t in svb["trajectory"] if t.get("flagged") is True
                 and t.get("months_to_failure") == svb["earliest_flag_lead_months"])
    month = first["period_end"][:7]
    names = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    return {
        "count": str(s["failures_with_data"]),
        "recall": f"{v['recall_overall'] * 100:.1f}",
        "lead": f"{s['median_lead_months']:.1f}",
        "auc": f"{v['auc_pooled_24m']:.3f}",
        "ci_lo": f"{s['recall_ci95_pct'][0]:.1f}",
        "ci_hi": f"{s['recall_ci95_pct'][1]:.1f}",
        "lift": f"{v['watchlist']['lift']:.1f}",
        "bank_quarters": f"{v['n_bank_quarters']:,}",
        "svb_lead": f"{svb['earliest_flag_lead_months']:.1f}",
        "svb_flag_month": f"{names[int(month[5:7]) - 1]} {month[:4]}",
        "n2026": _word(len(f2026)),
        "N2026": _word(len(f2026), capital=True),
        "flagged2026": _word(len(flagged2026)),
        "Flagged2026": _word(len(flagged2026), capital=True),
        "misses2026": _word(len(misses2026)),
        "leads2026": _and([f"{i['earliest_flag_lead_months']:.1f}" for i in flagged2026]),
        "pending2026": (f" ({_word(len(pending2026))} without a replay verdict yet)" if pending2026 else ""),
        "misses": _word(len(misses)),
        "flagged_named": f"{len(flagged)} of {len(failures)}",
        "named_tail": (f"; the {_word(len(misses))} misses are named"
                       + (f" and {_word(len(pending))} has no replay verdict yet" if len(pending) == 1 else
                          f" and {_word(len(pending))} have no replay verdict yet" if pending else "")),
        "_flagged": flagged, "_misses": misses, "_failures": failures,
    }


def pattern(template: str) -> re.Pattern[str]:
    parts = re.split(r"(\{[A-Za-z0-9_]+\})", template)
    seen: set[str] = set()
    out = []
    for part in parts:
        match = re.fullmatch(r"\{([A-Za-z0-9_]+)\}", part)
        if not match:
            out.append(re.escape(part))
        elif match.group(1) in seen:
            out.append(f"(?P={match.group(1)})")
        else:
            seen.add(match.group(1))
            out.append(f"(?P<{match.group(1)}>{SHAPES[match.group(1)]})")
    return re.compile("".join(out))


def render(template: str, values: dict) -> str:
    return re.sub(r"\{([A-Za-z0-9_]+)\}", lambda m: values[m.group(1)], template)


def _leads_block(values: dict) -> str:
    rows = sorted(values["_flagged"], key=lambda i: -i["earliest_flag_lead_months"])
    lines = []
    for inst in rows:
        lead = inst["earliest_flag_lead_months"]
        name = html.escape(SHORT_NAME.get(inst["cert"], inst["name"]))
        lines.append(f'      <div class="leadrow"><span class="who">{name}</span><div class="lane"><div class="bar" '
                     f'data-w="{round(lead / 24 * 100)}"></div></div><span class="months">{lead:.1f}</span></div>')
    for miss in values["_misses"]:
        if not miss["fail_date"].startswith("2026"):
            continue
        name = html.escape(SHORT_NAME.get(miss["cert"], miss["name"]))
        lines.append(f'      <div class="leadrow"><span class="who">{name}</span><div class="lane"><div class="bar" '
                     'data-w="0"></div></div><span class="months">miss</span></div>')
    return "\n".join(lines)


def _misses_block(values: dict) -> str:
    lines = []
    for miss in values["_misses"]:
        note = MISS_NOTE.get(miss["cert"])
        if note is None:
            note = (f"{miss['name']}, {miss['fail_date'][:4]} · named in the served record; "
                    "its cause has not been reviewed here")
        lines.append(f"        <li><b>MISS</b> · {html.escape(note, quote=False)}</li>")
    return "\n".join(lines)


BLOCKS = {"leads": _leads_block, "misses": _misses_block}


def rewrite(text: str, path: str, values: dict, problems: list[str]) -> str:
    for rel, template in TEMPLATES:
        if rel != path:
            continue
        compiled = pattern(template)
        found = len(compiled.findall(text))
        if found != expected_matches(template):
            problems.append(f"{rel}: template matches {found} times, expected "
                            f"{expected_matches(template)}: {template[:90]}")
            continue
        text = compiled.sub(lambda _m: render(template, values), text)

    def block(match: re.Match[str]) -> str:
        builder = BLOCKS.get(match.group("name"))
        if builder is None:
            problems.append(f"{path}: unknown generated block {match.group('name')}")
            return match.group(0)
        return match.group(1) + builder(values) + match.group(4)
    return BLOCK.sub(block, text)


def run(check: bool) -> list[str]:
    values = figures(load("us-radar-validation.json"), load("us-evidence.json"))
    problems: list[str] = []
    for rel in sorted({rel for rel, _ in TEMPLATES}):
        path = ROOT / rel
        source = path.read_text(encoding="utf-8")
        expected = rewrite(source, rel, values, problems)
        if expected != source:
            if check:
                problems.append(f"{rel}: a US figure differs from the captured artifact; run scripts/us_record_copy.py")
            else:
                path.write_text(expected, encoding="utf-8")
    return problems


def capture() -> None:
    for name, url in CAPTURES.items():
        request = urllib.request.Request(url, headers={"User-Agent": "liquilens-site us_record_copy"})
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError(f"{url}: response exceeds {MAX_BYTES} bytes")
        json.loads(body)
        (FIXTURES / name).write_bytes(body)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail when a published figure drifts")
    parser.add_argument("--capture", action="store_true", help="refresh the two API captures first")
    args = parser.parse_args(argv)
    if args.capture:
        capture()
    problems = run(check=args.check)
    for problem in problems:
        print(problem, file=sys.stderr)
    if not problems and not args.check:
        print("US record copy rendered from the captured artifacts")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
