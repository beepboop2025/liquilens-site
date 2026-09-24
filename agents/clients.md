# Install the free financial research tools

Checked on 24 September 2026. Start at https://liquilens.in/agents/ for
configurations, the Python brief and the n8n workflow. Public research endpoints
require no account or API key. Fair-use limits apply; your model provider may
charge separately.

## Hermes

1. Download https://liquilens.in/agents/hermes.yaml and review it.
2. Merge its `mcp_servers` entries into `~/.hermes/config.yaml`. Keep your existing
   settings and other servers. The configuration exposes nine research tools
   across Seiche, LiquiLens and Undertow.
3. Check each connection:

```sh
hermes mcp test seiche
hermes mcp test liquilens
hermes mcp test undertow
```

Start a new chat or use `/reload-mcp` in your existing session. Try this task:

> Use Seiche money_market_context to describe the funding backdrop. Keep its
> observation dates, units, stale sources and unavailable fields. Return the
> evidence and open questions.

We tested Hermes tag `v2026.9.24`, commit
`f97608f178d1ffeca59860195ab7da295f7c8e5f`, with Python 3.12. Its native runtime
registered all nine selected research tools and ten resource/prompt helpers.
Native calls to `money_market_context` and `banking_specialisation_coverage`
returned data. This checked runtime dispatch directly; it did not test a model's
decision to select those tools.

The configuration works as a custom connection. The optional Hermes catalog
[contribution](https://github.com/NousResearch/hermes-agent/pull/121379) is awaiting
review as of 24 September; it is not a Nous approval or a released catalog entry.

[Official Hermes MCP guide](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp)

## OpenClaw

Download https://liquilens.in/agents/openclaw.json and merge its `mcp.servers`
entries into `~/.openclaw/openclaw.json`, preserving your other settings. Then run:

```sh
openclaw mcp probe --json
```

In the result, check that LiquiLens, Seiche and Undertow are available. The kit
selects four LiquiLens tools, three Seiche tools and two Undertow tools. Use a
research task in your agent session after discovery succeeds.

We tested `openclaw@2026.9.6` with Node `24.16.0`. The native probe discovered all
three servers and nine selected tools with no diagnostics. This is a discovery
and filtering check; a model turn or native OpenClaw tool invocation was not
part of this check. Follow your installed release's Node requirements.

[Official OpenClaw MCP guide](https://docs.openclaw.ai/cli/mcp)

## Install the research skill

Read https://liquilens.in/agents/trading-research/SKILL.md first. In the project
where you want the skill, run the pinned Skills CLI and select your agent:

```sh
npx skills@1.7.0 add beepboop2025/liquilens-site --skill liquilens-trading-research
```

This installs task instructions; connect the MCP servers separately. Our check
installed this exact skill into an isolated Codex project and matched its bytes
to the published file. It did not run a model or establish user adoption.

[Official Skills CLI](https://github.com/vercel-labs/skills)

## n8n

Download https://liquilens.in/agents/n8n-funding-research.json and import it
through n8n's workflow menu. Leave it inactive, then select **Execute workflow**
once. Open **Preserve evidence and dates** to inspect the complete source record.
It needs no credentials or model. Your own n8n hosting costs may apply.

For CLI import, put the JSON in a directory containing only that workflow:

```sh
n8n import:workflow --separate --input=./workflow-folder
n8n list:workflow
n8n execute --id=YOUR_IMPORTED_WORKFLOW_ID
```

Use the generated ID from `list:workflow`. The download deliberately omits an
instance ID; directory import mode creates one. A direct single-file CLI import
rejected the missing ID in our tested release.

On `n8n@2.40.6` with Node `24.16.0` on macOS arm64, the unchanged workflow
imported and executed successfully. Its single HTTP node retrieved
`https://api.seiche.info/api/public`; its JavaScript Code node retained the full
`seiche.public.v2` response, including `generated_at` and `data_quality`. The
source record was generated at `2026-09-24T10:33:45+00:00` in that check.

The workflow stayed inactive and made one manual fetch. It contains no retry,
message destination or order action. This was a native CLI execution check;
the n8n template-library listing and editor presentation were not tested here.

## Python and other clients

The [starter kit](https://liquilens.in/agents/trading-research-kit.zip) includes a
Python 3.11+ client with no external packages. After reviewing and unzipping it:

```sh
python3 trading_brief.py doctor
python3 trading_brief.py run --size-usd 100000 > first.json
python3 trading_brief.py run --size-usd 100000 --previous first.json > next.json
```

The [text guide](https://liquilens.in/agents/README.md) explains partial results,
exit codes and scheduling. The page also generates Claude Code, Codex, Cursor
and VS Code configurations. Configuration generation is distinct from testing
each client's native runtime.

## Troubleshooting

- An unknown `mcp` command means you should check your installed client's version
  and its official MCP instructions.
- A connection error is not a market reading. Check the endpoint, network access
  and service status; keep failed sections unavailable.
- A returned result can still contain older observations. Compare the source's
  observation date with its retrieval and generation times before using it.
- Keep the same bank slug and dollar size when comparing saved Python briefs.
  Changed source payloads can reflect clocks, revisions or coverage changes.

These checks used separate local profiles. Operator MCP traffic was marked
synthetic and is excluded from adoption reporting. No model credentials,
persistent visitor identifiers or trading actions were added to the kit.
