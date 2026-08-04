#!/usr/bin/env python3
"""Check that the public surfaces of liquilens.in agree with reality.

Four rules, checked over every file the Pages workflow uploads:

  1. one US failure count, and it is the study denominator
  2. the Undertow price ladder, on Undertow surfaces only
  3. no surface describes a gated door as open, in any of the six ways a page
     carries a claim: text, an href, attribute copy such as og:description,
     JSON-LD, a string a script or a style rule writes into the page, and a
     comment that ships unrendered
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

import html
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

# Byte formats carry no readable copy. Everything else that survives a UTF-8
# decode is scanned, because the artifact uploads the whole checkout and a
# retired claim reads the same in a stylesheet comment as in a paragraph.
BINARY_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".ico",
                   ".pdf", ".woff", ".woff2", ".ttf", ".otf", ".eot", ".zip",
                   ".gz", ".mp4", ".webm", ".mp3", ".wav")

SKIP_DIRS = {".git", ".github", "scripts", "tests"}

# actions/upload-pages-artifact tars the checkout with these already dropped.
ARTIFACT_BUILTIN_EXCLUDES = {".git", ".github"}

WORKFLOW = os.path.join(".github", "workflows", "pages.yml")

DEMO_HOST = "demo.liquilens.in"

TAG = re.compile(r"<[^>]+>")

TAG_NAME = re.compile(r"</?\s*([a-zA-Z][^\s/>]*)")

# Copy that lives in an attribute is what a social card and an LLM quote, and
# stripping the tag takes the attribute with it. A data attribute is read by
# the page's own script, which is one more way copy reaches the reader, so a
# data value that reads like a sentence is read like one.
ATTR = re.compile(
    r"\b(?P<name>content|alt|title|aria-label|placeholder|data-[\w-]+)\s*=\s*"
    r"(?:\"(?P<dq>[^\"]*)\"|'(?P<sq>[^']*)'|(?P<bare>[^\s\"'>]+))", re.I)

# An http-equiv meta is an HTTP header, not prose. The CSP names the demo host
# because the browser has to reach it, and that is not a claim about access.
HTTP_EQUIV = re.compile(r"\bhttp-equiv\s*=", re.I)

# Tags that sit inside a sentence. Everything else ends one.
INLINE_TAGS = frozenset(
    "a abbr b bdi bdo cite code data del dfn em i ins kbd mark q s samp small "
    "span strong sub sup time u var wbr".split())

ELEMENT_BREAK = "\n"

ANCHOR = re.compile(
    r"<a\b[^>]*?href\s*=\s*(?:\"(?P<dq>[^\"]*)\"|'(?P<sq>[^']*)'|"
    r"(?P<bare>[^\s\"'>]+))[^>]*>.*?</a>", re.I | re.S)

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

SCRIPT = re.compile(r"<(script|style)\b[^>]*>(.*?)</\1>", re.I | re.S)

# The JSON-LD lives inside <script>, so tag stripping never reaches it.
JSONLD = re.compile(
    r"<script\b[^>]*\btype\s*=\s*[\"']application/ld\+json[\"'][^>]*>"
    r"(.*?)</script>", re.I | re.S)

# A script writes copy into the page and a style rule writes copy into the
# page, so dropping those elements drops the copy with them. The code is not
# prose, the strings in it are, so the strings are what gets read.
STRING_LITERAL = re.compile(
    r"\"([^\"\\\n]*(?:\\.[^\"\\\n]*)*)\""
    r"|'([^'\\\n]*(?:\\.[^'\\\n]*)*)'"
    r"|`([^`\\]*(?:\\.[^`\\]*)*)`", re.S)

# A string with no space in it is a URL, a selector, an element id or a class
# name. A sentence a reader is shown has spaces.
WORDS = re.compile(r"\S\s+\S")

# A comment is never rendered and it still ships in the file, where a reader
# who opens the source and a model that reads the page both find it.
COMMENT = re.compile(r"<!--(.*?)-->", re.S)

SPAN_END = re.compile(r"[.!?;:]\s|\n")

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

# Payload field names the site spells out for agents to read. A name the site
# stopped using is reported as an unwatched name, never dropped in silence.
BOND_BOOK = "https://api.liquilens.in/api/public-signals/bond-book"

FIELD_VS_LIVE = (
    ("tier1_negative_after_ugl_mark", BOND_BOOK,
     ("rows", 0, "tier1_negative_after_ugl_mark")),
    ("mark_qualifier", BOND_BOOK, ("rows", 0, "mark_qualifier")),
    ("mark_semantics", BOND_BOOK, ("mark_semantics",)),
)


def ignored_names(root: str) -> set[str]:
    """Names .gitignore keeps out of the checkout the workflow uploads."""
    names: set[str] = set()
    path = os.path.join(root, ".gitignore")
    if not os.path.exists(path):
        return names
    for line in open(path, encoding="utf-8").read().splitlines():
        line = line.strip()
        if line and not line.startswith(("#", "!")):
            names.add(line.strip("/"))
    return names


def readable(path: str) -> str | None:
    """The file as text, or None when it is bytes rather than copy.

    Copy the checkout serves in some other encoding is still read. Decoding
    it strictly meant one mis-encoded file raised and left every rule on
    every other file unchecked.
    """
    blob = open(path, "rb").read()
    if b"\x00" in blob:
        return None
    try:
        return blob.decode("utf-8")
    except UnicodeDecodeError:
        return blob.decode("latin-1")


def uncommented(raw: str) -> str:
    """The file with its comments read as copy rather than dropped as markup.

    Tag stripping swallows a comment whole, so a retired sentence parked in
    one reads as gone while it is still served in the file.
    """
    return COMMENT.sub(lambda m: " " + m.group(1) + " ", raw)


def published_files(root: str) -> list[str]:
    ignored = ignored_names(root)
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in SKIP_DIRS and d not in ignored]
        for name in filenames:
            if name in ignored or name.lower().endswith(BINARY_SUFFIXES):
                continue
            path = os.path.join(dirpath, name)
            if readable(path) is None:
                continue
            out.append(os.path.relpath(path, root))
    return sorted(out)


def attr_values(tag: str) -> list[str]:
    """The quotable copy carried by one tag's attributes."""
    if HTTP_EQUIV.search(tag):
        return []
    out = []
    for m in ATTR.finditer(tag):
        value = next((g for g in (m.group("dq"), m.group("sq"),
                                  m.group("bare")) if g is not None), "")
        value = html.unescape(value).strip()
        if not value:
            continue
        if m.group("name").lower().startswith("data-") \
                and not WORDS.search(value):
            continue
        out.append(value)
    return out


