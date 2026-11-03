#!/usr/bin/env python3
"""Render every India crisis-record figure on the site from captured API artifacts.

The home page, the research index, llms.txt and the evidence library state the
India construction-PIT headline: recall excluding fraud-masked failures, the
flagged count, the median lead, the Fisher test against healthy controls and
the two alert dials. None of it is maintained by hand. It is rendered from two
verbatim captures of the endpoints the evidence_india MCP tool reads:

  tests/fixtures/india-evidence.json     GET /api/evidence/summary
  tests/fixtures/india-alert-modes.json  GET /api/evidence/alert-modes

    python3 scripts/india_record_copy.py --capture   refresh both captures
    python3 scripts/india_record_copy.py             rewrite the published copy
    python3 scripts/india_record_copy.py --check     fail on any drifted figure

A phrase below is a template: its figures are placeholders, everything else is
literal. --check fails when a template no longer matches its page (the copy
moved and the figure is now unmanaged) or when a matched figure differs from
the capture (someone typed a number). The two captures must also agree with
each other; a disagreement means one of them is stale, so recapture both.

Dated articles are not rewritten here. They keep the figures they published,
with a dated correction note (scripts/article_corrections.py).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
CAPTURES = {
    "india-evidence.json": "https://api.liquilens.in/api/evidence/summary",
    "india-alert-modes.json": "https://api.liquilens.in/api/evidence/alert-modes",
}
MAX_BYTES = 8 * 1024 * 1024
WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven",
         "eight", "nine", "ten", "eleven", "twelve")

# The warning-horizon chapters on the home page run from the PCA replay's
# 41-month median (chapter 01) down to the outcome. The cohort-median chapter
# sits between the 27-month and 17-month chapters; outside that band the
# chapter order itself would need an editorial decision, so it is a problem.
TMINUS_ORIGIN_MONTHS = 41
TMINUS_NEIGHBOURS = (27, 17)

# Each placeholder's figure shape. A template matches only its own shapes, so
# a phrase about the US record or another metric can never be rewritten.
SHAPES = {
    "inst": r"\d{2,3}",
    "recall_ex": r"\d{1,3}\.\d",
    "k_ex": r"\d{1,3}",
    "n_ex": r"\d{1,3}",
    "lead": r"\d{1,3}(?:\.\d)?",
    "lead_whole": r"\d{1,3}",
    "lead_progress": r"\.\d{3}",
    "lead_mark": r"\d{1,3}\.\d",
    "fisher_p": r"0\.\d+",
    "fisher_controls": r"\d{1,3} of \d{1,3}",
    "cons_k": r"\d{1,3}",
    "cons_n": r"\d{1,3}",
    "cons_fp": r"\d{1,3}",
    "cons_fp_word": r"[a-z]+",
    "sens_k": r"\d{1,3}",
    "sens_n": r"\d{1,3}",
    "sens_fp_word": r"[a-z]+",
}

TEMPLATES: tuple[tuple[str, str], ...] = (
    ("index.html",
     '<span class="tminus__mark" style="left:34.1%"></span>\n'
     '        <span class="tminus__mark" style="left:{lead_mark}%"></span>'),
    ("index.html",
     '<li class="tminus__chapter" data-month="{lead}" data-progress="{lead_progress}" '
     'data-phase="Cohort median">'),
    ("index.html", '<span class="tminus__chapter-index">03 / 06 <b>{lead} months</b></span>'),
    ("index.html",
     "<p>The {inst}-institution construction-PIT diagnostic records a <b>{lead}-month median "
     "alert</b> across the replayed warning set.</p>"),
    ("index.html",
     '<div class="market">India · {inst} institutions</div><h3>Institution diagnostic</h3>'
     '<div class="truth-card__metrics"><span><b>{recall_ex}%</b> recall</span>'
     "<span><b>{lead} mo</b> median lead</span></div>"),
    ("index.html", "Its construction-PIT diagnostics report {recall_ex}% recall across {inst} Indian institutions"),
    ("index.html",
     "Filing-availability-proxied diagnostic over {inst} institutions; {recall_ex}% recall "
     "and {lead}-month median lead."),
    ("index.html",
     '<div class="num">{k_ex} of {n_ex}</div>\n'
     "        <p>Failures flagged ahead of the record, excluding books concealed by outright fraud, "
     "at a median lead of {lead} months. The same alarm fired on {fisher_controls} healthy controls "
     "(one-sided Fisher exact p = {fisher_p}), and the result is robust across a broad sweep of "
     "thresholds rather than one lucky setting.</p>"),
    ("index.html",
     "<p>Conservative mode caught {cons_k} of {cons_n} with {cons_fp_word} false alarms on healthy "
     "controls. Sensitive mode adds the funding lens and caught {sens_k} of {sens_n}, at the price "
     "of {sens_fp_word} healthy names warned."),
    ("index.html", "The separate {inst} institution balance-sheet diagnostic reports a median of {lead} months."),
    ("index.html",
     "The India diagnostic covers <b>{inst} institutions</b> and currently reports {recall_ex}% "
     "recall with a {lead}-month median lead;"),
    ("research/index.html",
     "<p>The served headline is {recall_ex} percent recall excluding fraud-masked failures "
     "({k_ex} of {n_ex}) and a {lead}-month median lead."),
    ("research/index.html",
     '<div class="stat"><b>{recall_ex}%</b><span>served recall</span></div>\n'
     '        <div class="stat"><b>{lead} mo</b><span>median lead</span></div>\n'
     '        <div class="stat"><b>{cons_fp}</b><span>false alarms, cons. mode</span></div>'),
    ("llms.txt",
     "- India: PERIOD_END_PROXY_CONSTRUCTION_PIT, a filing-availability-proxied construction-PIT "
     "diagnostic over {inst} institutions. Validated-backtest eligible: false. Real-money eligible: "
     "false. The served headline reports {recall_ex} percent recall excluding fraud-masked failures "
     "({k_ex} of {n_ex}) and a {lead}-month median lead."),
    ("evidence-library.js", "count.textContent = '{lead} mo median diagnostic lead';"),
    ("evidence-library.js",
     "count.textContent = Math.round({lead_whole}*p) + (Math.round({lead_whole}*p)===1?' month':' months') "
     "+ ' of warning';"),
)

# Every template must match exactly once, so a lookalike phrase about another
# market is reported instead of being rewritten.
REPEATS: dict[str, int] = {}


def expected_matches(template: str) -> int:
    return next((n for prefix, n in REPEATS.items() if template.startswith(prefix)), 1)


def _word(n: int) -> str:
    return WORDS[n] if 0 <= n < len(WORDS) else str(n)


def _compact(value: float) -> str:
    """23.0 -> '23', 21.5 -> '21.5': the record's own precision, no false decimals."""
    text = f"{float(value):.1f}"
    return text[:-2] if text.endswith(".0") else text


