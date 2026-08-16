*This is a historical replay, not current news and not a forecast. It asks where pressure first appeared in the dossier’s public-disclosure construction. It does not make a claim about any institution today.*

Global Trust Bank is the narrow answer to the desk question, with an important qualification. Its capital-and-asset-quality lens was the first scoreable institution signal: the replay records breaches of CRAR and NNPA for the period ended 2002-03-31. The institution defaulted on 2004-07-24. Yet the case is fraud-masked, and the funding lens is unscoreable. That means the sequence identifies the first *recorded disclosed* pressure point under this reconstruction; it cannot establish that the public record fully described the balance sheet or that a model independently foresaw the event.

The distinction among a filing-period signal, a market-price signal, and a model derivation is central. The action-zone observation is tied to a reporting period and a publication-time proxy. It is not a live market verdict. The dossier provides no Global Trust Bank market-price signal. And the resulting lead time is a model derivation from the chosen availability convention, not proof that market participants could have acted on complete information at that moment.

## The record before the event

The replay identifies the first action-zone observation as `threshold_2` in FY2002, for the period ended 2002-03-31. The recorded breaches were CRAR and NNPA. Under the PCA reconstruction, these are the disclosures that placed Global Trust Bank in an RBI action zone first.

The knowledge-time proxy is 2002-05-30, producing a 25-month lead to the default date. That is not a verified, complete filing-vintage timestamp. The dossier’s availability basis is an explicit publication clock where available; otherwise it applies period end plus 60 days. It expressly labels lead times optimistic.

This historical evidence has the status `PERIOD_END_PROXY_CONSTRUCTION_PIT`. It lacks a bitemporal input contract, is not eligible as a validated backtest, and is not eligible for real-money use. Those are not boilerplate qualifications. A replay that substitutes a period-end-plus-lag convention for a full contemporaneous publication record can overstate how early a warning was knowable.

