*This is a historical replay, not current news and not a forecast. It examines the record available before Abhyudaya Co-operative Bank’s event date of 2023-11-24. Similar mechanisms do not imply the same outcome at another institution.*

The narrow answer to the desk question is Abhyudaya Co-operative Bank: its disclosed asset-quality position should have demanded attention first because the replay records an RBI supervisory action-zone breach through NNPA. That is not the same as saying its funding failed first, that its market price predicted the event, or that a model assigned a reliable failure probability.

The distinction is central. A filing-period signal is an observation from a reported balance sheet, subject here to an availability proxy. A market-price signal is a repricing measure, available only where a market layer exists. A model derivation combines inputs under stated assumptions and must not be mistaken for either a filing fact or an outcome frequency. The case supports a bounded conclusion: an asset-side supervisory threshold was visible before the event, while the disclosed-liability lens did not fire first.

## The record before the event

Abhyudaya was a co-operative bank with an event date of 2023-11-24. Its first recorded action-zone period end was 2021-03-31, labelled FY2021. The sole recorded breach was NNPA. The replay assigns a knowledge-time proxy of 2021-05-30 and records a 29-month lead to the event.

Those dates should not be read as a complete contemporaneous information record. The historical evidence is explicitly **PERIOD_END_PROXY_CONSTRUCTION_PIT**. Where an explicit publication clock is unavailable, availability is treated as period end plus 60 days. The bitemporal input contract is absent, the record is not validated-backtest eligible, and it is not real-money eligible. Lead times may therefore be optimistic.

