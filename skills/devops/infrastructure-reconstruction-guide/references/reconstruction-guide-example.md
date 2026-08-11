# RECONSTRUCTION.md Reference — Real-World Example

> Example document produced for a Hermes Agent ecosystem with 48 profiles, 38 MCP servers, 70+ skills, 30 scripts, OmniRoute, Buzz relay, VPS hybrid.
> Full text: `~/Documents/github/hermes-config/RECONSTRUCTION.md` (998 lines, 34 KB)

## Table of Contents (Real Example)

```
1. Prerequisites
   1.1 Required Software
   1.2 Accounts & Access
2. Clone & Restore Config
   2.1 Clone the Config Repository
   2.2 Clone Supporting Repositories
   2.3 Update Paths in Config
   2.4 Run the Setup Script
3. Install Hermes Agent
   3.1 Install via Curl
   3.2 Verify Installation
   3.3 Copy Configuration
4. .env File Construction
   4.1 Create the .env File
   4.2 All Required Keys (20+ variables with source URLs)
   4.3 .env Template
5. Infrastructure Setup
   5.1 OmniRoute (Model Routing Gateway)
   5.2 Camoufox Browser
   5.3 Trinity / Trilium Notes
   5.4 Postgres (Twenty CRM Database)
   5.5 Logseq Knowledge Graph
   5.6 Buzz Relay (Nostr)
   5.7 FAL.ai Media Generation
   5.8 MemPalace Memory
   5.9 VPS Hybrid Setup (Oracle Free Tier)
6. MCP Server Recovery
   6.1 Browser-Based MCPs
   6.2 Knowledge MCPs
   6.3 Finance MCPs
   6.4 Dev Tools MCPs
   6.5 Intelligence MCPs
   6.6 Classic MCP Servers
   6.7 MCP Dependency Installation (Bulk)
7. Profile Restoration
   7.1 Create Profile Directories (46 profiles)
   7.2 Restore Profile Configuration
   7.3 Profile Recovery Strategy (4 priority tiers)
8. Scripts Restoration
   8.1 Copy All Scripts
   8.2 Script Dependencies (20+ scripts with purpose/dep table)
   8.3 Bulk Install Python Dependencies
   8.4 Essential Config Files for Scripts
9. Cron Jobs & Watchdogs
   9.1 Cron Guardian
   9.2 Guardian Angel (Process Watchdog)
   9.3 Nightly Watchdog
   9.4 Autogit Watchdog
   9.5 YouTube WatchLater
   9.6 Intelligence Collectors
   9.7 Welcome-Back Briefing
   9.8 Cron Jobs Summary (9 cron jobs with schedules)
10. Verification Checklist
    10.1 System Health
    10.2 API / Provider Connectivity
    10.3 Docker Services
    10.4 MCP Server Connectivity
    10.5 Knowledge Base
    10.6 Cron Jobs
    10.7 Profile Switching
    10.8 Skills
    10.9 Script Health
    10.10 VPS (if deployed)
    10.11 End-to-End Test
Appendix A: Quick-Start Checklist (20 boxes)
Appendix B: File Reference
Appendix C: Port Allocation
```

## Key Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Total lines | 998 | Dense — no fluff, every section is actionable |
| Sections | 10 + 3 appendices | Follows dependency order |
| Code blocks | 40+ | Every command copy-pasteable |
| Tables | 25+ | Software, accounts, MCP servers, scripts, cron, verification |
| Total file size | 34 KB | Manageable for a README reference |
| Total profiles | 48 | 46 with config.yaml, 45 with AGENTS.md, 46 with SOUL.md |
| Total MCP servers | 16+ | Across config.yaml, .hermes/config.yaml, and all profiles |
| Total scripts | 29 | In the config repo |
| Total cron jobs | 9 | With schedules and registration commands |

## Extraction Commands Used

These commands produced the data that fed the reconstruction guide:

```bash
# Profile inventory
ls ~/AppData/Local/hermes/profiles/
find ~/AppData/Local/hermes/profiles -name "config.yaml" | wc -l
find ~/AppData/Local/hermes/profiles -name "AGENTS.md" | wc -l
find ~/AppData/Local/hermes/profiles -name "SOUL.md" | wc -l

# Config file inventory
find ~/Documents/github/hermes-config -type f -not -path '*/.git/*' | sort

# MCP server extraction (from config.yaml mcp_servers section)
grep -A2 '^  [a-z]' ~/Documents/github/hermes-config/config/config.yaml | head -200

# Env var references
grep -rohP '\$\{[A-Z_]+}' ~/Documents/github/hermes-config/config/ | sort -u
grep -rohP 'os\.getenv\(['\"]([A-Z_]+)['\"]' ~/Documents/github/hermes-config/scripts/*.py | sort -u

# Port bindings
grep -rohP 'port[=: ]\s*\d+' ~/Documents/github/hermes-config/config/ ~/Documents/github/hermes-config/vps/ 2>/dev/null | sort -u

# Path migration targets
grep -rn 'yourdata\|/<you>/' ~/Documents/github/hermes-config/config/ 2>/dev/null | head -30

# Docker services
grep -A3 'image:' ~/Documents/github/hermes-config/vps/docker-compose.yml

# Script dependency extraction
for f in ~/Documents/github/hermes-config/scripts/*.py; do
  deps=$(grep -E '^(import |from )' "$f" | grep -v '^#\|^$' | sed 's/import //;s/from.*import .*//' | tr ',' '\n' | sed 's/^ *//' | sort -u | tr '\n' ' ')
  echo "$(basename $f): $deps"
done
```

## File Reference (from example)

| Path | Purpose |
|---|---|
| `~/Documents/github/hermes-config/` | Config repo (source of truth) |
| `~/AppData/Local/hermes/config.yaml` | Main Hermes configuration |
| `~/AppData/Local/hermes/.env` | Secrets (DO NOT COMMIT) |
| `~/AppData/Local/hermes/model_config.json` | Central model provider config (3 profiles) |
| `~/AppData/Local/hermes/jobs.json` | Job agent configuration |
| `~/AppData/Local/hermes/profiles/<name>/` | Per-profile config + AGENTS.md + SOUL.md |
| `~/AppData/Local/hermes/scripts/` | All automation scripts |
| `~/AppData/Local/hermes/skills/` | Skill library |
| `~/.logseq/hermes-graph/` | Logseq knowledge graph |

## Port Allocation (from example)

| Port | Service |
|---|---|
| 20128 | OmniRoute (model routing) |
| 8090 | Trilium Notes (Docker) |
| 33443 | Twenty CRM Postgres |
| 3000 | Buzz Relay (Nostr) |
| 8642 | Hermes API Server |
| 11434 | Ollama (local LLM) |
| 9223 | Firefox remote debugging |
| 2828 | Firefox Marionette |
| 5432 | Postgres (VPS) |
| 6379 | Redis (VPS) |
| 9020 | MemPalace MCP |
| 8080 | TradingView MCP (VPS) |
