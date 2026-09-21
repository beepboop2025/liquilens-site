*This is not current news and is not a forecast. It is a historical replay of Global Trust Bank, whose default date is 2004-07-24. Similar balance-sheet mechanisms do not imply the same outcome elsewhere.*

Global Trust Bank presents a deliberately uncomfortable answer to the question of which balance sheet should feel stress first. Its recorded supervisory-threshold signal appeared in reported capital adequacy and non-performing assets, not in a scoreable funding series and not in a market-price signal. For the period ended 2002-03-31, the replay records CRAR and NNPA breaches, a `threshold_2` action-zone status, and a knowledge-time proxy of 2002-05-30. That is a 25-month lead to default.

The finding matters, but only within its narrow evidential boundary. It is a filing-period signal reconstructed with a publication proxy where an explicit publication clock is unavailable. It is not proof that a tradable market anticipated the event, and it is not a model-derived probability of default. Most importantly, the institution is fraud-masked. The case says both that disclosed deterioration can warrant scrutiny and that reported disclosure can be the wrong object to trust.

## The record before the event

The first recorded action-zone entry was FY2002, for the period ended 2002-03-31. The stated breaches were CRAR and NNPA. The system assigns the knowledge-time proxy of 2002-05-30, then measures the interval to the 2004-07-24 default date as 25 months.

That chronology is not a clean point-in-time record. Historical evidence is labelled `PERIOD_END_PROXY_CONSTRUCTION_PIT`. The availability rule uses an explicit publication clock when present; otherwise it assumes period end plus 60 days. There is no bitemporal input contract. The replay is not validated-backtest eligible and is not real-money eligible. Its lead times are explicitly described as optimistic.

A period end is not the same thing as public knowledge. A proxy can make disclosures appear more uniformly available than they were, and can overstate the practical time available to investigate, fund, sell, or hedge. The replay therefore supports an investigative observation: reported capital and reported asset quality entered a defined danger zone before the event. It does not establish an executable historical trade or a contemporaneous credit decision.

