# ECOSYSTEM.md — Worked Example

This file documents the methodology used to build the master ECOSYSTEM.md for the
Hermes Agent ecosystem (the operator, your city NY). It is a real worked example
of applying the `system-architecture-mapping` skill to produce an architecture
overview document for a 48-profile multi-agent system.

## Source Document

The actual ECOSYSTEM.md lives at:
```
~/Documents/github/hermes-config/ECOSYSTEM.md
```
847 lines, 335 table rows, 64 section headers.

## Methodology Used

### Batch 1: Surface + Profiles (parallel)

These were all independent and fired simultaneously:

| Exploration | What it yielded |
|-------------|-----------------|
| `ls ~/Documents/github/hermes-config/` | Config repo structure (8 dirs, 5 docs) |
| `ls ${HERMES_HOME}/profiles/` | 48 profile directory names |
| `ls -laR ${HERMES_HOME}/` | All Hermes root files (config, scripts, skills, cron, db) |
| `read_file config.yaml` | Core config, OmniRoute, MCP servers (first 500 lines) |

### Batch 2: Profile Frontmatter (single grep pass)

```bash
for f in profiles/*/AGENTS.md; do
  profile=$(basename "$(dirname "$f")")
  fm=$(sed -n '/^---$/,/^---$/p' "$f" | grep -E '^(name:|codename:|team:|reports_to:|model:|tools:|mcp_servers:)')
  echo "$profile: $fm"
done
```

This revealed:
- 37 profiles with AGENTS.md (11 missing — flagged separately)
- Team structure: Technology, Operations, Investment, Revenue, Legal, Tax
- All use `deepseek-v4-flash` via `opencode-go`
- 43 of 48 have gateway connections (cross-referenced with presence of `gateway/` dir)

### Batch 3: Live-System Discovery (parallel)

| Exploration | What it yielded |
|-------------|-----------------|
| `read_file(config.yaml offset=501)` | Discord channel prompts, remaining MCP servers |
| `read_file(config.yaml offset=1001)` | MCP servers continued + platform config |
| `ls scripts/` | 195+ scripts catalogued |
| `ls cron/` + `cat cron/jobs.json` | 10+ cron jobs with schedule/profile/status |
| `ls skills/` (categories) | 138 skill directories, 444 SKILL.md files |
| `grep -c '=' .env` | 992 environment variables |
| `cat gateway_state.json` | Discord connected, api_server connected |
| `cat buzz_README.md` | 47 Nostr keypairs with channel maps |
| Key SOUL.md/AGENTS.md reads | Individual profile deep-dives for codenames |

### Batch 4: Cross-Reference

- Mapped each profile `reports_to` field to build the Executive Council hierarchy
- Cross-referenced `gateway/` dir presence vs AGENTS.md `supervisor` flag
- Cross-referenced Discord channel IDs in config.yaml with buzz channel maps
- Verified MCP server count by counting `mcp_servers:` blocks in config.yaml

## Output Structure

The final ECOSYSTEM.md followed this template:

1. **Executive Summary** — scale table (48 profiles, 36 MCP, 444 skills, 195+ scripts, 992 env vars)
2. **Architecture Diagram** — ASCII stack: Discord → Hermes Core → OmniRoute → MCP grid
3. **Component Index** — 7 detailed tables covering: Core, Profiles, MCP, Cron, Scripts, Skills, Integrations
4. **Data Flow** — 3 annotated diagrams (Discord→response, Buzz agent-to-agent, PIM pipeline)
5. **Key Paths** — 60+ paths in 5 tiers
6. **Operational Notes** — profile activation, MCP health, cron patterns, model routing

## Key Decisions

- **Teams over hierarchy**: Profiles are organized by team (Technology, Operations, Investment, Revenue, Legal, Tax) with a separate "Executive Council" table for leads reporting to chief-of-staff
- **Counts from live data**: Every number in the scale table has an `ls | wc -l` or `grep -c` behind it
- **Document type reference**: The README.md in the config repo references ECOSYSTEM.md as the "Master architecture overview" along with RECONSTRUCTION.md and INTEGRATIONS.md
- **Path accuracy**: All paths verified against real filesystem before being written

## What Would Be Different Next Time

- Could batch more profile AGENTS.md reads in parallel (48 files split into 4 groups of 12)
- Could do a phase-0 README scan first to understand the document index before exploring
- Gateway state + channel directory reads should be Phase 1, not Phase 3 (they inform the architecture diagram)
