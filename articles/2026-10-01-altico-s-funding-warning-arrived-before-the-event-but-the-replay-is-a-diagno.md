*This is not current news and is not a forecast. It is a historical replay of Altico, which defaulted on 2019-09-12. Similar mechanisms do not imply the same outcome at another institution or in another market.*

The balance sheet likely to feel stress first is not necessarily the lender with the weakest-looking assets. It may be one that must repeatedly refinance when confidence changes. Altico is a bounded example. Its earliest recorded funding signal was commercial-paper reliance of 29% at 2017-03-31, labelled rollover-freeze exposure. The funding index was 23.7, while the band was stable. That is a filing-period signal about disclosed liability structure—not evidence that a crisis had begun, and not a market-price signal.

The replay assigns a knowledge-time proxy of 2017-05-30, using period end plus 60 days, and records a 27-month lead to default. That sequence is informative but not investable proof. The historical record is PERIOD_END_PROXY_CONSTRUCTION_PIT, lacks a bitemporal input contract, is not eligible as a validated backtest or real-money record, and explicitly says lead times are optimistic.

## The record before the event

Altico’s scoreable funding lens, rather than its PCA field, supplies the earliest recorded warning. The PCA record has no first action zone and no PCA lead-month value. The funding flag says only that commercial-paper reliance created rollover-freeze exposure. Its stable band is an important restraint: a visible vulnerability is not equivalent to an imminent failure call.

The wider summaries establish possibility, not a universal ordering. Of 15 failed institutions in the PCA summary, 5 entered an action zone first, with a median lead of 41 months. Of the same 15, 10 had liability disclosures; the funding signal fired first for 4, with a median lead of 38 months. The India diagnostic covers 48 institutions across two decades and reports 88.9% of non-fraud failures flagged, with a median lead of 21.5 months.

