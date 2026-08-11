# Executive Council Design — June 2026 Restructure

Design and channel mapping for the 7-lead + Chief of Staff executive council.

## Council Structure

the operator (Principal) → Chief of Staff, codename Aegis → 7 leads:
- Development Lead (Architect) — Hermes dev, system health, infra
- Legal Lead (Counsel) — Compliance, contracts, policy monitoring
- Health Lead (Vital) — Nutrition, workouts, biomarkers, coaching
- Intelligence Lead (Oracle) — Pulse pipeline, research, daily digests
- Sports Betting Lead (Sharp) — Odds modeling, AI prediction
- Investment Lead (Capital) — Stock analysis, trading, portfolio
- Cyber Lead (Phantom) — Red team, off/def security, research

## Discord Channel Mapping

| Channel | ID | Lead |
|---------|-----|------|
| #command | <discord-channel-id> | Chief of Staff |
| #pulse-feed | <discord-channel-id> | Intel Lead (Oracle) |
| #dev | <discord-channel-id> | Dev Lead (Architect) |
| #legal | <discord-channel-id> | Legal Lead (Counsel) |
| #health | <discord-channel-id> | Health Lead (Vital) |
| #sports-betting | <discord-channel-id> | Betting Lead (Sharp) |
| #investing | <discord-channel-id> | Invest Lead (Capital) |
| #cyber | <discord-channel-id> | Cyber Lead (Phantom) |

## Cron Job Routing (updated June 6)

**To #pulse-feed** — the operator's Pulse (4h), Pulse Live Scan (4h), Morning Wrap-Up (6AM), Evening Wrap-Up (6PM), Morning Brief (7:01AM), Daily Pulsar (8PM), Weekly Digest (Sun 10AM), Pulse Weekly Roundup (Sun 6PM), PIM Ingestion (3h)

**To #dev** — dev-lead-pulse (4h), qa-lead-pulse (4h), integration-lead-pulse (6h), skills-lead-pulse (6h), docs-lead-pulse (6h), Self-Healing Pulse (4h), gbrain-dream-cycle (2AM)

**Stays in #command** — Daily Command Brief (11AM), Weekly Council Check-in (Mon 2PM)

## Spawn Template

`${MY_REPOS}\Documents\github\agent-fleet\teams\council\spawn-lead.py`
Usage: `python spawn-lead.py <name> <codename> "tagline"`
Creates AGENTS.md + SOUL.md + config.yaml for a new council lead.

## Channel Creation via Bot API

Extract token from `DISCORD_BOT_TOKEN` in `~/.hermes/.env`. Guild ID: <discord-channel-id>.
POST `https://discord.com/api/v10/guilds/{guild_id}/channels` with `{"name":"name","type":0,"topic":"..."}`.
Use Python subprocess or `requests` — avoid shell heredoc which breaks on token special chars.

## Cron Reroute

Use `cronjob action=update job_id="..." deliver="discord:channel_id"` to redirect any job.
