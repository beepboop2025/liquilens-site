*This is a historical replay, not current news and not a forecast. It examines Global Trust Bank before its default date of 2004-07-24. This is research, not investment advice, and it is not a credit rating.*

The narrow answer to the desk question is Global Trust Bank. Its disclosed record first showed stress through CRAR and NNPA, which jointly breached the PCA action-zone criteria for the period ended 2002-03-31. The funding lens was not scoreable and produced no first signal.

That finding needs strict limits. It is a filing-period signal reconstructed from reported information. It is not a market-price signal, because no authorized market reading supports the conclusion. Nor is it a model derivation that forecasts default. Global Trust Bank is fraud-masked, meaning a threshold engine can only process the reported record; it cannot establish that reported figures were truthful or complete.

## The record before the event

The PCA replay places Global Trust Bank in an action zone at the 2002-03-31 period end, on CRAR and NNPA breaches. Its knowledge-time proxy is 2002-05-30, and the recorded lead to the 2004-07-24 default date is 25 months.

That lead is not a tradable timetable or a claim that every action-zone breach ends in failure. The underlying construction is labelled PERIOD_END_PROXY_CONSTRUCTION_PIT. It is not validated-backtest eligible, is not real-money eligible, and has no bitemporal input contract. The subject record is available in the [Global Trust Bank replay](https://liquilens.in/replay/global-trust-bank/) and the broader screen is available on the [Failure Radar board](https://api.liquilens.in/api/failure-radar/board).

Where no explicit publication time exists, the record uses period end plus 60 days. That is an availability convention, not evidence that an investor, creditor, depositor, or supervisor knew the information at the reporting date. The dossier explicitly says lead times are optimistic. An economic condition, a report date, and an observer’s usable knowledge are different clocks; collapsing them would overstate what this replay demonstrates.

## What the lenses saw

The PCA lens supplied the first usable disclosed warning: simultaneous CRAR and NNPA breaches. The funding lens did not. It was not scoreable, had no first signal, and has no reported funding lead-month measure for this institution.

That absence is an eligibility disclosure, not reassurance. The funding framework only sees institutions that disclose a liability series. It cannot establish stable liabilities, easy refinancing, or the absence of liquidity pressure when the required disclosed series is unavailable. In this case, capital and asset-quality disclosures were usable; funding evidence was not.

Fraud masking makes that distinction more important. The validation record says that institutions whose filings were later shown falsified can look compliant to any threshold engine, with the forensic screen owning that problem. Here the reported ratios nevertheless breached the PCA lens. But the result is not a forensic reconstruction of the bank, nor proof that the disclosed record captured all relevant stress.

The broader historical summaries are similarly constrained. Of 15 failed institutions in the PCA summary, 5 entered the action zone first, with a median lead of 41 months. The funding summary covers 10 failed institutions with liability disclosures; 4 had the funding signal fire first, with a median lead of 38 months. These are descriptions of a limited construction record, not probabilities for a current lender. The [historical validation record](https://api.liquilens.in/api/failure-radar/validation) retains the eligibility conditions behind those figures.

## Why the warning mattered

The significance of the paired breach is modest but useful. The disclosed record showed both asset-quality pressure and a capital-related supervisory tripwire. That combination provided a usable balance-sheet warning before the funding lens could be scored.

It does not establish a complete causal chain to default. The replay does not identify unreported funding conditions, prove the timing of off-record pressures, or demonstrate that a different intervention would have changed the outcome. Nor does it show that capital and asset quality always lead funding stress. It only shows which disclosed lens produced the earlier recorded warning for this subject.

The appropriate conclusion is therefore comparative, not absolute: on this record, the PCA lens warned before the available funding lens because the latter was unavailable for scoring. Funding was not cleared; it was unobserved by this framework.

## The strongest counter-case

The counter-case can defeat any stronger thesis. The record relies on a period-end proxy and, where needed, a 60-day filing-lag convention. It lacks a bitemporal input contract, is ineligible for validated-backtest and real-money use, and labels lead times optimistic. A real-time observer may have possessed later, less complete, or less reliable information than the replay implies.

Fraud masking is a still deeper objection. If filings were later shown falsified, reported ratios cannot be treated as a complete account of the economic balance sheet. The bank may have been weaker or stronger than the disclosures suggested. The replay identifies where the disclosed record raised concern, not when every relevant fact became knowable.

Model results do not repair this limitation. The hazard panel contains 205 rows, 9 events, and 27 institutions, after 179 censored or unusable rows were excluded. Its leave-one-institution-out AUC is 0.752, with a confidence interval from 0.338 to 1.0. The temporal diagnostic AUC is 0.645 against a 0.65 gate and remains diagnostic only; the heuristic comparison is 0.799 on the same held-out rows. Those results cannot promote this construction replay into live predictive authority.

## What today's board shares

Today’s board is separate from the Global Trust Bank replay. It has 1 yellow institution and 2 green institutions, with no red or orange names. Belstar Microfinance Limited is yellow at 77.8. Annapurna Finance Private Limited and Arohan Financial Services Limited are green at 96.5 and 97.1. Their filing as-of date is 2026-03-31, their age is 7 months, and no signals fired are listed.

Those rows are not solvency judgments, forecasts, or credit ratings. The board excludes 35 stale institutions rather than presenting old filings as current. Institutions without vetted dossiers are absent by design: nothing here is scored from memory.

The market layer is present but has no tier authority. It is as of 2026-10-09 and was retrieved on 2026-10-13, yet it has 0 admitted canonical records out of 25. Display, model-gate, and tier-use approvals are not granted. The [market evidence endpoint](https://api.liquilens.in/api/evidence/markets) is context rather than an authorized live-tier input. A market-price signal is distinct from a filing-period signal, and none is used to support the historical conclusion here.

## The next falsifiable test

The thesis fails if future fully timestamped, vetted disclosures show that the CRAR-and-NNPA action-zone combination does not identify disclosed balance-sheet deterioration earlier than other usable lenses. It also fails if complete liability disclosures repeatedly supply an earlier independently usable funding signal.

A stronger screening claim would require prospective, bitemporal evidence that clears diagnostic gates unavailable to this corpus. Missing data cannot be counted as calm. An unapproved market layer cannot count as confirmation. Where filing reliability is in doubt, forensic assessment remains necessary.

## Follow the pressure chain

LiquiLens: **institution and lender balance-sheet risk**. Its [investigations archive](https://liquilens.in/investigations/) and [replay archive](https://liquilens.in/replay/) address disclosed institution records.

Seiche: **system dollar-funding capacity**. Its context is EROSION, while its editorial framing says divergence is a warning to investigate, not proof of a squeeze. See the [Seiche overview](https://api.seiche.info/api/overview).

Undertow: **market liquidity and executable exit capacity**. Its UST segment is STRAINED while other segments are NORMAL or PARTIAL. See the [Undertow board](https://api.seiche.info/undertow/board.json).

These are distinct mechanisms. Seiche and Undertow did not enter this institution score. A pressure chain becomes more credible when each layer independently confirms its own mechanism, rather than when filing signals, market prices, and model derivations are fused into an unsupported verdict.

## Sources, method, and limits

This article uses the [Failure Radar board](https://api.liquilens.in/api/failure-radar/board), [validation endpoint](https://api.liquilens.in/api/failure-radar/validation), [market evidence endpoint](https://api.liquilens.in/api/evidence/markets), and subject [replay](https://liquilens.in/replay/global-trust-bank/). Components are replayed independently on the construction-PIT record and fused only for presentation.

The resulting tier is a published rule over published components, not a failure forecast. Stale, future-dated, or unclocked market readings may remain visible without signal or tier authority. The conformal alarm is diagnostic and has no score or tier authority pending prospective revalidation. The final constraint is Global Trust Bank’s fraud-masked status: disclosed ratios can identify disclosed stress, but cannot certify the truthfulness or completeness of the disclosures.
