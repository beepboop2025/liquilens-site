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
