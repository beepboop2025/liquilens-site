*This is a historical replay, not current news and not a forecast. It examines Global Trust Bank’s pre-event disclosures and does not infer that similar mechanisms will produce the same outcome elsewhere. The historical record is construction-PIT, not a validated backtest or a real-money signal.*

The narrow thesis is that Global Trust Bank’s first disclosed institutional warning appeared in its balance-sheet record: an RBI PCA action-zone entry associated with breaches in CRAR and NNPA. That is a filing-period signal. It is not evidence that a market price warned first, because this case has no scoreable funding signal and the current market layer cannot be used to support an institutional claim. Nor is it proof that a model predicted failure. The replay uses a period-end availability proxy and explicitly labels its lead times optimistic.

The decisive limitation is fraud masking. A threshold engine can identify pressure in reported measures, but cannot establish that the reports were complete or truthful. This is therefore a useful case for separating disclosed stress, price-based evidence, and model construction from hindsight.

## The record before the event

Global Trust Bank defaulted on 2004-07-24. The record places its first PCA action-zone entry at the 2002-03-31 period end, identified as FY2002. The status was `threshold_2`; the recorded breaches were CRAR and NNPA. Using the dossier’s knowledge-time proxy of 2002-05-30, the replay reports a 25-month lead to default.

That lead is not an observed trading-time advantage. Where an explicit publication clock is unavailable, the framework uses period end plus 60 days. The relevant historical status is `PERIOD_END_PROXY_CONSTRUCTION_PIT`; there is no bitemporal input contract, no validated-backtest eligibility, and no real-money eligibility. The record says directly that lead times are optimistic.

