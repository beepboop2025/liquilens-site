*This is a historical replay, not current news and not a forecast. It examines Altico before its default date of 2019-09-12. The relevant filing period ended 2017-03-31, with a knowledge-time proxy of 2017-05-30. Current board and market material discussed below is separately as of 2026-09-08.*

The question is not whether Altico’s funding flag predicted its default. The dossier cannot support that claim. It can support a narrower observation: Altico’s first funding signal identified commercial-paper reliance of 29% and explicitly described rollover-freeze exposure, even though the funding index sat in a stable band. That contrast makes Altico a useful replay of a balance-sheet question: which institution should be investigated first when reported broad measures look calm but liabilities require recurring refinancing?

This is a screen for inquiry, not a conclusion about creditworthiness. It is **not a credit rating**, not investment advice, and not a prediction of institutional failure.

## The record before the event

Altico defaulted on 2019-09-12. Its recorded first funding signal belongs to the period ending 2017-03-31, with 2017-05-30 used as the knowledge-time proxy. The recorded lead was 27 months. The funding index was 23.7, its band was stable, and the disclosed flag was CP reliance of 29% with rollover-freeze exposure.

Those items are different kinds of evidence. The period-end balance-sheet observation is a filing-period signal. The knowledge-time proxy is an attempted estimate of when that signal could have been available, not proof of an exact public-information clock. The stable band is an output of a funding index. The rollover flag is a component-level warning. None is a market-price signal, and none is a calibrated probability that Altico would fail.

