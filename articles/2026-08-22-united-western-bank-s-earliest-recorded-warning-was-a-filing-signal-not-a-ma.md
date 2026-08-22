*This is not current news and not a forecast. It is a historical replay of United Western Bank, which defaulted on 2006-09-02. Similar balance-sheet mechanisms do not imply the same outcome elsewhere.*

United Western Bank supplies a deliberately narrow answer to LiquiLens’s question: which balance sheet should have felt financial stress first, and why? The replay’s first recorded action-zone entry is at the period ended 2001-03-31. The listed breach is NNPA, and the knowledge-time proxy is 2001-05-30. The stated lead to default is 63 months.

That sequence supports only a limited finding. NNPA was the first documented **filing-period signal** among the recorded lenses. It does not show that the breach caused the default. It is not a **market-price signal**: the dossier provides no contemporaneous market repricing evidence for this institution. Nor is it a **model derivation** of a failure probability. The PCA replay applies published tripwires to public disclosures and reports the resulting rule status.

## The record before the event

The case record contains two observations that must remain separate. The PCA replay records an action-zone entry at 2001-03-31, with NNPA listed as the breach. The funding lens records no first signal. Neither observation authorises a complete story about cause, liquidity, or eventual failure.

The relevant clocks also differ. The filing period is 2001-03-31, while the knowledge-time proxy is 2001-05-30. The article is dated 2026-08-22. The Failure Radar board is as of 2026-08-21, and its market layer is as of 2026-08-11. Displaying a historical replay beside a current board does not make the old filing signal current.

The historical evidence status is `PERIOD_END_PROXY_CONSTRUCTION_PIT`. It is not validated-backtest eligible and not real-money eligible. There is no bitemporal input contract. Where an explicit publication clock is unavailable, the availability convention is period end plus 60 days. The dossier therefore says lead times are optimistic. This is an estimate of when disclosed information may have been available, not proof that a fully vintage-controlled process possessed it then.

## What the lenses saw

The PCA lens recorded the NNPA breach at the March period end and uses the May knowledge-time proxy. The funding lens did not fire first. That absence is not a finding that funding was sound. It is only the recorded result of that lens for this case.

The funding lens has an explicit eligibility limit: it only sees institutions with a disclosed liability series. In the historical funding summary, 15 failed institutions are listed, but only 10 have liability disclosures. The funding signal fired first for 4, with a median lead of 38 months. United Western Bank’s no-signal result cannot distinguish between no qualifying rule trigger and a disclosure constraint not resolved in this article.

PCA has limits of its own. Of 15 failed institutions in its summary, 5 entered an action zone first, with a median lead of 41 months. This is a public-disclosure replay of RBI PCA/SAF tripwires, not a claim that an action-zone breach necessarily produces default. The method note also warns that institutions whose filings were later shown falsified can appear compliant to a threshold engine; the forensic screen owns that problem. United Western Bank is not fraud-masked, but that status does not make the replay a full account of its condition.

## Why the warning mattered

The warning mattered because it was the earliest disclosed rule breach in the available case record. A filing-period breach can identify where a balance-sheet review should begin. It cannot, by itself, establish the path from a reported condition to a later default.

The dossier does not provide United Western Bank’s capital changes, liability flows, asset mix, management decisions, intervening shocks, or market-price history. Those omissions matter. It would be overreach to convert NNPA into a demonstrated causal chain, or to infer a funding event merely because a default followed.

The practical distinction is simple. A filing signal says a published rule was crossed in a reported period. A market-price signal would say that market prices repriced risk; none is supplied here. A model derivation would translate inputs into a model output; the replay instead records a threshold result. These are complementary evidence types, but they are not substitutes.

## The strongest counter-case

The counter-case defeats any broader thesis. A single disclosed NNPA breach is too coarse to explain why a bank defaulted 63 months later. Conditions can change over that interval, and the period-end-plus-60-days convention can make timing appear more exact than the public-information record warrants. Funding silence is also ambiguous: it cannot demonstrate either liquidity stress or liquidity calm.