The underlying case also carries the dossier’s fraud-masked flag. A threshold engine can only process disclosed inputs. It cannot certify that reported capital, asset quality, or any omitted balance-sheet fact was complete. See the [Global Trust Bank replay](https://liquilens.in/replay/global-trust-bank/), the [failure-radar board](https://api.liquilens.in/api/failure-radar/board), and the [validation record](https://api.liquilens.in/api/failure-radar/validation).

## What the lenses saw

The PCA lens produced the first recorded signal: CRAR and NNPA crossed the `threshold_2` action zone. That is a filing-derived balance-sheet signal. It says that, in the replayed public record, capital and recognized net non-performing assets met the published-rule condition.

The funding lens did not corroborate or contradict it. Global Trust Bank is marked unscoreable for funding, with no first signal and no lead time. This is missing analytical coverage, not evidence that funding was sound, liquid, or unimportant. The dossier is explicit that the funding lens only sees institutions that disclose a liability series.

There is also no Global Trust Bank market layer in the supplied replay record. A market-price signal would be a separate observation, such as the board’s distance-to-default measure, derived from market data rather than a filing-period threshold. It should not be retrofitted into this case merely because market repricing can matter elsewhere.

The broader historical summaries provide context but cannot repair those gaps. Of 15 failed institutions, 5 entered the PCA action zone first, with median lead of 41 months. Of the 10 failures with liability disclosures, 4 had the funding signal fire first, with median lead of 38 months. Those results remain public-disclosure replays with the same timing limitation, not prospective performance.

## Why the warning mattered

The warning mattered as a disciplined triage fact, not as a failure prediction. Two disclosed action-zone breaches put attention on the institution’s reported loss-absorption and recognized problem-asset position before the event. That is sufficient to identify where an analyst should have pressed for more evidence.

Any stronger causal account is a model derivation. It is reasonable to examine whether reported asset-quality stress and capital adequacy might constrain balance-sheet capacity, then whether that pressure transmits into funding or market prices. But this dossier does not provide the missing liability series, a Global Trust Bank market-price measure, or a clean disclosure record needed to prove that chain in this case.

Fraud-masking makes this restraint decisive. Where filings were later shown falsified, compliance or partial compliance in a threshold system cannot be read as a clean bill of health. The dossier assigns that limitation to the forensic screen. It does not allow a threshold engine to claim knowledge beyond the public record.

## The strongest counter-case

The counter-case can defeat any predictive thesis. The PCA reading may have been a visible symptom rather than the earliest economically meaningful stress. Its availability date is a proxy. The reported data were fraud-masked. Funding is unscoreable. And no market-price series is supplied to establish whether prices confirmed, anticipated, or rejected the filing signal.

The model diagnostics reinforce the objection. The hazard model’s leave-one-institution-out row AUC was 0.752, while the heuristic score was 0.799 on the same held-out rows. Its temporal AUC was 0.645, below the 0.65 diagnostic gate, which failed. Construction-PIT diagnostics cannot promote into a validated predictive claim.

Accordingly, the counter-case defeats the claim that this replay validates a deployable default model, a tradable signal, or a general ordering from capital stress to funding stress. It does not defeat the narrower factual claim: under the stated rules, CRAR and NNPA were the first recorded scoreable warnings.

## What today's board shares

Today’s board is separate from this historical case. As of 2026-08-15, it contains 0 red, 1 orange, 3 yellow, and 15 green institutions, while excluding 21 stale institutions. Nothing older than 24 months is presented as current.

Utkarsh Small Finance Bank is orange, with filing data as of 2025-03-31 and an age of 17 months. ESAF Small Finance Bank is yellow, with data as of 2025-09-30, an age of 11 months, and market distance-to-default of 1.927. Belstar Microfinance Limited is yellow, with data as of 2026-03-31 and an age of 5 months.

These are neither ratings nor failure forecasts. The board’s market layer uses Yahoo Finance daily closes, auto-adjusted, as of 2026-08-11. A market distance-to-default reading is a market repricing signal, not a filing-period observation; the Merton PD is not a calibrated failure frequency. Consult the [board](https://api.liquilens.in/api/failure-radar/board) and [market evidence index](https://api.liquilens.in/api/evidence/markets).

## The next falsifiable test

The narrow thesis fails if a prospective dataset with complete filing vintages and verified publication times shows that action-zone breaches do not precede independently observable balance-sheet deterioration more reliably than comparable institutions without those breaches. It also fails for this case-specific ordering if a scoreable liability series shows an earlier funding signal than the CRAR-and-NNPA observation.

That test must retain the exclusions: stale dossiers remain excluded, unavailable liability disclosures remain missing, and fraud-masked cases cannot certify a threshold engine. Period-end proxies must not be relabelled as real-time information.

## Follow the pressure chain

Start with the filing-period record: what did recognized asset quality and capital disclosures show? Then seek a distinct funding record, if disclosed. Next ask whether a market-price signal independently reprices the institution. Finally assess whether market exit capacity is observable. Each stage can be absent, delayed, or contradicted.

LiquiLens covers **institution and lender balance-sheet risk**. [Seiche](https://api.seiche.info/api/overview) covers **system dollar-funding capacity**; its composite is 45.2, labelled STRAIN, with guarded confidence because modelled or slow-moving structure leads current plumbing confirmation. [Undertow](https://api.seiche.info/undertow/board.json) covers **market liquidity and executable exit capacity**. Its segments include PARTIAL coverage, which is not a clean market signal.

## Sources, method, and limits

This article uses only the supplied dossier, including the [replay archive](https://liquilens.in/replay/), [validation endpoint](https://api.liquilens.in/api/failure-radar/validation), [research archive](https://liquilens.in/research/), and [institution-risk investigations](https://liquilens.in/investigations/). The method uses one fresh vetted public dossier per institution; failed institutions are replayed rather than presented as current.

The conformal alarm remains diagnostic only and has no score or tier authority pending prospective revalidation. Missing evidence is not evidence of calm. The publication-grade conclusion is deliberately limited: Global Trust Bank’s disclosed capital and asset-quality record signalled first in this construction, while the available evidence cannot prove that it was the first underlying stress, the first market-recognized stress, or a reliable forecast of failure.

This is not a credit rating. Research and market data, not investment advice.
