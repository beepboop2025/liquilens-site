# Railway daily editorial controller

This isolated, manually uploaded controller runs the same daily writer and four
test files as `articles-daily.yml`, with the existing editorial model settings.
It fetches current main and publishes only generated article files, `llms.txt`
and `sitemap.xml`. It never force-pushes or rebases an edition onto different
source code; a concurrent main change produces exit 3 without a pass marker.

Run at `15 11 * * *` UTC with one replica, restart `NEVER`, no public endpoint
and no GitHub autodeployment. Set `EDITORIAL_APPLY=1` only after the image's
security tests and an actual dry run pass. The service receives a dedicated
write deploy key for `beepboop2025/liquilens-site` as `GITHUB_DEPLOY_KEY` and the
existing `EDITORIAL_LLM_*`, `EDITORIAL_REVIEW_MODEL`, and
`EDITORIAL_REASONING_EFFORT` settings. No PR or application service inherits them.

The writer runs as UID 65532 with no new privileges, closed inherited descriptors
and a scrubbed environment. It can read the editorial model key needed for the
existing writing step; it cannot read the Git publisher key. Tests receive
neither key. All UID-owned processes are killed and reaped before the controller
reads outputs using no-follow, single-link file descriptors. Source code and
unapproved paths must remain unchanged. Dependency-lock changes require a new
reviewed image; the runtime digest binds the controller, lock and security tests.

The dedicated key's ordinary Git push triggers the existing protected Pages
workflow. `RAILWAY_EDITORIAL_PASS` proves article generation, tests and Git
publication. Pages deployment and public-byte verification remain separate
GitHub identity steps and must be checked before claiming visitor-visible proof.
