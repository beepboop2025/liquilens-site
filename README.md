# LiquiLens public site

This repository is the source for [liquilens.in](https://liquilens.in), the public evidence and documentation site for LiquiLens.

LiquiLens monitors public signs of financial stress at banks, NBFCs, co-operative banks, and microfinance lenders. The site publishes the product definition, validation record, historical crisis replays, methodology notes, use cases, and developer entry points that can be checked without access to a private lender book.

## What belongs here

- Public product and methodology pages
- Reproducible crisis-replay pages
- Published validation artifacts and their explanatory copy
- Search, social, and machine-readable discovery files
- Links to the public API and MCP interface

The [developer guide](https://liquilens.in/developers/#research-recipes) includes
downloadable Python bank-review and funding-context recipes, named client
configurations, and a manual n8n bank-review workflow. The Python file uses the
standard library and needs no API key or LLM. The n8n guide records its tested
contract and any native execution gap. Recipes preserve the returned evidence,
source dates and limitations; none grants credit or execution authority.

The private scoring engine, customer data connectors, and production underwriting workflows do not live in this repository. The interactive demonstration is available by request at [demo.liquilens.in](https://demo.liquilens.in), and sign-in is required.

## Preview locally

The site is static and does not require a build step:

```bash
git clone https://github.com/beepboop2025/liquilens-site.git
cd liquilens-site
python3 -m http.server 8000
```

Open `http://localhost:8000`.

## Verify a change

The release gate checks that claims remain consistent across visible pages, metadata, structured data, and machine-readable discovery files:

```bash
python3 -m pip install --only-binary=:all: --require-hashes -r requirements-ci.txt
LIQUILENS_OFFLINE=1 python3 scripts/verify_public_claims.py
python3 -m pytest tests -q
node --test tests/*.mjs
```

Run the verifier without `LIQUILENS_OFFLINE=1` to compare public copy with the live API. Live-service differences are reported separately because that deployment is maintained outside this repository.

Every shareable public HTML route owns a contextual deterministic 1200x630
social card. Daily articles and historical case files are regenerated from
their reviewed structured records at `articles/<slug>/share.png` and
`replay/<slug>/share.png`; their archive publishers also own the collection
cards. Static product, guide, policy and evidence-routing pages use explicit
non-metric cards unless the route has a supported public datum. The home card's
public-board counts are pinned with source identity in
`research/share-card-board.json`. Image bytes bind a digest revision to the
Open Graph, Twitter and JSON-LD image URL.

For an offline detail-card refresh without fetching evidence, run:

```bash
python3 scripts/social_cards.py --articles articles --replay-index replay/index.json
```

For static route generation, or to fail when a static image or metadata block
is stale, run:

```bash
python3 scripts/static_social_cards.py
python3 scripts/static_social_cards.py --check
```

The renderer uses Pillow's pinned embedded font rather than host fonts, so the
same evidence produces the same PNG bytes on CI and developer machines.

## Public discovery surfaces

- [`robots.txt`](robots.txt) contains crawler policy and discovery pointers.
- [`sitemap.xml`](sitemap.xml) lists canonical public pages.
- [`llms.txt`](llms.txt) provides a compact product and documentation index.
- [`product-card.json`](product-card.json) states identity, use cases, limits, and public endpoints.
- [`world-economy/index.html`](world-economy/index.html) routes system-funding, institution-risk, market-exit, and revision-safe China-evidence questions without collapsing them into one score.
- [`money-markets/index.html`](money-markets/index.html), [`capital-markets/index.html`](capital-markets/index.html), and [`china-economy/index.html`](china-economy/index.html) are bounded intent routers with distinct evidence ownership and CTA attribution.
- [`world-economy/evidence-catalog.json`](world-economy/evidence-catalog.json) publishes four independent Schema.org `Dataset` records, source lineage, canonical distributions, and Palimpsest's explicit `financial authority: none` boundary.
- [`research/lab-reviewed-status-2026-08-09.json`](research/lab-reviewed-status-2026-08-09.json) publishes the bounded LiquiLens Lab reviewed-status receipt.
- [`.well-known/ai-catalog.json`](.well-known/ai-catalog.json) describes public resources for compatible agents.
- [`.well-known/security.txt`](.well-known/security.txt) gives the vulnerability-reporting route.

These files describe the same product from different interfaces. When changing a product claim or endpoint, update every affected surface and run the verification suite.

## Telegram-to-X handoff

[`go/x/index.html`](go/x/index.html) is a noindex, first-party handoff used by
reviewed Telegram buttons. It requires exactly one allowed `from`, `topic`, and
`action` value before emitting a property-free `community_growth` event. The
`follow` action opens X's official follow intent, while `share` opens a
topic-matched draft with fixed, reviewed copy; neither action follows or posts
automatically. The analytics request is a CORS-safelisted, keepalive delivery
and navigation does not wait for it.

Shared drafts link to [`go/telegram/index.html`](go/telegram/index.html), a
noindex Open Graph fallback that returns readers to the matching useful bot
view. Its compact `x26_crypto_<source>_<intent>` references remain within
Telegram's 64-byte start-parameter limit. Missing, invalid, duplicate, and
`operator_rehearsal` inputs still navigate safely through the non-counting
`qa` route but emit no growth event. An explicitly valid `organic` source is
countable; malformed attribution is never silently relabeled organic.

Release the API event allowlist first, this static route second, and bot/channel
buttons last. A bridge redirect measures an attempted X profile or composer
handoff or an attempted return to Telegram. It is not evidence of a follow, a
published post, a bot activation, or a retained member.

## Deployment

Merges to `main` run the consistency gate and deploy the static files to GitHub Pages. The workflow excludes test and verification code from the published artifact.

## Related repositories

- [LiquiLens MCP](https://github.com/beepboop2025/liquilens-mcp): public MCP connector and tool documentation
- [LiquiLens demo](https://github.com/beepboop2025/liquilens-demo): compiled interactive demonstration
- [Seiche](https://github.com/beepboop2025/seiche): open-source dollar funding stress monitor
- [Undertow MCP](https://github.com/beepboop2025/undertow-mcp): market-liquidity data connector
