# A repeatable treasury evidence review

Use this workflow to inspect funding, one covered bank's disclosures, and a
separately scoped BTC exit-depth example. It turns saved research into a queue
for a human reviewer and records the evidence that person actually reviewed.
It runs locally with Python 3.11+ and the standard library.

This is useful for an institutional research or treasury desk that needs those
three questions. BTC depth is not a substitute for deposit liquidity, collateral
liquidity, or an institution's private cash book. For a bank-only question, use
the [institution review](../institutions/) or [bank watchlist](bank-watchlist.md)
instead of adding an irrelevant asset.

| Product | Question | Evidence boundary |
| --- | --- | --- |
| Seiche | What changed in system funding? | Preserve each benchmark's observation date, source and freshness. |
| LiquiLens | What do the selected bank's disclosures support or contradict? | Filing periods and missing disclosures remain visible; no deposit-safety assurance. |
| Undertow | What does the published depth imply for the selected BTC example size? | Published estimates and venue gaps; no executable quote or instruction. |

## 1. Collect one bounded research snapshot

Keep these files together in an approved local directory:

- [financial_research.py](financial_research.py)
- [trading_brief.py](trading_brief.py)
- [treasury_review.py](treasury_review.py)

Discover covered bank slugs first:

```sh
python3 financial_research.py bank-review --verification
```

The following is an operator rehearsal using a covered bank example and a
USD 100,000 BTC example, not a selection or recommendation for a client:

```sh
python3 trading_brief.py run --slug cosmos-ucb --size-usd 100000 \
  --verification > brief-01.json
python3 treasury_review.py prepare brief-01.json > worksheet-01.json
python3 treasury_review.py prepare brief-01.json --format markdown > worksheet-01.md
```

Collection uses the existing three public MCP services. Its exit codes are
0 for returned responses, 2 for partial/unavailable responses, and 1 for a
client/input error. A partial brief is still worth reviewing; retain the file.
Returned responses can contain stale, historical or partial source evidence.

Every `treasury_review.py` command is offline. It does not install a scheduler,
send notes or identifiers, or write files itself. The shell redirections above
are explicit local writes. Preparation returns 0 when a worksheet was produced,
including a worksheet with gaps; it never means evidence is fresh or approved.
Invalid input returns 1 with a JSON error on stderr.

## 2. Review the next snapshot against the actual baseline

After the next intended review interval, collect into a **different** file:

```sh
python3 trading_brief.py run --slug cosmos-ucb --size-usd 100000 \
  --verification > brief-02.json
python3 treasury_review.py prepare brief-02.json --previous brief-01.json \
  > worksheet-02.json
python3 treasury_review.py prepare brief-02.json --previous brief-01.json \
  --format markdown > worksheet-02.md
```

Never redirect output over an input file. Preserve failed snapshots as well as
the last useful baseline. Baselines must precede the current collection and
match the exact bank, BTC size and verification mode. Embedded comparison
summaries are ignored; differences are recomputed from the supplied snapshots.

The queue puts gaps and explicit source limitations first, then a first review
or changed evidence, then unchanged evidence. Priorities 0, 1 and 2 are only
review ordering. They are not risk ratings. Inspection indexes source flags,
dates, rights and URLs when those fields are present, and reports truncation.
The JSON retains the full, unchanged source evidence and baseline for inspection.

Review the original source clocks, units, definitions, rights, missing values
and counterevidence. A changed generation timestamp is visible as its own field;
it is not described as a market move. An unchanged value can still be too old
for the intended decision. The bounded field index is not a complete validator
and does not assign its own freshness verdict.

## 3. Record what the human actually reviewed

Copy [treasury-assessments.example.json](treasury-assessments.example.json) to
`assessments.json`. Fill in **all three** notes after review. Choose `reviewed`,
`follow_up`, or `deferred` per product. Empty notes are rejected. `reviewed`
records inspection, not acceptance of a source, an institution, or a transaction.
Keep customer books, account details and personal information out of the notes.

```sh
python3 treasury_review.py acknowledge worksheet-02.json \
  --reviewer YOUR_LOCAL_ALIAS --assessments assessments.json \
  --reviewed-at YOUR_ACTUAL_REVIEW_TIME_WITH_TIMEZONE > review-02.json
```

For example, an actual review time has the form `2026-10-08T09:30:00+05:30`.
Use the time the review happened. Backdating before collection and future
timestamps are rejected. No acknowledgement is generated by preparation.

The record binds the exact worksheet, source briefs, assessments, reviewer
alias and review time. Modified records are rejected by the local validator.
These are content hashes, not signatures: someone who rewrites an entire
record and recomputes its hashes can create a new self-report. Production
sign-off requires your authenticated identity, access control and retention
system. This recipe does not duplicate or replace the family's signed evidence
and decision contracts.

## 4. Measure use without mistaking tests for adoption

```sh
python3 treasury_review.py measure review-01.json review-02.json > local-use.json
```

Supply 1–100 explicitly selected records. Measurement excludes records inherited
from `--verification` briefs and deduplicates repeated acknowledgements by
reviewer alias and exact source brief. Rewording a note or assigning another
review date to the same brief does not create another use. The earliest review
is retained when duplicates are supplied.

Counts describe local, self-reported acknowledgements and aliases returning on
multiple UTC days. They do not establish verified people, customers, retention
cohorts or payment. Those fields remain unknown. A record containing deferred
sections is an acknowledgement, not a completed all-section review; inspect
the separate disposition counts.

Use `--verification` for operator checks and demonstrations. For a real pilot,
start a separate series without that flag only when real reviewers use the
workflow. Decide its watchlist, purpose, cadence and local retention before
scheduling. No default schedule or outbound notification is installed.

## Scope limits

Public observations do not reveal private deposit flows, withdrawal-agent
mandates, liquid buffers or cash obligations. The worksheet cannot compute
live LCR/NSFR, certify compliance, predict a bank run, recommend a deposit
transfer, approve credit, or route an order. It keeps the three products'
questions separate and always requires human review.

Each input and output is capped at 24 MiB. Duplicate JSON keys, non-finite
numbers, incompatible identities, missing sections, altered worksheets and
inconsistent records are rejected. Existing data rights apply to every retained
snapshot; the source code's license does not relicense provider data.
