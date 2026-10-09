*This is a historical replay, not current news and not a forecast. It examines Sambandh Finserve using a filing-availability-proxied construction record around past reporting periods. Similar mechanisms do not imply the same outcome elsewhere.*

Sambandh Finserve is the answer to this replay’s narrow question only in a limited sense: its disclosed liability structure generated the first recorded funding signal before its default. The institution defaulted on 2020-10-13 and is marked fraud-masked. That qualification is decisive. A threshold screen can identify a disclosed balance-sheet vulnerability; it cannot prove that the disclosures were complete or true, identify fraud, or turn an observed signal into a causal explanation of failure.

The signal belonged to the period ending 2016-03-31. Its knowledge-time proxy was 2016-05-30, based on period end plus 60 days where no explicit publication clock was available. Wholesale leverage was 8.51x, above the 7x flag, and the funding index was 78.7, in the fragile band. The recorded lead was 52 months. None of those facts makes the result a tradeable timestamp, a prospective forecast, or a finding that wholesale funding caused the default.

## The record before the event

The distinction among clocks is the first safeguard against retrospective overstatement. The reporting period ended on 2016-03-31; the replay assigns 2016-05-30 as a knowledge-time proxy; the article is dated 2026-10-09. These are not interchangeable dates. The proxy exists because the construction record does not have a bitemporal input contract and may lack an exact public availability time.

Sambandh was scoreable in the funding lens because the necessary liability series was disclosed. The lens recorded wholesale leverage of 8.51x against a 7x threshold, producing the fragile 78.7 reading. This was its first funding signal. The separate PCA record has no first-action-zone date and no PCA lead time. That missing record cannot be treated as evidence of resilience, just as it cannot be filled with an inference from the later default.