def _fraction(text: str, label: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d+)/(\d+) fired", str(text))
    if not match:
        raise ValueError(f"the Fisher table's {label} cell is not 'k/n fired': {text!r}")
    return int(match.group(1)), int(match.group(2))


def load(name: str) -> dict:
    with open(FIXTURES / name, encoding="utf-8") as fh:
        return json.load(fh)


def figures(evidence: dict, modes: dict) -> dict:
    """Every figure the copy states, read from the two captures only."""
    summary = evidence["summary"]
    ex = evidence["uncertainty"]["recall_ex_fraud"]
    if f"{summary['recall_ex_fraud_pct']:.1f}" != f"{ex['rate_pct']:.1f}":
        raise ValueError("the summary and its uncertainty block disagree on recall; recapture")
    by_mode = {row["mode"]: row for row in modes["modes"]}
    conservative, sensitive = by_mode["conservative"], by_mode["sensitive"]
    if (sensitive["recall_ex_fraud"]["k"], sensitive["recall_ex_fraud"]["n"]) != (ex["k"], ex["n"]):
        raise ValueError("the alert-mode and evidence captures disagree on recall; recapture both")
    if float(sensitive["median_lead_months"]) != float(summary["median_lead_months"]):
        raise ValueError("the alert-mode and evidence captures disagree on the median lead; recapture both")
    table = evidence["ensemble_fisher"]["table"]
    if _fraction(table["failed_ex_fraud"], "failed") != (ex["k"], ex["n"]):
        raise ValueError("the Fisher table and the recall headline disagree; recapture")
    controls_fired, controls = _fraction(table["healthy_controls"], "controls")
    if controls_fired != sensitive["fpr"]["k"] or controls != sensitive["fpr"]["n"]:
        raise ValueError("the Fisher table and the sensitive dial disagree on controls; recapture both")
    p_value = float(evidence["ensemble_fisher"]["p_value_one_sided"])
    if not (0 < p_value < 1) or not math.isfinite(p_value):
        raise ValueError("the Fisher p-value is not a probability")

    lead = float(summary["median_lead_months"])
    upper, lower = TMINUS_NEIGHBOURS
    if not lower < lead < upper:
        raise ValueError(
            f"median lead {lead} no longer sits between the {upper}- and {lower}-month chapters; "
            "the warning horizon needs an editorial reorder")
    progress = (TMINUS_ORIGIN_MONTHS - lead) / TMINUS_ORIGIN_MONTHS
    return {
        "inst": str(summary["institutions"]),
        "recall_ex": f"{float(summary['recall_ex_fraud_pct']):.1f}",
        "k_ex": str(ex["k"]),
        "n_ex": str(ex["n"]),
        "lead": _compact(lead),
        "lead_whole": str(math.floor(lead)),
        "lead_progress": f"{progress:.3f}"[1:],
        "lead_mark": f"{progress * 100:.1f}",
        "fisher_p": repr(p_value),
        "fisher_controls": f"{controls_fired} of {controls}",
        "cons_k": str(conservative["recall_ex_fraud"]["k"]),
        "cons_n": str(conservative["recall_ex_fraud"]["n"]),
        "cons_fp": str(conservative["fpr"]["k"]),
        "cons_fp_word": _word(int(conservative["fpr"]["k"])),
        "sens_k": str(sensitive["recall_ex_fraud"]["k"]),
        "sens_n": str(sensitive["recall_ex_fraud"]["n"]),
        "sens_fp_word": _word(int(sensitive["fpr"]["k"])),
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
    return text


def run(check: bool) -> list[str]:
    values = figures(load("india-evidence.json"), load("india-alert-modes.json"))
    problems: list[str] = []
    for rel in sorted({rel for rel, _ in TEMPLATES}):
        path = ROOT / rel
        source = path.read_text(encoding="utf-8")
        expected = rewrite(source, rel, values, problems)
        if expected != source:
            if check:
                problems.append(f"{rel}: an India figure differs from the captured artifact; "
                                "run scripts/india_record_copy.py")
            else:
                path.write_text(expected, encoding="utf-8")
    return problems


def capture() -> None:
    for name, url in CAPTURES.items():
        request = urllib.request.Request(url, headers={"User-Agent": "liquilens-site india_record_copy"})
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
        print("India record copy rendered from the captured artifacts")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
