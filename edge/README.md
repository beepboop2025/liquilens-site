# LiquiLens catalog edge route

GitHub Pages remains the site host. This Worker owns only
`https://liquilens.in/.well-known/ai-catalog.json`, so the ARD catalog remains
available with its preferred media type and CORS headers if a Pages deployment
is delayed.

The catalog is imported from the repository's canonical
`.well-known/ai-catalog.json`; do not maintain a second manifest in this
directory.

Validate and deploy from the repository root:

```bash
node --test tests/test_catalog_worker.mjs
npx wrangler deploy --config wrangler.catalog.jsonc --dry-run
npx wrangler deploy --config wrangler.catalog.jsonc
```

Production deployment is also available through the manual **Deploy AI catalog
edge Worker** workflow. Its `production` environment requires
`CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`; store them as GitHub
environment secrets and never paste their values into an issue or workflow
input. The workflow deploys with Wrangler 4.125.0 and requires the anonymous
edge response to equal the committed catalog before it succeeds.
