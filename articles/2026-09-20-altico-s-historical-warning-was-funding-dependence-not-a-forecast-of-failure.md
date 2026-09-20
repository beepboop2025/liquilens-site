*This is a historical replay, not current news and not a forecast. It examines Altico before its 2019-09-12 default. The key filing period ended 2017-03-31; the conservative knowledge-time proxy is 2017-05-30. The market-layer date is 2026-09-18 and publication is 2026-09-20.*

The proposition is deliberately narrow: Altico’s balance sheet should have been investigated first through funding, because disclosed commercial-paper reliance created rollover-freeze exposure. That is neither a claim that the flag proved distress nor that it forecast a default. It distinguishes a filing-period signal from a market-price signal and from a model derivation. The former records a disclosed liability structure; the second would show repricing by market participants; the third converts inputs into a score or rule. None is interchangeable.

## The record before the event

Altico was an NBFC, its funding lens was scoreable, and the dossier records no fraud-masking designation. Its first funding signal was a 23.7 index reading in the stable band at the 2017-03-31 period end. The accompanying flag was explicit: **“CP reliance 29% (rollover-freeze exposure)”**. The replay assigns a 27-month lead to the 2019-09-12 default.

That interval must not be mistaken for a tradable warning. The evidence status is `PERIOD_END_PROXY_CONSTRUCTION_PIT`. Where an explicit publication clock is unavailable, the construction uses period end plus 60 days. The dossier says lead times are optimistic, the record has no bitemporal input contract, and it is neither validated-backtest eligible nor real-money eligible. A period-end observation is therefore not proof that an outside creditor, investor, or counterparty possessed it on that date.

