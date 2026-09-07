# Browser research measurement

The page loads without making a research-tool call. A visitor must click **Get the evidence**. Each run initializes the selected public MCP and calls one fixed read-only tool. A 30-second total deadline and a 2 MiB response limit apply; there is no automatic refresh or retry.

The existing LiquiLens event endpoint receives only a fixed surface (`mcp_start`) and an allowlisted event name. The event prefix identifies the selected example (`bank`, `funding`, or `exit`). Actions distinguish start, response received, unavailable response, failure, copied setup, copied question, downloaded setup, copied question link, downloaded evidence, and optional helpful-button clicks. A copied setup does not prove installation. A returned result does not establish usefulness. A helpful click is self-reported interaction, not an independently verified research outcome.

No prompt, research response, account, email, wallet, bank identifier, referrer URL or persistent browser identifier is sent in the event body. The page creates no cookies, local storage identity or scheduled calls. Event counts cannot establish unique people, external agents or retention. The API may use network metadata transiently for abuse limits under its existing policy. Product requests go directly to the displayed MCP endpoint.

Operators must use `/start/?verification=1&task=bank` (or `funding` / `exit`). Verification mode disables interaction beacons, declares an operator-verification MCP client and adds the explicit synthetic header where that service’s browser CORS contract permits it. Seiche and Undertow do not currently expose a reliable operator/client classification in their completion logs; record test times and exclude the corresponding calls separately. Do not classify all other calls as verified external usage.

Coverage depends on the backend event vocabulary being deployed and on provider log retention. Missing events are not zero activity. Marketing attribution and named-pilot conversion must be established separately.

Accepted first-result events are retained as `LIQUILENS_PUBLIC_FUNNEL` records with schema `liquilens.public-funnel.v1`, server time, the fixed surface and event, and traffic class (`unknown` or operator-declared `synthetic`). Filter synthetic records before reporting audience interactions. Prometheus counters include accepted requests and reset with the process; use the dated retained log records for an audit window. Neither an origin header nor an unknown traffic class verifies an external user.
