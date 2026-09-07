# Railway public-edge verification

The dedicated `liquilens-site-ci` service runs the existing public-surface,
protocol, edge, community-handoff, dependency-audit and Worker dry-run checks.
Configure `deploy/railway-ci/Dockerfile`, one replica, restart policy `NEVER`
and Wait for CI disabled. The service uses Python 3.12, Node 24 and the existing
hash-locked dependencies. It receives no production or GitHub credentials.

Only `RAILWAY_CI_PASS` for the exact source SHA and deployment proves success.
Every run has a ten-minute deadline and exits when complete. Live evidence
verification and the protected Pages/Worker publication workflows retain their
own release gates; this job does not publish an article or promote a Worker.
