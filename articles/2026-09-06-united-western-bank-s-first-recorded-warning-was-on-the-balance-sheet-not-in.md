*This is a historical replay, not current news and not a forecast. It examines United Western Bank through a construction-PIT public-disclosure record; similar mechanisms do not imply the same outcome elsewhere.*

United Western Bank’s earliest recorded pressure in this file was a disclosed balance-sheet signal. The bank entered an RBI action-zone threshold in the period ended 2001-03-31, on an NNPA breach. The replay assigns that observation a knowledge-time proxy of 2001-05-30. Default followed on 2006-09-02, producing a 63-month lead in the record.

The claim needs to remain narrow. The PCA screen fired before the event; the funding lens, though scoreable for the bank, records no first signal. That is an ordering of available disclosures, not proof that funding was sound, that the NNPA breach caused default, or that every comparable breach will lead to distress. It distinguishes a filing-period signal from a model derivation and from a market-price signal that this case does not supply.

## The record before the event

The core chronology is short. The period ended 2001-03-31 is the first action-zone observation, classified as `threshold_2`; NNPA is the listed breach. The knowledge-time proxy is 2001-05-30. The recorded default date is 2006-09-02. The [United Western Bank replay](https://liquilens.in/replay/united-western-bank/) and the [historical validation record](https://api.liquilens.in/api/failure-radar/validation) are the relevant source records.

This is a public-disclosure replay of RBI PCA/SAF tripwires. Where an explicit publication clock is present, the construction uses it. Otherwise, it uses period end plus 60 days. That convention is a proxy for availability, not evidence of what every decision-maker knew. The dossier explicitly says the resulting lead times are optimistic, that the record lacks a bitemporal input contract, and that it is neither validated-backtest eligible nor real-money eligible.

The broader PCA summary provides context but cannot establish this bank’s causal history. It covers 15 failed institutions, with five entering an action zone first and a median lead of 41 months. United Western Bank is one file inside that limited record, not confirmation that action-zone entry is a universal precursor.

## What the lenses saw

The PCA lens saw an NNPA threshold breach. The funding lens had no first signal. Read literally, that is the result: the disclosed asset-quality and supervisory-threshold screen appeared first in this replay.

A non-signal from funding is not a positive finding about deposits, liquidity, or liability resilience. The funding lens only sees institutions with usable liability disclosures. In the historical set, liability disclosures exist for 10 of 15 failed institutions; a funding signal fired first for four, with a median lead of 38 months. Limited visibility makes absence especially unsuitable as reassurance.

The model layer is a separate matter. Its hazard panel contains 205 rows, nine events, and 27 institutions, while 179 censored or unusable rows were excluded. Leave-one-institution-out AUC was 0.752, with a confidence interval of 0.338 to 1.0. The heuristic scored 0.799 on the same held-out rows. A temporal diagnostic returned 0.645 against a 0.65 gate and did not pass. It remains diagnostic only and cannot promote the construction-PIT result.

Nor is there a usable market-price confirmation here. The market layer is fresh and clocked, but has no admission, tier, or publication authority: admitted canonical records are 0/25. It therefore cannot confirm, soften, or rank the institutional conclusion. The [market evidence index](https://api.liquilens.in/api/evidence/markets) documents that boundary.

## Why the warning mattered

The warning mattered because it identified a concrete disclosed condition before default and before any recorded funding signal. It changed the appropriate question from whether the bank looked broadly normal to whether the deterioration would reverse, persist, or deepen.

That is not a complete pressure chain. The dossier provides no intervening liability-run chronology, market repricing sequence, or decomposition that would establish why default followed. A threshold is a filing-period screen, not a calibrated failure probability. The hazard model is a model derivation with its own weak promotion status; a Merton measure, where available elsewhere, is a market repricing signal rather than a calibrated failure frequency. These categories should not be fused into certainty.

The replay marks United Western Bank as `fraud_masked: false`. That does not guarantee perfect disclosure. The method note cautions that filings later shown falsified can appear compliant to threshold engines; the forensic screen owns that limitation. Missing evidence must not be translated into calm.

## The strongest counter-case

The strongest counter-case can defeat any stronger version of the thesis. The apparent 63-month lead may partly reflect construction rather than an actionable contemporaneous advantage. The period-end-plus-60-days convention is conservative only relative to a period-end assumption; it is not a complete historical publication archive. Without a bitemporal input contract, amended data, timing gaps, and incomplete disclosure remain live threats to inference.

Further, an action-zone breach can identify stress without identifying a terminal outcome. The PCA cohort itself does not show that every failure was first captured by that lens. Funding may also have been stressed in ways that the disclosed-liability series did not measure. Therefore the defensible conclusion is limited to the available record: the PCA observation came first, while the funding lens did not record a first signal.

This is **not a credit rating**. It is also not evidence that a similar institution should fail, or that an investor could have converted the replay’s lead into a reliable trade or exit decision.

## What today's board shares

Today’s [Failure Radar board](https://api.liquilens.in/api/failure-radar/board) is separate from this historical clock. As of 2026-09-06, it shows zero red, one orange, three yellow, and 15 green institutions; 21 are excluded as stale. Utkarsh Small Finance Bank is orange, while Belstar Microfinance Limited and ESAF Small Finance Bank are yellow.

Those tiers are published rules over published components, not predictions of failure. Institutions without vetted dossiers are absent by design; nothing is scored from memory. Current market observations cannot supply authority where display rights and canonical-record approvals are absent.

## The next falsifiable test

The thesis would fail if a prospective bitemporal dataset, using actual publication times and complete liability disclosures, found that action-zone breaches did not precede adverse outcomes more usefully than funding signals. It would also fail in an individual case if a disclosed breach reversed without a later adverse event while funding consistently supplied the earlier dependable warning.

That test must preserve the distinction between a filing-period observation, a market-price signal, and a model output. Construction-PIT diagnostics are useful prompts for investigation, not tradable timing rules.

## Follow the pressure chain

For this bank, the observable chain is deliberately sparse: period ended 2001-03-31; NNPA breach; `threshold_2`; knowledge-time proxy of 2001-05-30; no first funding signal; default on 2006-09-02. Each arrow describes ordering, not unobserved causation.

LiquiLens covers **institution and lender balance-sheet risk**. Seiche covers **system dollar-funding capacity**. Undertow covers market liquidity and executable exit capacity. The [Seiche overview](https://api.seiche.info/api/overview) reports EROSION with guarded confidence; the [Undertow board](https://api.seiche.info/undertow/board.json) includes PARTIAL and NORMAL segment readings. Neither is institution-level confirmation for this replay.

## Sources, method, and limits

Primary references are the [Failure Radar board](https://api.liquilens.in/api/failure-radar/board), [validation record](https://api.liquilens.in/api/failure-radar/validation), [market evidence index](https://api.liquilens.in/api/evidence/markets), and [United Western Bank replay](https://liquilens.in/replay/united-western-bank/). Additional desk context is available through [LiquiLens research](https://liquilens.in/research/) and [LiquiLens investigations](https://liquilens.in/investigations/).

The historical evidence is PERIOD_END_PROXY_CONSTRUCTION_PIT. It is not validated for backtesting or real-money use, lacks a bitemporal input contract, and may overstate lead times. Missing funding or market evidence is not evidence of calm. This article is **not investment advice**.
