# Spacebar Bot Deployment — the operator (May 2026)

Full session record: deploying 35 AI agent bots (expanded from 17) to a self-hosted Spacebar instance at discy.your-domain.example, with the Hermes agent fleet routed to it via a discord.py monkey-patch wrapper.

## Architecture

```
Fermi Web UI (port 8080)     AI Agents (Discord API)
        │                              │
        └──────────┬──────────────────┘
                   ▼
     Spacebar API (port 3001)
           │
           ▼
     PostgreSQL (port 5432)
```

## Bot Inventory (35 agents — May 29 session expanded from 17 to 35)

The original deploy batch covered 17 council+specialist bots. In the May 29 session, this was expanded to 35, adding Dev Team (5), Trading Scouts (8), and Social Media (5) across the same the operator guild.

Full inventory in `agent-fleet/docs/CHANNEL_CREDENTIALS.md` and `agent-fleet/config/spacebar-fleet.yaml`.

### Original 17 (Council + Specialists)

| Bot | Codename | Role |
|-----|----------|------|
| chief-of-staff | Aegis | Executive coordination |
| technology-lead | Architect | Engineering, CI/CD, infra |
| growth-lead | Quartermaster | Sales, MES, jobs, content |
| intelligence-lead | Oracle | OSINT, research |
| treasury-lead | Ledger | Cash, accounting |
| counsel-lead | Counsel | Contracts, compliance |
| compliance-lead | Exchequer | Tax planning |
| portfolio-lead | Capital | Investments, RE, portfolio |
| operations-lead | Conductor | Workflows, infra |
| manufacturing-lead | ForgeMaster | MES consulting |
| ai-agency | AIA | AI solutions |
| media-lead | Scribe | Content, media |
| cyber-osint | Phantom | Cyber threat intel |
| market-lead | Equity | Real estate analysis |
| legal-case-support | Brief | Legal case research |
| health-performance | Vital | Health tracking |
| outreach-lead | Hire | Job pipeline |

### Additional 18 (May 29 — Dev, Scouts, Social)

**Dev Team (5):**
| Bot | Role |
|-----|------|
| dev-lead | Hermes core development, architecture |
| docs-lead-dev | Documentation, release management |
| qa-lead | QA, CI/CD, test automation |
| skills-lead | Skills & tooling development |
| integration-lead | MCP server integration |

**Trading Scouts (8):**
| Bot | Codename | Role |
|-----|----------|------|
| data-lead | Insider | SEC Form 4 filings |
| assistant | Holdings | 13F institutional filings |
| verifier | Macro | Fed policy, macro indicators |
| product-lead | Blockchain | On-chain data, wallets |
| admin | Technical | Technical analysis, portfolio |
| scout | Congress | STOCK Act filings |
| people | Consensus | Vote aggregation, scoring |
| analyst | Alert | Alert distribution, routing |

**Social Media Team (5):**
| Bot | Role |
|-----|------|
| nova | Content strategist, editorial calendar |
| writing-lead | Content creator, writing, graphics |
| notes | X/Twitter publisher |
| lane | LinkedIn publisher |
| pulse | Analytics, trend research |

## Channel Layout (8 categories, 31 channels)

```
Command Center (4 channels)
  ├ #command
  ├ #announcements
  ├ #status
  └ #logs
Technology (4 channels)
  ├ #dev
  ├ #engineering
  ├ #deployments
  └ #github-feed
Revenue (6 channels)
  ├ #revenue
  ├ #revenue-pipeline
  ├ #mes-consulting
  ├ #ai-agency
  ├ #content
  └ #careers
Intelligence (4 channels)
  ├ #intel
  ├ #osint-reports
  ├ #threat-intel
  └ #research
Finance & Legal (5 channels)
  ├ #finance
  ├ #expenses
  ├ #investments
  ├ #deals
  └ #legal
Operations (4 channels)
  ├ #ops
  ├ #scheduling
  ├ #projects
  └ #ops-alerts
Social Media (3 channels)
  ├ #content-drafts
  ├ #published
  └ #analytics
Voice Channels (2 channels)
  ├ #war-room
  └ #standup
```

## Key Deployment Steps

### 1. Server Setup
- Fork spacebarchat/server → pmb2/spacebar
- `npm install && npm run build:tsgo`
- Create PostgreSQL database `spacebar` (trust auth for 127.0.0.1)
- Start server, let it generate config.json, then edit

