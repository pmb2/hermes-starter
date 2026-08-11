# Fleet Audit Methodology

When asked to "audit all agents/bots/leads" — a systematic cross-reference of Spacebar DB bots, local Hermes profiles, config templates, and running gateways.

## Parallel Audit Pattern

Use `delegate_task(tasks=[...])` with 2-3 parallel subagents for efficiency:

### Sub-Agent 1: VPS Side (Spacebar DB + API)

Uses SSH + DB queries against the VPS to discover:
- List ALL bot users in the Spacebar DB (`SELECT username, id, bot FROM users WHERE bot = true`)
- List ALL channels in the guild (`GET /api/v9/guilds/{id}/channels`)
- Identify channels with missing descriptions, wrong permissions, or empty assignments
- Cross-reference expected channels (from rep-config.json) against actual channels

**Key queries:**
```sql
-- Bot user count
SELECT COUNT(*) FROM users WHERE bot = true;

-- Full bot roster  
SELECT username, id, bot FROM users WHERE bot = true ORDER BY username;
```

### Sub-Agent 2: Local Side (Profile Configs + Token Inventory)

Scans local filesystem for:
- All Hermes profile configs (`~/.hermes/profiles/<name>/config.yaml` and `.env`)
- All profile templates in `agent-fleet/config/profiles/` (YAML + .env pairs)
- All bot token files (`spacebar-tokens.env`, `*.credentials*.env`, `.env.spacebar`, `discord-tokens-backup.json`)
- Per-bot config quality (full config vs stub vs missing)
- Manifest channel assignments and rep mappings from `rep-config.json`

**What to check per profile:**
- Full config.yaml (model, tools, skills, MCP servers) vs stub (only model + directives TBD)
- .env has DISCORD_BOT_TOKEN and DISCORD_HOME_CHANNEL
- profile exists in `~/.hermes/profiles/` (deployed) vs only in `config/profiles/` (template only)
- Token matches between .env and the Spacebar DB entry

### Cross-Reference Report

The parent agent compiles the two results into a single gap analysis table:

| Dimension | Inventory | Status |
|-----------|-----------|--------|
| Bots in Spacebar DB | N bots | Count |
| Running gateway processes | PIDs | 0 = none online |
| Profiles with full configs | Names | vs stubs |
| Profile templates (undeployed) | Names | Need deployment |
| Channels with assignments | Channels | vs gaps |
| Duplicate/conflicting tokens | Per-bot count | Flag duplicates |

### Common Findings from Prior Audits

- **Zero bots running**: The most common finding. 39 bots registered in DB but 0 gateway processes active. The profiles exist as templates but were never deployed.
- **~/.hermes/profiles/ missing**: The profiles directory doesn't exist — no profile has ever been deployed to this Hermes instance.
- **Token proliferation**: Each bot has 2-5 token versions across different env files (spacebar-tokens.env, credentials-vps.env, .env.spacebar). Tokens often differ between files, meaning they were regenerated at different times against different guilds/servers.
- **6 of 13 council leads are stubs**: Configs with placeholders for directives/TBD — need completion before deployment.
