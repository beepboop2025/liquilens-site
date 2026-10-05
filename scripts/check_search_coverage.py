#!/usr/bin/env python3
"""Read-only discovery monitoring; never a ranking, indexing, or usage claim."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


PRODUCTS = (
    {"name": "LiquiLens", "origin": "https://liquilens.in", "minimum_urls": 124,
     "pages": ("/", "/start/", "/agents/", "/developers/"),
     "sitemaps": ("/sitemap.xml",)},
    {"name": "Seiche", "origin": "https://seiche.info", "minimum_urls": 166,
     "pages": ("/", "/money-markets/", "/markets/"),
     "sitemaps": ("/sitemap.xml",)},
    {"name": "Undertow", "origin": "https://liquilens-undertow.com", "minimum_urls": 28,
     "pages": ("/", "/crypto/"),
     "sitemaps": ("/sitemap.xml", "/articles/sitemap.xml")},
)
AGENT = "LiquiLens-Discovery-Monitor/1.0 (+https://liquilens.in/)"
SEARCH_BOTS = ("Googlebot", "Bingbot", "OAI-SearchBot", "Claude-SearchBot", "PerplexityBot")
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
MAX_BYTES = 3 * 1024 * 1024
MAX_URLS = 2500
MAX_SITEMAPS = 20
NOINDEX = re.compile(r"(?:^|[\s,:;])(noindex|none)(?:$|[\s,;])", re.I)


def validate_url(url, origin):
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or parsed.netloc != urllib.parse.urlsplit(origin).netloc
            or parsed.username or parsed.password or parsed.fragment
            or any(ord(c) < 33 for c in url)):
        raise ValueError("URL must stay on the exact reviewed HTTPS origin")
    return url


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def encoded_path(value):
    value = urllib.parse.quote(value, safe="/?&=;+,:@!$'()*[]%-._~")
    def normalize(match):
        char = chr(int(match[0][1:], 16))
        return char if char.isascii() and (char.isalnum() or char in "-._~") else match[0].upper()
    return re.sub(r"%[0-9a-fA-F]{2}", normalize, value)


class RobotsPolicy:
    """Search REP rules: specific groups, merged repeats, longest path, allow ties.

    Unlike urllib.robotparser's first-match policy, this detects an accidental
    Disallow below an existing Allow: /. Supports * and $ path matching.
    """
    def __init__(self, content):
        self.groups, self.sitemaps = [], []
        agents, rules = [], []
        for raw in content.splitlines():
            line = raw.split("#", 1)[0].strip()
            if ":" not in line:
                continue
            field, value = (part.strip() for part in line.split(":", 1))
            field = field.lower()
            if field == "sitemap":
                self.sitemaps.append(value)
            elif field == "user-agent":
                if rules:
                    self.groups.append((agents, rules))
                    agents, rules = [], []
                token = re.match(r"[a-z_-]+", value.lower())
                agents.append(token[0] if token else value.lower())
            elif field in {"allow", "disallow"} and agents:
                rules.append((field == "allow", encoded_path(value)))
        if agents:
            self.groups.append((agents, rules))

    def can_fetch(self, bot, url):
        candidates = []
        for agents, rules in self.groups:
            matches = [0 if a == "*" else len(a) for a in agents if a == "*" or (a and bot.lower().startswith(a))]
            if matches:
                candidates.append((max(matches), rules))
        if not candidates:
            return True
        specificity = max(rank for rank, _ in candidates)
        parsed = urllib.parse.urlsplit(url)
        path = encoded_path((parsed.path or "/") + ("?" + parsed.query if parsed.query else ""))
        matches = []
        for rank, rules in candidates:
            if rank != specificity:
                continue
            for allowed, rule in rules:
                if not rule:
                    continue
                rule = rule.rstrip("*")
                anchored = rule.endswith("$")
                pattern = rule[:-1] if anchored else rule
                expression = "^" + ".*".join(re.escape(part) for part in pattern.split("*")) + ("$" if anchored else "")
                if re.search(expression, path):
                    matches.append((len(rule.encode()), allowed))
        return max(matches, default=(0, True))[1]


def fetch(url, origin, plain=False):
    validate_url(url, origin)
    headers = {"Accept": "*/*"}
    if not plain:
        headers["User-Agent"] = AGENT
    request = urllib.request.Request(url, headers=headers)
    opener = urllib.request.build_opener(NoRedirect)
    try:
        try:
            response = opener.open(request, timeout=15)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise ValueError("response exceeds the reviewed byte limit")
            return {"url": url, "status": response.status,
                    "headers": {k.lower(): v for k, v in response.headers.items()},
                    "body": body, "error": None}
    except (OSError, ValueError) as error:
        return {"url": url, "status": None, "headers": {}, "body": b"", "error": str(error)}


def require_response(response, types):
    if response["error"] or response["status"] != 200:
        raise ValueError(f"HTTP {response['status']}: {response['error'] or 'expected 200 without redirect'}")
    media = response["headers"].get("content-type", "").split(";", 1)[0].lower().strip()
    if media not in types:
        raise ValueError(f"unexpected content type {media!r}")
    if NOINDEX.search(response["headers"].get("x-robots-tag", "")):
        raise ValueError("HTTP X-Robots-Tag prevents indexing")
    return response["body"].decode("utf-8")


def sitemap_locations(body, origin):
    # Do not process entities, DTDs, unbounded indexes, or off-site URLs.
    if b"<!DOCTYPE" in body.upper() or b"<!ENTITY" in body.upper():
        raise ValueError("DTD/entity declarations are not admitted")
    root = ET.fromstring(body)
    if root.tag == NS + "urlset":
        rows, kind = root.findall(NS + "url"), "pages"
    elif root.tag == NS + "sitemapindex":
        rows, kind = root.findall(NS + "sitemap"), "sitemaps"
    else:
        raise ValueError("missing sitemap namespace or unsupported root")
    locations = [(row.findtext(NS + "loc") or "").strip() for row in rows]
    if not locations or len(locations) > MAX_URLS:
        raise ValueError("empty or oversized sitemap")
    if len(locations) != len(set(locations)):
        raise ValueError("duplicate locations in sitemap")
    for url in locations:
        validate_url(url, origin)
    return kind, locations


class PageMetadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_title = False
        self.title = ""
        self.canonicals = []
        self.description = ""
        self.noindex = False

    def handle_starttag(self, tag, attrs):
        attrs = {key: value or "" for key, value in attrs}
        if tag == "title":
            self.in_title = True
        if tag == "link" and "canonical" in attrs.get("rel", "").lower().split():
            self.canonicals.append(attrs.get("href", ""))
        if tag == "meta":
            name, content = attrs.get("name", "").lower(), attrs.get("content", "")
            if name == "description":
                self.description = content.strip()
            if name in {"robots", *(bot.lower() for bot in SEARCH_BOTS)} and NOINDEX.search(content):
                self.noindex = True

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data


def validate_page(response, url):
    suffix = Path(urllib.parse.urlsplit(url).path).suffix.lower()
    if suffix == ".json":
        content = require_response(response, {"application/json"})
        document = json.loads(content)
        if not isinstance(document, (dict, list)) or not document:
            raise ValueError("empty or invalid public JSON document")
        return
    if suffix == ".md":
        content = require_response(response, {"text/markdown", "text/plain"})
        if len(content.strip()) < 100:
            raise ValueError("empty public Markdown document")
        return
    page = PageMetadata()
    page.feed(require_response(response, {"text/html", "application/xhtml+xml"}))
    problems = []
    if not page.title.strip():
        problems.append("missing title")
    if not page.description:
        problems.append("missing description")
    if page.noindex:
        problems.append("HTML robots directive prevents indexing")
    if len(page.canonicals) != 1 or urllib.parse.urljoin(url, page.canonicals[0]) != url:
        problems.append("expected one self-referencing canonical")
    if problems:
        raise ValueError("; ".join(problems))


def audit_product(product, full=False, fetcher=fetch):
    origin = product["origin"]
    result = {"product": product["name"], "origin": origin, "errors": [], "warnings": [],
              "requests": [], "sitemaps": {}, "sitemap_urls": [], "pages_checked": 0}

    def read(url, plain=False):
        response = fetcher(url, origin, plain=plain)
        result["requests"].append({"url": url, "client": "plain-python" if plain else "identified-monitor",
                                   "status": response["status"], "error": response["error"],
                                   "bytes": len(response["body"]),
                                   "sha256": hashlib.sha256(response["body"]).hexdigest()})
        return response

    def problem(url, error, warning=False):
        result["warnings" if warning else "errors"].append({"url": url, "problem": str(error)})

    robots = None
    sitemap_queue = [origin + path for path in product["sitemaps"]]
    for path in ("/robots.txt", "/llms.txt", "/.well-known/ai-catalog.json"):
        url = origin + path
        try:
            response = read(url)
            content = require_response(response, {"application/json", "application/ai-catalog+json"}
                                       if path.endswith(".json") else {"text/plain"})
            if path == "/robots.txt":
                robots = RobotsPolicy(content)
                declared = robots.sitemaps
                if origin + "/sitemap.xml" not in declared:
                    raise ValueError("robots.txt omits the primary sitemap")
                sitemap_queue.extend(declared)
            elif path.endswith(".json"):
                catalog = json.loads(content)
                if not isinstance(catalog, dict) or not catalog:
                    raise ValueError("AI catalog must be a nonempty JSON object")
            elif len(content.strip()) < 200 or origin not in content:
                raise ValueError("LLM reference is empty or lacks this product's origin")
        except (ValueError, ET.ParseError) as error:
            problem(url, error)

    visited, pages = set(), set()
    while sitemap_queue:
        url = sitemap_queue.pop(0)
        if url in visited:
            continue
        if len(visited) >= MAX_SITEMAPS:
            problem(url, "sitemap index exceeds the reviewed limit")
            break
        visited.add(url)
        try:
            validate_url(url, origin)
            response = read(url)
            require_response(response, {"application/xml", "text/xml"})
            kind, locations = sitemap_locations(response["body"], origin)
            result["sitemaps"][url] = {"kind": kind, "locations": len(locations)}
            if kind == "sitemaps":
                sitemap_queue.extend(locations)
            else:
                pages.update(locations)
                if len(pages) > MAX_URLS:
                    raise ValueError("total sitemap URLs exceed reviewed limit")
        except (ValueError, ET.ParseError) as error:
            problem(url, error)
    result["sitemap_urls"] = sorted(pages)
    if len(pages) < product["minimum_urls"]:
        problem(origin, f"sitemap coverage {len(pages)} below reviewed minimum {product['minimum_urls']}")
    required = {origin + path for path in product["pages"]}
    for url in sorted(required - pages):
        problem(url, "required entry page absent from sitemaps")

    # Policy checks cover every declared page even in the lightweight run.
    if robots is not None:
        for url in sorted(pages | required):
            blocked = [bot for bot in SEARCH_BOTS if not robots.can_fetch(bot, url)]
            if blocked:
                problem(url, "robots.txt blocks search retrieval: " + ", ".join(blocked))
    for url in sorted((pages if full else set()) | required)[:MAX_URLS]:
        try:
            validate_page(read(url), url)
        except ValueError as error:
            problem(url, error)
        result["pages_checked"] += 1

    # A generic-client block is a compatibility warning, not evidence that an
    # authenticated Google/OpenAI crawler was blocked. Do not impersonate bots.
    for path in ("/robots.txt", "/sitemap.xml", "/llms.txt", "/.well-known/ai-catalog.json"):
        response = read(origin + path, plain=True)
        if response["status"] != 200 or response["error"]:
            problem(origin + path, f"plain Python client: HTTP {response['status']}, {response['error']}", True)
    result["status"] = "FAIL" if result["errors"] else "PASS_WITH_WARNINGS" if result["warnings"] else "PASS"
    return result


def summarize(report):
    lines = ["# Public search coverage", "", f"Observed: {report['observed_at']}", "",
             "| Product | Status | Sitemap URLs | Pages checked | Errors | Warnings |",
             "| --- | --- | ---: | ---: | ---: | ---: |"]
    for p in report["products"]:
        lines.append(f"| {p['product']} | {p['status']} | {len(p['sitemap_urls'])} | {p['pages_checked']} | {len(p['errors'])} | {len(p['warnings'])} |")
    lines.extend(["", "Technical retrieval checks only. Google processing/indexing, ranking, autocomplete, AI citations, source-data coverage/freshness, and external adoption are NOT verified by this monitor."])
    for p in report["products"]:
        for severity in ("errors", "warnings"):
            for item in p[severity]:
                lines.append(f"\n- {p['product']} {severity}: `{item['url']}` — {item['problem']}")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="Fetch every declared sitemap page")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with ThreadPoolExecutor(max_workers=3) as pool:
        products = list(pool.map(lambda p: audit_product(p, args.full), PRODUCTS))
    report = {"schema": "liquilens.search-coverage.v1", "observed_at": datetime.now(timezone.utc).isoformat(),
              "full_page_audit": args.full, "operator_probe": True, "products": products,
              "google_processing_verified": False, "indexing_verified": False,
              "ranking_verified": False, "adoption_verified": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    args.output.with_suffix(".md").write_text(summarize(report))
    print(summarize(report))
    return int(any(p["errors"] for p in products))


if __name__ == "__main__":
    raise SystemExit(main())
