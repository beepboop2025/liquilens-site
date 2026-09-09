# Manual Railway catalog Worker publisher

This isolated controller replaces the execution of `deploy-catalog-edge.yml`
for the single `liquilens-ai-catalog` Worker. It has no cron, repository trigger,
public endpoint or PR environment instance. Each invocation requires an explicit
`EXPECTED_MAIN_SHA` equal to current protected main. `PUBLISH_APPLY=0` prepares
and verifies without Cloudflare credentials; `PUBLISH_APPLY=1` performs the
reviewed publication transaction. Use one replica and restart policy `NEVER`.

Assemble an owner-signed controller commit with `assemble.py OUTPUT`, then
upload that standalone context to the dedicated validation service. The image
runs Linux UID-isolation regressions under Tini before it can deploy. A change
to the pinned verification scripts, original release workflow, Worker config
or CI command requires a newly reviewed signed controller.

The source builder is UID 10001, with a clean environment, no new privileges,
and no publishing credential. It runs the locked Python/Node checks and
Wrangler's dry-run bundler. All processes for that UID, including detached
children, are killed and reaped before a bounded, single-link regular Worker
module is read through its inspected descriptor.

The privileged controller never executes the built JavaScript or asks a local
bundler to resolve its imports. It sends the sealed bytes as one multipart ESM
module through Cloudflare's fixed versions API. The account, script name,
compatibility date, limiter and version bindings are fixed. Only Workers
Scripts Edit for account `6b33e9ac81f0df1e9b52650676ddb0f1` is required; no OAuth
credential is copied and no route, Pages, Zone, KV or D1 permission is needed.
The API's actual version metadata is retained without inventing a Wrangler or
GitHub execution identity.

The controller records the prior stable version on its private `/evidence`
volume, uploads and binds a source-tagged candidate, stages it at zero traffic,
proves its catalogs/MCP behavior, then promotes it and runs the complete existing
live proof. Failures restore the exact prior version. A concurrent third-party
Worker release is never overwritten by rollback. An interrupted transaction is
reconciled to its recorded prior version on the next explicit invocation before
new publication proceeds.

Catalog and MCP probes require the source tag and actual Worker version ID,
including when an unchanged catalog would otherwise pass. Zero-traffic staging
allows up to 24 attempts at five-second intervals within a 150-second total
network budget for deployment propagation. Post-promotion checks require the
candidate ID without an override, proving that ordinary traffic reached it.
An uploaded version's metadata read retries only HTTP 404, with at most 18 reads
inside 90 seconds. The upload is never retried by this check; authorization
errors and invalid metadata remain immediate failures before traffic changes.

Service credential updates do not authorize source changes. Keep the API token
only on this validation service; application and PR CI must have no copy.
`RAILWAY_CATALOG_PREPARED` and `RAILWAY_CATALOG_PUBLISH_PASS` identify exact-source
proof; Railway deployment status alone is insufficient.
