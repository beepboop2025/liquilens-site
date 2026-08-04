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
they set the exit code. An incomplete local walk or unreadable artifact also
sets the exit code: uncertainty about what this checkout will publish is a
failed verification. Rule 4 reads the live API, whose state belongs to
another repo's deploy, so it only ever prints a warning. Set
LIQUILENS_OFFLINE=1 to skip it; an endpoint that cannot be reached is never
treated as evidence either way.

    python3 scripts/verify_public_claims.py

Exit 1 when a file in this checkout contradicts another file, or when the
local publishable surface cannot be read completely. Live API failures stay
advisory because that state belongs to another repository's deployment.
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
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

URL_TOKEN = re.compile(r"(?:https?:)?//[^\s\"'<>]+", re.I)

HOST_BOUNDARY = re.compile(
    r"(?<![a-zA-Z0-9.-])" + re.escape(DEMO_HOST) +
    r"(?![a-zA-Z0-9.-])", re.I)

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
    ("mark_semantics", BOND_BOOK, ("mark_semantics",)),
)

MARK_FIELD = "tier1_negative_after_ugl_mark"
MARK_QUALIFIER = "mark_qualifier"
MARK_SEMANTICS = "mark_semantics"


class ScanError(RuntimeError):
    """The local Pages surface could not be inspected completely."""


def readable(path: str) -> str | None:
    """The file as text, or None when it is bytes rather than copy.

    Copy the checkout serves in some other encoding is still read. Decoding
    it strictly meant one mis-encoded file raised and left every rule on
    every other file unchecked.
    """
    try:
        blob = open(path, "rb").read()
    except OSError as exc:
        raise ScanError(f"cannot read publishable file {path}: {exc}") from exc
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
    """Every regular file that can reach the Pages artifact.

    Git ignore rules are intentionally irrelevant here. The upload action is
    rooted at the workspace and can include ignored, untracked, or force-
    tracked files. Only directories the workflow removes (and the upload
    action's own metadata exclusions) are skipped.
    """
    if os.path.islink(root) or not os.path.isdir(root):
        raise ScanError(f"publish root is not a readable directory: {root}")
    excludes = artifact_excludes(root)

    def walk_error(exc: OSError) -> None:
        raise ScanError(f"cannot walk publishable surface: {exc}") from exc

    out: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root, onerror=walk_error):
        for name in dirnames:
            path = os.path.join(dirpath, name)
            excluded = name in ARTIFACT_BUILTIN_EXCLUDES or \
                (dirpath == root and name in excludes)
            if not excluded and os.path.islink(path):
                raise ScanError(
                    f"publishable directory is a symlink and cannot be "
                    f"verified as a regular artifact path: {path}")
        dirnames[:] = [
            name for name in dirnames
            if name not in ARTIFACT_BUILTIN_EXCLUDES and
            not (dirpath == root and name in excludes)]
        for name in filenames:
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root)
            if name in ARTIFACT_BUILTIN_EXCLUDES or \
                    (dirpath == root and name in excludes):
                continue
            if os.path.islink(path):
                raise ScanError(
                    f"publishable file is a symlink and cannot be verified "
                    f"as a regular artifact file: {path}")
            if not os.path.isfile(path):
                raise ScanError(f"publishable path is not a regular file: {path}")
            if name.lower().endswith(BINARY_SUFFIXES):
                continue
            out.append(rel)
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

    return html.unescape(re.sub(r"\s+", " ", TAG.sub(strip, text))).strip()


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
        href = html.unescape(
            m.group("dq") or m.group("sq") or m.group("bare") or "")
        inner = elements(m.group(0)).strip("«» \t\n")
        if not is_demo_url(href):
            return f" {inner} "
        return f" {MARK_OPEN}{inner}{MARK_CLOSE} "

    def tag(m: re.Match) -> str:
        name = TAG_NAME.match(m.group(0))
        name = name.group(1).lower() if name else ""
        return " " if name in INLINE_TAGS else ELEMENT_BREAK

    text = ANCHOR.sub(anchor, SCRIPT.sub(ELEMENT_BREAK, raw))
    return html.unescape(re.sub(r"[^\S\n]+", " ", TAG.sub(tag, text)))


def canonical_hostname(value: str) -> str | None:
    """The decoded DNS host for an absolute or protocol-relative URL."""
    try:
        parsed = urllib.parse.urlsplit(html.unescape(value).strip())
        host = parsed.hostname
    except ValueError:
        return None
    if not host or (parsed.scheme and parsed.scheme.lower() not in
                    {"http", "https"}):
        return None
    try:
        return urllib.parse.unquote(host).rstrip(".").lower()
    except (UnicodeDecodeError, ValueError):
        return None


