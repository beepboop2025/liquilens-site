This is a historical replay, not current news and not a forecast. Its narrow question is which part of a balance sheet may register financial stress first when continued refinancing matters. IL&FS is a case study, not a template for asserting that another institution will have the same outcome.

IL&FS defaulted on 2018-08-28. Its first funding signal belongs to the period ending 2015-03-31, with a knowledge-time proxy of 2015-05-30. That distinction is central. The replay supplies a filing-period signal: a result derived from reported information and an assumed availability clock. It is not a contemporaneous market-price signal, and it is not proof that the model discovered a causal mechanism before the event.

## The record before the event

The funding lens first registered a watch-band index of 45.4 for IL&FS at 2015-03-31. Under the dossier’s timing convention, the information became knowable at 2015-05-30, producing a reported lead of 38 months before default. The [IL&FS replay](https://liquilens.in/replay/ilfs/) is the relevant case file.

The interval is notable, but the evidence label sharply limits what it can mean. Historical evidence is `PERIOD_END_PROXY_CONSTRUCTION_PIT`: it is not validated-backtest eligible, not real-money eligible, and lacks a bitemporal input contract. When an explicit publication clock is unavailable, the record assumes period end plus 60 days. The dossier explicitly says lead times are optimistic. A filing-period date should therefore not be confused with the moment an investor, lender, supervisor, or counterparty could actually have acted on a fully understood warning.

IL&FS is also marked fraud-masked. Filings later shown to be falsified can look compliant to a threshold engine. That is not a minor caveat: it means a mechanical replay can register a pattern in disclosures while missing the reliability of the disclosures themselves. The forensic screen owns that failure mode. A threshold result is not evidence that reported figures were economically complete or trustworthy.

## What the lenses saw

The funding lens was the first recorded lens to signal for IL&FS. Its watch reading had no listed flags. The PCA lens has no recorded first action zone and no lead time for the institution. This is enough to say that, within this construction, a liability-side signal appeared before a recorded formal action-zone signal. It is not enough to say funding deterioration caused default, or that the same ordering will recur.

Across the funding summary, 15 institutions failed, while 10 had liability disclosures for the lens. The funding signal fired first in 4 cases, with a median lead of 38 months. That is descriptive evidence with an eligibility condition, not comprehensive evidence about every failed institution. Missing liability series are not neutral observations; they remove institutions from this particular comparison.

The PCA summary supplies a competing lens rather than a confirmation of funding supremacy. Of 15 failed institutions, 5 entered the action zone first, with a median lead of 41 months. It replays public disclosure of RBI PCA or SAF tripwires, using explicit publication time where present and the period-end-plus-60-day proxy otherwise. The [validation record](https://api.liquilens.in/api/failure-radar/validation) retains those limitations.

A model derivation needs equally careful treatment. The hazard diagnostic has 205 rows, 9 events and 27 institutions; 179 censored or unusable rows were excluded. Its leave-one-institution-out row AUC was 0.752, with a confidence interval of 0.338 to 1.0. The heuristic scored 0.799 on the same held-out rows. Its temporal AUC was 0.645, below the 0.65 diagnostic gate. The result is diagnostic only; construction-PIT diagnostics cannot promote.

## Why the warning mattered

A funding warning matters because liabilities must continue to be renewed. Where refinancing access or terms worsen, pressure may pass through funding, liquidity, earnings, asset sales, capital, and eventually supervisory response. But this is a pressure chain, not an observed causal sequence established by the replay. Each link needs contemporaneous evidence.

The useful IL&FS proposition is consequently modest: for a funding-dependent balance sheet, liability-side information may deserve investigation before a formal action-zone breach is recorded. The filing-period signal identifies where to look. It does not establish the timing of market recognition, identify an inevitable solvency event, or convert a watch band into a failure probability.

The radar’s tier is **not a credit rating**, and this article is **not investment advice**. Fraud masking makes those boundaries especially important: a system based on public disclosures should prompt investigation rather than replace it.

## The strongest counter-case

The strongest counter-case can defeat the thesis. The apparent early warning may be a construction artifact. The 60-day proxy can make the chronology look more actionable than real information flow was. The funding lens could be seeing changes in disclosure, liability management, or a condition that never becomes a failure. It observes only institutions with the necessary liability series, and IL&FS itself is fraud-masked.

Nor does the absence of a recorded PCA action-zone entry prove that funding was economically dominant. PCA and funding are different lenses with different inputs, thresholds, disclosure dependencies, and failure modes. A formal action-zone trigger may be absent from the available replay without establishing that it was absent in the underlying institution. The historical record is not a validated backtest or a real-money test.

That counter-case means IL&FS should not be described as predictably doomed at 2015-05-30. The defensible conclusion is narrower: under stated filing-availability assumptions, a funding watch signal existed and deserved analytical attention. If that is too weak to guide a decision without forensic, market, and fresh-disclosure confirmation, the thesis should be rejected for that decision.

## What today's board shares

Today’s board is a separate screen, not an extension of the IL&FS replay. As of 2026-08-15, it showed 0 red, 1 orange, 3 yellow, and 15 green institutions; 21 stale institutions were excluded. Institutions without fresh vetted public dossiers are absent by design. Their absence cannot be read as calm. The [Failure Radar board](https://api.liquilens.in/api/failure-radar/board) presents one row per institution with a fresh vetted public dossier, and nothing older than 24 months is presented as current.

Utkarsh Small Finance Bank was orange with a dossier as of 2025-03-31, aged 17 months. ESAF Small Finance Bank was yellow on information as of 2025-09-30, aged 11 months, with market distance-to-default of 1.927 and a `market_dd_below_2` signal. Belstar Microfinance Limited was yellow on a 2026-03-31 dossier, aged 5 months. These are rule-based tiers, not predictions.

The market layer, available as of 2026-08-11, uses Yahoo Finance daily auto-adjusted closes for listed names. Market distance-to-default is a market repricing signal, not a calibrated failure frequency. It must not be merged with a filing-period replay as though both carried the same timestamp or interpretation. The [market evidence index](https://api.liquilens.in/api/evidence/markets) is the separate market record.

## The next falsifiable test

The thesis fails if prospective, timestamped disclosures do not show that the funding lens adds timely information beyond formal action zones, forensic indicators, and market repricing on the same eligible institutions. The test requires a genuine bitemporal input contract: preserve what was public at the time, retain publication timestamps, and prevent amended or later-discovered information from entering the historical record.

It must keep missing liability series visible rather than treating them as benign. If funding does not improve early identification under those conditions, the IL&FS lesson should be narrowed or rejected.

## Follow the pressure chain

LiquiLens covers **institution and lender balance-sheet risk**. Seiche covers **system dollar-funding capacity**. Undertow covers **market liquidity and executable exit capacity**. These are boundaries, not interchangeable confirmations.

As of 2026-08-17, Seiche reported a guarded STRAIN read of 45.2, while its editorial noted that modelled or slow-moving structure led current market plumbing. Undertow reported PARTIAL coverage across several segments, despite NORMAL candidate tiers in some areas. Neither output turns an IL&FS filing replay into an institutional verdict. Read the [Seiche overview](https://api.seiche.info/api/overview) and [Undertow board](https://api.seiche.info/undertow/board.json) separately.

## Sources, method, and limits

This article uses the [replay archive](https://liquilens.in/replay/), the [IL&FS replay](https://liquilens.in/replay/ilfs/), the [Failure Radar board](https://api.liquilens.in/api/failure-radar/board), the [validation record](https://api.liquilens.in/api/failure-radar/validation), and the [market evidence index](https://api.liquilens.in/api/evidence/markets), alongside separate Seiche and Undertow diagnostics.

The tier is a published rule over published components. The conformal alarm has no score or tier authority pending prospective revalidation. Construction-PIT timing, optimistic lead times, incomplete liability disclosure, stale exclusions, missing dossiers, fraud masking, and the distinction between filing data, market prices, and model derivations are limits—not assurances. The productive question is not which screen foretells failure, but which balance sheet appears most exposed to refinancing pressure, what evidence supports that view, and what future evidence could falsify it.
