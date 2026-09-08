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

## Pull requests

The same tests run during the image build, so a failed verification makes the
native Railway deployment check fail. Runtime logs still carry the exact source
and deployment completion marker. Neither build nor runtime receives publishing
or controller credentials.

The Railway `public-pr-ci` environment is the isolated PR base. It contains only
public test services, no shared secrets, volumes, or public domains. Focused PR
environments build the changed repository; bot PR environments are enabled.
Railway only creates previews for contributors associated with the workspace or
project, so the GitHub PR workflow remains as fallback for external contributors
until an equivalent external-fork executor is available.
