*This is a historical replay, not current news and not a forecast. It examines Nedungadi Bank through reconstructed public-disclosure timing before its default. Similar mechanisms do not imply the same outcome at another institution.*

The answer to the desk question is narrow. In this replay, Nedungadi Bank’s capital position produced the first identified warning: an RBI action-zone breach in CRAR at the period ended **1999-03-31**. The bank defaulted on **2002-11-02**. The funding lens did not produce an earlier competing signal because the institution was not scoreable under that lens.

That is a sequence, not a complete explanation of failure. A filing-period signal says that a disclosed condition was recorded for a reporting period. A knowledge-time proxy estimates when that condition could have been known. A market-price signal, by contrast, is a contemporaneous repricing measure. A model derivation turns available inputs into a rule, score, or tier. Confusing those categories can make a historical replay sound more predictive than the evidence permits.

The relevant research boundary is explicit: **PERIOD_END_PROXY_CONSTRUCTION_PIT** evidence is not a validated backtest and is not real-money-eligible. The institution-risk boundary is equally explicit: LiquiLens covers **institution and lender balance-sheet risk**. It does not turn a historical action-zone observation into a default probability, a credit rating, or a trade instruction.

## The record before the event

Nedungadi Bank’s first recorded PCA action-zone observation was FY1999, for the period ended **1999-03-31**. The status was threshold_1 and the breach was CRAR. The reconstruction assigns **1999-05-30** as the knowledge-time proxy, using the stated period-end-plus-**60-day** convention where no explicit publication clock is available. The reported lead to default is **41 months**.

These dates serve different purposes. **1999-03-31** is a filing-period endpoint, not proof that market participants knew the result that day. **1999-05-30** is a conservative availability proxy, not a verified publication timestamp. **2002-11-02** is the default date. The distinction is material: the reported lead depends on the availability convention, and the dossier says lead times are optimistic.

