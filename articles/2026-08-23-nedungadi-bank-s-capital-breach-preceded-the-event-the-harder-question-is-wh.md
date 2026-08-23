*This is a historical replay, not current news and not a forecast. It examines information associated with Nedungadi Bank before its default date, rather than asserting that similar mechanisms must produce the same outcome elsewhere. Similar mechanisms do not imply the same outcome.*

Nedungadi Bank is a useful stress case precisely because the record is incomplete. The replay records a CRAR breach that put the bank into an RBI action zone at FY1999. Its default date is later. That sequence makes capital a serious investigative signal, but it does not establish that capital caused the outcome, that funding was sound, or that an observer could have known every relevant fact in real time.

The essential distinction is temporal. A filing-period signal describes a reported condition at a period end. The replay translates that into an availability estimate using an explicit publication clock when present, or a filing-lag proxy when it is not. A market-price signal is a separate repricing measure, available only where market data exist and dated on its own clock. A model derivation combines published components under stated rules; it is neither a filing nor a market quote. Conflating those objects would turn a bounded reconstruction into a claim it cannot support.

## The record before the event

The first recorded action-zone observation for Nedungadi Bank is FY1999, with period end `1999-03-31`, status `threshold_1`, and CRAR listed as the breach. The replay uses `1999-05-30` as its knowledge-time proxy. The default date is `2002-11-02`, and the reported lead is `41` months. The supplied record does not mark the institution fraud-masked.

That is a material sequence, not a completed causal narrative. It says that a supervisory tripwire was publicly reconstructable before the event under the replay’s timing convention. It does not show what management knew, what creditors did, whether a recapitalisation route existed, or whether other pressures were more decisive.

The funding lens supplies no compensating answer. Nedungadi is explicitly unscoreable for funding, with no first signal and no funding lead time. Missing liability disclosure is an information boundary, not evidence that liabilities were stable. In the failed-institution funding summary, `10` of `15` had liability disclosures and `4` had a funding signal fire first; median lead was `38` months. The capital-first observation cannot therefore be converted into a finding that the bank’s funding position was benign.

