# Read bank evidence in n8n

[Download the workflow](https://liquilens.in/developers/recipes/n8n-bank-review.json) and import the JSON file into n8n. This manually triggered workflow makes one read-only bank review call. It needs no model, LiquiLens account or API key. Your own n8n hosting costs and LiquiLens rate limits still apply.

1. Import the JSON file through n8n's workflow menu.
2. Open **Read bank asset-quality evidence**. The example JSON uses `cosmos-ucb`, Cosmos Co-operative Bank. Change `slug` to another covered institution if needed. The `banking_specialisation_coverage` tool at the same MCP endpoint lists valid slugs; coverage is not a census.
3. Leave authentication set to **None** and transport set to **HTTP Streamable**. Use a version of n8n with **MCP Client 1.1**; version 1.0 does not reliably stop on tool-level errors.
4. Select **Execute workflow** once, then inspect **Keep the complete research record**.

The tool is `bank_asset_quality_review` at `https://api.liquilens.in/mcp`. Its required argument is `slug`. `include_history` is optional and defaults to `false`; setting it to `true` requests the available history. An optional `as_of` date uses `YYYY-MM-DD` and must not be in the future. The workflow omits it to request the current evidence cutoff.

The output retains the complete research record. Read `status`, `period_end`, `available_at`, `retrieved_at`, `sources`, `source_documents`, `historical_evidence`, and `interpretation_limits` with the metrics. The current cutoff is not the reporting period. Null figures remain missing. Observed, stale, historical and unavailable evidence are kept distinct. No result grants score, credit or execution authority.

This workflow has no schedule, automatic retry, message destination, or order action. Repeated executions should serve an actual research task. A normal workflow request is not proof of a distinct human user or autonomous agent.

## Validation and compatibility

The serialized MCP node configuration was checked against the official **n8n 2.37.10** source and its tests. The node's input and output contracts, JSON parameter mode, `none` authentication, `httpStreamable` transport, and version 1.1 error behavior were verified there. The output-checking JavaScript was executed with Node against successful, stale, historical, unavailable, malformed and error fixtures. A separate operator-labelled live probe confirmed the example slug, tool schema and response contract on **2026-09-05**; those probes are verification traffic.

Native validation passed on **n8n 2.37.10 with Node 24.19.0** on **2026-09-05**. The unchanged recipe imported through CLI directory mode (`--separate`), which creates its local instance ID, and exported with identical nodes and connections. A temporary copy used a loopback forwarder to label live calls as operator verification. Its bank review preserved the complete evidence record; an injected MCP tool error stopped the workflow before the output step. The download retains the public, unauthenticated endpoint. This file is a downloadable recipe, not an accepted n8n template-library listing.

- [Official MCP Client node documentation](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-langchain.mcpclient.md)
- [Pinned MCP Client implementation](https://github.com/n8n-io/n8n/blob/n8n%402.37.10/packages/%40n8n/nodes-langchain/nodes/mcp/McpClient/McpClient.node.ts)
- [Pinned node tests](https://github.com/n8n-io/n8n/blob/n8n%402.37.10/packages/%40n8n/nodes-langchain/nodes/mcp/McpClient/__test__/McpClient.node.test.ts)
- [n8n template contribution guidance](https://docs.n8n.io/build/ways-of-building-workflows/use-templates.md)
