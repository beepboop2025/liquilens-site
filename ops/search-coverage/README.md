# Independent search coverage scheduler

The systemd units run a pinned, reviewed copy of the stdlib monitor with no
credentials and no ability to modify the websites. Install code from an exact
merged revision under `/opt/fleet-search-coverage/releases/<sha>/`, then point
`/opt/fleet-search-coverage/current` to it. Include the three monitor scripts,
`search-coverage-retirements.json`, and these units. Keep code root-owned and
read-only to the service. Seed `baseline.json` in its StateDirectory from the
validated, successful GitHub report; never use a failed report to reset history.
Record the baseline's source-run receipt and file hashes at installation.

The timer runs 15 minutes after each completed audit, with up to 30 seconds of
jitter. Sitemaps, robots, LLM references and AI catalog changes trigger a full
audit for the affected product. The 21 priority topic pages are always checked.
A full family audit also runs whenever the last successful full audit is at
least 24 hours old. This detects new published URLs and changes to advertised
discovery; it does not infer source-data freshness from publication timestamps.

`latest.json` and `latest.md` preserve the most recent attempt, including
failure. `baseline.json` advances only after a successful history comparison;
`last-full.json` advances only after a complete successful family audit.
`runs.jsonl` records scheduler completion. Details also go to the system journal.
Two simultaneous processes cannot start overlapping audits. There are no
outbound email, Telegram, social or search-engine submissions.

After installation, verify the source hashes, run `systemd-analyze verify` on
both units, start the service and check its report. Enable the timer only after
that first run. Observe a subsequent timer-initiated completion before claiming
recurrence. Use `systemctl status fleet-search-coverage.timer` and
`journalctl -u fleet-search-coverage.service` for operations. A last completed
attempt older than 35 minutes means this scheduler's coverage is unknown;
GitHub remains the independent external monitor. No independent alert delivery
is claimed by these units.

Rollback switches the `current` symlink to a retained reviewed release and
restarts the service; it does not discard successful inventory history. Disable
only this timer when retiring the monitor. Do not change product release or
collection units. This pinned fallback does not automatically execute new code
from a remote repository; reviewed monitor upgrades are installed separately.