That limitation changes what can responsibly be claimed. The replay shows that a reported NNPA breach was placed in the action zone before the event. It does not establish causation, identify every later development, or show that a reader at the time possessed a fully timestamped filing archive. The case file is available in the [Abhyudaya replay](https://liquilens.in/replay/abhyudaya-co-operative-bank/).

The funding result is equally important. Abhyudaya was scoreable for the funding lens, but no first funding signal is recorded. That is not evidence of ample liquidity, depositor confidence, or safety. It says only that the disclosed-liability screen did not provide the first recorded warning. The dossier also records no fraud masking for Abhyudaya. More generally, filings later shown to be falsified can look compliant to a threshold engine; the forensic screen, rather than a numerical rule, owns that problem.

## What the lenses saw

The asset-quality lens saw an NNPA action-zone breach. The funding lens did not fire first. These are not rival verdicts and should not be collapsed into a single story of bank stress. One is a filing-period observation about a supervisory tripwire; the other is a screen over disclosed liability information. Neither is a market-price signal.

The wider PCA and SAF replay supplies limited context. Among 15 failed institutions, 5 entered the action zone first, with a median lead of 41 months. This is a replay of RBI tripwires using explicit publication time where available and otherwise the period-end-plus-60-days convention. It is not a claim that action-zone entry produces a known probability of failure.

The funding subset is narrower. Of 15 failed institutions, 10 had liability disclosures, and 4 had a funding signal fire first, with a median lead of 38 months. The lens can only see institutions that disclose a liability series. A missing signal can therefore be a data boundary rather than evidence that funding conditions were sound. The [validation record](https://api.liquilens.in/api/failure-radar/validation) and [Failure Radar board](https://api.liquilens.in/api/failure-radar/board) retain those eligibility constraints.

## Why the warning mattered

The warning mattered as an attention-allocation signal. An NNPA breach locates pressure in reported asset quality and in the supervisory framework. It gives an analyst a concrete balance-sheet channel to investigate before inventing a funding panic that the evidence does not document.

A plausible pressure chain runs from weaker asset performance to recognition and provisioning demands, then to reduced capacity to absorb further losses. But that is a balance-sheet mechanism for examination, not an evidenced account of every step in Abhyudaya’s subsequent path. The dossier does not establish that this mechanism caused the event.

The sequence is the usable finding. A filing-period asset-quality threshold appeared first in this case. The funding screen did not lead. The event followed. That sequence is meaningful for historical triage, but insufficient for a deterministic thesis about any present institution.

## The strongest counter-case

The counter-case can defeat any stronger version of the thesis. A single NNPA tripwire is blunt; only 5 of 15 failed institutions entered the action zone first. The historical construction uses a partly proxied availability clock, and its lead times may be optimistic. It cannot show what investors, depositors, supervisors, or management knew at each exact moment without the missing bitemporal contract.

The model diagnostics provide no escape from that weakness. The hazard panel has 205 rows, 9 events, and 27 institutions; 179 censored or unusable rows were excluded. Its leave-one-institution-out row AUC was 0.752, with a confidence interval of 0.338 to 1.0. The heuristic score was 0.799 on the same held-out rows. The temporal diagnostic AUC was 0.645, below the 0.65 gate, and remains diagnostic only.

That evidence does not support a production claim of predictive precision. Nor does the action-zone finding establish that asset quality always leads funding stress. It supports only the narrower historical observation that Abhyudaya’s reported NNPA breach preceded any recorded first funding signal in this construction.

## What today's board shares

Today’s board is separate from the historical replay. As of 2026-08-26, it shows 0 red, 1 orange, 3 yellow, and 15 green institutions; 21 stale institutions are excluded. ESAF Small Finance Bank is yellow, as of 2025-09-30, with a score of 66.0 and market DD of 1.927. Utkarsh Small Finance Bank is orange, as of 2025-03-31, with a score of 74.9. Belstar Microfinance Limited is yellow, as of 2026-03-31, with a score of 77.8.

Those rows have different evidence ages and should not be treated as replays of Abhyudaya. The market layer is separately as of 2026-08-11. A market DD is a market-price signal; it is not a filing-period fact. The Merton PD is a market repricing signal, not a calibrated failure frequency.

The exact institution-risk boundary is: **LiquiLens: institution and lender balance-sheet risk**. The board uses a published rule over published components, while the conformal alarm has no score or tier authority pending prospective revalidation. Fresh vetted public dossiers are required; nothing older than 24 months is presented as current, and institutions without vetted dossiers are absent by design.

## The next falsifiable test

The thesis would weaken if fresh, prospectively timestamped dossiers show repeated action-zone entries without a subsequent asset-pressure chain, while institutions without such breaches repeatedly disclose earlier funding stress. It would weaken further if actual publication timestamps erase the apparent lead produced by the period-end-plus-60-days proxy.

A credible test needs the missing bitemporal input contract: preserve original filing vintages, record publication time, pre-specify the rule, and observe outcomes prospectively. Until then, the historical replay is diagnostic evidence, not certainty, a credit opinion, or investment advice.

## Follow the pressure chain

For Abhyudaya, follow the disclosed sequence: the 2021-03-31 NNPA action-zone breach; the 2021-05-30 availability proxy; no recorded first funding signal; and the 2023-11-24 event. This ordering distinguishes reported balance-sheet pressure from an unobserved liability panic.

For current names, first check dossier freshness. Then identify whether a tier arises from level, deterioration, a funding flag, a forensic indicator, or market DD. Do not merge those categories. A model derivation, a market repricing, and a filing-period observation answer different questions.

## Sources, method, and limits

The principal materials are the [Abhyudaya replay](https://liquilens.in/replay/abhyudaya-co-operative-bank/), the [board](https://api.liquilens.in/api/failure-radar/board), the [historical validation](https://api.liquilens.in/api/failure-radar/validation), and the [market evidence index](https://api.liquilens.in/api/evidence/markets). The [NDFI watch](https://api.liquilens.in/api/us-radar/ndfi) is separate U.S. lender context, not evidence about Abhyudaya.

The research boundary is: **PERIOD_END_PROXY_CONSTRUCTION_PIT**. It means the replay relies on explicit publication clocks when present and otherwise a 60-day filing-lag proxy; it does not meet a bitemporal, validated-backtest, or real-money standard. Missing liability evidence is not funding strength, and absent system context is not calm.

The broader products also have distinct remits. [Seiche](https://api.seiche.info/api/overview) covers system dollar-funding capacity. [Undertow](https://api.seiche.info/undertow/board.json) covers market liquidity and executable exit capacity. Neither should be used to repair missing institution-level evidence in this replay.

This is not a credit rating. Research and market data, not investment advice.