def is_demo_url(value: str) -> bool:
    """True only when the URL actually navigates to the gated demo host."""
    return canonical_hostname(value) == DEMO_HOST


def _mark_bare_host(text: str) -> str:
    return HOST_BOUNDARY.sub(MARK_OPEN + MARK_CLOSE, text)


def marked(text: str) -> str:
    """Text with every real pointer at the demo replaced by MARK.

    URLs are parsed before bare prose is considered. This keeps a demo URL in
    another site's query string or user-info from becoming a false pointer.
    """
    text = html.unescape(text)
    out: list[str] = []
    end = 0
    for match in URL_TOKEN.finditer(text):
        out.append(_mark_bare_host(text[end:match.start()]))
        value = match.group(0)
        out.append(MARK_OPEN + MARK_CLOSE if is_demo_url(value) else value)
        end = match.end()
    out.append(_mark_bare_host(text[end:]))
    return "".join(out)


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


CONCAT_GAP = re.compile(r"\s*\+\s*")

JS_NAME = r"[a-zA-Z_$][\w$]*"

JS_DECLARATION = re.compile(
    rf"^\s*(?:const|let|var)\s+(?P<name>{JS_NAME})\s*=\s*(?P<expr>.+?)\s*$",
    re.S)

JS_HREF_ASSIGNMENT = re.compile(
    rf"^\s*(?P<receiver>{JS_NAME})\.href\s*=\s*(?P<expr>.+?)\s*$",
    re.S)

JS_HREF_ATTRIBUTE = re.compile(
    rf"^\s*(?P<receiver>{JS_NAME})\.setAttribute\s*\(\s*"
    r"['\"]href['\"]\s*,\s*(?P<expr>.+?)\s*\)\s*$", re.S)

JS_LABEL_ASSIGNMENT = re.compile(
    rf"^\s*(?P<receiver>{JS_NAME})\."
    r"(?:textContent|innerText)\s*=\s*(?P<expr>.+?)\s*$", re.S)


def javascript_statements(body: str) -> list[str]:
    """Split on semicolons outside string literals.

    This is intentionally a small recognizer, not a JavaScript parser. Its
    only job is to stop values from unrelated statements being reconstructed
    as one browser-visible link.
    """
    literals = iter(STRING_LITERAL.finditer(body))
    literal = next(literals, None)
    start = 0
    out: list[str] = []
    at = 0
    while at < len(body):
        if literal is not None and at == literal.start():
            at = literal.end()
            literal = next(literals, None)
            continue
        if body[at] == ";":
            statement = body[start:at].strip()
            if statement:
                out.append(statement)
            start = at + 1
        at += 1
    statement = body[start:].strip()
    if statement:
        out.append(statement)
    return out