The broader PCA summary covers 15 failed institutions, of which 5 entered an action zone first, with a median lead of 41 months. That is useful context for a threshold lens, not a universal failure clock. The underlying limitations are available in the [historical validation record](https://api.liquilens.in/api/failure-radar/validation) and the institution-specific [Global Trust Bank replay](https://liquilens.in/replay/global-trust-bank/).

## What the lenses saw

The PCA lens saw the first recorded warning: CRAR and NNPA crossed the stated action-zone framework. This is a filing-period signal. It concerns reported loss-absorption capacity and reported impaired assets. The economic logic is straightforward but conditional: worsening impaired assets can require provisions or generate losses; losses can reduce capital; a smaller capital buffer leaves less room for further deterioration.

That logic is balance-sheet arithmetic, not an assertion that every threshold breach ends in default. The dossier does not provide a complete sequence of losses, liabilities, counterparties, withdrawals, or interventions. It cannot establish a complete causal route from the reported period to the later default.

The funding lens did not deliver a competing signal. It is `scoreable: false` for Global Trust Bank, with no first signal and no lead time. This is missing-data information, not a positive finding on funding resilience. The funding lens can only observe institutions that disclose a liability series. No usable signal cannot be translated into stable funding.

Nor does this replay contain a market-price warning. A market-derived reading is conceptually different from a filing signal: it reflects price movement rather than reported balance-sheet information. The historical case offers no scoreable funding lead and no stated market lead. It should not be rewritten as evidence that markets confirmed the threshold breach.

Finally, fraud masking changes the hierarchy of evidence. The validation note states that institutions whose filings were later shown falsified can look compliant to any threshold engine; the forensic screen owns those cases. Reported ratios can identify disclosed vulnerability. They cannot independently authenticate the reports from which those ratios are made.

## Why the warning mattered

The warning mattered because it changed the right investigative question. Once reported capital and reported non-performing assets cross a supervisory threshold, the task is no longer simply to ask whether the institution looks healthy. It is to examine how much further asset deterioration the reported capital base can absorb, whether the disclosed asset-quality measure is credible, and what information is missing from the liability side.

This is not a claim that the threshold caused the outcome. It is a claim about triage. A defined breach creates a reason to intensify diligence on capital, assets, funding disclosures, and reporting integrity.

The distinction between a signal and a verdict is essential here. The recorded breach is a filing-period observation. The 25-month lead is a construction-PIT derivation from the selected availability rule and the default date. Neither is equivalent to a verified, real-time warning available on an exact market clock. The value of the replay lies in preserving that distinction rather than erasing it.

## The strongest counter-case

The strongest counter-case can defeat any claim that the threshold engine “called” Global Trust Bank. The institution is fraud-masked. A system based on reported CRAR and NNPA can be misled if reports are unreliable. Its historical availability also relies on period end plus 60 days where publication timing is absent, and the dossier says lead times are optimistic.

The aggregate diagnostics add restraint rather than rescue. The hazard panel contains 205 rows, 9 events, and 27 institutions, with 179 censored or unusable rows excluded. Its leave-one-institution-out row AUC is 0.752, with a confidence interval of 0.338 to 1.0. The heuristic score reaches 0.799 on the same held-out rows. The temporal diagnostic AUC is 0.645, below the 0.65 gate, and is diagnostic only.

Those figures do not promote construction-PIT work into a validated forecast. The proper conclusion is narrower: the replay records a prior disclosed threshold breach, while simultaneously documenting why reported thresholds alone cannot settle a fraud-masked case.

## What today's board shares

Today’s board is not a continuation of this historical case. As of 2026-09-21, it lists 0 red, 1 orange, 3 yellow, and 15 green institutions. Utkarsh Small Finance Bank is orange, as of 2025-03-31, with an age of 18 months and a score of 74.9. Belstar Microfinance Limited is yellow, as of 2026-03-31, age 6 months, score 77.8. ESAF Small Finance Bank is yellow, as of 2025-09-30, age 12 months, score 66.0.

These are board tiers, not default predictions, credit ratings, or evidence that any named institution resembles Global Trust Bank. The board excludes 21 stale institutions. It presents one row per institution with a fresh vetted public dossier; institutions without vetted dossiers are absent by design, not scored from memory.

The current market layer is fresh and knowledge-authorized, but it has no admission, publication, or tier authority: admitted canonical records are 0/25. Market-derived display is not approved for every expected canonical record. Thus current market data cannot authorize board tiers. Read the [Failure Radar board](https://api.liquilens.in/api/failure-radar/board) alongside the [market evidence index](https://api.liquilens.in/api/evidence/markets), not as interchangeable evidence.

## The next falsifiable test

The thesis weakens if prospectively collected, properly time-stamped disclosures show that action-zone capital and asset-quality breaches do not identify subsequent fragility after disclosure integrity is independently examined. It weakens further if exact publication times replace the 60-day proxy and the apparent lead time disappears.

The test is practical: preserve each filing’s exact availability time, validate reported inputs, retain missing liability disclosures as missing rather than benign, and evaluate threshold and forensic lenses prospectively. If that process does not improve on disclosed-ratio heuristics, the claimed early-warning value should be reduced rather than defended by retrospective reconstruction.

## Follow the pressure chain

Begin with asset quality: NNPA points to reported impairment. Move to capital: CRAR points to the reported buffer against losses. Then ask whether liabilities are disclosed well enough for funding analysis; Global Trust Bank shows why no scoreable funding signal is not evidence of strength. Finally, test disclosure integrity, because fraud masking can make apparent ratio comfort unreliable.

LiquiLens addresses **institution and lender balance-sheet risk**. It should be paired, not confused, with Seiche’s **system dollar-funding capacity** view and Undertow’s **market liquidity and executable exit capacity** view. These are different questions: a lender’s reported resilience, the capacity of dollar-funding plumbing, and the ability to exit a position need not move together. See [Seiche’s overview](https://api.seiche.info/api/overview) and [Undertow’s board](https://api.seiche.info/undertow/board.json).

## Sources, method, and limits

The relevant primary materials are the [Failure Radar board](https://api.liquilens.in/api/failure-radar/board), [historical validation](https://api.liquilens.in/api/failure-radar/validation), [market evidence](https://api.liquilens.in/api/evidence/markets), and the [Global Trust Bank replay](https://liquilens.in/replay/global-trust-bank/). Broader context is collected in [LiquiLens research](https://liquilens.in/research/) and [LiquiLens investigations](https://liquilens.in/investigations/).

The historical record remains construction-PIT, not fully point-in-time. Its 60-day filing proxy applies where explicit publication clocks are absent; lead times are optimistic; it is neither validated-backtest eligible nor real-money eligible. Missing liability disclosures constrain the funding lens. Fraud masking constrains every interpretation based on reported thresholds. The current board is a diagnostic screen, not investment advice, a credit rating, or a forecast of failure.

This is not a credit rating.
