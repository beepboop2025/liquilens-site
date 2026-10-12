*This is a historical replay, not current news and not a forecast. It examines a pre-default balance-sheet mechanism at Altico; similar mechanisms do not imply the same outcome elsewhere. The key disclosure period ended on 2017-03-31, its knowledge-time proxy was 2017-05-30, and the event date was 2019-09-12.*

Altico’s disclosed liability mix contained a clear vulnerability: commercial paper represented 29% of funding, explicitly flagged as rollover-freeze exposure. The conclusion must remain narrow. That exposure identified the balance-sheet channel most likely to transmit a loss of refinancing access into stress. It did not establish that a refinancing freeze would occur, when it would occur, or that default was inevitable.

The funding lens first signalled at the 2017-03-31 period end, with a knowledge-time proxy of 2017-05-30. That was 27 months before default. The index was 23.7 and its band was stable. The tension is central to this replay: a filing-period screen can identify a structural funding dependency without classifying the institution as presently deteriorating.

## The record before the event

Altico’s relevant filing period ended on 2017-03-31. Where an explicit publication clock is unavailable, the historical record uses period end plus 60 days as a conservative availability proxy; that produces 2017-05-30 here. This is not a fully bitemporal filing record. The evidence status is `PERIOD_END_PROXY_CONSTRUCTION_PIT`, the record is not validated-backtest eligible, it is not real-money eligible, and it lacks a bitemporal input contract. Lead times may therefore be optimistic.

The default date in the record is 2019-09-12. No first PCA action-zone entry is recorded. The record also marks `fraud_masked` as false. That absence should not be overread. Filings later shown to be falsified can look compliant to a threshold engine; the dossier assigns that failure mode to a forensic screen rather than a mechanical threshold.

The underlying reconstruction is available through the [Altico replay](https://liquilens.in/replay/altico/) and the [Failure Radar board](https://api.liquilens.in/api/failure-radar/board). Neither link turns a reconstructed availability date into evidence that a live investor received, understood, or acted on the disclosure at that time.

## What the lenses saw

The funding lens saw commercial-paper reliance and labelled the associated exposure: a rollover freeze. It did not observe a market refusal to refinance Altico paper. It did not report a market-price drawdown. It did not derive a probability that Altico would fail. This was a filing-period signal about liability structure.

The historical funding summary is informative but restricted. Of 15 failed institutions, 10 had liability disclosures usable by the lens. The funding signal fired first in 4 cases, with median lead of 38 months. The PCA or SAF replay covered 15 failed institutions, with 5 entering the action zone first and median lead of 41 months. These lenses can surface different forms and timings of vulnerability; neither result establishes a universal ordering.

The wider India diagnostic covers 48 institutions across two decades and reports 88.9% of non-fraud failures flagged, with median lead of 21.5 months. It retains the same construction-PIT qualification: explicit publication clocks are used when present, otherwise availability is proxied by period end plus 60 days. The [historical validation record](https://api.liquilens.in/api/failure-radar/validation) is a construction diagnostic, not prospective proof.

## Why the warning mattered

Commercial paper must be refinanced. A lender reliant on it may need replacement funding, liquidity buffers, asset sales, or reduced lending if investors stop rolling paper or demand more costly terms. That is why the 29% share matters: it describes a potential transmission channel from confidence pressure to liquidity management.

But the dossier does not establish every link in that chain as an observed Altico transaction. It supports the starting fact and the stated rollover-freeze exposure. It does not show the timing, scale, counterparties, or terms of an actual refinancing withdrawal. The proper conclusion is diagnostic: the funding mix deserved investigation because it could become binding quickly under a rollover shock.

The stable band does not negate the exposure. A band reflects the published classification rule; it is not a credit rating and not a failure prediction. A stable classification can coexist with a liability structure vulnerable to a discontinuous loss of market access.

## The strongest counter-case

The best objection is strong enough to defeat any broader thesis. Commercial-paper reliance may have been an ordinary funding choice rather than evidence of impending distress. Altico’s index was 23.7, its band was stable, and there was no recorded PCA action-zone entry. A 27-month lead is long enough that a user would not have known whether stress would emerge, or whether the signal would ever matter.

The model diagnostics reinforce that restraint. The hazard panel contains 205 rows, 9 events, and 27 institutions; 179 censored or unusable rows were excluded. Leave-one-institution-out AUC was 0.752, with an interval from 0.338 to 1.0. The temporal diagnostic AUC was 0.645, below the 0.65 gate, and is diagnostic only. The heuristic comparator recorded AUC of 0.799 on the same held-out rows. Those results can defeat any claim that the funding flag alone supplied reliable timing or superior predictive certainty.

The thesis survives only in limited form: disclosed commercial-paper reliance identified a plausible fragility, not a demonstrated near-term default signal.

## What today's board shares

Today’s board is separate from Altico’s historical outcome. As of 2026-10-12, it shows 1 yellow institution and 2 green institutions, with no red or orange institutions. Belstar Microfinance Limited is yellow at 77.8; Annapurna Finance Private Limited and Arohan Financial Services Limited are green at 96.5 and 97.1. Their filings are as of 2026-03-31 and are 7 months old. The board excludes 35 stale institutions.

The market layer is fresh as of 2026-10-09, but it has no admission, publication, signal, or tier authority. Rights and display use are not approved, and admitted canonical records are 0/25. It cannot be used as market confirmation for the board or for Altico. The [market evidence endpoint](https://api.liquilens.in/api/evidence/markets) records that authority boundary.

## The next falsifiable test

The claim would weaken if prospectively clocked liability disclosures show that commercial-paper reliance adds no identification of later funding stress beyond other published components, or if comparable reliance repeatedly appears without measurable rollover pressure. It would strengthen only through fresh, rights-cleared, time-stamped disclosures and prospective observation that does not rely on period end plus 60 days.

The conformal alarm remains diagnostic only and has no score or tier authority pending prospective revalidation. A usable test must ask what information was available when a decision could have been made, not what can be reconstructed after default.

## Follow the pressure chain

The investigative chain is commercial-paper reliance; refinancing refusal or repricing; liquidity-management pressure; and potential asset-side pressure. Altico’s record supports the first link and identifies rollover-freeze exposure. It does not license certainty about the remaining links.

LiquiLens covers **institution and lender balance-sheet risk**. [Seiche](https://api.seiche.info/api/overview) covers **system dollar-funding capacity**. [Undertow](https://api.seiche.info/undertow/board.json) covers **market liquidity and executable exit capacity**. These are complementary lenses, not interchangeable verdicts. An institutional funding vulnerability should prompt examination of system funding conditions and exit capacity, not a declaration that either has confirmed the other.

## Sources, method, and limits

Sources include the [Failure Radar board](https://api.liquilens.in/api/failure-radar/board), [historical validation](https://api.liquilens.in/api/failure-radar/validation), [Altico replay](https://liquilens.in/replay/altico/), [LiquiLens research](https://liquilens.in/research/), and [LiquiLens investigations](https://liquilens.in/investigations/). The [NDFI watch endpoint](https://api.liquilens.in/api/us-radar/ndfi) concerns a separate US watchlist and is not evidence about Altico.

Components are replayed independently on a 48-institution construction-PIT record and fused only for presentation. Probability-of-default levels are corpus-fitted and prior-corrected to a ~0.25% yearly population base rate; the Merton measure is a market repricing signal, not a calibrated failure frequency. Institutions without vetted dossiers are absent by design, not judged safe. Stale, future-dated, or unclocked market readings may remain visible but have no signal or tier authority. This article is not investment advice and not a credit rating.
