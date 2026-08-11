# Config

Templates for the Hermes configuration. Copy `config.example.yaml` to your Hermes home
as `config.yaml` (setup.sh does this) and edit.

## Files

| File | Purpose |
|------|---------|
| `config.example.yaml` | Full Hermes config — models, agent behavior, Discord personas, MCP servers, cron, plugins. Secrets are `${ENV_VAR}` placeholders. |
| `agent-model-overrides.example.yaml` | Per-agent model routing manifest for multi-profile fleets (optional — shows the pattern) |
| `model-config.example.json` | Provider profile set (deepseek/openrouter/opencode/omniroute-style) |

## Highlights of the example config

- **Model chain** — primary model + 5-tier fallback chain (router → direct API → local
  pool → ollama). Swap in your own provider keys.
- **Discord personas** — the `discord.channel_prompts` block maps channel IDs to agent
  identities. Three examples included; make your own.
- **MCP servers** — a core set enabled (chrome-devtools, context7, playwright,
  markitdown, postgres, healthy-food-filter, geo-tracker, headroom, remotion-docs,
  a2asearch). Personal/repo-dependent servers are **commented out** with a `# requires:`
  note — uncomment what you actually clone/install.
- **Plugins** — `intelligence-routing` (dual-tier model routing with sticky overrides)
  and `provider-recovery` (silent self-healing) ship in `../plugins/`.
- **Safety defaults** — approvals in smart/semi mode, Tirith sandboxing on, secret
  redaction available via `hermes config set security.redact_secrets true`.

## Secrets

Real values belong in `.env` (gitignored), referenced as `${VAR_NAME}` in YAML.
The example config never contains a real secret.