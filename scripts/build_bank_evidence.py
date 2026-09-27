#!/usr/bin/env python3
"""Build citable filing snapshots from accepted public evidence, never bank scores.

--fetch captures today's observed records from the public API. Review the diff
before the normal Pages release. --check reproduces committed HTML and hashes
offline; it never silently substitutes a newer filing for a reviewed snapshot.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
from html import escape
import json
import math
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

try:
    from scripts.social_cards import render_card, route_card_spec
    from scripts.static_social_cards import inject_metadata
except ModuleNotFoundError:  # direct execution
    from social_cards import render_card, route_card_spec
    from static_social_cards import inject_metadata

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://liquilens.in"
API = "https://api.liquilens.in/api/experimental/v1/banking"
PREFIX = "/banking/institutions/"
SCHEMA = "liquilens.public-filing-snapshot.v1"
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
LIMIT = "Research evidence, not a credit rating, deposit-safety conclusion or investment advice."


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def digest(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def safe_url(value):
    if not isinstance(value, str):
        raise ValueError("source URL must be text")
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("source URL must be public HTTPS without credentials")
    return value


def validate(record, expected_slug):
    if not SLUG.fullmatch(expected_slug) or record.get("slug") != expected_slug:
        raise ValueError("institution identity mismatch")
    if record.get("schema") != "liquilens.bank-specialisation.v1" or record.get("scope") != "research":
        raise ValueError("unsupported evidence contract")
    if record.get("score_authority") is not False or record.get("can_authorize_credit") is not False:
        raise ValueError("snapshot must have no scoring or credit authority")
    if record.get("status") not in {"observed", "stale", "historical", "unavailable"}:
        raise ValueError("unknown evidence state")
    if date.fromisoformat(record["period_end"]) > date.fromisoformat(record["as_of"]):
        raise ValueError("future reporting period")
    if not isinstance(record.get("name"), str) or not record["name"].strip():
        raise ValueError("institution name missing")
    if not record.get("sources") or not record.get("interpretation_limits"):
        raise ValueError("source trail and limits required")
    for source in record["sources"]:
        safe_url(source)
    for document in record.get("source_documents", []):
        safe_url(document["url"])
        if not re.fullmatch(r"[0-9a-f]{64}", document.get("sha256", "")):
            raise ValueError("source document digest missing")
    for metric in record.get("metrics", {}).values():
        value = metric.get("value")
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
            raise ValueError("metric must be finite or absent")
        if value is not None and not metric.get("unit"):
            raise ValueError("numeric metric without unit")
    return record


def metric_value(metric):
    value = metric.get("value")
    state = metric.get("status", "unavailable")
    if value is None or state not in {"observed", "stale", "historical"}:
        return "Not disclosed / unavailable"
    suffix = {"percent": "%", "INR_crore": " INR crore"}.get(metric["unit"], " " + metric["unit"])
    number = format(Decimal(str(value)), ',f')
    if '.' in number:
        number = number.rstrip('0').rstrip('.')
    return number + suffix


def shell(title, description, path, body, structured):
    url = SITE + path
    metadata = encoded(structured).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' https://static.cloudflareinsights.com; style-src 'self'; img-src 'self' data:; connect-src 'self' https://cloudflareinsights.com; object-src 'none'; base-uri 'self'">
<title>{escape(title)}</title><meta name="description" content="{escape(description, quote=True)}">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
<link rel="canonical" href="{url}"><link rel="stylesheet" href="/banking/style.css"><link rel="stylesheet" href="/banking/institutions/evidence.css">
<meta property="og:type" content="article"><meta property="og:site_name" content="LiquiLens"><meta property="og:url" content="{url}"><meta property="og:title" content="{escape(title, quote=True)}"><meta property="og:description" content="{escape(description, quote=True)}">
<script type="application/ld+json">{metadata}</script></head><body>
<a class="skip" href="#main">Skip to evidence</a><header class="shell top"><a class="brand" href="/">LiquiLens</a><nav aria-label="Main"><a href="/banking/">Bank research</a><a href="{PREFIX}">Filing evidence</a><a href="/developers/">API + MCP</a></nav></header>
<main id="main" class="shell">{body}<p class="boundary">{LIMIT} Missing disclosures remain missing. Latest accepted means latest in this corpus, not a guarantee that no newer filing exists.</p></main>
<footer class="shell"><a href="/about/">About LiquiLens</a><span><a href="/banking/#methods">Methods</a> · <a href="/terms/">Terms</a> · <a href="/privacy/">Privacy</a> · <a href="https://t.me/LiquiLens_bot?start=tool_review">Research bot</a></span></footer></body></html>\n'''


def evidence_card(*, path, name, period, status, signature, collection=False):
    spec = route_card_spec(
        slug='filing-evidence' if collection else path.strip('/').split('/')[-1],
        canonical_path=path, eyebrow='LIQUILENS / FILING EVIDENCE', subject=name,
        title='Source-linked bank disclosures.' if collection else 'NPA, capital and funding disclosures.',
        clock_label='SNAPSHOT CAPTURE' if collection else 'REPORTING PERIOD', clock=period,
        status=status, source='ACCEPTED ISSUER FILINGS', role_label='RESEARCH SNAPSHOT',
        role_value='SOURCE DATES + JSON', role_detail='REPORTED VALUES / EXPLICIT MISSING DATA',
        signature_label='EVIDENCE', signature=signature,
    )
    return render_card(spec, SITE + path)


def record_card(snapshot):
    record = snapshot['evidence']
    return evidence_card(path=PREFIX + record['slug'] + '/', name=record['name'],
                         period=record['period_end'], status=record['status'] + ' AT CAPTURE',
                         signature=snapshot['source_payload_sha256'])


def index_card(manifest):
    return evidence_card(path=PREFIX, name='BANK FILING EVIDENCE',
                         period=manifest['captured_at'][:10], status='DATED RESEARCH SNAPSHOTS',
                         signature=digest(manifest), collection=True)


def render_record(snapshot, card=None):
    record = validate(snapshot["evidence"], snapshot["evidence"]["slug"])
    if snapshot.get("schema") != SCHEMA or digest(record) != snapshot.get("source_payload_sha256"):
        raise ValueError("snapshot digest or schema mismatch")
    slug = record["slug"]; name = record["name"]; path = PREFIX + slug + "/"
    if snapshot.get('api_url') != API + '/institutions/' + slug + '?include_history=true':
        raise ValueError('snapshot API route does not match institution')
    captured = datetime.fromisoformat(snapshot['captured_at'].replace('Z', '+00:00'))
    if captured.tzinfo is None:
        raise ValueError('snapshot capture clock needs timezone')
    title = f"{name}: NPA, capital and funding evidence | LiquiLens"
    description = f"Dated {name} filing evidence for {record['period_end']}: reported NPA, capital and funding disclosures, source citations and explicit missing data."
    metrics = "".join(f"<tr><th scope=\"row\">{escape(m['label'])}</th><td>{escape(metric_value(m))}</td><td>{escape(m.get('status', 'unavailable'))}</td><td>{escape(m.get('basis') or 'As labelled in the accepted record.')}</td></tr>" for m in record["metrics"].values())
    documents = {d['url']: d for d in record.get('source_documents', [])}
    sources = []
    for url in record['sources']:
        document = documents.get(url, {})
        details = ""
        if document.get('pdf_pages'):
            details += "<p>PDF pages: " + escape(", ".join(map(str, document['pdf_pages']))) + "</p>"
        if document.get('sha256'):
            details += "<p>Source document SHA-256: <code>" + document['sha256'] + "</code></p>"
        sources.append(f'<li><a href="{escape(url, quote=True)}">Source filing at {escape(urlsplit(url).hostname)}</a>{details}</li>')
    limits = list(record.get('interpretation_limits', [])) + list(record.get('comparability_notes', []))
    missing = record.get('next_disclosures', [])
    movement = record.get('npa_movement', {})
    movement_text = movement.get('reason') or 'Read the accepted NPA movement fields in the linked evidence JSON; no cash-recovery conclusion is inferred from a ratio change.'
    citation = f"LiquiLens. {name}: filing evidence for period ending {record['period_end']}. Evidence snapshot captured {snapshot['captured_at']}; source publication {record.get('publication_date') or 'not supplied'}. {SITE + path}"
    structured = {"@context":"https://schema.org", "@type":"Dataset", "@id":SITE + path + "#dataset", "url":SITE + path,
        "name":title.replace(' | LiquiLens', ''), "description":description + ' ' + LIMIT,
        "creator":{"@type":"Organization", "name":"LiquiLens", "url":SITE + '/about/'},
        "dateModified":snapshot['captured_at'], "temporalCoverage":record['period_end'],
        "identifier":"sha256:" + snapshot['source_payload_sha256'], "isBasedOn":record['sources'],
        "measurementTechnique":"Selected disclosed facts from accepted issuer filings; definitions, absent values and reporting clocks are preserved.",
        "variableMeasured":[m['label'] for m in record['metrics'].values()],
        "distribution":[{"@type":"DataDownload", "encodingFormat":"application/json", "contentUrl":SITE + path + 'evidence.json'}],
        "isPartOf":{"@type":"DataCatalog", "name":"LiquiLens accepted bank filing evidence", "url":SITE + PREFIX}}
    body = f'''<section class="hero"><p class="eyebrow">Accepted filing evidence · dated research snapshot</p><h1>{escape(name)}</h1><p class="lede">Reported NPA, capital and funding disclosures for the period ending <strong>{record['period_end']}</strong>. Read every value with its definition and source.</p><p class="evidence-state">Evidence state at capture: <strong>{escape(record['status'])}</strong>. This page is a dated snapshot, not a live bank-health assessment.</p><div class="actions"><a class="button" href="evidence.json">Download cited evidence JSON</a><a class="button secondary" href="{escape(snapshot['api_url'], quote=True)}">Check latest accepted API record</a></div></section>
<section class="section"><h2>Keep the clocks separate</h2><dl class="evidence-clocks"><dt>Reporting period</dt><dd>{record['period_end']} · {escape(record.get('quarter') or '')}</dd><dt>Source publication date</dt><dd>{escape(record.get('publication_date') or 'Not supplied')}</dd><dt>Evidence available in the corpus</dt><dd>{escape(record.get('available_at') or 'Not supplied')}</dd><dt>Source retrieval</dt><dd>{escape(record.get('retrieved_at') or 'Not supplied')}</dd><dt>This snapshot captured</dt><dd>{escape(snapshot['captured_at'])}</dd></dl><p>The source period, publication date and capture time are different facts. The snapshot does not become current because this page is fetched again.</p></section>
<section class="section"><h2>Disclosed figures and missing evidence</h2><div class="evidence-scroll"><table><caption>{escape(name)} · {record['period_end']} · source definitions retained</caption><thead><tr><th scope="col">Disclosure</th><th scope="col">Value</th><th scope="col">State</th><th scope="col">Definition / basis</th></tr></thead><tbody>{metrics}</tbody></table></div></section>
<section class="section"><h2>NPA movement</h2><p>Accepted movement status: <strong>{escape(movement.get('status', 'unavailable'))}</strong>.</p><p>{escape(movement_text)}</p><p>A reduction in an NPA ratio does not identify cash recovered. Loan growth, upgrades, write-offs and sales have different meanings.</p></section>
<section class="section"><h2>Read the primary filings</h2><ul class="source-list">{''.join(sources)}</ul><p>Original reports remain with their publishers. This page does not grant a licence to redistribute the linked reports.</p></section>
<section class="section"><h2>What this record does not establish</h2><ul>{''.join('<li>'+escape(item)+'</li>' for item in limits)}</ul><p>This page assigns no credit score, bank ranking, regulatory action or deposit-safety verdict. Supervisory scope and licence changes require separate dated evidence.</p><h3>Disclosures to examine next</h3><ul>{''.join('<li>'+escape(item)+'</li>' for item in missing)}</ul></section>
<section class="section"><h2>Cite this record</h2><blockquote>{escape(citation)}</blockquote><p>Snapshot payload SHA-256: <code>{snapshot['source_payload_sha256']}</code>. The digest identifies the captured API evidence; source PDF digests are listed separately above.</p><p><a href="{PREFIX}">Browse accepted filing snapshots</a> · <a href="/banking/">Interactive bank review</a> · <a href="/developers/institutions/">Institution research for agents</a></p></section>'''
    return inject_metadata(shell(title, description, path, body, structured),
                           route=path, card=card or record_card(snapshot), og_type='article')


def render_index(manifest, card=None):
    rows = manifest['records']
    title = "Bank filing evidence: NPA, capital and funding disclosures | LiquiLens"
    description = "Browse dated, source-linked Indian bank filing snapshots with reported NPA, capital and funding disclosures, JSON downloads and explicit missing evidence."
    links = ''.join(f'<tr><th scope="row"><a href="{r["slug"]}/">{escape(r["name"])}</a></th><td>{r["period_end"]}</td><td>{escape(r["status"])}</td></tr>' for r in rows)
    body = f'''<section class="hero"><p class="eyebrow">Public filing evidence · readable without JavaScript</p><h1>Bank disclosures you can inspect and cite.</h1><p class="lede">These {len(rows)} snapshots preserve accepted filing evidence, source links and missing disclosures. Each page identifies its reporting period and capture date.</p><p>Coverage snapshot: {escape(manifest['captured_at'])}. This collection contains records observed at capture. It is not a census of Indian banks or a ranking.</p></section><section class="section"><h2>Accepted filing snapshots</h2><div class="evidence-scroll"><table><caption>Institution, source period and evidence state at capture</caption><thead><tr><th scope="col">Institution</th><th scope="col">Period ending</th><th scope="col">State at capture</th></tr></thead><tbody>{links}</tbody></table></div></section><section class="section"><h2>Use the source trail</h2><p>Open a record for the disclosed figures, definitions, reporting and publication dates, available source digests and the exact JSON snapshot. Check the linked live API when freshness matters. A static page's capture date never replaces a filing date.</p><p><a href="/banking/">Interactive bank research</a> · <a href="{API}/coverage">Live coverage including historical records</a> · <a href="/replay/">Historical failure replays and their limits</a> · <a href="manifest.json">Machine-readable snapshot catalog</a></p></section>'''
    structured = {"@context":"https://schema.org", "@type":"DataCatalog", "name":"LiquiLens accepted bank filing evidence", "description":description, "url":SITE + PREFIX,
        "creator":{"@type":"Organization", "name":"LiquiLens", "url":SITE + '/about/'},
        "dataset":[{"@type":"Dataset", "name":r['name'] + ' filing evidence', "url":SITE + PREFIX + r['slug'] + '/'} for r in rows]}
    return inject_metadata(shell(title, description, PREFIX, body, structured),
                           route=PREFIX, card=card or index_card(manifest), og_type='website')


def sitemap_snapshot_block(existing, manifest):
    start = '<!-- BANKING-SNAPSHOTS:START -->'
    end = '<!-- BANKING-SNAPSHOTS:END -->'
    if existing.count(start) != existing.count(end) or existing.count(start) > 1:
        raise ValueError('invalid managed sitemap block')
    existing = re.sub(re.escape(start) + r'.*?' + re.escape(end) + r'\n?', '', existing, flags=re.S)
    urls = [SITE + PREFIX] + [SITE + PREFIX + r['slug'] + '/' for r in manifest['records']]
    stamp = datetime.fromisoformat(manifest['captured_at'].replace('Z', '+00:00')).date().isoformat()
    block = start + '\n' + ''.join(f'  <url><loc>{url}</loc><lastmod>{stamp}</lastmod></url>\n' for url in urls) + end + '\n'
    if existing.count('</urlset>') != 1:
        raise ValueError('expected one sitemap URL set')
    return existing.replace('</urlset>', block + '</urlset>')


def fetch_json(url):
    request = Request(url, headers={'Accept':'application/json', 'User-Agent':'LiquiLens-PublicEvidencePublisher/1.0'})
    with urlopen(request, timeout=30) as response:
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000: raise ValueError('public evidence response too large')
        if not response.headers.get('Content-Type', '').startswith('application/json'): raise ValueError('expected JSON evidence')
    return json.loads(raw)


def capture():
    coverage = fetch_json(API + '/coverage')
    if coverage.get('schema') != 'liquilens.bank-specialisation.v1': raise ValueError('coverage contract changed')
    selected = [r for r in coverage['rows'] if r['status'] == 'observed']
    if not 1 <= len(selected) <= 100: raise ValueError('review unexpected coverage size')
    if len({r['slug'] for r in selected}) != len(selected): raise ValueError('duplicate institution')
    captured_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    def one(row):
        slug = row['slug']
        if not SLUG.fullmatch(slug): raise ValueError('unsafe coverage slug')
        url = API + '/institutions/' + slug + '?include_history=true'
        record = validate(fetch_json(url), slug)
        if record['as_of'] != coverage['as_of'] or record['period_end'] != row['period_end'] or record['status'] != row['status']:
            raise ValueError('coverage changed during capture; retry from a consistent cut')
        return {'schema':SCHEMA, 'captured_at':captured_at, 'api_url':url, 'source_payload_sha256':digest(record), 'evidence':record}
    with ThreadPoolExecutor(max_workers=3) as pool:
        snapshots = list(pool.map(one, selected))
    manifest = {'schema':'liquilens.public-filing-catalog.v1', 'captured_at':captured_at, 'coverage_as_of':coverage['as_of'], 'selection':'observed_at_capture_not_a_census',
        'records':[{k:s['evidence'][k] for k in ('slug','name','period_end','status')} for s in snapshots]}
    return manifest, snapshots


def build(root=ROOT, fetch=False, check=False):
    destination = root / PREFIX.strip('/')
    if fetch:
        manifest, snapshots = capture()
    else:
        manifest = json.loads((destination/'manifest.json').read_text())
        snapshots = []
        for row in manifest['records']:
            if not SLUG.fullmatch(row['slug']): raise ValueError('unsafe manifest slug')
            snapshot = json.loads((destination/row['slug']/'evidence.json').read_text())
            if any(snapshot['evidence'][k] != row[k] for k in ('slug','name','period_end','status')):
                raise ValueError('catalog and snapshot disagree')
            snapshots.append(snapshot)
    collection_card = index_card(manifest)
    outputs = {destination/'index.html':render_index(manifest, collection_card),
               destination/'manifest.json':encoded(manifest), destination/'share.png':collection_card.png}
    for snapshot in snapshots:
        folder = destination/snapshot['evidence']['slug']
        card = record_card(snapshot)
        outputs[folder/'index.html'] = render_record(snapshot, card)
        outputs[folder/'evidence.json'] = encoded(snapshot)
        outputs[folder/'share.png'] = card.png
    sitemap = root/'sitemap.xml'
    if sitemap.exists():
        outputs[sitemap] = sitemap_snapshot_block(sitemap.read_text(), manifest)
    # Render and validate the entire cut before changing any output file.
    for path, content in outputs.items():
        expected = content if isinstance(content, bytes) else content.encode('utf-8')
        if check:
            if not path.exists() or path.read_bytes() != expected: raise ValueError('generated evidence differs: ' + str(path.relative_to(root)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists() or path.read_bytes() != expected: path.write_bytes(expected)
    print(f"{'Verified' if check else 'Built'} {len(snapshots)} source-linked filing snapshots")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--fetch', action='store_true')
    mode.add_argument('--check', action='store_true')
    args = parser.parse_args()
    build(fetch=args.fetch, check=args.check)
