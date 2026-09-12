# Railway public-edge verification

The dedicated `liquilens-site-ci` service runs the existing public-surface,
protocol, edge, community-handoff, dependency-audit and Worker dry-run checks.
Configure `deploy/railway-ci/Dockerfile`, one replica, restart policy `NEVER`
and Wait for CI disabled. The service uses Python 3.12, Node 24 and the existing
hash-locked dependencies. It receives no production or GitHub credentials.

The CI and manual Worker publisher use Docker Official Images from ECR Public,
pinned to identical manifests verified against Docker Hub. This avoids requiring
Docker Hub availability for each build's base-image resolution. Update both
Dockerfiles together after verifying the new official manifest digests, then run
the full native checks and assemble a new signed publisher controller. Digest
pins do not advance automatically when an upstream tag receives security updates.

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
project, so the GitHub PR workflow runs only as fallback for non-owner contributors
until an equivalent external-fork executor is available.

Native verification requires current main to be an ancestor of the exact tested
head. A stale pull request fails admission and must merge/rebase main before
rerunning. Build logs record both head and base revisions.

## Pages publication

The Pages workflow follows this service's successful status for exact protected
main, or an explicit main dispatch. It checks the authenticated Railway bot,
fixed service and credential-free main environment, and newest result for that
commit before using the native offline claims/Python/Node proof. It checks again
immediately before artifact upload and before deployment. A newer pending or
failed result, malformed target, changed main or preview environment revokes the
admission. Only admitted deploy jobs enter the Pages concurrency group.

Pages retains its fresh external release checks, advisory live API/Worker checks,
original GitHub environment/OIDC origin, artifact sanitization and mandatory
public-byte comparison. It does not reinstall test dependencies or repeat tests.
The existing external-contributor PR fallback is unchanged.

IndexNow remains advisory and follows successful deployment and public proof. Its
exact diff begins at the most recent successful GitHub Pages source, so a batched
push or delayed native build retains all changed routes. The bounded lookup reads
only successful runs of the fixed Pages workflow ID/path on canonical-repository
main, including push, status and explicit dispatch events. It validates exact run
identity and source ancestry; a completed workflow also proves its retained live
byte gate passed. Initial publication uses
Git's empty tree; a repeat of the same source has no changed routes. A lookup
failure is visible and skips the advisory notification, never silently narrows
its range. No new publishing or notification credential is introduced.
