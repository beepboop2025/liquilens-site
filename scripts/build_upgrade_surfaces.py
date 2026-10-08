#!/usr/bin/env python3
"""Render connected capability entry points from one reviewed public manifest.

The optional sibling roots update only the named homepage block and stylesheet.
They are explicit build inputs, not runtime imports or deployment instructions.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
from html import escape
import json
from pathlib import Path
import re

try:
    from scripts.static_social_cards import ROUTES, _definition_card, inject_metadata
except ModuleNotFoundError:
    from static_social_cards import ROUTES, _definition_card, inject_metadata

ROOT = Path(__file__).resolve().parents[1]
START = '<!-- CONNECTED-UPGRADES:START -->'
END = '<!-- CONNECTED-UPGRADES:END -->'


def manifest(root=ROOT):
    raw = (root / 'updates/capabilities.json').read_bytes()
    data = json.loads(raw)
    if data['schema'] != 'liquilens.connected-upgrades.v1' or data['authority'] != {
        'combined_score': False, 'can_authorize_credit': False,
        'can_authorize_trade': False, 'human_review_required': True,
    }:
        raise ValueError('Unexpected capability authority')
    return data, hashlib.sha256(raw).hexdigest()


def block(data, revision):
    cards = ''.join(
        f'<article><h3>{escape(c["title"])}</h3><p>{escape(c["description"])}</p>'
        f'<small>{escape(c["state"])}</small><a href="{escape(c["url"], quote=True)}">{escape(c["action"])}</a></article>'
        for c in data['capabilities']
    )
    return (
        f'<section class="family-upgrades" aria-labelledby="connected-upgrades-heading" data-upgrade-revision="{revision}">'
        f'<div class="family-upgrades-intro"><h2 id="connected-upgrades-heading">{escape(data["title"])}</h2>'
        f'<p>{escape(data["description"])}</p><a href="https://liquilens.in/updates/">What changed and what each tool can do</a></div>'
        f'<div class="family-upgrades-grid">{cards}</div>'
        '<p class="family-upgrades-boundary">Each source keeps its dates, coverage and permissions. '
        'These tools support human review; they do not produce a combined risk score or authorize credit or trading.</p></section>'
    )


def page(title, path, description, body):
    url = 'https://liquilens.in' + path
    source = f'''<!doctype html>
<html lang="en" class="research-interface" data-product="liquilens"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} | LiquiLens</title><meta name="description" content="{escape(description, quote=True)}">
<link rel="canonical" href="{url}"><link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%23E3B778'/%3E%3Ctext x='16' y='23' font-family='Georgia,serif' font-size='20' font-weight='600' fill='%231A1206' text-anchor='middle'%3EL%3C/text%3E%3C/svg%3E" type="image/svg+xml">
<link rel="stylesheet" href="/research-ui/research.css"><link rel="stylesheet" href="/research-ui/institution-monitor.css"><link rel="stylesheet" href="/research-ui/family-upgrades.css">
<meta property="og:type" content="website"><meta property="og:url" content="{url}"><meta property="og:title" content="{escape(title, quote=True)}"><meta property="og:description" content="{escape(description, quote=True)}">
<script type="application/ld+json">{json.dumps({'@context':'https://schema.org','@type':'WebPage','name':title,'url':url,'description':description,'publisher':{'@type':'Organization','name':'LiquiLens','legalName':'LIQUILENS PRIVATE LIMITED'}})}</script>
</head><body class="research-site"><a class="research-skip" href="#main">Skip to content</a>
<header class="research-header"><div class="research-mast"><a class="research-identity" href="/"><span><strong>LiquiLens</strong><small>Institution intelligence</small></span></a><nav class="research-network" aria-label="Products"><a href="/">LiquiLens</a><a href="https://seiche.info/">Seiche</a><a href="https://liquilens-undertow.com/">Undertow</a></nav><a class="research-api" href="/agents/">API &amp; agents</a></div><nav class="research-tabs" aria-label="LiquiLens sections"><a href="/">Overview</a><a href="/banking/monitoring/">Institution monitoring</a><a href="/banking/">Banking research</a><a href="/start/">Review workspace</a><a href="/updates/">Product updates</a></nav></header>
<main id="main" class="research-page">{body}</main>
<footer class="research-page rw-footer"><p>LiquiLens · LIQUILENS PRIVATE LIMITED · Research for human review.</p><nav aria-label="Further information"><a href="/investors/">Company &amp; investors</a><a href="/research/">Methods &amp; evidence</a><a href="/privacy/">Privacy</a><a href="/terms/">Terms</a></nav></footer>
<script type="module" src="/research-ui/institution-monitor.mjs"></script></body></html>
'''
    card = _definition_card(next(row for row in ROUTES if row.path == path))
    # Page copy uses the committed asset's identity across platforms. The
    # independent social-card build still verifies the image on native CI.
    image_path = ROOT / path.strip('/') / 'share.png'
    if image_path.is_file():
        payload = image_path.read_bytes()
        revision = hashlib.sha256(payload).hexdigest()[:16]
        card = replace(card, png=payload, revision=revision,
                       url=url + 'share.png?v=' + revision)
    return inject_metadata(source, route=path, card=card, og_type='website')


def outputs(root=ROOT):
    data, revision = manifest(root)
    section = block(data, revision)
    intro = '<section class="research-intro"><div><h1>Institution monitoring.</h1><p>Keep the gaps in view. Review dated changes, overdue disclosures and the primary sources behind each institution record.</p></div></section>'
    monitor = intro + '<institution-monitor id="institution-monitor" aria-label="Institution evidence monitoring"><p>Enable JavaScript for the review queue, or <a href="https://api.liquilens.in/api/experimental/v1/banking/monitoring/watchlist">read the public source register</a>.</p></institution-monitor>'
    monitor += '<section class="rw-follow"><h2>Use the same evidence in your workflow</h2><p>The public API and MCP tool <code>institution_evidence_monitor</code> use the same monitoring contract. Source dates, missing fields and human review remain explicit.</p><p><a href="/agents/">Connect an agent</a> · <a href="/banking/institutions/">Read filing snapshots</a> · <a href="/updates/">Explore the connected tools</a></p></section>'
    update_intro = '<section class="research-intro"><div><h1>Stronger reviews. Connected evidence.</h1><p>Recent upgrades connect institution monitoring, recurring research, noise analysis and paper rehearsal. Choose the part of the review you need; each product retains its own evidence and authority.</p></div></section>'
    products = '<section class="rw-follow"><h2>Three distinct evidence roles</h2><div class="rw-follow-grid">' + ''.join(f'<article><h3>{escape(p["name"])}</h3><p>{escape(p["owns"])}</p><a href="{escape(p["url"],quote=True)}">Open {escape(p["name"])}</a></article>' for p in data['products']) + '</div></section>'
    records = '<section class="rw-follow"><h2>Release scope and evidence</h2><p>Reviewed 8 October 2026. This is a dated capability record. Source observations have their own dates; the monitor reads the current source register when opened.</p><dl class="upgrade-evidence">'
    for capability in data['capabilities']:
        records += f'<dt>{escape(capability["title"])}</dt><dd>{escape(capability["boundary"])} <a href="{escape(capability["source"],quote=True)}">Reviewed source</a></dd>'
    records += '</dl><p><a href="/updates/capabilities.json">Machine-readable capability record</a></p></section>'
    home = (root / 'index.html').read_text()
    marked = START + '\n' + section + '\n' + END
    if START in home:
        home = re.sub(re.escape(START) + r'.*?' + re.escape(END), lambda _: marked, home, flags=re.S)
    else:
        home = home.replace('<institution-analytics ', marked + '\n<institution-analytics ', 1)
    if marked not in home:
        raise ValueError('LiquiLens homepage insertion point not found')
    return {
        root / 'index.html': home,
        root / 'banking/monitoring/index.html': page('Institution monitoring', '/banking/monitoring/', 'Review institution evidence, changes and visibility gaps with original source dates and human review boundaries.', monitor),
        root / 'updates/index.html': page('Connected product upgrades', '/updates/', data['description'], update_intro + section + products + records),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--undertow-root', type=Path)
    parser.add_argument('--seiche-root', type=Path)
    args = parser.parse_args()
    rendered = outputs()
    data, revision = manifest()
    section = block(data, revision)
    css = (ROOT / 'research-ui/family-upgrades.css').read_text()
    if args.undertow_root:
        file = args.undertow_root / 'index.html'
        source = file.read_text()
        marked = START + '\n' + section + '\n' + END
        if START in source:
            source = re.sub(re.escape(START)+r'.*?'+re.escape(END),lambda _:marked,source,flags=re.S)
        else:
            source = source.replace('<liquidity-analytics ',marked+'\n<liquidity-analytics ',1)
        if marked not in source:
            raise ValueError('Undertow homepage insertion point not found')
        if '/research-ui/family-upgrades.css' not in source:
            source = source.replace('</head>','<link rel="stylesheet" href="/research-ui/family-upgrades.css">\n</head>')
        rendered[file] = source
        rendered[args.undertow_root / 'research-ui/family-upgrades.css'] = css
    if args.seiche_root:
        file = args.seiche_root / 'frontend/src/ProductHome.tsx'
        source = file.read_text()
        start,end = '{/* CONNECTED-UPGRADES:START */}','{/* CONNECTED-UPGRADES:END */}'
        marked = start + '\n' + section.replace(' class="', ' className="') + '\n' + end
        if start in source:
            source = re.sub(re.escape(start)+r'.*?'+re.escape(end),lambda _:marked,source,flags=re.S)
        else:
            source = source.replace('      <FundingPreview />','      <FundingPreview />\n      '+marked,1)
        if marked not in source:
            raise ValueError('Seiche homepage insertion point not found')
        if './family-upgrades.css' not in source:
            source = 'import "./family-upgrades.css";\n' + source
        rendered[file] = source
        rendered[args.seiche_root / 'frontend/src/family-upgrades.css'] = css
    mismatches = []
    for path, content in rendered.items():
        if args.check:
            if not path.exists() or path.read_text() != content:
                mismatches.append(str(path))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    if mismatches:
        raise SystemExit('Generated capability surfaces differ: ' + ', '.join(mismatches))
    print(('Verified' if args.check else 'Generated') + f' {len(rendered)} surfaces; revision {revision}')


if __name__ == '__main__':
    main()
