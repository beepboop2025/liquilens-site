*This is a historical replay, not current news and not a forecast. It examines information associated with Abhyudaya Co-operative Bank before its 2023-11-24 default date. Similar mechanisms do not imply the same outcome at another institution.*

The central finding is narrow. In this replay, Abhyudaya Co-operative Bank first entered the recorded action zone at 2021-03-31, in FY2021, on NNPA. Its funding lens was scoreable but recorded no first signal. The balance-sheet pressure visible first in the disclosed record was therefore asset quality, not a liability-side alarm.

That is a filing-period signal, not proof that market participants acted on it at that moment, and not a model-derived probability of failure. The difference is decisive. A period end identifies when a reported condition existed; a publication clock identifies when it could have been known from the available public record; a model combines inputs under rules that may be useful for presentation but cannot establish causation. This replay has a knowledge-time proxy of 2021-05-30, based on period end plus 60 days where no explicit publication clock is present.

## The record before the event

The case record identifies an NNPA breach as Abhyudaya’s first recorded supervisory action-zone signal. It reports a 29-month lead to the default date and marks the institution as not fraud-masked. The proper conclusion is not that NNPA alone determined the outcome. It is that the disclosed asset-quality condition was the first recorded trigger demanding closer work on loss absorption, funding disclosures, and the path between them.

The replay is classified as `PERIOD_END_PROXY_CONSTRUCTION_PIT`. It is not validated-backtest eligible, not real-money eligible, and does not have a bitemporal input contract. Availability uses an explicit publication clock when present; otherwise it uses the period-end-plus-60-days proxy. The dossier explicitly says lead times are optimistic.

That limitation bars a stronger claim about real-time foresight. A threshold may have become public later than the proxy assumes. Equally, a measured lead is not an investable lead. The relevant evidence is available in [the Abhyudaya replay](https://liquilens.in/replay/abhyudaya-co-operative-bank/) and the wider [LiquiLens replay archive](https://liquilens.in/replay/).

## What the lenses saw

The PCA/SAF lens recorded the NNPA breach first. In the PCA summary, 15 institutions failed, 5 entered the action zone first, and median lead was 41 months. The funding summary describes a different and materially constrained lens: of 15 failed institutions, 10 had liability disclosures, 4 fired a funding signal first, and median lead was 38 months.

Those summaries do not show that either lens predicts an individual outcome. They show that different public disclosures can reveal different parts of a pressure chain. The funding lens can only assess institutions with a disclosed liability series. No fired funding signal is therefore not evidence of stable funding; it can be an observation boundary.

The broader India diagnostic covers 48 institutions across two decades and reports that 88.9% of non-fraud failures were flagged, with median lead of 21.5 months. It carries the same construction-PIT status and optimistic-lead warning. Readers should treat the [Failure Radar board](https://api.liquilens.in/api/failure-radar/board) and [historical validation record](https://api.liquilens.in/api/failure-radar/validation) as diagnostics, not as a promoted failure model.

The hazard work reinforces that restraint. Its leave-one-institution-out AUC was 0.752, with a confidence interval of 0.338 to 1.0. The comparison heuristic reached 0.799 on the same held-out rows. Its temporal AUC was 0.645, below the 0.65 gate, and is explicitly diagnostic only. Construction-PIT diagnostics cannot promote.

## Why the warning mattered

An NNPA action-zone breach matters because it directs attention to the asset side before a funding alarm is recorded. If impaired assets weaken, the questions become whether loss recognition, provisions, earnings capacity, capital resilience, and liability disclosures can withstand the strain. The dossier supports that investigative sequence; it does not supply evidence for a deposit run, a liquidity event, or a single causal mechanism at Abhyudaya.

The absence of a first funding signal is useful precisely because it prevents the article from asserting one. It leaves a limited proposition: asset quality was the earlier recorded pressure point in this replay. A supervisory-relevant tripwire is more informative than an isolated ratio, but it still cannot reveal all information held by management or supervisors, or decide whether a breach would be cured.

## The strongest counter-case

The counter-case can defeat the thesis. An NNPA breach may be lagging, manageable, or shaped by recognition timing. The decisive pressure could instead have been governance, operations, funding, or another unobserved channel. The funding lens’s silence cannot distinguish calm from insufficient liability disclosure. Nor does the replay establish that an asset-quality signal was the first condition known to all relevant actors.

The timing limitation sharpens that objection. Without a bitemporal input contract, and with a fallback publication proxy, the apparent ordering can change when a true filing-availability archive is available. The dossier also warns that institutions whose filings were later shown falsified can look compliant to any threshold engine; the forensic screen owns those cases. Abhyudaya is not fraud-masked, but that boundary still prevents a clean screen history from becoming proof of safety.

## What today's board shares

Today’s board is separate from the Abhyudaya replay. As of 2026-09-07, it has 0 red, 1 orange, 3 yellow, and 15 green institutions. Utkarsh Small Finance Bank is orange, using a 2025-03-31 filing aged 18 months, with a score of 74.9. Belstar Microfinance Limited is yellow, using a 2026-03-31 filing aged 6 months, with a score of 77.8. ESAF Small Finance Bank is yellow, using a 2025-09-30 filing aged 12 months, with a score of 66.0.

No market drawdown is supplied for those rows. Market data are fresh, but they have no publication, admission, model-gate, or tier authority because rights and display use are not approved for every expected canonical record. They cannot validate names or tiers. The board also excludes 21 stale institutions. Institutions without vetted dossiers are absent by design: nothing here is scored from memory.

## The next falsifiable test

The asset-quality-first reading fails if properly time-stamped disclosures show that the NNPA breach was cured without material deterioration in loss-absorption capacity, while an independently documented funding or other channel appeared earlier and proved more consequential. It also fails if a true publication-time archive materially reverses the ordering.

The practical test is therefore prospective and archival: preserve original availability times, separate filing conditions from public knowledge, and observe whether an asset-quality trigger precedes a demonstrable balance-sheet constraint. Until that standard is met, the replay supports scrutiny rather than certainty.

## Follow the pressure chain

Begin with the disclosed action-zone condition. Then examine the transmission through loss absorption and liability disclosures, without treating missing series as reassuring. Only after that should an analyst ask whether market pricing or executable exit conditions independently confirm stress.

LiquiLens covers **institution and lender balance-sheet risk**. Seiche covers **system dollar-funding capacity**; its [overview](https://api.seiche.info/api/overview) reads 44.9, EROSION, with guarded confidence as of 2026-09-07. Undertow covers **market liquidity and executable exit capacity**; its [board](https://api.seiche.info/undertow/board.json) has multiple PARTIAL segments. Those are distinct product boundaries, not interchangeable confirmations of Abhyudaya’s historical mechanism.

## Sources, method, and limits

This article uses the dossier’s [market evidence index](https://api.liquilens.in/api/evidence/markets), [US NDFI watch](https://api.liquilens.in/api/us-radar/ndfi), [LiquiLens research](https://liquilens.in/research/), and cited replay and validation materials. Components are replayed independently on the 48-institution construction-PIT record and fused only for presentation. The conformal alarm remains diagnostic; its historical tier wiring is suspended and it has no score or tier authority pending prospective revalidation.

Stale, future-dated, or unclocked market readings remain visible but have no signal or tier authority. Fresh readings here still lack the approvals required for per-name publication and tier use. The conclusion is bounded: Abhyudaya’s NNPA breach was the earliest recorded screen signal in this replay. It identifies an asset-quality question worth investigating, not inevitability, complete causation, a present judgment on another institution, or investment advice.

This is not a credit rating. Research and market data, not investment advice.
