*This is a historical replay, not current news and not a forecast. Similar mechanisms do not imply the same outcome.*

Nedungadi Bank is the clearest answer in this record to the question of which balance sheet should have felt stress first: its reported capital position entered an RBI action zone before its eventual default. But that conclusion needs boundaries. The breach is a filing-period signal, reconstructed using a publication-time proxy. It is not a contemporaneous market-price signal, and it is not a model-derived probability of default. The replay records an early warning; it does not prove a complete causal sequence.

## The record before the event

Nedungadi Bank defaulted on 2002-11-02. Its first documented PCA action-zone event was a CRAR breach for the period ending 1999-03-31, identified as FY1999. The PCA record labels the event `threshold_1` and assigns a knowledge-time proxy of 1999-05-30. The measured lead to default is 41 months.

That chronology is the core fact. The period end says when the reported condition existed in the replayed record. The knowledge-time proxy says when an outside observer may have been able to know it under the construction rule. Where no explicit publication clock exists, the system uses period end plus 60 days. It is therefore inappropriate to treat 1999-03-31 as a verified real-time observation date.

The funding lens supplies no offsetting result. Nedungadi is marked unscoreable for funding, with no first signal and no measured funding lead. That does not show that funding was stable. It shows that the available liability disclosure was insufficient for this lens. Missing information is an evidence boundary, not reassurance.

## What the lenses saw

The PCA lens saw a CRAR threshold breach. The funding lens did not produce a scoreable reading. The market layer available for the current board is a separate dataset, dated 2026-10-06, and cannot be retrofitted into the Nedungadi chronology. Conflating these layers would turn distinct forms of evidence into a false confirmation.

A filing-period capital breach is a reported regulatory-threshold condition. A market-price signal would instead be a repricing observation. The dossier describes the Merton PD specifically as a market repricing signal, not a calibrated failure frequency. A model output is another category again: it is a derivation from specified inputs and rules, not direct evidence that a bank has failed or will fail.

The historical PCA summary covers 15 failed institutions, of which 5 entered an action zone first; its median lead is 41 months. The funding summary has liability disclosures for 10 of those 15 institutions and records funding as the first signal for 4, with a median lead of 38 months. Those comparisons do not establish that capital is always the earliest lens. They show that different disclosed pathways appeared first in different cases.

The India diagnostic spans 48 institutions across two decades and reports that 88.9% of non-fraud failures were flagged, with a median lead of 21.5 months. Yet it is explicitly a filing-availability-proxied construction-PIT diagnostic. It is not validated-backtest eligible, not real-money eligible, and does not have a bitemporal input contract.

## Why the warning mattered

The economic significance of the breach is limited but intelligible: the dossier identifies capital as the first documented action-zone pressure point at Nedungadi. A capital threshold is closer to loss-absorption capacity than a broad narrative about confidence or market access. It can therefore be useful in triage as a question for investigation: what changed in the reported buffer, and did other disclosed constraints follow?

The quadrant rule treats an RBI action-zone breach as sufficient for the highest screen category. That is a screening rule, not a finding of causation. Other routes to concern include reported loss levels, deterioration, funding flags, forensic indicators and fresh authoritative market drawdown signals. The rule identifies a reason to look harder; it does not provide timing certainty or a complete failure explanation.

The model evidence should make readers more restrained, not more confident. The leave-one-institution-out hazard AUC is 0.752, while the disclosure heuristic reaches 0.799 on the same held-out rows. The temporal diagnostic AUC is 0.645, below the 0.65 gate, and is diagnostic only. Construction-PIT diagnostics cannot promote.

## The strongest counter-case

The counter-case can defeat the thesis. A capital action-zone breach may be an early regulatory marker without becoming the decisive driver of failure. The 41-month lead is particularly important: it is evidence against reading the breach as a countdown. A bank might repair reported capital, alter its balance sheet, or receive support. The dossier supplies no institution-specific evidence that the CRAR breach itself caused Nedungadi’s default.

The sample also weakens any claim of universality. Only 5 of 15 failed institutions entered the PCA action zone first. Funding was first among 4 institutions with the relevant liability disclosures. And Nedungadi’s funding lens is unavailable, so this case cannot establish whether capital preceded a liability-side deterioration or merely became observable first.

Timing is another serious objection. The replay relies on an explicit publication clock where present and otherwise a conservative period-end plus 60-day proxy. Even so, the dossier says lead times may be optimistic. Filings later shown to be falsified can make institutions appear compliant to a threshold engine; the forensic screen owns that problem. Nedungadi is marked fraud-masked false, but that label does not remove the general limitation.

## What today's board shares

Today’s board is not an extension of the Nedungadi result. As of 2026-10-07, the Failure Radar shows 0 red names, 0 orange names, 1 yellow name and 2 green names. Belstar Microfinance Limited is yellow, while Annapurna Finance Private Limited and Arohan Financial Services Limited are green. Their listed filings are as of 2026-03-31 and are 7 months old.

The board excludes 35 stale institutions. Its presentation rule does not treat quarterly filings older than 183 days, or annual filings older than 400 days, as current. Institutions without vetted dossiers are absent by design. This makes the roster a screened subset rather than a claim about every lender.

Current market data are fresh, but their display, publication and tier use are not approved for every expected canonical record. The admitted canonical-record count is 0/25. Market-derived readings therefore cannot validate a current tier in this article.

## The next falsifiable test

The thesis should be tested prospectively, not defended through a single replay. Preserve the original filing vintage and exact public availability time for each new disclosure. Track capital, funding and forensic signals separately. Report stale and missing institutions as exclusions rather than as negative observations. Then test whether action-zone breaches identify independently observed balance-sheet stress earlier than comparable non-breaching institutions.

The thesis fails if capital thresholds do not add timely information once publication timing, missing liability disclosures, revised filings and forensic masking are handled honestly. It also fails if later information is required to make the earlier warning look useful.

## Follow the pressure chain

For Nedungadi, the documented chain is short: a reported CRAR breach, followed 41 months later by default. Any middle link between those facts is an interpretation, not a recorded institution-specific event in this dossier.

LiquiLens covers **institution and lender balance-sheet risk**. [Seiche](https://api.seiche.info/api/overview) covers **system dollar-funding capacity**. [Undertow](https://api.seiche.info/undertow/board.json) covers market liquidity and executable exit capacity. These are complementary boundaries, not interchangeable signals.

## Sources, method, and limits

The relevant records are the [Failure Radar board](https://api.liquilens.in/api/failure-radar/board), [historical validation output](https://api.liquilens.in/api/failure-radar/validation), [market evidence index](https://api.liquilens.in/api/evidence/markets), and the [Nedungadi Bank replay](https://liquilens.in/replay/nedungadi-bank/). Readers can also review the [research archive](https://liquilens.in/research/), [investigations](https://liquilens.in/investigations/), [replay archive](https://liquilens.in/replay/), and [NDFI watch](https://api.liquilens.in/api/us-radar/ndfi).

This is construction-PIT evidence with a 60-day filing-lag proxy when an explicit publication time is absent. Lead times may be optimistic. It is not a validated backtest or real-money result. The narrow conclusion is that Nedungadi’s CRAR breach was an early documented filing-period warning worth studying, not proof that a current institution will repeat its path.

This is not a credit rating. Research and market data, not investment advice.
