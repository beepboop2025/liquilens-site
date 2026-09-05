# Review a bank watchlist

Use this recipe when one research task needs the disclosed asset-quality evidence for several selected banks. It accepts 1–20 distinct exact slugs, opens one MCP session, checks coverage once, and requests each covered review sequentially. No API key, LLM or Python package is required.

Download [bank_watchlist.py](https://liquilens.in/developers/recipes/bank_watchlist.py) and [financial_research.py](https://liquilens.in/developers/recipes/financial_research.py) into the same directory, inspect both files, and use Python 3.11 or later. The watchlist imports the existing recipe's bounded transport.

For an operator's setup check, first discover the exact covered slugs, then try one covered bank:

```sh
python3 financial_research.py bank-review --verification
python3 bank_watchlist.py cosmos-ucb --verification > watchlist-check.json
```

These commands contact the live service and explicitly mark the calls as synthetic verification. They are not an offline dry run. Use only exact slugs present in the coverage response. You can append up to 19 other distinct covered slugs to the second command. For a real research task, omit `--verification`; keep that flag for rehearsals, operator probes and automated tests.

Each invocation serves the caller's selected research task. The script has no scheduler, polling loop, automatic retry or cache, and does not save research state; shell redirection saves the JSON. Python may create its normal import bytecode cache. If you schedule it yourself, run it only when the output serves a real research need, and stop or reduce the schedule when the output is no longer used. Repeated calls and successful requests alone do not establish adoption or investment usefulness.

## Read the result

- `evidence.coverage` retains the original coverage response. An exact slug absent from its rows gets `not_covered` and no review request.
- `results` follows the requested order. Each returned review is retained unchanged in `evidence.review`, including sources, missing disclosures, zero values, reporting dates, availability dates, eligibility flags and interpretation limits.
- `retrieved_at` records when this client received evidence or finished the run. It does not establish source freshness. Read the review's original evidence dates and states. Historical, unavailable and missing data retain their meaning.
- `complete` means every selected bank was considered. It can be true when some banks are unavailable or not covered. `execution_authority` remains false; a returned review does not grant trading authority or validate a forecast.

Exit code `0` means every selected bank returned evidence, which can still include stale or missing facts. Exit code `2` means the run completed but at least one bank was unavailable or not covered. Exit code `1` means an input, transport, protocol or tool error occurred.

After a request fails, the script stops immediately. Its JSON report keeps earlier completed reviews, marks the failed review as `error` when applicable, and marks remaining banks `not_attempted`. The report has `complete: false`, `outcome: "error"` and an `error.stage`. Invalid input fails before network access and writes an error to stderr. A response for a different bank is rejected. Do not treat a partial report as a successful run.

The inherited client allows only the documented endpoint, refuses redirects, and limits each HTTP exchange to 20 seconds and 2 MiB. Requests run sequentially; the entire watchlist can take longer than one exchange. An HTTP error, including `429`, stops the run without retrying. Respect any applicable service limit before deciding whether a later research task should run.

## Optional repeat-client measurement

By default the script sends no client identifier. If you explicitly opt in, supply your own hyphenated UUID4 through `--client-id YOUR-UUID4`, retaining that same identifier across your own runs. Do not use an email, account number, customer identifier or secret. The script validates the UUID before network access; it does not generate or store one, and does not echo it into the report.

This option adds `X-Liquilens-Client-Id` only to the fixed LiquiLens endpoint. The backend can derive a keyed, pseudonymous repeat-client identity when server-side identity measurement is configured; the option alone does not prove that measurement is enabled. An identifier is neither authentication nor a verified person or customer. It does not authorize any additional access.

`--verification` works with or without `--client-id` and always retains the existing operator User-Agent and synthetic traffic header, so opting in does not turn test traffic into adoption.
