# LiquiLens public edge routes

GitHub Pages remains the site host. This Worker owns the ARD catalog at
`https://liquilens.in/.well-known/ai-catalog.json` and the stateless, read-only
Financial Evidence MCP endpoint at
`https://liquilens.in/mcp/financial-evidence`. It also owns the optional OpenAI
Apps domain-verification route at
`https://liquilens.in/.well-known/openai-apps-challenge`. Every other path
returns `404`.

The OpenAI Apps route is fail-closed. Without the dedicated
`OPENAI_APPS_CHALLENGE_TOKEN` Worker secret it returns `404`; after OpenAI
issues a challenge value, store that exact value without quotes or a trailing
newline:

```bash
npx --no-install wrangler secret put OPENAI_APPS_CHALLENGE_TOKEN \
  --config wrangler.catalog.jsonc
```

Once configured, `GET` returns only the exact token as `text/plain`, `HEAD`
returns the same metadata without a body, and every other method returns `405`.
Never commit the issued token or pass it through a workflow input.

The MCP endpoint exposes three read-only tools for LiquiLens, Undertow, Seiche,
and Palimpsest over current Streamable HTTP, with stateless compatibility for
2025 clients. It has no account or mutation surface and can fetch only the
fixed public HTTPS evidence routes in the committed worker.

The public boundary rejects request bodies over 32 KiB and JSON-RPC batches.
Only two unique topics may be fetched per call, individual upstream documents
are capped at 768 KiB, the aggregate source-byte budget is 1.5 MiB, the encoded
evidence packet is capped at 2 MiB, and the fully serialized HTTP response is
capped at 4 MiB. Fetches run sequentially, use a 30-second edge cache, and pass
through a coarse 60-per-minute, per-location Cloudflare rate-limit bucket.
Topic discovery and offline route resolution remain outside that fetch limiter.
Server-side clients need no Origin header; browser requests are accepted only
from <code>https://liquilens.in</code> to preserve MCP's DNS rebinding defense.

The catalog is imported from the repository's canonical
`.well-known/ai-catalog.json`; do not maintain a second manifest in this
directory.

Validate and deploy from the repository root:

```bash
npm ci --ignore-scripts
npm run test:edge
npx --no-install wrangler deploy --config wrangler.catalog.jsonc --dry-run
npx --no-install wrangler deploy --config wrangler.catalog.jsonc
```

Production deployment is also available through the manual **Deploy AI catalog
edge Worker** workflow. Its `production` environment requires
`CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`; store them as GitHub
environment secrets and never paste their values into an issue or workflow
input. The workflow deploys with Wrangler 4.125.0 and requires the anonymous
edge response to equal the committed catalog before it succeeds.