The [Altico replay](https://liquilens.in/replay/altico/) and [Failure Radar board](https://api.liquilens.in/api/failure-radar/board) preserve this distinction. A stable aggregate band did not erase the disclosed funding feature; it meant that the broad index did not register a more severe state. The replay therefore argues against reading a single band as a clean bill of health.

## What the lenses saw

Altico’s funding lens was scoreable and fired first, with the recorded 27-month lead. The historical funding summary covers 15 failed institutions. Liability disclosures were available for 10, the funding signal fired first for 4, and the median lead was 38 months. These are descriptive replay results, not a validated backtest or a real-money record.

A separate regulatory-action lens gives a different picture. In the public-disclosure replay of RBI PCA or SAF tripwires, 5 of 15 failed institutions entered an action zone first, with a median lead of 41 months. The India diagnostic describes 48 institutions across two decades and reports 88.9% of non-fraud failures flagged, with a median lead of 21.5 months. These figures do not show that a funding flag dominates a supervisory threshold. They show that different disclosed lenses may register at different points in a failure sequence.

The historical record is explicitly `PERIOD_END_PROXY_CONSTRUCTION_PIT`. It is not validated-backtest eligible, not real-money eligible, and lacks a bitemporal input contract. Where an explicit publication clock was unavailable, the availability basis was period end plus 60 days. The dossier says lead times are optimistic. A filing-period value may therefore have been treated as knowable earlier than a user could have verified it.

The [historical validation record](https://api.liquilens.in/api/failure-radar/validation) adds a further restraint. Its temporal diagnostic AUC was 0.645, below the 0.65 gate, and did not pass. The held-out comparison also reported a heuristic AUC of 0.799 against hazard AUC of 0.752 on the same rows. The model derivation is consequently diagnostic only; it cannot promote the construction-PIT evidence into a settled forecasting claim.

## Why the warning mattered

The warning mattered as a question about liability structure, not as proof of causation. The dossier’s own wording identifies rollover-freeze exposure. Commercial paper is therefore the specific disclosed channel worth examining in this replay: refinancing dependence can be important even when a wider funding index remains stable.

That conclusion should be kept at the level the evidence permits. Altico’s flag did not establish that refinancing pressure caused the default. The dossier does not provide an event-by-event account of funding withdrawals, asset sales, liquidity use, hidden losses, or misconduct. It does show a disclosed feature, a later default date, and a recorded lead under a proxy availability convention.

The more defensible lesson is about aggregation. A composite can summarize multiple inputs while a discrete component identifies a vulnerability the composite does not elevate. The filing-period signal is therefore a reason to inspect refinancing sensitivity; it is not a market verdict and not a model-derived failure frequency.

## The strongest counter-case

The counter-case can defeat an overconfident thesis. Altico may be an anecdote selected after the event. Its funding band was stable. Among failed institutions with the stated historical coverage, only 4 funding signals fired first, and only 10 of 15 had usable liability disclosures. The lens is conditioned by disclosure availability. Institutions without a liability series are not demonstrated to be safe; they are simply not observable through that particular lens.

Timing may also flatter the result. The dossier warns that period-end-plus-60-day availability can make lead times optimistic. Its hazard panel excluded 179 censored or unusable rows, while the temporal diagnostic did not clear its stated gate. Filings later shown to be falsified can look compliant to a threshold engine; the dossier assigns that limitation to a forensic screen. Altico is not fraud-masked, but the broader masking risk remains.

A serious reader can therefore reject the proposition that CP reliance reliably identifies the next failure. The evidence supports only a conditional investigative rule: where the disclosure exists, a rollover flag may deserve attention alongside, rather than instead of, other lenses.

## What today's board shares

Today’s board is not evidence about Altico’s past and must not be fused with the replay. As of 2026-09-08, the board reports 0 red, 1 orange, 3 yellow, and 15 green institutions; 21 stale institutions are excluded. Utkarsh Small Finance Bank is orange, based on 2025-03-31 material aged 18 months, with a score of 74.9. Belstar Microfinance Limited is yellow from 2026-03-31, aged 6 months, with a score of 77.8. ESAF Small Finance Bank is yellow from 2025-09-30, aged 12 months, with a score of 66.0.

These are published screen tiers, not ratings or forecasts. The stated rule can use levels, deterioration, funding flags, forensic indicators and, only when authoritative, market drawdown inputs. The [market evidence endpoint](https://api.liquilens.in/api/evidence/markets) is fresh by its pack clock, but has no publication, admission, knowledge, or tier authority. Rights and display approval were not granted for every expected canonical record. Freshness is not authorization, and this market layer cannot validate or rank a current institution here.

## The next falsifiable test

The Altico inference should fail if prospectively collected disclosures of short-term rollover dependence do not identify earlier subsequent funding strain than comparable disclosed balance sheets. It should also fail if actual publication timestamps remove the apparent lead created under the period-end-plus-60-day proxy.

A credible test would fix the funding definition before outcomes, use vetted public dossiers, record actual availability, and preserve the rule before observing subsequent events. It would need to improve on the disclosed heuristic in a future temporal sample. Until then, the replay remains a historical mechanism test, not a deployable prediction engine.

## Follow the pressure chain

The pressure chain begins with the liability mix and its refinancing requirement. Altico’s disclosed CP-reliance flag places attention on that requirement, but does not establish its later path. LiquiLens covers **institution and lender balance-sheet risk**. [Seiche](https://api.seiche.info/api/overview) covers **system dollar-funding capacity**; its composite was 44.9, EROSION, with guarded confidence because modelled or slow-moving structure led current market-plumbing confirmation. [Undertow](https://api.seiche.info/undertow/board.json) covers **market liquidity and executable exit capacity** and reports several segments as PARTIAL.

These are separate layers. They are not confirmation that Altico’s historical mechanism is active now, and no layer substitutes for another.

## Sources, method, and limits

Key dossier-linked materials include the [Failure Radar board](https://api.liquilens.in/api/failure-radar/board), [validation record](https://api.liquilens.in/api/failure-radar/validation), [market evidence](https://api.liquilens.in/api/evidence/markets), [Altico replay](https://liquilens.in/replay/altico/), and [LiquiLens research](https://liquilens.in/research/).

Nothing older than 24 months is presented as current on the board; failed institutions are presented through replay evidence instead. Institutions without vetted dossiers are absent by design and are not scored from memory. Stale, future-dated, or unclocked market readings may remain visible but have no signal or tier authority. Missing liability disclosure is not safety, missing system context is not calm, and a historical replay is not a forecast.
