# Browser research measurement

The page loads without making a research-tool call. A visitor must click **Get the evidence**. Each run initializes the selected public MCP and calls one fixed read-only tool. A 30-second total deadline and a 2 MiB response limit apply; there is no automatic refresh or retry.

The existing LiquiLens event endpoint receives a fixed surface (`mcp_start`), an allowlisted event name and a closed source label. The event prefix identifies the selected example (`bank`, `funding`, or `exit`). Actions distinguish start, response received, unavailable response, failure, copied setup, copied question, downloaded setup, copied question link, downloaded evidence, and optional helpful-button clicks. A copied setup does not prove installation. A returned result does not establish usefulness. A helpful click is self-reported interaction, not an independently verified research outcome.

No prompt, research response, account, email, wallet, bank identifier, referrer URL or persistent browser identifier is sent in the event body. The page creates no cookies, local storage identity or scheduled calls. Event counts cannot establish unique people, external agents or retention. The API may use network metadata transiently for abuse limits under its existing policy. Product requests go directly to the displayed MCP endpoint.

Operators must use `/start/?verification=1&task=bank` (or `funding` / `exit`). Verification mode disables interaction beacons, declares an operator-verification MCP client and adds the explicit synthetic header where that service’s browser CORS contract permits it. Seiche and Undertow do not currently expose a reliable operator/client classification in their completion logs; record test times and exclude the corresponding calls separately. Do not classify all other calls as verified external usage.

Coverage depends on the backend event vocabulary being deployed and on provider log retention. Missing events are not zero activity. Marketing attribution and named-pilot conversion must be established separately.

Accepted first-result events are retained as `LIQUILENS_PUBLIC_FUNNEL` records with schema `liquilens.public-funnel.v1`, server time, the fixed surface and event, and traffic class (`unknown` or operator-declared `synthetic`). Filter synthetic records before reporting audience interactions. Prometheus counters include accepted requests and reset with the process; use the dated retained log records for an audit window. Neither an origin header nor an unknown traffic class verifies an external user.


## Social link attribution

Only one exact `utm_source` value is accepted: `instagram`, `facebook`, `linkedin`, `youtube`, `reddit`, `telegram`, `x`, `shared` or `unknown`. Missing, duplicated and arbitrary values become `unknown`; no full query, referrer, platform click identifier, creative label or account name is transmitted. These URL labels are user-controlled: they do not prove that a platform sent a visitor. A copied question link uses `shared` so later readers do not inherit the original social source.

Accepted source-bearing requests also emit `LIQUILENS_PUBLIC_ACQUISITION`, schema `liquilens.public-acquisition.v1`, with the same event and timestamp plus `source`. This is a second view of the same event. Never add acquisition counts to `LIQUILENS_PUBLIC_FUNNEL` counts. The original five-field log and seven-day launch reader remain compatible, including synthetic exclusions. Old clients continue producing only the original record.

Telegram buttons use `social_SOURCE_TASK` start tokens. A browser click is not a bot start or subscription. LiquiLens and Seiche subscribe after Start; Undertow opens the desk and requires /watch for its watcher stream. Each CTA describes that behavior. These labels do not establish a cross-device person identifier or D1/D7 retention.

Roll out the API's optional source field before this page. During a failed analytics request, research calls, setup, copying and Telegram navigation still work. New interactions are not replayed or silently converted into audience records.
