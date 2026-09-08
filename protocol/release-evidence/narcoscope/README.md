# NarcoScope production evidence

NarcoScope production uses the existing Fleet publisher and Railway service
`21d80a60-b268-46f0-a581-4cfc48598268`. The older Vercel deployment records remain
failed and are not represented as successful deployments.

The source-named directory contains the established `fleet-publisher-receipt/v1`
receipt and its immutable `fleet-release-manifest/v1` manifest. The detached
`fleet-release` SSH signature records owner review of this particular receipt;
it does not claim that the Fleet publisher itself signs every automatic run.
The owner key is pinned in `scripts/verify_narcoscope_release.py`.

For source `0f3887d456fbb985a1dd3532ec689cda259e1aa4`, independent Railway API
inspection confirmed deployment `95ff9569-ef42-400c-814b-41befc447659`, its fixed
project/environment/service, successful status, and release-bound CLI message.
The image digest was
`sha256:105dd3163daea7a0f6cca7e6d517359c5c0a8ce2046f4e7bac5cc93f72ee0c9d`.
Both provider and canonical public health endpoints then matched the receipt's
source, release ID and artifact tree. The review evidence is retained with the
2026-09-08 Railway migration artifacts.

This signature proves a historical deployment of the exact catalog release
source. Later automated data revisions can advance the live source. Every site
publication separately verifies that the current provider and canonical origins
agree on a complete ready Fleet identity, and retains the existing live version,
Registry, MCP and contract-byte gates. The old receipt is never presented as
proof of those later bytes.