The [Nedungadi Bank replay](https://liquilens.in/replay/nedungadi-bank/) and the [Failure Radar board](https://api.liquilens.in/api/failure-radar/board) are the relevant records for that distinction.

## What the lenses saw

The capital lens saw the CRAR action-zone breach. The funding lens did not score the bank. The forensic boundary remains important even though Nedungadi is not labelled fraud-masked: the validation note says filings later shown to have been falsified can appear compliant to a threshold engine, and assigns that problem to the forensic screen.

The historical evidence status is `PERIOD_END_PROXY_CONSTRUCTION_PIT`. It is not validated-backtest eligible, not real-money eligible, and has no bitemporal input contract. Its availability basis is an explicit publication clock where present and otherwise period end plus `60` days. The dossier explicitly says lead times are optimistic. Those qualifications are not footnotes. They limit the proposition to a public-disclosure reconstruction rather than a demonstration of an investor’s actual information set.

The India diagnostic covers `48` institutions across two decades and reports `88.9%` of non-fraud failures flagged, with median lead of `21.5` months. It carries the same construction-PIT limitations. The [validation record](https://api.liquilens.in/api/failure-radar/validation) and [market evidence index](https://api.liquilens.in/api/evidence/markets) make the status visible rather than allowing the headline to stand alone.

Market distance-to-default, where available, belongs in a different evidentiary bucket. The dossier defines it as a market repricing signal, not a calibrated failure frequency. It should not be read backward into Nedungadi’s filing-based capital result, and a filing breach should not be presented as if it were a contemporaneous market verdict.

## Why the warning mattered

An action-zone breach mattered because it identified a disclosed supervisory threshold crossing before the event. That is enough to justify a fuller inquiry into the balance sheet. It is not enough to declare a failure path inevitable.

The `41`-month lead is ambiguous in both directions. It may show that the action-zone lens surfaced an issue well before default. It also leaves room for recovery, changed conditions, measurement error, interventions, and developments not captured by this replay. Long lead time is not automatically stronger proof; it increases the importance of asking whether later evidence confirmed or contradicted the early signal.

The proper interpretation is conditional: a CRAR breach can be the first observable link in a pressure chain. Whether it became decisive would require evidence on losses, funding, disclosure quality, supervisory constraints, and market repricing at their respective availability times. The dossier does not supply that complete chain for Nedungadi.

## The strongest counter-case

The counter-case can defeat any claim that Nedungadi proves a general capital-first thesis. Only `5` of `15` failed institutions entered an action zone first in the PCA summary, even though its median lead was `41` months. The funding lens was unavailable for Nedungadi. A threshold may identify a regulatory condition without explaining the eventual event.

The model evidence is also not a rescue. The hazard panel has `205` rows, `9` events, and `27` institutions; `179` censored or unusable rows were excluded. Its leave-one-institution-out row AUC is `0.752`, with a `0.338` to `1.0` interval, while the heuristic AUC is `0.799`. The temporal diagnostic AUC is `0.645`, below the `0.65` gate, and is diagnostic only. Construction-PIT diagnostics cannot promote.

Accordingly, the replay supports investigation, not certainty. It does not validate a real-money strategy, a calibrated probability of default, or a claim that the first visible ratio explains the final outcome.

## What today's board shares

Today’s board is not a present-tense extension of the Nedungadi case. As of `2026-08-23`, it lists `0` red, `1` orange, `3` yellow, and `15` green institutions, while excluding `21` stale institutions. Institutions without fresh vetted dossiers are absent by design; absence is not a calm signal.

Utkarsh Small Finance Bank is orange on a `2025-03-31` filing, aged `17` months, with score `74.9` and no listed fired signals. ESAF Small Finance Bank is yellow on `2025-09-30`, aged `11` months, with score `66.0` and market distance-to-default `1.927`. Belstar Microfinance Limited is yellow on `2026-03-31`, aged `5` months, with score `77.8`.

Those are board-rule outputs over published components, not analogues to Nedungadi. Orange can arise from a level of at least `1.00%`, deterioration from at least `0.25%`, or market distance-to-default below `1`; yellow can arise from deterioration, a funding or forensic flag, a level of at least `0.25%`, or market distance-to-default below `2`. The current market layer is dated `2026-08-11`, separately from filing dates.

## The next falsifiable test

The narrow thesis fails if, under true filing-vintage timestamps, action-zone capital breaches do not precede a measurable worsening in other available evidence more often than comparable institutions without those breaches. It also fails if capital adds no useful information after funding, forensic, and market signals are aligned to the same decision time.

That test requires the features this replay lacks: a bitemporal public-data contract, prospective scorekeeping, and sufficient liability disclosures. Until then, the defensible action is to treat a breach as a prompt to inspect the pressure chain—not as a declaration of fate.

## Follow the pressure chain

LiquiLens: institution and lender balance-sheet risk. Its question is whether an institution’s published balance-sheet evidence warrants closer scrutiny. Seiche addresses system dollar-funding capacity; its overview describes a guarded strain read, led by modelled or slow-moving structure while current market plumbing has not broadly confirmed it. [Seiche’s overview](https://api.seiche.info/api/overview) is therefore a system context, not confirmation of an institution-level thesis.

Undertow addresses market liquidity and executable exit capacity. Its board shows `NORMAL` for IG and `PARTIAL` across several other segments, with complete upstream coverage spanning `2026-06-30` to `2026-08-23`. The [Undertow board](https://api.seiche.info/undertow/board.json) is a market-exit context, not evidence that Nedungadi’s capital signal was right.

## Sources, method, and limits

This article uses only the supplied dossier and its linked product records: the [Failure Radar board](https://api.liquilens.in/api/failure-radar/board), [historical validation](https://api.liquilens.in/api/failure-radar/validation), [market evidence index](https://api.liquilens.in/api/evidence/markets), [NDFI watch](https://api.liquilens.in/api/us-radar/ndfi), and [LiquiLens research](https://liquilens.in/research/). Readers can also inspect the [replay archive](https://liquilens.in/replay/).

The controlling limits are proxy availability timing, the `60`-day fallback, optimistic lead times, incomplete liability disclosures, suspended conformal tier wiring, and the possibility that falsified filings can obscure weakness. A filing-period signal, a market-price signal, and a model derivation remain different claims. Missing evidence remains missing evidence.

This is not a credit rating. Research and market data, not investment advice.