Readers can inspect the [Altico replay](https://liquilens.in/replay/altico/) alongside the [Failure Radar board](https://api.liquilens.in/api/failure-radar/board) and [validation record](https://api.liquilens.in/api/failure-radar/validation). The appropriate conclusion is that the liability structure merited investigation, not that the historical timestamp established actionable foresight.

## What the lenses saw

The funding lens saw a disclosed dependency on CP and labelled its relevant vulnerability: a possible rollover freeze. It did not document an actual freeze, identify the cause of the later default, or establish a complete causal chain. Its contribution was more limited: it isolated a liability channel through which refinancing conditions could become consequential while the asset side remained outstanding.

The historical funding record is small and selectively observable. Of 15 failed institutions, 10 had liability disclosures, and the funding signal fired first for 4; median lead was 38 months. The lens can only assess institutions that disclose a liability series. Missing disclosure is missing data, not evidence of comfortable funding. Nor does a funding flag tell readers whether another lens supplied an earlier or more useful warning.

The broader model diagnostics reinforce restraint. The hazard panel had 205 rows, 9 events, and 27 institutions, while 179 censored or unusable rows were excluded. Its leave-one-institution-out AUC was 0.752, with an interval of 0.338 to 1.0. The temporal result was 0.645, below the 0.65 gate, and remains diagnostic only. On the same held-out rows, the heuristic AUC was 0.799. These figures describe model derivations under constrained historical construction; they do not validate a live failure forecast.

## Why the warning mattered

A liability requiring renewal can create pressure before a broad balance-sheet screen visibly changes. If renewal becomes less available or more costly, replacement liquidity becomes the immediate question. That mechanism explains why CP reliance is a sensible diligence prompt. It does not assert an unrecorded Altico event.

The stable band is central to the interpretation. A stable composite reading did not erase the documented funding flag; equally, the flag did not overrule the stable reading and pronounce distress. The useful lesson is about sequencing: an individual funding dependency can deserve scrutiny before a composite level settles the broader case.

A separate public-disclosure replay of RBI PCA or SAF tripwires found that 5 of 15 failed institutions entered an action zone first, with median lead of 41 months. That does not make the regulatory lens superior to the funding lens, or vice versa. Filings later shown falsified can look compliant to a threshold engine; the forensic screen owns that limitation.

## The strongest counter-case

The counter-case can defeat an overconfident thesis. CP reliance of 29% may have been a visible financing choice rather than evidence of imminent impairment. The funding index was 23.7 and stable. The 27-month historical interval is long enough for an institution’s funding mix, liquidity, and counterparties to change materially. Because the availability clock is partly proxied, the replay cannot prove the precise contemporaneous information set.

The sample further limits any generalisation. Only 10 of 15 failed institutions disclosed usable liabilities, and only 4 had the funding signal fire first. The temporal model missed its stated gate; the heuristic outperformed the hazard measure on the reported held-out rows. Nothing here shows that CP reliance outperformed every alternative warning method, or that it distinguished Altico from every comparable lender.

The defensible thesis is therefore conditional: the disclosure made Altico a stronger candidate for rollover-capacity diligence. It did not show failure was inevitable, determine timing, or provide a complete explanation of the default.

## What today's board shares

Today’s board is not an Altico replay. As of 2026-09-20, it reports 0 red, 1 orange, 3 yellow, and 15 green institutions, with 21 excluded as stale. Utkarsh Small Finance Bank is orange with a 2025-03-31 as-of date and age of 18 months. Belstar Microfinance Limited is yellow at 2026-03-31 and 6 months; ESAF Small Finance Bank is yellow at 2025-09-30 and 12 months.

These are published screens, not ratings or predictions. The rule can assign yellow for a funding flag among other conditions. But the market layer lacks tier authority: records are fresh and clocked, yet display and tier use are not approved for every expected canonical record. Its [market evidence interface](https://api.liquilens.in/api/evidence/markets) identifies Yahoo Finance daily closes as source, but the dossier does not permit market-derived display to support a published tier conclusion.

## The next falsifiable test

This account would weaken if a prospective dataset, timed to actual publication, found that disclosed CP reliance did not precede measurable funding stress more often than comparable balance-sheet indicators after controlling for disclosure availability. It would weaken further if flagged institutions repeatedly renewed funding without observable pressure while other usable lenses consistently gave earlier warnings.

The test must retain actual availability times and preserve absent liability disclosure as missing rather than benign. It should compare the funding signal with independently observed subsequent stress outcomes. Until then, this construction-period replay is a hypothesis generator, not a validated trading rule, default model, or substitute for institution-specific diligence.

## Follow the pressure chain

The products have distinct remits. LiquiLens covers **institution and lender balance-sheet risk**: funding mix, disclosure quality, and lender-specific pressure points. Seiche covers **system dollar-funding capacity**; its [overview](https://api.seiche.info/api/overview) offers system context. Undertow covers **market liquidity and executable exit capacity**; its [board](https://api.seiche.info/undertow/board.json) reports incomplete segment coverage rather than a universal all-clear.

A system-funding divergence is a warning to investigate, not proof of a squeeze. A lender funding flag does not prove an exit problem, and partial market coverage cannot be read as normality. The diagnostic handoff is to locate pressure: institutional liabilities, system funding capacity, or executable exit capacity.

## Sources, method, and limits

Core materials are the [Failure Radar board](https://api.liquilens.in/api/failure-radar/board), [historical validation](https://api.liquilens.in/api/failure-radar/validation), [market evidence](https://api.liquilens.in/api/evidence/markets), and [Altico replay](https://liquilens.in/replay/altico/). Further desk material appears in [LiquiLens research](https://liquilens.in/research/) and [investigations](https://liquilens.in/investigations/).

The limits are substantive: filing-availability-proxied construction, a 60-day fallback lag, optimistic lead times, no bitemporal contract, selective liability disclosures, and no inference of calm from missing data. The replay identifies a historical balance-sheet mechanism worth testing. It does not convert that mechanism into a repeatable forecast.

This is not a credit rating. Research and market data, not investment advice.
