# Hermes Dev Team (Team 7) — Reference Example

This is a concrete example of building and launching a 5-agent team on Spacebar.
Use as a template when creating new teams.

## Team Manifest

| Agent | Role | Skills | MemPalace Wings |
|-------|------|--------|-----------------|
| dev-lead | Core Engineer | systematic-debugging, codebase-inspection, karpathy-principles, subagent-driven-development, plan, spike, token-optimization-rtk | hermes-core-wing, architecture-wing, changelog-wing |
| skills-lead | Skills Architect | hermes-agent-skill-authoring, writing-plans, foss-first-engineering, codebase-hardening, open-source-tool-research | skills-wing, tool-reference-wing, quality-reports-wing |
| integration-lead | MCP Integrator | native-mcp, building-mcp-servers, open-source-tool-research, fastapi-mcp-bridge, mcp-server-onboarding | mcp-wing, server-health-wing, integration-reports-wing |
| qa-lead | QA/CI-CD Engineer | test-driven-development, systematic-debugging, github-code-review, requesting-code-review, codebase-hardening, web-app-qa | quality-wing, test-reports-wing, security-audit-wing |
| docs-lead | Docs/Release Manager | project-documentation-standards, hermes-agent-skill-authoring, writing-plans, design-md | docs-wing, changelog-wing, release-history-wing |

## Fleet Config Entries

### spacebar-fleet.yaml (tokens)

```yaml
  - name: dev-lead
    description: "Hermes core development, architecture, system design"
    team: hermes-dev
    discord_token: "${SPACEBAR_BOT_FORGE}"

  - name: skills-lead
    description: "Skills development, tooling, developer experience"
    team: hermes-dev
    discord_token: "${SPACEBAR_BOT_SKILLMATE}"

  - name: integration-lead
    description: "MCP server integration, protocol development"
    team: hermes-dev
    discord_token: "${SPACEBAR_BOT_WEAVER}"

  - name: qa-lead
    description: "Quality assurance, CI/CD pipelines, test automation"
    team: hermes-dev
    discord_token: "${SPACEBAR_BOT_SENTRY}"

  - name: docs-lead
    description: "Documentation, release management, changelogs"
    team: hermes-dev
    discord_token: "${SPACEBAR_BOT_SCRIBE}"
```

### full-fleet.yaml (hierarchy)

```yaml
  - name: dev-lead
    description: "Hermes core dev, architecture, system design"
    team: hermes-dev
    reports_to: technology-lead

  - name: skills-lead
    description: "Skills dev, tooling, developer experience"
    team: hermes-dev
    reports_to: technology-lead

  - name: integration-lead
    description: "MCP integration, protocol dev"
    team: hermes-dev
    reports_to: technology-lead

  - name: qa-lead
    description: "QA, CI/CD, test automation"
    team: hermes-dev
    reports_to: technology-lead

  - name: docs-lead
    description: "Docs, release management, changelogs"
    team: hermes-dev
    reports_to: technology-lead
```

## .env.spacebar Template

```
# Spacebar env for <agent-name>
export SPACEBAR_CHANNEL=#hermes-dev
export SPACEBAR_BOT_TOKEN=<jwt-token>
export SPACEBAR_GUILD_NAME="the operator"
export SPACEBAR_GATEWAY_URL=wss://discy.your-domain.example/
export SPACEBAR_GUILD_ID=<discord-channel-id>
export SPACEBAR_API_URL=https://discy.your-domain.example/api/v9
```

## Profile .env Template

```
DISCORD_BOT_TOKEN=<jwt-token>
HERMES_GATEWAY_BUSY_ACK_ENABLED=false
GATEWAY_ALLOW_ALL_USERS=true
```

## Launch Sequence

1. Create #hermes-dev channel on Spacebar (under council category)
2. Assign bots a Bot role with view/send permissions (bots don't inherit @everyone perms on Spacebar — see pitfalls in main SKILL.md)
3. Update each agent's channel_directory.json to include the new channel
4. Set SPACEBAR_CHANNEL in each agent's .env.spacebar
5. Start agents as daemon background processes (one `terminal(background=true)` call per agent)

```bash
cd ${MY_REPOS}/agent-fleet/scripts
source ${MY_REPOS}/agent-fleet/.env.spacebar
PYTHONPATH=${HERMES_HOME}/hermes-agent

# Start each agent in background (daemon — no notify_on_complete):
terminal(background=true, command="${USER_HOME}/.../python.exe spacebar-gateway.py dev-lead")
terminal(background=true, command="${USER_HOME}/.../python.exe spacebar-gateway.py skills-lead")
terminal(background=true, command="${USER_HOME}/.../python.exe spacebar-gateway.py integration-lead")
terminal(background=true, command="${USER_HOME}/.../python.exe spacebar-gateway.py qa-lead")
terminal(background=true, command="${USER_HOME}/.../python.exe spacebar-gateway.py docs-lead")
```

Wait 3-5s between launches to avoid identify collisions.

**Note:** The discord.py patching approach currently hangs after slash command registration. Use the raw WebSocket reference (`references/raw-websocket-qa.md`) for a working connectivity test. The bots are functional via REST API and raw WebSocket even without the Hermes gateway running.

## Verification

```bash
for agent in dev-lead skills-lead integration-lead qa-lead docs-lead; do
  f="${HERMES_HOME}/profiles/$agent/gateway_state.json"
  [ -f "$f" ] && echo "$agent: $(grep -o '\"state\":\"[^\"]*\"' $f | head -1)"
done
```

For REST-level verification (no gateway needed):
```bash
# Check bot responds via API
curl -s https://discy.your-domain.example/api/v9/users/@me -H "Authorization: <token>"
# Post test message
curl -s -X POST "https://discy.your-domain.example/api/v9/channels/<channel_id>/messages" \
  -H "Authorization: <token>" \
  -H "Content-Type: application/json" \
  -d '{"content":"test"}'
```

All should show `"state":"connected"`.

## Key Channels

- #hermes-dev (<discord-channel-id>) — Team 7 home channel
- Under council category (<discord-channel-id>)

## Known Issues

- Gateway.lock file may be stuck from previous run ("Device or resource busy"). The spacebar-gateway.py autofalls back to gateway.lock.alt — no action needed. For persistent issues, patch the lock path to `gateway.lock.spacebar`.
- The "No user allowlists configured" warning is harmless. Guild messages work without it; DMs from non-allowed users are rejected.
- **discord.py gateway hangs:** The `spacebar-gateway.py` patching approach gets stuck after slash command registration. Bots remain connected at the protocol level (raw WebSocket works) but the Hermes gateway never completes initialization. Use the raw WebSocket approach for connectivity; REST API for message posting.
- **Bot guild channel access:** Spacebar bots need an explicit Bot role assigned to view/send in guild channels. @everyone permissions are not inherited by bot users. Fix via the guild owner account: create a Bot role, assign bots to it.

## Online Verification

The guild API's `presence_count` field is unreliable on Spacebar (always 0). Verify online status via DB sessions:

```bash
ssh -i ~/.ssh/oracle_vps ubuntu@129.153.156.190
docker exec -i mobile-mechanic_postgres_1 psql -U hamilton -d spacebar -c "
SELECT u.username, s.status, to_char(s.last_seen, 'HH24:MI:SS') as seen
FROM sessions s JOIN users u ON u.id = s.user_id
WHERE u.username IN ('dev-lead','skills-lead','integration-lead','qa-lead','docs-lead')
AND s.status = 'online'
ORDER BY u.username;
"
```

Expected: all 5 show `status = "online"` with `seen` within the last 60 seconds.
