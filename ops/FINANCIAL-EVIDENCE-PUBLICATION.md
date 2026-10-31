# Financial Evidence app information publication

The seven files under financial-evidence/ can be published independently on the
owned liquilens.in domain. This assets-only Cloudflare Worker handles only
/financial-evidence and /financial-evidence/*. It has no application code,
secrets, API bindings, catalog routes, or spreadsheet access.

The full-site Pages workflow and catalog Worker keep their existing external
release checks. Their state does not become accepted when these app pages ship.
This separate publisher prevents Google OAuth remediation from publishing
unsupported sibling-product catalog claims.

Before deployment, require the current protected main and its successful
authenticated railway-automation - liquilens-site-pr-ci status using
scripts/verify_pages_ci.py. Use the pinned Wrangler from npm ci --ignore-scripts.
Stage into a new empty path on qualified storage:

    python3 scripts/financial_evidence_publication.py stage \
      --commit EXACT_MAIN_SHA --destination /qualified-storage/new-public-directory
    npx --no-install wrangler deploy --config wrangler.financial-evidence.jsonc \
      --assets /qualified-storage/new-public-directory --dry-run
    npx --no-install wrangler dev --config wrangler.financial-evidence.jsonc \
      --assets /qualified-storage/new-public-directory --local --ip 127.0.0.1 --port FREE_PORT
    python3 scripts/financial_evidence_publication.py verify \
      --commit EXACT_MAIN_SHA --base-url http://127.0.0.1:FREE_PORT --attempts 1 --delay 0
    npx --no-install wrangler deploy --config wrangler.financial-evidence.jsonc \
      --assets /qualified-storage/new-public-directory --tag EXACT_MAIN_SHA
    python3 scripts/financial_evidence_publication.py verify \
      --commit EXACT_MAIN_SHA --receipt /qualified-storage/public-readback.json

Staging reads the exact committed Git blobs, not uncommitted working files. It
copies only the fixed seven-file allowlist and a source-identity response header.
Postdeployment verification requires every public byte, content type, canonical
URL and source header to agree.

A dry run packages the Worker but does not start the runtime. The local
preview runs the pinned workerd against the staged files, so a runtime
rejection appears before production does. Stop the preview before deploying.
tests/test_wrangler_compatibility.mjs keeps every Worker compatibility_date at
or below the date the pinned workerd declares, so a config dated today fails
CI instead of failing at deploy time. Raise a compatibility date only together
with a Wrangler upgrade that supports it.

This Worker serves a snapshot of one commit. An edit to any of the seven files
changes nothing public until it is staged and deployed again from the new main
commit and the public verify passes. Google reviewers read these URLs, so
redeploy in the same change window as any policy edit.

Authenticate with the existing Cloudflare account using standard Wrangler login.
Do not commit credentials. Retain the deployment version and readback receipt
outside the public bundle. A failed check is not publication acceptance.

If this route is later retired, first prove the normal Pages origin serves the
same reviewed app files. Then remove only this Worker's two routes and verify
the three canonical URLs again; leave the catalog Worker routes untouched.
