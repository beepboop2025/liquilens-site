This is not current news and not a forecast. It is a historical replay of New India Co-operative Bank, whose recorded event date is 2025-02-13. The narrow thesis is that the institution’s balance sheet should have shown stress first through disclosed asset quality: an RBI action-zone breach associated with net non-performing assets, or NNPA, appeared before the event. The thesis does not say a market price predicted the outcome, and it does not claim that the reported ratio establishes the underlying cause.

The distinction is essential. A filing-period signal says what the replay finds in reported information at a reporting date, with an assumed availability clock where necessary. A market-price signal would describe what a tradable instrument repriced when. A model derivation would turn inputs into a score, tier, or estimated risk measure. Those are different objects. Treating one as evidence for another is the fastest way to make a retrospective warning look more useful than it was.

## The record before the event

The first recorded supervisory action-zone trigger is the 2021-03-31 period end, identified as FY2021. The breached lens was NNPA. Because the record lacks an explicit publication clock, the replay assigns a knowledge-time proxy of 2021-05-30 under its period-end-plus-60-days convention. The stated lead to the 2025-02-13 event is 44 months.

That is a filing-period chronology, not a claim that an investor received a verified warning on the period-end date. The replay explicitly uses an availability proxy: an explicit publication clock when present, otherwise period end plus 60 days. Its historical evidence is labelled PERIOD_END_PROXY_CONSTRUCTION_PIT, its lead times are explicitly optimistic, and it lacks a bitemporal input contract. It is **not validated-backtest eligible** and **not real-money eligible**.

The [New India Co-operative Bank replay](https://liquilens.in/replay/new-india-co-operative-bank/) and the [Failure Radar board](https://api.liquilens.in/api/failure-radar/board) identify the institution as fraud-masked. That label is not a conclusion about the nature, timing, or scope of misconduct. It is a methodological warning: filings later shown falsified can look compliant to a threshold engine, while disclosed deterioration can fail to capture the hidden condition that ultimately mattered.

## What the lenses saw

The PCA/SAF-style lens recorded NNPA as the first action-zone signal. The funding lens recorded no first signal. Those findings have sharply different meanings from a clean bill of health. The first is a disclosed threshold breach in the replay. The second is not evidence of stable funding: the funding lens only observes institutions with a usable liability series, and missing liability disclosure can prevent a signal from being observed.

The validation summaries provide limited context. Among 15 failed institutions in the PCA summary, 5 entered an action zone first, with a median lead of 41 months. In the funding summary, 10 of 15 failed institutions had liability disclosures; 4 had a funding signal fire first, with a median lead of 38 months. These are descriptive replay outcomes, not conditional failure probabilities and not proof that the same mechanism dominated at New India.

The model evidence is also weaker than a polished score can imply. The temporal diagnostic AUC is 0.645, below its 0.65 gate. The diagnostic is explicitly not promotable: construction-PIT diagnostics cannot promote. The conformal alarm remains a diagnostic, but its historical tier wiring is suspended and it has no score or tier authority pending prospective revalidation. A retrospective narrative cannot cure a failed gate.

## Why the warning mattered

An NNPA action-zone breach matters as a balance-sheet signal because impaired disclosed assets can make collections less dependable and loss recognition more consequential. If pressure persists, capital absorption and management flexibility may become more important. That can affect confidence in the institution’s ability to absorb losses or adjust funding.

But that is a mechanism, not an established causal sequence for this bank. The dossier does not show that funding stress followed NNPA stress, nor does it establish that asset quality was the decisive source of the recorded event. The defensible conclusion is smaller: NNPA was the earliest documented supervisory-risk signal in this replay.

## The strongest counter-case

The counter-case can defeat the thesis. Because this institution is fraud-masked, the visible ratio may be a poor map of the true balance sheet. The NNPA breach could have been early, late, incomplete, or incidental to a hidden condition. A threshold engine can be useful for disclosed fragility while remaining unable to reconstruct what disclosures concealed.

The 44-month lead is also too long to demonstrate event timing. A warning can identify vulnerability without identifying imminence. The proxy availability convention may make the lead look cleaner than a genuinely point-in-time research record would permit. And the absence of a funding first signal may reflect missing or unusable liability information rather than an asset-led path.

The steel-manned verdict is therefore not that NNPA caused the event. It is that NNPA was the first disclosed warning available in this construction-PIT record, subject to a fraud-masking limitation strong enough to prevent causal certainty.

## What today's board shares

Today’s board is not a current scorecard for New India Co-operative Bank; failed institutions are replayed on the Evidence tab. As of 2026-10-08, the comparison set contains 0 red institutions, 0 orange, 1 yellow, and 2 green. Belstar Microfinance Limited is yellow with a score of 77.8; Annapurna Finance Private Limited and Arohan Financial Services Limited are green at 96.5 and 97.1. Their filing as-of date is 2026-03-31 and their stated age is 7 months.

Those are model-derived board outputs, not market-price signals and not credit ratings. The board excludes 35 stale institutions. Nothing older than 183 days for quarterly filings or 400 days for annual filings is presented as current. Omission is not reassurance; institutions without vetted dossiers are absent by design rather than scored from memory.

The market layer is available and fresh in clock terms, dated 2026-10-07 and retrieved on 2026-10-08. Yet it has 0 admitted canonical records out of 25, and no publication or tier authority. Its [market evidence index](https://api.liquilens.in/api/evidence/markets) may support investigation, but cannot support a market-derived institutional tier claim.

## The next falsifiable test

This thesis fails if a fully time-stamped authoritative record shows that the relevant disclosed NNPA condition did not enter the action zone before 2025-02-13, or was not available by the assumed 2021-05-30 proxy date. It weakens if reliable contemporaneous liability disclosures reveal an earlier funding signal missed by this replay.

The prospective test is to preserve original publication times, revisions, and later evidence of falsification, then test whether action-zone breaches add timely information beyond funding and forensic evidence. Until that exists, the 44-month figure is a historical replay lead, not an investable lead time.

## Follow the pressure chain

The diagnostic chain is conditional: impaired disclosed assets may reduce expected collections; reduced collections may increase loss-recognition and capital pressure; capital pressure may narrow balance-sheet flexibility; narrowing flexibility may make funding confidence more consequential. No arrow is asserted as a fact about every institution.

LiquiLens covers **institution and lender balance-sheet risk**. [Seiche](https://api.seiche.info/api/overview) covers **system dollar-funding capacity**. [Undertow](https://api.seiche.info/undertow/board.json) covers market liquidity and executable exit capacity. These are separate research boundaries: system conditions, an institution’s disclosed condition, and the ability to exit a position are not interchangeable confirmations.

## Sources, method, and limits

The principal records are the [Failure Radar board](https://api.liquilens.in/api/failure-radar/board), [historical validation file](https://api.liquilens.in/api/failure-radar/validation), [New India replay](https://liquilens.in/replay/new-india-co-operative-bank/), [market evidence index](https://api.liquilens.in/api/evidence/markets), [Seiche overview](https://api.seiche.info/api/overview), [Undertow board](https://api.seiche.info/undertow/board.json), and [US NDFI diagnostic](https://api.liquilens.in/api/us-radar/ndfi). The US diagnostic is context only and supplies no evidence about New India.

The tier rule fuses independently replayed components for presentation. Stale, future-dated, or unclocked market readings can remain visible but have no signal or tier authority. Most importantly, fraud masking means neither an apparently calm disclosure record nor an observed ratio can substitute for forensic reconstruction.

This is not a credit rating. Research and market data, not investment advice.
