# Earn recurring use in financial teams

Prepared 7 October 2026 for LIQUILENS PRIVATE LIMITED. This is an execution
plan and pilot hypothesis, not a claim of industry adoption or a validated
forecast about AI-driven withdrawals.

## What the Banker bots article changes

The user-supplied FT Newswrap newsletter, dated 7 October 2026, describes AI
changing banking work and potentially accelerating deposit switching. Its
commercial implication for this family is a need for faster, reviewable
evidence before people or agents act. The newsletter's reported job cuts and
valuation estimates are not model inputs, verified customer demand, or reasons
to imply that a specific institution is unsafe.

This interpretation is consistent with two primary sources. A South African
Reserve Bank speech hosted by BIS discusses correlated behaviour, potentially
faster AI-driven withdrawals, data governance and meaningful human oversight:
[Regulation and supervision in the age of AI](https://www.bis.org/speeches/20260520-regulation-and-supervision-financial-sector-age-artificial-intelligence).
Andrew Bailey's 30 September 2026 essay calls for testing and credible ways to
intervene in increasingly autonomous systems:
[Frontier AI and the question of governance](https://www.bankofengland.co.uk/bank-insights/2026/frontier-ai-and-the-question-of-governance).
These support the problem framing; neither endorses this company or validates
these products. The supplied newsletter is retained privately by its owner,
not copied into this repository.

## Product roles and the first paid problem

Sell a recurring evidence review for a **covered** institutional risk,
treasury or research workflow. The initial deliverable is a reviewer's morning
or event-driven evidence packet, a visible exception queue and a record of
which evidence was inspected. Start with one jurisdiction and one agreed
watchlist. Source cadence governs what can genuinely change.

| Product | Recurring job | Evidence to earn reliance | Main missing input for the article's deposit scenario |
| --- | --- | --- | --- |
| LiquiLens | Review bank/lender disclosures, concentration and counterevidence for a selected watchlist | Exact entity matching, dated filings, explained changes, explicit missingness and a retained reviewer assessment | Permissioned current deposits, depositor cohorts, withdrawal mandates and institution-specific calibration |
| Seiche | Identify funding changes and source-health exceptions before a treasury review | Source-observation clocks, admitted benchmarks, visible release holds and observed collector recurrence | Local intraday funding and institution cash-book context where current coverage is absent |
| Undertow | Inspect supported market depth and exit assumptions for a separately scoped asset/size | Venue timestamps, coverage gaps, depth assumptions and independent review | Broader entitled asset coverage, executable quotes and the customer's actual liquidation constraints |

Use all three only where all three questions belong in the customer's workflow.
The current downloadable three-product example uses a covered bank and BTC
depth. It is not a universal bank treasury model. Bank-only reviews can use the
existing institution workflow. Do not present the development retail/SMB
Undertow workspace as the public market-liquidity service.

The commercial hypothesis is that a team will pay for review time saved,
repeatable evidence and accountable follow-up. Test that hypothesis before
expanding the number of features or promising financial outcomes.

## Delivered in this change

- An offline worksheet built on the existing `trading_brief.py` collector,
  preserving exact LiquiLens, Seiche and Undertow payloads and baselines.
- A queue that puts explicit missing/stale/restricted evidence ahead of other
  review work and treats changed payloads as an inspection prompt.
- Human-written per-product assessments bound to the exact source snapshots;
  no automatic review, new score, financial approval or money movement.
- Local-use measurement that excludes verification traffic, deduplicates
  acknowledgements and leaves external users, retention and payments unknown.
- A [runnable guide](../developers/recipes/treasury-review.md) linked from the
  developer and institutional entry points.

Hashes provide internal consistency, not authenticated sign-off. Production
identity, tenant access, record retention and decision contracts remain the
responsibility of the existing institutional application and shared engines.

## Pilot sequence and explicit pass/fail gates

The following numbers are proposed experiment targets, not observed results.
The owner must validate the buyer, watchlist and scope with participants.

| Window | Concrete work | Gate before further investment |
| --- | --- | --- |
| Days 1–7 | Recruit 3–5 named design-partner teams with a real recurring review. Observe their existing process and record time, required sources and unresolved decisions. | At least 3 teams agree on a watchlist, reviewer, evidence scope, cadence and baseline. An introduction or download is not activation. |
| Days 8–30 | Run an agreed pilot using existing APIs/MCP and the review worksheet. Compare outputs with source records, retain errors, collect actual reviewer notes and sample review time. | At least 3 teams complete 4 successive agreed review cycles, a majority of required sections receive actual review, no known missing evidence is portrayed as reassuring, and median review time improves by a proposed 30% against that same team's baseline. |
| Days 31–60 | Integrate the workflow into each successful team's approved tools; add authenticated reviewers and retention through existing application contracts. Agree source-specific service expectations. | At least 2 teams return without founder prompting and accept a written paid scope. Measure real invoices/payment separately from intent or trials. |
| Days 61–90 | Expand one adjacent workflow using the proven source and reviewer contracts. Add permissioned customer inputs only under explicit scope and access control. | A repeatable onboarding path, renewed use, verified payment and understood support cost justify expansion. Otherwise narrow or stop the weak workflow. |

For each team, track distinct stages: qualified problem, agreed pilot, first
source-backed review, next review cycle, retained use, paid contract, received
payment and renewal. Record source completeness and reviewer follow-up alongside
use. Do not aggregate page views, bots, API transports and users into one number.
The local recipe's alias counts are only a development aid; verified pilot
retention needs participant identity and a declared cohort denominator.

## Prioritized engineering after the pilot confirms demand

1. **Source reliability and admitted coverage.** Finish the active release
   owners' freshness, exact-version, publication and recovery work. Test source
   clocks and observed recurrence, not just endpoint availability.
2. **Useful review changes.** Use the packet's exact field differences with
   jurisdiction-specific units, periods and definitions. Ask reviewers which
   differences merit attention; do not learn credit labels from review clicks.
3. **Authenticated institutional records.** Integrate pilot review notes with
   existing tenant, reviewer, access and shared evidence contracts. A local
   hash-only acknowledgement does not satisfy an institution's control regime.
4. **Permissioned deposit scenarios.** If customers confirm the need, implement
   explicitly assumed withdrawal-speed and concentration scenarios through the
   existing scenario/strategy owners. Require actual customer-authorized inputs,
   clocks and assumptions. Return scenarios, not bank-run probabilities or
   deposit-transfer instructions.
5. **Distribution proven by use.** Feed the existing marketplace/listing lane a
   working use case and measured conversion. Prefer the customer's existing
   Python, spreadsheet, MCP or review system over another standalone dashboard.

## Concurrent-session ownership

This change owns only the new review recipe, its tests, guide, assessment
template, pilot plan and small navigation links. It was prepared in an isolated
SSD worktree. Other active sessions own marketplace listings and product
release/recovery completion; payment work already has its own lane. This work
does not modify their checkouts, stop processes, replay a collector/export,
change production schedules, submit directory listings or send outreach.

Release through the existing repository checks and publication owner. A tested
branch or draft PR is not a served production feature. Customer reliance,
regulated control acceptance and payment remain unproven until their own
evidence exists.