Those results are reconstructions under filing-availability assumptions. They cannot establish that every relevant disclosure was available to a decision-maker at the reconstructed time. The [Failure Radar board](https://api.liquilens.in/api/failure-radar/board) and [historical validation record](https://api.liquilens.in/api/failure-radar/validation) retain that eligibility boundary.

## What the lenses saw

The funding lens saw a disclosed liability mix: commercial paper represented 29% at the cited period end. A lender dependent on repeated issuance has a specific vulnerability if refinancing becomes unavailable. It may need replacement cash or other balance-sheet actions under time pressure.

But the dossier does not identify a particular creditor, failed issuance, liquidity reserve, asset-quality trend, management action, or contemporaneous market repricing. It does not establish that every proposed step in a pressure chain occurred at Altico. The correct reading is narrower: disclosed funding dependence preceded a recorded default.

The PCA lens did not offer an earlier action-zone signal here. That does not prove funding measures are superior to supervisory-style tripwires. It shows that the lenses address different failure pathways and can disagree in timing.

Nor should disclosed-data screening be mistaken for forensic detection. The validation note says filings later shown falsified can appear compliant to a threshold engine, with the forensic screen owning those cases. Altico is not fraud-masked in this dossier. That classification does not turn absent evidence into evidence of calm.

## Why the warning mattered

Commercial paper can be efficient in ordinary conditions. Its distinctive risk is not simply cost; it is the need to obtain market consent again and again. A refusal or delay can compress the time available for balance-sheet decisions before assets run off or other funding is secured.

That creates a plausible chain: refinancing reliance can create rollover risk; rollover risk can force defensive liquidity or asset actions; those actions can affect confidence; weaker confidence can make subsequent refinancing harder. This is a model derivation from a disclosed liability structure, not a demonstrated causal narrative of Altico’s final months.

The distinction is essential. A filing-period signal identifies what accounts disclosed. A market-price signal would describe repricing in traded instruments. The dossier supplies the former for Altico, not the latter. A model derivation explains why the disclosed feature might matter; it must not be presented as an observed event.

## The strongest counter-case

The counter-case defeats any simple thesis. A 29% commercial-paper share may be a manageable funding choice rather than a precursor to distress. A lender may roll paper reliably, hold liquidity, use alternative funding, or manage asset and liability timing in ways this observation cannot see. Altico’s stable band supports that caution.

The aggregate evidence is also limited. The hazard panel contains 205 rows, 9 events, and 27 institutions, while 179 censored or unusable rows were excluded. Its leave-one-institution-out AUC was 0.752, with an interval from 0.338 to 1.0. The heuristic AUC was 0.799 on the same held-out rows. The temporal diagnostic AUC was 0.645, below the 0.65 gate, and remains diagnostic only.

The counter-case is therefore central: Altico may be an intelligible historical chronology without being reliable evidence that comparable commercial-paper reliance predicts failure elsewhere. The construction-PIT diagnostic cannot promote into a forecast claim.

## What today's board shares

Today’s board is separate from the Altico replay. As of 2026-10-01, it contains 1 yellow institution and 2 green institutions: Belstar Microfinance Limited, Annapurna Finance Private Limited, and Arohan Financial Services Limited. Their cited filing date is 2026-03-31 and their age is 7 months. Their scores are 77.8, 96.5, and 97.1, respectively; no signals fired are listed.

Yellow is not a credit rating or a prediction of failure. Under the published rule, it may reflect deterioration, a level threshold, a funding flag, a forensic indicator, or a fresh authoritative market drawdown condition. The board excludes 36 stale institutions. Its method does not present quarterly filings older than 183 days or annual filings older than 400 days as current. Institutions without vetted dossiers are absent by design: nothing is scored from memory.

Market data were as of 2026-09-30 and retrieved on 2026-10-01. The market layer is fresh and clock-authoritative, but it has no admission, publication, or tier authority. Admitted canonical records are 0/25, while display rights and expected-record approvals are absent. It cannot upgrade the current tier story. See the [market evidence record](https://api.liquilens.in/api/evidence/markets).

## The next falsifiable test

The thesis weakens if future vetted disclosures show comparable refinancing reliance commonly persisting without liquidity strain, or if stressed institutions more often lack prior disclosed funding vulnerability. It also fails as a useful model if a prospective bitemporal dataset finds no discrimination beyond simpler disclosed-data heuristics.

A credible test needs actual publication times rather than the period-end-plus-60-days proxy, preserved missing disclosures, and outcomes unavailable when a signal was formed. It must not assign model or tier authority to unapproved market data. Until that work exists, historical lead times remain reconstructions rather than promises.

## Follow the pressure chain

The product boundaries are deliberately separate. [LiquiLens](https://liquilens.in/replay/altico/) covers **institution and lender balance-sheet risk**. [Seiche](https://api.seiche.info/api/overview) covers **system dollar-funding capacity**. [Undertow](https://api.seiche.info/undertow/board.json) covers **market liquidity and executable exit capacity**.

These questions can move together without becoming interchangeable. System funding conditions are not an institution filing signal. An institution’s disclosed liability structure is not a traded-market price. Exit capacity is not proof of either balance-sheet solvency or refinancing access. The [LiquiLens research archive](https://liquilens.in/research/) is a research record, not a substitute for those distinctions.

## Sources, method, and limits

This article draws on the [Failure Radar board](https://api.liquilens.in/api/failure-radar/board), [historical validation](https://api.liquilens.in/api/failure-radar/validation), [market evidence](https://api.liquilens.in/api/evidence/markets), [Altico replay](https://liquilens.in/replay/altico/), and [replay archive](https://liquilens.in/replay/). Publication date: 2026-10-01.

Altico’s filing observation is 2017-03-31; its availability proxy is 2017-05-30; its default date is 2019-09-12. Current institution filings cited here are as of 2026-03-31, while the market layer is as of 2026-09-30. This is a bounded historical interpretation of disclosed-data diagnostics. Its construction-PIT, missing-data, staleness, fraud-masking, rights, and authority limits are part of the finding, not footnotes to it. Research and market data, not investment advice.
