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
2025 clients. Its v0.1.6 identity, tool metadata, and accepted input schemas are
locked to the packaged server by
[`protocol/financial-evidence-mcp-v0.1.6.json`](../protocol/financial-evidence-mcp-v0.1.6.json).
It has no account or mutation surface and can fetch only the fixed public HTTPS
evidence routes in the committed worker.

The v0.1.6 packet keeps transport success separate from evidence evaluation and
Carrier verification. Its fixed routes and eight source adapters are copied from
the signed package core in `protocol/financial-evidence-routing-v0.1.6.json`;
only declared scalar paths are reported, with exact source-byte provenance.
Missing fields remain `not_reported`. An output cap preserves transport results
and marks `output_status` unavailable when documents must be omitted. If the
projected metadata itself still exceeds the 2 MiB packet cap, it is explicitly
marked `source_reported_omitted` with reason `encoded_output_limit`; it is never
relabeled `not_reported`. Original source byte counts, hashes and transport
results remain in the bounded receipt. The separately serialized JSON-RPC HTTP
response still has its own 4 MiB cap. The complete MCP result is measured
separately because the text mirror escapes JSON again and structured content
repeats metadata. It reserves 40 KiB for the bounded request ID and protocol
envelope; if necessary, metadata is explicitly omitted with reason
`serialized_result_limit` while the typed transport receipt is retained.

The public boundary rejects request bodies over 32 KiB and JSON-RPC batches.
All eight unique topics may be fetched in one call, producing at most nine
source records from eight distinct fixed sources. GIFT City and gold share one
public GET context: the Worker retrieves it once per packet and reuses the same
receipt, including failures, source hash and retrieval clock. These are separate
topic records of one observation, not independent corroboration. Forex uses the
bounded public forex section. No topic runs a scenario or produces an executable
quote, and the Worker preserves upstream partial, restricted and unavailable
states and source-native clocks. The package-compatible `max_bytes` ceiling is
4 MiB per source and the default is 1 MiB, while the remote endpoint additionally enforces a 1.5 MiB
aggregate source-byte budget, a 2 MiB encoded evidence-packet cap, and a 4 MiB
fully serialized HTTP-response cap. The aggregate byte budget is accounted
sequentially: a source may use the caller's full per-source ceiling while
packet capacity remains, rather than receiving an undocumented equal share.
Fetches run sequentially, accept timeouts up to 30 seconds per source, and share
a 30-second aggregate packet deadline. The
upstream abort signal also follows client cancellation. Fetches use a 30-second
edge cache and pass through a coarse 60-per-minute, per-location Cloudflare
rate-limit bucket. Topic discovery and offline route resolution remain outside
that fetch limiter. Server-side clients need no Origin header; browser requests
are accepted only from <code>https://liquilens.in</code> to preserve MCP's DNS
rebinding defense.

The catalog is imported from the repository's canonical
`.well-known/ai-catalog.json`; do not maintain a second manifest in this
directory.

Validate from the repository root:

```bash
npm ci --ignore-scripts
LIQUILENS_OFFLINE=1 python3 -m pytest tests -q
npm run test:edge
node --test tests/test_x_bridge.mjs
npm audit --audit-level=moderate
npx --no-install wrangler deploy --config wrangler.catalog.jsonc --dry-run
```

Production Worker publication is separate from merging the source and publishing
Pages. Use the existing [manual Railway signed controller](../deploy/railway-ci/edge-publisher/README.md)
with the exact current protected main SHA; it replaces execution of the legacy
`deploy-catalog-edge.yml` workflow. The v0.1.6 verification scripts change pinned
controller inputs, so assemble and review a new owner-signed controller. Keep
credentials only on its dedicated publishing service.

First reconcile retained controller evidence and any existing candidate; do not
repeat an upload after an interrupted invocation. Prepare with `PUBLISH_APPLY=0`,
then use the reviewed apply transaction with `PUBLISH_APPLY=1`. The controller
stages the candidate at zero traffic, requires exact source tag and Worker
version identity, verifies all eight routes and limiter-backed money-market,
GIFT City, forex and gold receipts, then promotes and repeats the live proof.
The GIFT City and gold receipts must match apart from topic. Transport completion
does not assert evidence eligibility, freshness or Carrier verification. On a
failed proof, the controller restores the recorded prior version while respecting
concurrent releases. Preserve the immutable v0.1.5 protocol and fixture snapshots.
