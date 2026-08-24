# LiquiLens public edge routes

GitHub Pages remains the site host. This Worker owns the ARD catalog at
`https://liquilens.in/.well-known/ai-catalog.json` and the stateless, read-only
Financial Evidence MCP endpoint at
`https://liquilens.in/mcp/financial-evidence`. Every other path returns `404`.

The MCP endpoint exposes three read-only tools for LiquiLens, Undertow, Seiche,
and Palimpsest over current Streamable HTTP, with stateless compatibility for
2025 clients. It has no account or mutation surface and can fetch only the
fixed public HTTPS evidence routes in the committed worker.

The catalog is imported from the repository's canonical
`.well-known/ai-catalog.json`; do not maintain a second manifest in this
directory.

Validate and deploy from the repository root:

```bash
npm ci --ignore-scripts
npm run test:edge
npx wrangler deploy --config wrangler.catalog.jsonc --dry-run
npx wrangler deploy --config wrangler.catalog.jsonc
```

Production deployment is also available through the manual **Deploy AI catalog
edge Worker** workflow. Its `production` environment requires
`CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`; store them as GitHub
environment secrets and never paste their values into an issue or workflow
input. The workflow deploys with Wrangler 4.125.0 and requires the anonymous
edge response to equal the committed catalog before it succeeds.
