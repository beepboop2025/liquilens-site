*This is a historical replay, not current news and not a forecast. United Western Bank defaulted on 2006-09-02. Its relevant filing-period observation was 2001-03-31, with 2001-05-30 used as a knowledge-time proxy. The publication date is 2026-10-10.*

United Western Bank offers a narrow answer to the desk question: the first disclosed sign of strain was in asset quality. The record shows an NNPA breach of an RBI action-zone threshold at the 2001-03-31 period end. The funding lens was scoreable, yet records no first signal and no lead-month figure. The case therefore supports a limited proposition: disclosed impairment appeared before an observable funding-lens warning.

It does not establish that asset quality caused the default, that markets ignored a known fact, or that the interval was tradable. The distinction matters. This is a filing-period signal reconstructed with a publication proxy; it is not a contemporaneous market-price signal. Nor is it a model derivation capable of converting the breach into a calibrated probability of failure.

## The record before the event

The [United Western Bank replay](https://liquilens.in/replay/united-western-bank/) identifies the first PCA action-zone observation as `threshold_2`, with NNPA as the breach, at 2001-03-31. Where an exact publication clock is unavailable, the historical process uses period end plus a 60-day filing lag. That produces the 2001-05-30 knowledge-time proxy and a stated lead of 63 months to the 2006-09-02 default.

That lead is useful only if read correctly. The period end says when the reported condition is assigned in the replay. The proxy says when the process assumes that condition could have been known. Neither says when every creditor, depositor, investor, or supervisor actually learned it, how they interpreted it, or how a security price reacted. There is no approved market-derived institution conclusion in this case.

The institution was not fraud-masked. Still, the replay is not a full causal history. It cannot show from this record alone whether the impairment was repaired, whether other balance-sheet pressures were already active, or whether a separate channel determined the path to failure. It shows a disclosed supervisory-style tripwire before default.

## What the lenses saw

The PCA lens saw an NNPA action-zone breach. The funding lens saw no first signal. That asymmetry is the entire factual core of the article.

The [Failure Radar board](https://api.liquilens.in/api/failure-radar/board) states that an RBI action-zone breach can place an institution in the highest screen category. But a screen rule is not a causal mechanism. The dossier permits a pressure-chain interpretation: impaired assets may reduce loss-absorption capacity, which may later affect resilience. It does not supply a quarter-by-quarter decomposition of losses, capital, funding cost, withdrawals, or refinancing for United Western Bank.

The historical summaries are similarly constrained. Of 15 failed institutions, five first entered an action zone, with a median lead of 41 months. The funding lens had liability disclosures for 10 of the 15, fired first for four, and had a median lead of 38 months. Those are replay descriptions of selected historical records, not competing estimates of a universal failure process.

The broader India diagnostic covers 48 institutions across two decades and reports 88.9% of non-fraud failures flagged, with a median lead of 21.5 months. Yet the [validation record](https://api.liquilens.in/api/failure-radar/validation) classifies that evidence as `PERIOD_END_PROXY_CONSTRUCTION_PIT`. It is not validated-backtest eligible, not real-money eligible, and does not have a bitemporal input contract.

## Why the warning mattered

The warning mattered because it marked a condition worth investigating before the funding lens registered one. An NNPA threshold breach is a filing-based sign that the asset side had reached a supervisory-style tripwire. For a balance-sheet analyst, that changes the next questions: was the impairment contained, was loss-absorption capacity changing, and did later disclosures reveal a transmission into funding access or resilience?

It should not be turned into a countdown. The 63-month figure is the replay’s interval between a proxy availability date and default, not proof that a lender had 63 months to act. The dossier explicitly says lead times are optimistic. A later actual filing date would compress the apparent lead.

Nor does the absence of a funding signal demonstrate funding calm. The funding lens only sees institutions with a disclosed liability series. United Western Bank was scoreable, but a no-signal outcome can mean the lens found no qualifying pattern; it cannot prove that every relevant funding pressure was absent. Missing or unmeasured evidence is not evidence of calm.

## The strongest counter-case

The counter-case can defeat the thesis. The apparent precedence of asset quality may be partly a construction artifact. The action-zone observation is anchored to period end, then made available through a 60-day proxy rather than a verified publication timestamp. The record lacks the bitemporal contract needed to establish what data existed in what form at each historical decision point.

There is also no market confirmation to invoke. The available market layer is fresh by its clock, but has no admission, tier, or publication authority: rights and display approvals are not complete for every expected canonical record, with admitted canonical records at 0/25. Market-derived display and tier conclusions are therefore not authorized here. A filing signal cannot be recast as a market-price signal merely because market data exist elsewhere in the product.

The model evidence is no rescue. The hazard model’s held-out row AUC is 0.752, while the heuristic is 0.799 on the same held-out rows. The temporal AUC is 0.645, below the 0.65 diagnostic gate, and remains diagnostic only. Model outputs do not promote construction-PIT evidence into a validated predictive system.

Most importantly, asset impairment may have identified early stress without explaining the route to default. A complete, timestamped liability record could show that an unobserved funding warning came first. Comparable action-zone breaches could also reverse without failure. United Western Bank is therefore evidence of early disclosed impairment, not proof that asset quality always leads liquidity.

## What today's board shares

Today’s board is separate from the historical replay. As of 2026-10-10, it has 0 red institutions, 0 orange institutions, 1 yellow institution, and 2 green institutions. Belstar Microfinance Limited is yellow; Annapurna Finance Private Limited and Arohan Financial Services Limited are green. Their filings are as of 2026-03-31 and aged 7 months.

The board excludes 35 stale institutions. That is a data-quality safeguard, not reassurance about omitted names. The stated policy does not present quarterly filings older than 183 days or annual filings older than 400 days as current. Institutions without vetted dossiers are absent by design; nothing is scored from memory.

## The next falsifiable test

The thesis weakens if original, timestamped filings show that the NNPA observation was not available by 2001-05-30. It fails as a claim of precedence if a complete liability series shows a qualifying funding signal before the asset-quality observation. It also loses practical force if a prospective record finds that comparable breaches add no timely information beyond funding disclosures.

The necessary test is prospective and bitemporal: retain original filings, actual publication times, liability disclosures, and lens outputs as known at the time. Then test whether action-zone breaches improve timely diagnosis without period-end assumptions. Until that exists, the 63-month interval remains a historical diagnostic.

## Follow the pressure chain

Start with the disclosed asset-quality condition. Next, examine whether later filings show reduced capacity to absorb losses or a change in liability pressure. Then separate a reported balance-sheet condition from a confirmed funding event and from a market-price move.

The product boundary is deliberate: Seiche covers **system dollar-funding capacity**; LiquiLens covers **institution and lender balance-sheet risk**; Undertow covers **market liquidity and executable exit capacity**. These are adjacent lenses, not interchangeable verdicts. Readers can use the [replay library](https://liquilens.in/replay/), [LiquiLens research](https://liquilens.in/research/), [Seiche overview](https://api.seiche.info/api/overview), and [Undertow board](https://api.seiche.info/undertow/board.json) in their respective lanes.

## Sources, method, and limits

This article relies on the supplied [Failure Radar board](https://api.liquilens.in/api/failure-radar/board), [historical validation](https://api.liquilens.in/api/failure-radar/validation), [market evidence index](https://api.liquilens.in/api/evidence/markets), and United Western Bank replay.

The central evidence remains `PERIOD_END_PROXY_CONSTRUCTION_PIT`: exact publication clocks may be missing; the fallback is period end plus 60 days; lead times are optimistic; validated backtesting and real-money eligibility are false; and no bitemporal input contract exists. The funding lens has incomplete observability because it depends on liability disclosures. Stale, future-dated, or unclocked market readings have no signal or tier authority. Filings later shown falsified can make a threshold engine appear compliant; the dossier assigns that problem to a forensic screen. These limits are not footnotes to the result. They define what the result can mean.

This is not a credit rating. Research and market data, not investment advice.