The validation diagnostics argue for the same restraint. The hazard panel has 205 rows, 9 events, and 27 institutions, while 179 censored or unusable rows are excluded. Its leave-one-institution-out row AUC is 0.752, with an interval from 0.338 to 1.0. The heuristic reaches 0.799 on the same held-out rows. The temporal diagnostic AUC is 0.645 against a 0.65 threshold and is diagnostic only. Construction-PIT diagnostics cannot promote.

The defensible conclusion is therefore modest: asset quality was the first documented filing-period stress signal in the available replay. The record does not demonstrate a calibrated failure probability, a market consensus, a funding sequence, or a causal explanation of default.

## What today's board shares

Today’s board is separate evidence. As of 2026-08-21, it lists 0 red, 1 orange, 3 yellow, and 15 green institutions, while 21 stale institutions are excluded. It presents one row per institution with a fresh vetted public dossier and does not present anything older than 24 months as current.

Utkarsh Small Finance Bank is orange on a 2025-03-31 dossier aged 17 months, with a score of 74.9 and no listed fired signals. ESAF Small Finance Bank is yellow on a 2025-09-30 dossier aged 11 months, with a score of 66.0 and market distance-to-default of 1.927. Belstar Microfinance Limited is yellow on a 2026-03-31 dossier aged 5 months, with a score of 77.8. These are published-rule screens, not ratings or predictions.

[LiquiLens’s board](https://api.liquilens.in/api/failure-radar/board) states the institution-risk boundary: **LiquiLens: institution and lender balance-sheet risk**. The research boundary is: **construction-PIT only; no bitemporal input contract**. [Seiche](https://api.seiche.info/api/overview) covers **system dollar-funding capacity**. [Undertow](https://api.seiche.info/undertow/board.json) covers **market liquidity and executable exit capacity**.

## The next falsifiable test

This interpretation would weaken if a contemporaneously available, properly vintage-controlled record showed a qualifying United Western Bank funding signal before the NNPA breach. It would also weaken if revised evidence changed either the March classification or the availability date.

A prospective bitemporal test should ask whether action-zone breaches precede later balance-sheet stress more effectively than the available funding lens. If they do not, the thesis fails. The current record cannot settle that contest because it is construction-PIT only and its lead times are optimistic.

## Follow the pressure chain

Start with the verified sequence: NNPA breach at 2001-03-31, knowledge-time proxy at 2001-05-30, and default at 2006-09-02. Then seek independent evidence in liability disclosures, market repricing, or system and exit conditions. The order matters because it prevents two unsupported conclusions: asserting an unobserved funding problem as fact, and treating no funding flag as reassurance.

Historical replay can locate an early disclosed pressure point. It cannot make the outcome inevitable.

## Sources, method, and limits

The [United Western Bank replay](https://liquilens.in/replay/united-western-bank/) is the case file. The [Failure Radar board](https://api.liquilens.in/api/failure-radar/board) provides current tiers and components, while the [validation record](https://api.liquilens.in/api/failure-radar/validation) contains the historical summaries and diagnostics. The [market evidence index](https://api.liquilens.in/api/evidence/markets) describes the Yahoo Finance daily-close market layer. The [NDFI dataset](https://api.liquilens.in/api/us-radar/ndfi) is a United States watch and is not evidence about United Western Bank. Further [LiquiLens research](https://liquilens.in/research/) and the [replay archive](https://liquilens.in/replay/) provide context.

The limits are decisive: construction-PIT only; no bitemporal input contract; a 60-day filing-lag proxy where no explicit publication clock exists; optimistic lead times; and eligibility constrained by disclosure availability. Missing data are not calm. This is an evidence-bound historical diagnosis, not investment advice, not a credit rating, and not a forecast.