def string_expression(expression: str,
                      variables: dict[str, str]) -> str | None:
    """Resolve a literal/identifier `+` expression without executing JS."""
    values: list[str] = []
    for term in CONCAT_GAP.split(expression.strip()):
        term = term.strip()
        while len(term) >= 2 and term[0] == "(" and term[-1] == ")":
            term = term[1:-1].strip()
        literal = STRING_LITERAL.fullmatch(term)
        if literal:
            values.append(next(
                (group for group in literal.groups() if group is not None),
                ""))
        elif re.fullmatch(JS_NAME, term) and term in variables:
            values.append(variables[term])
        else:
            return None
    return "".join(values) if values else None


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
        body = m.group(2)
        literals = list(STRING_LITERAL.finditer(body))
        values = [next((g for g in lit.groups() if g is not None), "")
                  for lit in literals]
        seen: set[str] = set()

        def emit(value: str) -> None:
            value = html.unescape(value).strip()
            if value and WORDS.search(value) and value not in seen:
                seen.add(value)
                out.append((where, value))

        for value in values:
            emit(value)

        # JavaScript commonly builds markup by joining short literals. Scan
        # each direct concatenation as the browser receives it, rather than
        # letting a host split at the dot evade the pointer rules.
        if literals:
            run = values[0]
            run_count = 1
            for previous, current, value in zip(
                    literals, literals[1:], values[1:]):
                gap = body[previous.end():current.start()]
                if CONCAT_GAP.fullmatch(gap):
                    run += value
                    run_count += 1
                else:
                    if run_count > 1:
                        emit(run)
                    run = value
                    run_count = 1
            if run_count > 1:
                emit(run)

        if where != "script":
            continue

        # Follow simple string values into the href and label assignments of
        # the same element. This catches split link builders without joining a
        # health-probe URL to an unrelated contact link elsewhere in a script.
        variables: dict[str, str] = {}
        links: dict[str, dict[str, str]] = {}

        def assign_link(receiver: str, kind: str, value: str) -> None:
            link = links.setdefault(receiver, {})
            link[kind] = html.unescape(value).strip()
            href = link.get("href", "")
            label = link.get("label", "")
            if is_demo_url(href) and label:
                emit(f"{href} {label}")

        for statement in javascript_statements(body):
            declaration = JS_DECLARATION.fullmatch(statement)
            if declaration:
                value = string_expression(
                    declaration.group("expr"), variables)
                if value is not None:
                    variables[declaration.group("name")] = value
                continue

            href = (JS_HREF_ASSIGNMENT.fullmatch(statement) or
                    JS_HREF_ATTRIBUTE.fullmatch(statement))
            if href:
                value = string_expression(href.group("expr"), variables)
                if value is not None:
                    assign_link(href.group("receiver"), "href", value)
                continue

            label = JS_LABEL_ASSIGNMENT.fullmatch(statement)
            if label:
                value = string_expression(label.group("expr"), variables)
                if value is not None:
                    assign_link(label.group("receiver"), "label", value)
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
        raw = readable(os.path.join(root, rel))
        if raw is None:
            continue
        raw = uncommented(raw)
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
        raw = readable(os.path.join(root, rel))
        if raw is None:
            continue
        text = plain(uncommented(raw))
        for label, pattern, _endpoints, _serves in WITHHOLD_VS_LIVE:
            if pattern.search(text):
                claimed.setdefault(label, []).append(rel)
        watched_fields = [field for field, _url, _path in FIELD_VS_LIVE]
        if MARK_QUALIFIER not in watched_fields:
            watched_fields.append(MARK_QUALIFIER)
        for field in watched_fields:
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
        value = dig(payload, path)
        if value is MISSING:
            problems.append(
                f"{', '.join(sorted(set(named[field])))}: the site names the "
                f"field {field}, and {url} no longer carries it at "
                f"{'.'.join(str(p) for p in path)}")
        elif field == MARK_SEMANTICS and \
                (not isinstance(value, str) or not value.strip()):
            problems.append(
                f"{', '.join(sorted(set(named[field])))}: the site names the "
                f"field {field}, and {url} does not carry a non-empty string "
                f"at {'.'.join(str(p) for p in path)}")

    if MARK_QUALIFIER not in named:
        notes.append(
            f"no published surface names {MARK_QUALIFIER}, so nothing is "
            f"checked against {BOND_BOOK}")
    schema_names = [
        field for field in (MARK_FIELD, MARK_QUALIFIER) if field in named]
    if schema_names:
        if BOND_BOOK not in payloads:
            payloads[BOND_BOOK] = fetch(BOND_BOOK)
        payload = payloads[BOND_BOOK]
        if payload is None:
            if MARK_QUALIFIER in named:
                notes.append(
                    f"{BOND_BOOK} did not answer, {MARK_QUALIFIER} not "
                    f"checked")
        else:
            rows = dig(payload, ("rows",))
            semantics = dig(payload, ("mark_semantics",))
            sources = ", ".join(sorted({
                rel for field in schema_names for rel in named[field]}))
            if not isinstance(rows, list):
                problems.append(
                    f"{sources}: the site names the bond-book mark schema, "
                    f"and {BOND_BOOK} has no rows list")
            else:
                for index, row in enumerate(rows):
                    if not isinstance(row, dict):
                        problems.append(
                            f"{sources}: {BOND_BOOK} carries a non-object "
                            f"bank row at "
                            f"rows.{index}")
                        continue
                    mark = row.get(MARK_FIELD, MISSING)
                    if not isinstance(mark, bool):
                        problems.append(
                            f"{sources}: "
                            f"{BOND_BOOK} must carry a boolean {MARK_FIELD} "
                            f"for every bank, and rows.{index}.{MARK_FIELD} "
                            f"is missing or not boolean")
                        continue
                    if mark is not True or MARK_QUALIFIER not in named:
                        continue
                    qualifier = row.get(MARK_QUALIFIER)
                    if not isinstance(qualifier, str) or not qualifier.strip():
                        problems.append(
                            f"{sources}: "
                            f"the site says every {MARK_FIELD} row carries "
                            f"{MARK_QUALIFIER}, and {BOND_BOOK} is missing it "
                            f"at rows.{index}.{MARK_QUALIFIER}")
                    elif isinstance(semantics, str) and semantics.strip() and \
                            qualifier.strip() != semantics.strip():
                        problems.append(
                            f"{sources}: "
                            f"{BOND_BOOK} carries a {MARK_QUALIFIER} at "
                            f"rows.{index}.{MARK_QUALIFIER} that does not "
                            f"match mark_semantics")
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
        print(f"REFUSING: the local checks could not inspect the complete "
              f"publishable surface: {exc!r}", file=sys.stderr)
        return 1

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
