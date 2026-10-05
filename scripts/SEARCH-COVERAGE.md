# Search coverage operations

The `Search coverage monitor` workflow checks LiquiLens, Seiche and Undertow
from outside their hosting infrastructure. It has read-only permissions and
does not edit Cloudflare, publish content, submit sitemaps, run model inference,
or send social/Telegram/email messages.

## Cadence and scope

- Hourly, at minute 23: discovery files, every advertised sitemap, coverage
  minimums, search-crawler robots permissions, and required entry pages.
- Daily, at 03:43 UTC: also fetch every URL found through those sitemaps,
  including Undertow's separate article sitemap and nested sitemap indexes.
- After a successful LiquiLens Pages publication: repeat the lightweight check.
- Manual dispatch: full audit by default.

Failures include HTTP errors, unexpected redirects/challenge HTML, invalid
XML/JSON, missing sitemaps or required pages, reductions below reviewed page
minimums, missing metadata, accidental `noindex`, incorrect canonicals, and
robots exclusions for Googlebot, Bingbot, OAI-SearchBot, Claude-SearchBot or
PerplexityBot. A failed check fails the workflow and retains the JSON/Markdown
report for 30 days. GitHub notification delivery depends on account settings;
no separate notification service is installed by this workflow.

HTML pages require a title, description and one correct canonical. Published
JSON and Markdown documents receive content-type and parse/content checks;
they are not incorrectly required to have HTML metadata. Robots checks merge
specific groups and apply longest-path rules, wildcard/end markers, encoded
paths and allow-on-tie behavior. Unsupported policy extensions are preserved.

Plain Python clients are also probed on the four discovery paths. Blocks are
compatibility warnings rather than proof that a verified search crawler is
blocked. The main monitor identifies itself honestly; it does not impersonate
Googlebot. Training-crawler policy is not changed by this monitor.

The minimum sitemap counts (124, 166, 58) and required entry routes are reviewed
baselines, not frozen totals or evidence that the corpus is complete. Every live
workflow compares the complete sitemap inventory against the previous successful
live run on `main`. A disappearing URL fails even if a new URL replaces it and
totals remain above the minimum. New URLs in a successful run become part of the
next comparison. Failed reports never redefine the successful baseline.

`search_coverage_history.py` uses read-only GitHub Actions access to retrieve the
exact artifact from a successful schedule, manual, or post-publication run of
this workflow in this repository. PRs, other branches, forks, and the current run
are excluded. The archive is bounded and only its root `report.json` is read;
it is never extracted. The report is validated for all three origins, required
pages, successful checks, and distinct bounded URL inventories. Its run, attempt,
commit, artifact ID and downloaded hashes are retained in `baseline.source.json`.

An absent, expired, malformed, or inaccessible baseline fails history validation
while preserving the current site's audit report. There is no silent empty
baseline or older-artifact fallback. The downloader step may continue after an
error so current retrieval can still be measured; the final audit then fails.
After a retention gap, restore a reviewed baseline through an explicit code and
evidence review. A manual run alone does not reset history.

For a deliberate retirement, add the exact product, URL and a meaningful reason
(including the redirect/indexing plan) to `scripts/search-coverage-retirements.json`
through normal review. Wildcard retirements are not supported; required entry
pages cannot be retired. This permission does not waive minimum counts, current
page validation or robots checks. Reviewed removals remain visible in reports.

The probe is bounded to three exact HTTPS
origins, at most 20 sitemaps and 2,500 URLs per product, 3 MiB per response, and
a 15-second socket timeout. One product runs at a time per worker, with three
workers total. Increasing these bounds requires review.

GitHub scheduled jobs can be delayed or disabled. Confirm a completed hourly
run within the last two hours and a completed full audit within the last 26
hours when reviewing operations. A missing/unfinished run means unknown
coverage, not success. This workflow does not independently alert if GitHub's
scheduler stops, and a scheduled configuration alone is not recurrence proof.

## Separate weekly visibility review

1. In each domain's Google Search Console, verify sitemap processing, actual
   indexed canonical pages, and excluded-page reasons. A successful HTTP fetch
   or this monitor's pass is not Google indexing proof. Retain Seiche's working
   `sitemap.xml?discovery=20261005` submission; do not repeatedly resubmit it.
2. Review a fixed complete window of branded and problem-specific impressions,
   clicks, and Google's Generative AI report. Keep country/device filters fixed.
3. Sample a fixed prompt/query set in Google and available AI search products,
   recording date, geography/account context, model/search mode, cited URL, and
   whether the citation describes the right product. This is a sample, not
   coverage of all users or all models.
4. Measure external completed tasks and repeat use separately. Exclude this
   monitor, other operator probes, crawlers, and unclassified API requests.

Suggested subjects: LiquiLens for bank/lender filing evidence; Seiche for dollar
funding, repo and money markets; Undertow for market depth and exit-cost evidence.
Show source dates and product limitations. Maintain useful worked examples and
working MCP/client setup; use genuine distribution and earned references.

Google autocomplete depends on actual searches, language, location, trends,
personal history, and patterns across the web. It has no permanent placement
setting. Do not turn automated searches or purchased mentions into a growth
strategy. Google says special AI files such as `llms.txt` do not improve its
rankings; those files remain useful integration references where supported.

Sources:
- https://support.google.com/websearch/answer/7368877
- https://developers.google.com/search/docs/fundamentals/ai-optimization-guide
- https://developers.openai.com/api/docs/bots

## Local verification

```sh
python3 -m unittest discover -s tests -p 'test_search_coverage*.py' -v
python3 scripts/search_coverage_history.py --output /path/to/evidence/baseline.json
python3 scripts/check_search_coverage.py --full \
  --baseline /path/to/evidence/baseline.json \
  --retirements scripts/search-coverage-retirements.json \
  --output /path/to/evidence/report.json
```

The downloader requires an authenticated `gh` CLI with Actions read access.
Local runs without `--baseline` label inventory history `NOT_REQUESTED`; they
do not claim to have checked historical losses. CI always requires the baseline.

The monitor establishes bounded technical retrieval coverage only. Source-data
coverage, rights, freshness, Google processing/indexing, autocomplete placement,
AI citations, and product adoption have independent evidence requirements.