The dedicated [Sambandh replay](https://liquilens.in/replay/sambandh-finserve/) should therefore be read alongside the [Failure Radar board](https://api.liquilens.in/api/failure-radar/board) and the [historical validation record](https://api.liquilens.in/api/failure-radar/validation). The replay establishes a visible liability-side condition in disclosed data. It does not reconstruct the entire institution, its creditor relationships, or the integrity of every reported item.

## What the lenses saw

The funding lens saw a potential refinancing vulnerability rather than a completed stress event. Wholesale funding dependence can matter before reported asset impairment becomes decisive, because creditor willingness, funding terms, and the availability of refinancing can change before a final accounting break is visible. The relevant question is not whether a high ratio mechanically equals failure. It is whether the institution could withstand funders becoming less willing to renew or more demanding about price and terms.

The historical funding summary offers context but not validation. It covers 15 failed institutions, of which 10 had liability disclosures usable for the lens. The funding signal fired first for 4, with a median lead of 38 months. That is enough to support investigation of funding structure in some historical cases. It is not enough to claim that the lens is a calibrated prospective failure model.

The broader India diagnostic spans 48 institutions across two decades and reports that 88.9% of non-fraud failures were flagged, with a median lead of 21.5 months. Yet its status is PERIOD_END_PROXY_CONSTRUCTION_PIT. It is not eligible for a validated backtest or real-money use. Its filing convention is 60 days when an explicit clock is unavailable, and its lead times are explicitly optimistic.

The hazard exercise adds restraint. Its leave-one-institution-out row AUC was 0.752, with a confidence interval from 0.338 to 1.0. Its temporal AUC was 0.645, below the 0.65 diagnostic gate. The heuristic outperformed the hazard score on the same held-out rows. These are model derivations, not filing-period facts and not market-price signals. They cannot upgrade Sambandh’s observed funding flag into a production probability.

## Why the warning mattered

The warning mattered because it specified where to look first: the liability side. A wholesale-dependent institution may face pressure if refinancing becomes scarcer, shorter, or more expensive. That pressure could then constrain liquidity and earnings capacity, with confidence effects potentially intensifying the strain. This is a pressure chain to investigate, not an asserted history of Sambandh’s failure.

The fraud-masked designation prevents a stronger conclusion. Filings later shown to be falsified can look compliant to any threshold engine. Conversely, a visible funding flag can coexist with unobserved facts that dominate the eventual outcome. The forensic screen owns the question of deceptive or distorted disclosure. The funding screen owns only the disclosed liability signal.

## The strongest counter-case

The counter-case can defeat the thesis. Wholesale leverage above a threshold is not itself an event, and the funding lens fired first in only 4 cases with suitable disclosures. Some institutions may manage comparable dependence through liquidity, profitability, funding relationships, or changes in business model. Others lacked the liability series needed for the lens, which means the historical record is selective by construction.

For Sambandh, the fraud-masked status is more damaging still. If the reported liability series was materially incomplete or distorted, the ratio may be an unreliable description of the economic balance sheet. The later default does not validate the threshold as causal. It may show only that a disclosed warning coexisted with conditions the screen could not observe.

The thesis also fails if a fully timestamped reconstruction shows that the information was not available at the proxy date, differed materially from the replayed value, or gave no useful warning about refinancing terms, liquidity capacity, creditor access, or funding cost. That is why the 52-month lead must remain an optimistic construction result rather than an operational performance claim.

## What today's board shares

Today’s board is not a continuation of Sambandh’s replay. As of 2026-10-09, it has 0 red institutions, 0 orange institutions, 1 yellow institution, and 2 green institutions. Belstar Microfinance Limited is yellow with a score of 77.8. Annapurna Finance Private Limited and Arohan Financial Services Limited are green with scores of 96.5 and 97.1. Their filing date is 2026-03-31 and each is 7 months old.

These are screens, not predictions or credit ratings. The board excludes 35 stale institutions rather than presenting old evidence as calm. Nothing older than 183 days for quarterly filings or 400 days for annual filings is presented as current. Institutions without vetted dossiers are absent by design; absence is not a safety finding.

The market layer was fresh as of 2026-10-08, but had no admission, publication, or tier authority because market-derived display was not approved for every expected canonical record. It cannot upgrade, downgrade, or narrate these institution tiers. See the [market evidence index](https://api.liquilens.in/api/evidence/markets) for that limitation.

## The next falsifiable test

The appropriate test is prospective and timestamped. Preserve filing vintages and explicit publication times; separate forensic exceptions; then test whether funding flags add warning beyond simpler disclosure-based heuristics. A signal should demonstrate useful information before measurable deterioration in refinancing terms, liquidity capacity, creditor access, or funding cost, not merely appear persuasive after a default.

A diagnostic that misses its stated temporal gate remains diagnostic. Construction-period lead times cannot become an operational claim until the research record can meet the stricter test.

## Follow the pressure chain

The chain is not “high leverage equals failure.” It is wholesale dependence, possible refinancing pressure, possible constraints on liquidity and earnings, and possible confidence pressure. Sambandh’s filing-period signal identifies the first link in disclosed data. Its fraud-masked status means the remaining links cannot be asserted from this replay.

[Seiche’s overview](https://api.seiche.info/api/overview) covers system dollar-funding capacity. [Undertow’s board](https://api.seiche.info/undertow/board.json) covers market liquidity and executable exit capacity. LiquiLens covers institution and lender balance-sheet risk. These are separate diagnostic domains, not interchangeable scores or a combined failure call.

## Sources, method, and limits

Sources include the [Failure Radar board](https://api.liquilens.in/api/failure-radar/board), [validation dataset](https://api.liquilens.in/api/failure-radar/validation), [market evidence index](https://api.liquilens.in/api/evidence/markets), and [Sambandh case replay](https://liquilens.in/replay/sambandh-finserve/). Further context is available through [LiquiLens research](https://liquilens.in/research/) and [LiquiLens investigations](https://liquilens.in/investigations/).

The central limitation is the exact research boundary: this is PERIOD_END_PROXY_CONSTRUCTION_PIT, not eligible for a validated backtest or real-money use, with no bitemporal input contract and optimistic lead times. The institution-risk boundary is equally exact: LiquiLens covers institution and lender balance-sheet risk. It does not certify filing integrity, forecast default, or convert a historical signal into investment advice.

This is not a credit rating. Research and market data, not investment advice.