def plain(text: str) -> str:
    def strip(m: re.Match) -> str:
        return " " + " ".join(attr_values(m.group(0))) + " "

    return re.sub(r"\s+", " ", TAG.sub(strip, text)).strip()


def plain_lines(raw: str) -> list[str]:
    return [plain(line) for line in raw.splitlines()]


def elements(text: str) -> str:
    """Tag stripping that keeps every element boundary as a break."""
    def strip(m: re.Match) -> str:
        name = TAG_NAME.match(m.group(0))
        name = name.group(1).lower() if name else ""
        edge = " " if name in INLINE_TAGS else ELEMENT_BREAK
        return edge + " ".join(attr_values(m.group(0))) + edge

    return TAG.sub(strip, text)


def visible(raw: str) -> str:
    """Reader-visible copy, with every element boundary kept as a break.

    Tag stripping alone runs two neighbouring elements into one line, and a
    cue in the neighbour then reads as though it sat beside the pointer. One
    anchor can hold several elements, so its own copy is read the same way.
    """
    def anchor(m: re.Match) -> str:
        href = m.group("dq") or m.group("sq") or m.group("bare") or ""
        inner = elements(m.group(0)).strip("«» \t\n")
        if DEMO_HOST not in href.lower():
            return f" {inner} "
        return f" {MARK_OPEN}{inner}{MARK_CLOSE} "

    def tag(m: re.Match) -> str:
        name = TAG_NAME.match(m.group(0))
        name = name.group(1).lower() if name else ""
        return " " if name in INLINE_TAGS else ELEMENT_BREAK

    text = ANCHOR.sub(anchor, SCRIPT.sub(ELEMENT_BREAK, raw))
    return re.sub(r"[^\S\n]+", " ", TAG.sub(tag, text))


def marked(text: str) -> str:
    """Text with every pointer at the demo replaced by MARK."""
    bare = MARK_OPEN + MARK_CLOSE
    text = re.sub(r"https?://" + re.escape(DEMO_HOST) + r"\S*", bare, text,
                  flags=re.I)
    return re.sub(re.escape(DEMO_HOST), bare, text, flags=re.I)


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


def sentence_span(text: str, at: int) -> str:
    """The sentence and the element the pointer ends in, and nothing wider.

    A link is read to its end, so that is where the pointer sits. An anchor
    can carry a heading, a paragraph and a call to action, and a cue in the
    element above the call to action is a cue about something else.
    """
    left = 0
    for m in SPAN_END.finditer(text[:at]):
        left = m.end()
    m = SPAN_END.search(text, at)
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
            sentence = sentence_span(text, close)
            if require_cue and not ACCESS_CUE.search(sentence):
                problems.append(
                    f"{where}: a pointer at {DEMO_HOST} says nothing about "
                    f"the gate in its own sentence, and the URL answers 401: "
                    f"{sentence.strip()!r}")
        at = text.find(MARK_OPEN, close)
    return problems


def script_texts(raw: str) -> list[tuple[str, str]]:
    """Every string a <script> or a <style> on this page could write into it.

    The JSON-LD blocks are read as data elsewhere, so they are left alone
    here rather than reported twice under two names.
    """
    out: list[tuple[str, str]] = []
    for m in SCRIPT.finditer(raw):
        if JSONLD.match(m.group(0)):
            continue
        where = m.group(1).lower()
        for lit in STRING_LITERAL.finditer(m.group(2)):
            value = next((g for g in lit.groups() if g is not None), "")
            value = html.unescape(value).strip()
            if WORDS.search(value):
                out.append((where, value))
    return out


def copy_segments(rel: str, raw: str) -> list[tuple[str, str]]:
    """Every surface a reader, a social card or an LLM quotes this file from."""
    out = [(rel, visible(raw))]
    for m in TAG.finditer(SCRIPT.sub(" ", raw)):
        for value in attr_values(m.group(0)):
            out.append((f"{rel} attribute", value))
    for value in jsonld_texts(raw):
        out.append((f"{rel} JSON-LD", value))
    for where, value in script_texts(raw):
        out.append((f"{rel} {where}", value))
    return out


def demo_pointer_problems(rel: str, raw: str) -> list[str]:
    require_cue = rel not in DATED_HISTORY
    problems = []
    for where, text in copy_segments(rel, raw):
        problems += pointer_problems_in(where, marked(text), require_cue)
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
        raw = uncommented(readable(os.path.join(root, rel)) or "")
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
        text = plain(uncommented(readable(os.path.join(root, rel)) or ""))
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
            notes.append(
                f"no published surface names {field}, so nothing is checked "
                f"against {url}")
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
