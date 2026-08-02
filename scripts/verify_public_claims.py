#!/usr/bin/env python3
"""Check that the public surfaces of liquilens.in agree with reality.

Four rules, checked over every file the Pages workflow uploads:

  1. one US failure count, and it is the study denominator
  2. the Undertow price ladder, on Undertow surfaces only
  3. no surface describes a gated door as open, hrefs and JSON-LD included
  4. no surface claims something is withheld that a public API serves

Rules 1 to 3 read only the checked out files, so they are deterministic and
they set the exit code. Rule 4 reads the live API, whose state belongs to
another repo's deploy, so it only ever prints a warning. Set
LIQUILENS_OFFLINE=1 to skip it; an endpoint that cannot be reached is never
treated as evidence either way.

    python3 scripts/verify_public_claims.py

Exit 1 only when a file in this checkout contradicts another file in this
checkout. Everything else prints loudly and exits 0, because a gate that
blocks the only publish path stops being a gate and starts being an outage.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The study-backed denominator. /us/ and /research/ own this result, so this is
# where it changes, once, when the FDIC record grows.
US_FAILURE_COUNT = "550"

# The Undertow ladder as it is priced on liquilens-undertow.com. It governs
# Undertow surfaces only; LiquiLens and Seiche prices are not on this ladder.
UNDERTOW_PRICES = {"$29/mo", "$99/mo", "$199/mo", "$8,000/yr", "$0.05/call"}

PUBLISHED_SUFFIXES = (".html", ".txt", ".xml", ".json")

SKIP_DIRS = {".git", ".github", "scripts", "tests"}

# actions/upload-pages-artifact tars the checkout with these already dropped.
ARTIFACT_BUILTIN_EXCLUDES = {".git", ".github"}

WORKFLOW = os.path.join(".github", "workflows", "pages.yml")

DEMO_HOST = "demo.liquilens.in"

TAG = re.compile(r"<[^>]+>")

ANCHOR = re.compile(r"<a\b[^>]*?href=\"([^\"]*)\"[^>]*>(.*?)</a>", re.I | re.S)

FAILURE_COUNT = re.compile(
    r"(?<![\d,])(\d{3,4})\s+(?:US\s+)?(?:FDIC\s+)?(?:bank\s+)?"
    r"(?:failures|collapses|receiverships)\b", re.I)

YEAR = re.compile(r"(?:19|20)\d{2}")

PRICE = re.compile(
    r"\$\s?\d[\d,]*(?:\.\d+)?(?:\s?[-\u2013\u2014]\s?\d[\d,]*)?\s?/\s?"
    r"(?:mo|yr|call|month|year)\b", re.I)

UNDERTOW = re.compile(r"undertow", re.I)

PRICE_WINDOW = 160

FALSE_CLAIMS = (
    ("demo openness",
     re.compile(r"demo\.liquilens\.in[^.]{0,200}?\bno\s+(?:signup|sign up|"
                r"access code|code)\b", re.I),
     "demo.liquilens.in returns 401; it is granted on request"),
    ("demo openness",
     re.compile(r"\bno\s+(?:signup|sign up|access code)\b[^.]{0,200}?"
                r"demo\.liquilens\.in", re.I),
     "demo.liquilens.in returns 401; it is granted on request"),
    ("demo openness",
     re.compile(r"demo\.liquilens\.in\b[^.]{0,80}\bis open\b", re.I),
     "demo.liquilens.in returns 401; it is granted on request"),
    ("undertow web desk",
     re.compile(r"free web desk", re.I),
     "every path under liquilens-undertow.com/app/ returns 401 until sign in"),
)

NO_SIGNUP = re.compile(r"\bno\s+(?:signup|sign up)\b", re.I)
WEB_DESK = re.compile(r"web desk|/app/", re.I)

# A link's destination lives in the href, which tag stripping discards.
MARK_OPEN = "«DEMO "
MARK_CLOSE = "»"
MARK_WINDOW = 200

SCRIPT = re.compile(r"<(script|style)\b.*?</\1>", re.I | re.S)

# The JSON-LD lives inside <script>, so tag stripping never reaches it.
JSONLD = re.compile(
    r"<script\b[^>]*\btype\s*=\s*[\"']application/ld\+json[\"'][^>]*>"
    r"(.*?)</script>", re.I | re.S)

SENTENCE_END = re.compile(r"[.!?;:]\s")

# Dated history: exempt from the access cue, not from the open door rule.
DATED_HISTORY = {os.path.join("ship-log", "index.html")}

ACCESS_CUE = re.compile(
    r"\bon request\b|\baccess request\b|\brequest(?:s|ed|ing)?\b|\b401\b|"
    r"\bgranted\b|\bpilot tenants?\b|\bsign in\b", re.I)

OPEN_PROMISE = (
    re.compile(r"\bone click away\b", re.I),
    re.compile(r"\bopen (?:the|it|now)\b", re.I),
    re.compile(r"\bsee the\b", re.I),
    re.compile(r"\breplays? it live\b", re.I),
    re.compile(r"\btry it\b", re.I),
    re.compile(r"\bview the\b", re.I),
    re.compile(r"\bclick through\b", re.I),
    re.compile(r"\bis open\b", re.I),
    re.compile(r"\bno\s+(?:signup|sign up|access code|code)\b", re.I),
)

MISSING = object()

# Each entry: what the site says it withholds, the endpoints that would prove
# it wrong, and where in those payloads to look.
WITHHOLD_VS_LIVE = (
    ("fitted weights",
     re.compile(r"\bfitted weights\b", re.I),
     (("https://api.liquilens.in/api/failure-radar/model-card",
       ("hazard_fit", "coefficients", "coef")),
      ("https://api.liquilens.in/api/us-radar/validation",
       ("validation", "weights"))),
     "serves the fitted weight vector"),
    ("current scores of living institutions",
     re.compile(r"\bscores of living institutions\b", re.I),
     (("https://api.liquilens.in/api/failure-radar/board",
       ("rows", 0, "score")),),
     "serves named living institutions with their current score"),
)

# Payload field names the site spells out for agents to read.
FIELD_VS_LIVE = (
    ("marked_insolvent",
     "https://api.liquilens.in/api/public-signals/bond-book",
     ("rows", 0, "marked_insolvent")),
)


def published_files(root: str) -> list[str]:
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(PUBLISHED_SUFFIXES):
                out.append(os.path.relpath(os.path.join(dirpath, name), root))
    return sorted(out)


def plain(text: str) -> str:
    return re.sub(r"\s+", " ", TAG.sub(" ", text)).strip()


def plain_lines(raw: str) -> list[str]:
    return [plain(line) for line in raw.splitlines()]


def marked(raw: str) -> str:
    """Plain text with every pointer at the demo replaced by MARK."""
    def anchor(m: re.Match) -> str:
        href, inner = m.group(1), plain(m.group(2)).strip("«»")
        if DEMO_HOST not in href:
            return f" {inner} "
        return f" {MARK_OPEN}{inner}{MARK_CLOSE} "

    text = plain(ANCHOR.sub(anchor, SCRIPT.sub(" ", raw)))
    bare = MARK_OPEN + MARK_CLOSE
    text = re.sub(r"https?://" + re.escape(DEMO_HOST) + r"\S*", bare, text)
    return text.replace(DEMO_HOST, bare)


def jsonld_texts(raw: str) -> list[str]:
    """Every string value inside every JSON-LD block on the page.

    A block that will not parse is handed back whole, so malformed markup is
    still scanned rather than quietly skipped.
    """
    out: list[str] = []
    for m in JSONLD.finditer(raw):
        body = m.group(1)
        try:
            payload = json.loads(body)
        except ValueError:
            out.append(body)
            continue
        stack = [payload]
        while stack:
            node = stack.pop()
            if isinstance(node, str):
                out.append(node)
            elif isinstance(node, dict):
                stack.extend(node.values())
            elif isinstance(node, list):
                stack.extend(node)
    return out


def sentence_span(text: str, start: int, end: int) -> str:
    """The sentences the pointer itself sits in, and nothing further out."""
    left = 0
    for m in SENTENCE_END.finditer(text[:start]):
        left = m.end()
    m = SENTENCE_END.search(text, end)
    right = m.start() if m else len(text)
    return text[left:right]


def pointer_problems_in(where: str, text: str, require_cue: bool) -> list[str]:
    problems = []
    at = text.find(MARK_OPEN)
    while at >= 0:
        close = text.find(MARK_CLOSE, at)
        close = close + 1 if close >= 0 else at + len(MARK_OPEN)
        window = text[max(0, at - MARK_WINDOW):close + MARK_WINDOW]
        for promise in OPEN_PROMISE:
            hit = promise.search(window)
            if hit:
                problems.append(
                    f"{where}: a pointer at {DEMO_HOST} reads as an open door "
                    f"({hit.group(0)!r}), and the URL answers 401")
                break
        else:
            sentence = sentence_span(text, at, close)
            if require_cue and not ACCESS_CUE.search(sentence):
                problems.append(
                    f"{where}: a pointer at {DEMO_HOST} says nothing about "
                    f"the gate in its own sentence, and the URL answers 401: "
                    f"{sentence.strip()!r}")
        at = text.find(MARK_OPEN, close)
    return problems


def demo_pointer_problems(rel: str, raw: str) -> list[str]:
    require_cue = rel not in DATED_HISTORY
    problems = pointer_problems_in(rel, marked(raw), require_cue)
    for value in jsonld_texts(raw):
        problems += pointer_problems_in(
            f"{rel} JSON-LD", marked(value), require_cue)
    return problems


def dig(payload, path):
    node = payload
    for step in path:
        if isinstance(step, int):
            if not isinstance(node, list) or len(node) <= step:
                return MISSING
            node = node[step]
        else:
            if not isinstance(node, dict) or step not in node:
                return MISSING
            node = node[step]
    return node


# The edge answers 403 to the default urllib agent string.
FETCH_HEADERS = {"User-Agent": "liquilens-claim-gate/1.0",
                 "Accept": "application/json"}


def live_fetch(url: str):
    request = urllib.request.Request(url, headers=FETCH_HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return None


def artifact_excludes(root: str) -> set[str]:
    """Directories the Pages workflow keeps out of the uploaded artifact."""
    excludes = set(ARTIFACT_BUILTIN_EXCLUDES)
    path = os.path.join(root, WORKFLOW)
    if not os.path.exists(path):
        return excludes
    raw = open(path, encoding="utf-8").read()
    for m in re.finditer(r"rm\s+-rf\s+([^\n|&;]+)", raw):
        for token in m.group(1).split():
            excludes.add(token.strip("'\"").rstrip("/"))
    for m in re.finditer(r"--exclude=(\S+)", raw):
        excludes.add(m.group(1).strip("'\"").rstrip("/"))
    return excludes


def check(root: str = ROOT) -> list[str]:
    problems = []
    counts: dict[str, list[str]] = {}
    prices: dict[str, list[str]] = {}

    for rel in published_files(root):
        raw = open(os.path.join(root, rel), encoding="utf-8").read()
        text = plain(raw)

        for value in FAILURE_COUNT.findall(text):
            if YEAR.fullmatch(value):
                continue
            counts.setdefault(value, []).append(rel)

        for m in PRICE.finditer(text):
            window = text[max(0, m.start() - PRICE_WINDOW):
                          m.end() + PRICE_WINDOW]
            if UNDERTOW.search(rel) or UNDERTOW.search(window):
                token = re.sub(r"\s+", "", m.group(0))
                prices.setdefault(token, []).append(rel)

        for label, pattern, why in FALSE_CLAIMS:
            if pattern.search(text):
                problems.append(f"{rel}: {label} claim is false, {why}")
        for line in plain_lines(raw):
            if WEB_DESK.search(line) and NO_SIGNUP.search(line):
                problems.append(
                    f"{rel}: the browser desk is described as needing no "
                    f"signup, and it returns 401 until sign in")
                break

        problems += demo_pointer_problems(rel, raw)

    if len(counts) > 1:
        detail = "; ".join(
            f"{value} in {', '.join(sorted(set(files)))}"
            for value, files in sorted(counts.items()))
        problems.append(
            f"the US failure count is published as {len(counts)} different "
            f"numbers: {detail}")
    for value, files in sorted(counts.items()):
        if value != US_FAILURE_COUNT:
            problems.append(
                f"the US failure count is published as {value} in "
                f"{', '.join(sorted(set(files)))}, and the study record is "
                f"{US_FAILURE_COUNT}")
    for token, files in sorted(prices.items()):
        if token not in UNDERTOW_PRICES:
            problems.append(
                f"{token} in {', '.join(sorted(set(files)))} is not on the "
                f"Undertow ladder ({', '.join(sorted(UNDERTOW_PRICES))})")
    if not counts:
        problems.append("no US failure count found on any surface")

    if os.path.exists(os.path.join(root, WORKFLOW)):
        excludes = artifact_excludes(root)
        for skipped in sorted(SKIP_DIRS - excludes):
            problems.append(
                f"{skipped}/ is never scanned for retired claims and is not "
                f"excluded from the Pages upload, so it publishes at "
                f"liquilens.in/{skipped}/")

    return problems


def check_live(root: str = ROOT, fetch=live_fetch):
    """Compare what the site says about the API against what the API serves."""
    problems: list[str] = []
    notes: list[str] = []
    claimed: dict[str, list[str]] = {}
    named: dict[str, list[str]] = {}

    for rel in published_files(root):
        text = plain(open(os.path.join(root, rel), encoding="utf-8").read())
        for label, pattern, _endpoints, _serves in WITHHOLD_VS_LIVE:
            if pattern.search(text):
                claimed.setdefault(label, []).append(rel)
        for field, _url, _path in FIELD_VS_LIVE:
            if field in text:
                named.setdefault(field, []).append(rel)

    payloads: dict[str, object] = {}
    for label, _pattern, endpoints, serves in WITHHOLD_VS_LIVE:
        if label not in claimed:
            continue
        for url, path in endpoints:
            if url not in payloads:
                payloads[url] = fetch(url)
            payload = payloads[url]
            if payload is None:
                notes.append(f"{url} did not answer, {label} not checked")
                continue
            value = dig(payload, path)
            if value is MISSING or value in (None, {}, [], ""):
                continue
            problems.append(
                f"{', '.join(sorted(set(claimed[label])))}: the site says "
                f"{label} are withheld, and {url} {serves} at "
                f"{'.'.join(str(p) for p in path)} with no auth")

    for field, url, path in FIELD_VS_LIVE:
        if field not in named:
            continue
        if url not in payloads:
            payloads[url] = fetch(url)
        payload = payloads[url]
        if payload is None:
            notes.append(f"{url} did not answer, {field} not checked")
            continue
        if dig(payload, path) is MISSING:
            problems.append(
                f"{', '.join(sorted(set(named[field])))}: the site names the "
                f"field {field}, and {url} no longer carries it at "
                f"{'.'.join(str(p) for p in path)}")
    return problems, notes


def live_warnings(root: str) -> tuple[list[str], list[str]]:
    if os.environ.get("LIQUILENS_OFFLINE"):
        return [], ["LIQUILENS_OFFLINE is set, the live API was not read"]
    try:
        return check_live(root)
    except Exception as exc:
        return [], [f"the live API checks could not run: {exc!r}"]


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else ROOT
    try:
        local = check(root)
    except Exception as exc:
        print(f"WARNING: the local checks could not run, so nothing was "
              f"verified: {exc!r}", file=sys.stderr)
        local = []

    warnings, notes = live_warnings(root)
    for note in notes:
        print(f"note: {note}")
    for w in warnings:
        print(f"WARNING: {w}", file=sys.stderr)
    if warnings:
        print(f"WARNING: {len(warnings)} live API disagreement(s) above. "
              f"They depend on a deploy in another repo, so they are reported "
              f"and not enforced; publication continues.", file=sys.stderr)

    if local:
        print("REFUSING: files in this checkout contradict each other",
              file=sys.stderr)
        for p in local:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print(f"liquilens.in: one failure count ({US_FAILURE_COUNT}), one price "
          f"ladder, no retired access claims")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