### 2. Critical Patches
- **login.ts line 69**: Add `{ username: login }` to TypeORM where clause (Spacebar only searches by email/phone)
- **config.json**: Generate `security.jwtSecret` (secrets.token_hex(32)), disable both rate limiters, relax registration

### 3. Fermi Client
- Fork MathMan05/Fermi → pmb2/Fermi
- Edit `src/webpage/instances.json` — add local instance as first entry with `"display": true`
- `npm install && npm run build && npm run start` — serves on port 8080

### 4. Bot Registration (35 bots)
```
POST /auth/register
{
  "username": "<bot-name>",
  "password": "<password>",
  "consent": true
  // NOTE: do NOT include "bot": true — Spacebar rejects unknown fields
}
```
- Capture tokens from registration response, or login after creation
- With rate limits disabled, all 35 bots register in ~40 seconds with 1s delays
- **Batch script:** `agent-fleet/scripts/spacebar-deploy.sh` registers all 35, creates guild + channels, saves tokens to `.env.spacebar`
- **Guild creation:** Spacebar API rejects `"description"` field in guild creation payload (50035 `additionalProperties` error). Use `{"name":"Guild Name"}` only.

### 5. Guild & Channel Creation
```python
# Pattern for each category+channels
CAT = POST /guilds/{id}/channels  {"name":"Category","type":4}
CH  = POST /guilds/{id}/channels  {"name":"channel","type":0,"parent_id":CAT}
```
- Categories (type=4) created first
- Text channels (type=0) reference category via `parent_id`

### 6. Guild Ownership
- If you recreate the admin user (e.g. re-running deploy script), the new admin is NOT the guild owner
- The old guild must be deleted from the database before re-creating:
  ```sql
  DELETE FROM channels WHERE guild_id='<guild-id>';
  DELETE FROM guilds WHERE id='<guild-id>';
  ```
- The `PUT /guilds/:id/members/:user_id` endpoint requires OAuth2 — it cannot add members without bot tokens

## Agent Migration (Discord → Spacebar)

Since Hermes agents use discord.py which hardcodes Discord's API URLs, redirection requires monkey-patching. Theoretical config changes (as below) don't work because discord.py ignores them:

```
# ❌ This doesn't work — discord.py doesn't read these from config
discord:
  api_endpoint: "http://localhost:3001/api/v9"
  gateway: "ws://localhost:3001/"
```

### Working Approach: Python Wrapper

Create a wrapper that patches discord.py's constants BEFORE importing gateway code:

```python
def patch_discord():
    import discord.http, discord.gateway
    from yarl import URL
    old = discord.http.Route.BASE
    discord.http.Route.BASE = "http://localhost:3001/api/v9"
    discord.gateway.DiscordWebSocket.DEFAULT_GATEWAY = URL("ws://localhost:3001/")
```

Full implementation at `agent-fleet/scripts/spacebar-gateway.py`.

### Automated Fleet Deploy

`agent-fleet/scripts/spacebar-fleet-deploy.sh`:
1. Sources `.env.spacebar` for 35 bot tokens
2. Creates/updates Hermes profiles (set tokens, disable busy-ack)
3. Stops old gateways
4. Starts each gateway via nohup + wrapper

Usage:
```bash
cd ${MY_REPOS}/agent-fleet
source .env.spacebar
bash scripts/spacebar-fleet-deploy.sh
```

### Profile Location (Windows)

**Important:** On Windows, Hermes profiles live at:
```
~/AppData/Local/hermes/profiles/<name>/    ← correct
~/.hermes/profiles/<name>/                  ← does not exist (Linux/Mac path)
```

### Windows Batch File

`agent-fleet/scripts/start-all-spacebar-agents.bat` — double-click to start all 35 gateways. Each starts minimized, logs to `~/.hermes/logs/spacebar-<agent>.log`.

### Verification

After starting gateways, check logs for:
```
[Spacebar] Route.BASE: https://discord.com/api/v10 → http://localhost:3001/api/v9
[Spacebar] DEFAULT_GATEWAY: wss://gateway.discord.gg/ → ws://localhost:3001/
```

## Token Management
- Tokens are JWT-based, prefixed with `mfa_`
- Tokens expire? (not observed in dev — long-lived per session)
- Source token env file before making API calls: `source spacebar-tokens.env`
- Token variables: `SPACEBAR_ADMIN_TOKEN`, `SPACEBAR_BOT_<NAME>` (uppercase, hyphens→underscores)