Still, the filing-period result has analytical content. The PCA lens recorded a joint capital and asset-quality breach before the event. It says the disclosed balance sheet had crossed a supervisory-style threshold, not that every investor, depositor, creditor, or market participant possessed the same information at the same instant. The [Global Trust Bank replay](https://liquilens.in/replay/global-trust-bank/) and [Failure Radar board](https://api.liquilens.in/api/failure-radar/board) preserve that distinction.

## What the lenses saw

The PCA lens is the only lens that produces a first signal in this case. Its action-zone record combines CRAR and NNPA breaches. Within the replay, that is the basis for saying that disclosed balance-sheet stress arrived before the default.

The funding lens does not offer a rival chronology. Global Trust Bank is marked unscoreable for funding, with no first signal and no lead time. That should not be translated into evidence that funding conditions were benign. It means the liability-disclosure series did not permit scoring. Missing data is neither a clean negative signal nor permission to fill the gap with narrative.

The forensic limitation is more important still. Global Trust Bank is explicitly fraud-masked. The validation record states that institutions whose filings were later shown falsified can look compliant to a threshold engine, and that the forensic screen owns that problem. In this instance, the PCA signal can show what the disclosed measures indicated; it cannot certify the integrity of those measures.

The broader summaries are descriptive context, not a probability model. The PCA replay covers 15 failed institutions, with five entering an action zone first and a median lead of 41 months. The funding summary also covers 15 failed institutions, but only 10 had liability disclosures; four saw the funding signal fire first, with a median lead of 38 months. The India diagnostic covers 48 institutions across two decades and reports 88.9% of non-fraud failures flagged, with a median lead of 21.5 months. It retains the same construction-PIT, proxy-availability, and optimistic-lead-time warnings. See the [validation record](https://api.liquilens.in/api/failure-radar/validation) and [market evidence index](https://api.liquilens.in/api/evidence/markets).

## Why the warning mattered

The significance of the joint breach is not that a threshold mechanically causes default. It is that the reported record placed asset quality and capital resilience under simultaneous scrutiny. A CRAR breach concerns the disclosed capital cushion; an NNPA breach concerns disclosed net non-performing assets. Together, they identify a balance-sheet condition that warranted closer examination before the event.

That is a triage conclusion. The signal directs attention to the reported loan book, provisioning, capital capacity, supervisory thresholds, disclosure credibility, and the unavailable funding lens. It does not supply an event chronology, assign causality, or establish that the reported breach alone determined the outcome.

The proper hierarchy is therefore clear. The filing-period signal is the PCA entry. A market-price signal would require authorized market evidence and a separate price-based interpretation. A model derivation is the replay’s application of rules and timing conventions to its historical inputs. Treating any one of those as the other would overstate the record.

## The strongest counter-case

The strongest counter-case can defeat a stronger version of the thesis. The apparent 25-month lead may exaggerate usable foresight because it begins with a period-end proxy and a 60-day filing-lag convention where an explicit publication clock is absent. Without immutable historical vintages and a bitemporal contract, the replay cannot prove the information set available on each decision date.

The diagnostics do not rescue that claim. The leave-one-institution-out hazard result reports row AUC of 0.752, with a confidence interval from 0.338 to 1.0. Its heuristic comparator has AUC of 0.799 on the same held-out rows. The temporal diagnostic reports AUC of 0.645, below the 0.65 gate, and is diagnostic only. These outputs may be informative construction checks, but they are not a promotion path to validated prediction.

Fraud masking is the deeper objection. A disclosure-driven engine cannot see through false, incomplete, stale, or unavailable inputs merely because its thresholds are well specified. The case can support the modest statement that disclosed PCA stress preceded the event in this replay. It cannot support a claim that the system would reliably uncover concealed weakness or issue a tradable failure call.

## What today's board shares

Today’s board is separate from this replay. As of 2026-10-02, it shows no red institutions, no orange institutions, one yellow institution, and two green institutions. Belstar Microfinance Limited is yellow, with a score of 77.8 and a 2026-03-31 as-of date. Annapurna Finance Private Limited and Arohan Financial Services Limited are green, with scores of 96.5 and 97.1. The displayed filings are seven months old, and 35 stale institutions are excluded.

Those rows are not analogues of Global Trust Bank. Belstar has no listed fired signals and no market drawdown in its comparison row. The current market layer is fresh and clock-authorized, but lacks display, admission, publication, model-gate, and tier approval. It has admitted canonical records of 0/25. It therefore cannot substantiate a present institutional-risk claim.

LiquiLens covers **institution and lender balance-sheet risk**. [Seiche](https://api.seiche.info/api/overview) covers **system dollar-funding capacity**. [Undertow](https://api.seiche.info/undertow/board.json) covers **market liquidity and executable exit capacity**. These are distinct products, evidence types, and authority boundaries.

## The next falsifiable test

The thesis should fail if a prospective record with actual publication timestamps and immutable vintages finds that joint PCA-style CRAR and NNPA breaches do not precede independently observed institutional stress after fraud-masked cases, unavailable liability series, and stale filings are separated. It should also weaken if verified disclosures show that such breaches routinely resolve without subsequent pressure over the applicable observation horizon.

The reverse is not a rerun of this replay. Credibility would require prospective evidence, explicit publication clocks, complete eligibility rules, preserved missing-data treatment, and a clear distinction between disclosure signals and market signals. Replacing the period-end proxy with auditable availability is the test.

## Follow the pressure chain

Begin with the reported assets and asset-quality measures. Then ask whether the reported capital measure has crossed the relevant action-zone threshold. Next, determine whether liability disclosures actually support a funding assessment; for Global Trust Bank, they do not. Finally, test whether the disclosures themselves deserve confidence. In a fraud-masked case, apparent calm in a reported component is not a clean bill of health.

The handoff should remain disciplined: use LiquiLens for balance-sheet review, Seiche for broad dollar-funding context, and Undertow for market exit conditions. Do not fuse their outputs into one failure verdict.

## Sources, method, and limits

This article uses only recorded dossier outputs: the [Global Trust Bank replay](https://liquilens.in/replay/global-trust-bank/), [Failure Radar board](https://api.liquilens.in/api/failure-radar/board), [historical validation output](https://api.liquilens.in/api/failure-radar/validation), [market evidence record](https://api.liquilens.in/api/evidence/markets), [Seiche overview](https://api.seiche.info/api/overview), and [Undertow board](https://api.seiche.info/undertow/board.json). Further desk material is available through [LiquiLens research](https://liquilens.in/research/).

The historical evidence remains `PERIOD_END_PROXY_CONSTRUCTION_PIT`, not validated-backtest eligible and not real-money eligible. The funding lens is unscoreable for Global Trust Bank. Fraud masking limits every disclosure-based inference. Current market data may be visible in the underlying system, but its authority gates prohibit its use here as institutional proof. These limits are central to the conclusion, not footnotes to it.

This is not a credit rating. Research and market data, not investment advice.
