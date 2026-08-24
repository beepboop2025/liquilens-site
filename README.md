# LiquiLens public site

This repository is the source for [liquilens.in](https://liquilens.in), the public evidence and documentation site for LiquiLens.

LiquiLens monitors public signs of financial stress at banks, NBFCs, co-operative banks, and microfinance lenders. The site publishes the product definition, validation record, historical crisis replays, methodology notes, use cases, and developer entry points that can be checked without access to a private lender book.

## What belongs here

- Public product and methodology pages
- Reproducible crisis-replay pages
- Published validation artifacts and their explanatory copy
- Search, social, and machine-readable discovery files
- Links to the public API and MCP interface

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
LIQUILENS_OFFLINE=1 python3 scripts/verify_public_claims.py
python3 -m pytest tests -q
```

Run the verifier without `LIQUILENS_OFFLINE=1` to compare public copy with the live API. Live-service differences are reported separately because that deployment is maintained outside this repository.

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

## Deployment

Merges to `main` run the consistency gate and deploy the static files to GitHub Pages. The workflow excludes test and verification code from the published artifact.

## Related repositories

- [LiquiLens MCP](https://github.com/beepboop2025/liquilens-mcp): public MCP connector and tool documentation
- [LiquiLens demo](https://github.com/beepboop2025/liquilens-demo): compiled interactive demonstration
- [Seiche](https://github.com/beepboop2025/seiche): open-source dollar funding stress monitor
- [Undertow MCP](https://github.com/beepboop2025/undertow-mcp): market-liquidity data connector