The [Nedungadi Bank replay](https://liquilens.in/replay/nedungadi-bank/) and the [Failure Radar board](https://api.liquilens.in/api/failure-radar/board) support only the narrow finding that CRAR was the first action-zone breach captured in this reconstruction. They do not establish the full path of asset deterioration, management action, supervisory intervention, depositor behavior, or funding conditions between the observation and default.

The record does not mark Nedungadi as fraud-masked. Still, the framework cautions that filings later shown to be falsified can look compliant to a threshold engine. That is why a forensic screen owns disclosure deception rather than the threshold logic. No filing-based system can observe what disclosed data omit.

## What the lenses saw

The PCA lens fired first because CRAR crossed an action-zone threshold. The funding lens was not scoreable: it has no first signal and no funding lead-time result. This is missing-data disclosure, not evidence that funding was healthy, stable, or irrelevant.

That difference matters. The PCA lens is a filing-based supervisory-threshold signal. The funding lens requires a usable disclosed liability series. In the historical funding summary, **10** of **15** failed institutions had liability disclosures; a funding signal fired first for **4**, with a median lead of **38 months**. Those figures suggest that funding disclosures can add warning where they exist. They do not make absent disclosures reassuring.

The PCA summary covers **15** failed institutions, of which **5** entered an action zone first, with a median lead of **41 months**. It is a public-disclosure replay of RBI PCA/SAF tripwires, not a causal study. Timing begins at an exact publication time when present, or the period-end-plus-**60-day** proxy otherwise. The [historical validation record](https://api.liquilens.in/api/failure-radar/validation) preserves that condition.

The broader India diagnostic includes **48** institutions across two decades and reports **88.9%** of non-fraud failures flagged, with median lead of **21.5 months**. But it carries the same construction-PIT limitation: no bitemporal input contract, no validated-backtest eligibility, and no real-money eligibility. A useful historical pattern is not automatically a live, tradable signal.

## Why the warning mattered

A capital breach matters because it identifies reduced loss-absorbing room under a supervisory framework. In mechanism terms, less capital capacity can constrain management options, sharpen supervisory attention, and make confidence more consequential. Funding pressure may then follow, or may become observable only later.

Nedungadi supports that conditional mechanism only in a limited sense. The capital breach is observed. The funding lens is unavailable. The record therefore permits: capital weakness was the first captured warning. It does not permit: capital weakness caused every subsequent development, or funding stress was absent.

This is also why the absence of a funding alert cannot be read as an all-clear. “Unscoreable” is not “safe.” It means there is no eligible funding inference from the disclosed series. The distinction is the core editorial lesson of the case.

## The strongest counter-case

The counter-case is strong enough to defeat any deterministic thesis. A CRAR threshold can identify supervisory concern without measuring severity, persistence, recoverability, or the route to eventual default. A **41-month** interval weakens claims of imminence. And the availability date is partly derived from a filing-period proxy, so even the apparent lead may be optimistic.

The model evidence is also insufficient for a failure-forecast claim. The hazard panel has **205** rows, **9** events, and **27** institutions, while **179** censored or unusable rows were excluded. Its leave-one-institution-out row AUC is **0.752**, with a confidence interval of **0.338** to **1.0**. The heuristic score reached **0.799** on the same held-out rows. The temporal diagnostic AUC is **0.645**, below the **0.65** gate, and is diagnostic only.

The counter-case wins whenever the replay is presented as a dependable prediction engine. The evidence supports an observed warning order, not a reliable timetable, causal proof, or investable forecast.

## What today's board shares

The current Failure Radar is dated **2026-10-18**. Its displayed institution filings are as of **2026-03-31** and aged **7 months**. It shows **1** yellow institution and **2** green institutions, with no red or orange names; **35** institutions were excluded as stale. These are published screening outputs, not credit ratings.

The market layer is separately as of **2026-10-16** and retrieved on **2026-10-18**. Its clock is fresh, but it has no admission, publication, or tier authority: admitted canonical records are **0/25**, and display rights are not approved for every expected record. Thus no market-price signal may validate or alter a LiquiLens tier here. The [market evidence index](https://api.liquilens.in/api/evidence/markets) is evidence of a separate layer, not authority to publish derived institution-level market conclusions.

## The next falsifiable test

The thesis fails if prospectively time-stamped filings show that capital action-zone breaches add no earlier or more useful warning than eligible funding disclosures, forensic evidence, or other published components. It also fails if exact publication timestamps erase the apparent advantage created by the period-end proxy.

A credible test requires a bitemporal input contract, prospectively frozen inputs and outcomes, and missing liability series retained as missing. It must test the signal after applying the forensic boundary, rather than treating disclosure-based compliance as a complete account of risk.

## Follow the pressure chain

The products answer distinct questions. LiquiLens addresses **institution and lender balance-sheet risk** through [LiquiLens investigations](https://liquilens.in/investigations/). Seiche addresses **system dollar-funding capacity** through the [Seiche overview](https://api.seiche.info/api/overview). Undertow addresses **market liquidity and executable exit capacity** through the [Undertow board](https://api.seiche.info/undertow/board.json).

They are not interchangeable scores. Seiche’s current context is low confidence because a source or engine fault reduced its evidence set. Undertow labels UST STRAINED while other segments are NORMAL or PARTIAL. Neither is used in LiquiLens institution scoring. The [US NDFI watch](https://api.liquilens.in/api/us-radar/ndfi) is likewise a separate disclosure-based watch, not evidence about Nedungadi.

## Sources, method, and limits

This article relies only on the [Failure Radar board](https://api.liquilens.in/api/failure-radar/board), [historical validation](https://api.liquilens.in/api/failure-radar/validation), [Nedungadi replay](https://liquilens.in/replay/nedungadi-bank/), [market evidence index](https://api.liquilens.in/api/evidence/markets), [Seiche overview](https://api.seiche.info/api/overview), [Undertow board](https://api.seiche.info/undertow/board.json), and [US NDFI watch](https://api.liquilens.in/api/us-radar/ndfi).

The historical record is construction-PIT, lacks a bitemporal input contract, and may overstate lead times. Missing funding evidence is not reassurance. A filing-period observation is not a market-price signal; a model derivation is not an observed fact. Nedungadi’s capital breach is therefore a meaningful historical warning sequence, not a current forecast.

This is not a credit rating. Research and market data, not investment advice.
