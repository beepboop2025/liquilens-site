#!/bin/sh
set -eu
cd /app
test -z "${GITHUB_TOKEN:-}${GH_TOKEN:-}${RAILWAY_TOKEN:-}${RAILWAY_API_TOKEN:-}${CLOUDFLARE_API_TOKEN:-}"
printf '%s\n' "${RAILWAY_GIT_COMMIT_SHA:-}" | grep -Eq '^[0-9a-f]{40}$'
python3 scripts/verify_public_claims.py
python3 -m pytest tests -q
npm run test:edge
node --test tests/test_x_bridge.mjs
npm audit --audit-level=moderate
npx --no-install wrangler deploy --config wrangler.catalog.jsonc --dry-run
printf 'RAILWAY_CI_PASS source=%s deployment=%s\n' \
  "$RAILWAY_GIT_COMMIT_SHA" "${RAILWAY_DEPLOYMENT_ID:-unavailable}"
