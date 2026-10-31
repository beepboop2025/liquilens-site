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
    npx --no-install wrangler deploy --config wrangler.financial-evidence.jsonc \
      --assets /qualified-storage/new-public-directory --tag EXACT_MAIN_SHA
    python3 scripts/financial_evidence_publication.py verify \
      --commit EXACT_MAIN_SHA --receipt /qualified-storage/public-readback.json

Staging reads the exact committed Git blobs, not uncommitted working files. It
copies only the fixed seven-file allowlist and a source-identity response header.
Postdeployment verification requires every public byte, content type, canonical
URL and source header to agree.

Authenticate with the existing Cloudflare account using standard Wrangler login.
Do not commit credentials. Retain the deployment version and readback receipt
outside the public bundle. A failed check is not publication acceptance.

If this route is later retired, first prove the normal Pages origin serves the
same reviewed app files. Then remove only this Worker's two routes and verify
the three canonical URLs again; leave the catalog Worker routes untouched.
