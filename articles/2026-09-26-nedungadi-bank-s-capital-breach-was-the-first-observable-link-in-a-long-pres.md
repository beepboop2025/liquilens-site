*This is a historical replay, not current news and not a forecast. Similar mechanisms do not imply the same outcome. The relevant filing period ended on 1999-03-31; the replay uses 1999-05-30 as its knowledge-time proxy. The separate market-data pack is as of 2026-09-25.*

Nedungadi Bank should have appeared under pressure first through disclosed capital, not through a scored funding signal. The narrow thesis is that its CRAR entry into the first RBI action zone in FY1999 was the earliest observable warning in this replay. It preceded the bank’s 2002-11-02 default by 41 months. That does not prove capital caused the default, establish what market participants knew, or show that an investor could have traded a known outcome.

The distinction is central. The CRAR breach is a filing-period signal, subject to an availability proxy. A market-price signal would require authorised market evidence, and none establishes Nedungadi’s historical pathway. A model derivation is a rule or diagnostic built over observed records; it is not itself an observed event. Conflating these categories would turn a limited replay into a claim it cannot support.

This historical replay is **not investment advice** and **not a credit rating**.

## The record before the event

The [Nedungadi Bank replay](https://liquilens.in/replay/nedungadi-bank/) records its first PCA/SAF action-zone entry at the 1999-03-31 period end, labelled FY1999. The breach was CRAR and its status was `threshold_1`. The knowledge-time proxy is 1999-05-30, using the stated 60-day filing lag. The replay’s 41-month lead runs from that proxy date to the recorded default.

That chronology is less certain than its precision may suggest. Historical evidence is classified as `PERIOD_END_PROXY_CONSTRUCTION_PIT`. It has no bitemporal input contract, is not eligible as a validated backtest, and is not eligible for real-money use. When an explicit publication clock is unavailable, the convention is period end plus 60 days. The dossier explicitly warns that lead times may be optimistic.

Thus, 1999-03-31 is an accounting reference date, while 1999-05-30 is an imposed availability convention. Neither proves every participant received the information simultaneously. The [Failure Radar board](https://api.liquilens.in/api/failure-radar/board) preserves that separation rather than silently treating period-end information as immediately known.

Nedungadi is marked as not fraud-masked. That means this replay does not assign it to the group in which filings later shown to be falsified can make an institution appear compliant to a threshold engine. It does not establish that disclosed information was complete.

## What the lenses saw

The PCA lens saw the CRAR breach. The funding lens was not scoreable and produced no first signal. This is a missing-data outcome, not a conclusion that funding was calm, stable, or irrelevant. The funding framework can observe only institutions disclosing a liability series; Nedungadi’s record does not support that lens.

The broader summaries remain bounded. Of 15 failed institutions in the PCA summary, 5 entered an action zone first, with a median lead of 41 months. In the funding summary, 10 of 15 failed institutions had liability disclosures, 4 had the funding signal fire first, and the median lead was 38 months. These are constrained replay descriptions, not competing failure probabilities or proof that one lens is always earlier.

The hazard work cannot repair this gap. Its leave-one-institution-out row AUC is 0.752, and its temporal AUC is 0.645, below the 0.65 diagnostic gate. The temporal result is diagnostic only; construction-PIT diagnostics cannot promote. The [validation record](https://api.liquilens.in/api/failure-radar/validation) documents limitation rather than a performance warrant.

## Why the warning mattered

The warning mattered because it was a disclosed regulatory tripwire before default, attached to a named measure, period, and availability convention. The replay can say Nedungadi’s CRAR entered an RBI action zone before the outcome. It can also say the funding lens supplied no competing dated signal because that lens was unscoreable.

It cannot complete a causal transmission story. The dossier provides no historical market repricing measure for Nedungadi, no scored funding event, and no evidence identifying the intervening route from CRAR weakness to default. “Capital was first” therefore means first observable within these disclosed and scoreable inputs, not first in the bank’s economic reality.

The rule-based `threshold_1` classification is also not a market price. The 41-month lead is a model derivation from a proxy knowledge date and a recorded default date. Neither converts an action-zone breach into a calibrated failure frequency.

## The strongest counter-case

A stronger version of this thesis can fail. One action-zone breach in a construction-PIT record may identify regulatory vulnerability while revealing little about timing, severity, or the eventual failure mechanism. A 41-month lead itself argues against interpreting the result as an imminent-event alarm.

The availability convention may flatter apparent warning time. The record lacks a bitemporal input contract and substitutes period end plus 60 days where no explicit publication clock exists. Even that proxy leaves lead times labelled optimistic. Missing funding evidence is equally ambiguous: absent liability disclosure is not absent funding pressure.

If fully timestamped, contemporaneous liability information had generated an earlier warning, the claim that capital should feel stress first would fail. If a market-price measure had repriced before the filing became knowable, it would answer a different question and also defeat any claim that the filing was the first observable warning overall. The defensible conclusion is narrower: capital was the earliest recorded signal in this replay.

## What today's board shares

Today’s board is not a live continuation of Nedungadi. As of 2026-09-26, it contains 0 red, 1 orange, 3 yellow, and 15 green institutions, while excluding 21 stale institutions. Utkarsh Small Finance Bank is orange on a 2025-03-31 dossier. Belstar Microfinance Limited and ESAF Small Finance Bank are yellow.

These are published-rule screens over vetted public dossiers, not ratings. Yet the current market layer has 0 of 25 admitted canonical records and has no tier or publication authority. It is fresh and clocked, but display and tier use are not approved. The [market evidence endpoint](https://api.liquilens.in/api/evidence/markets) records that boundary.

## The next falsifiable test

The thesis weakens if a prospective, fully timestamped filing record shows that action-zone entry does not precede meaningful balance-sheet stress more reliably than available alternatives when disclosure timing is held constant. It also weakens if institutions with disclosed liability series repeatedly generate earlier usable funding warnings and CRAR adds no incremental diagnostic value.

That test must use actual publication timestamps rather than period-end proxies, preserve missing disclosures as missing, and separate forensic cases in which filings can mask weakness. Until then, this remains a historically grounded mechanism claim, not a calibrated forecast.

## Follow the pressure chain

The pressure chain supported here stops at disclosed CRAR weakness, RBI action-zone entry, and eventual default. The funding link is unobserved, not absent. No market-price link is established.

The product boundaries matter: Seiche covers **system dollar-funding capacity**; LiquiLens covers **institution and lender balance-sheet risk**; Undertow covers market liquidity and executable exit capacity. Seiche’s composite is 41.2 and labelled EROSION, with guarded confidence because slow-moving or modelled structure has not been broadly confirmed by current market plumbing. Undertow reports partial coverage across segments. Neither is evidence about Nedungadi’s historical route. See the [Seiche overview](https://api.seiche.info/api/overview) and [Undertow board](https://api.seiche.info/undertow/board.json).

## Sources, method, and limits

Primary material is the [Nedungadi replay](https://liquilens.in/replay/nedungadi-bank/), the [Failure Radar board](https://api.liquilens.in/api/failure-radar/board), and the [historical validation endpoint](https://api.liquilens.in/api/failure-radar/validation). Further method material is in the [LiquiLens research archive](https://liquilens.in/research/).

The decisive limits are construction-PIT historical status, no real-money eligibility, no bitemporal input contract, proxy timing that can leave lead times optimistic, no authorised market-derived tier evidence, and unscoreable funding evidence for Nedungadi. Missing evidence is not calm. It is a boundary on what this replay can claim.
