# Rep System Deployment Reference

Session: June 2026 — Built and deployed channel rep routing for 9 core council bots.

## Files Created

| File | Purpose |
|------|---------|
| `agent-fleet/configs/rep-config.json` | Channel→rep mapping, free channel lists per bot |
| `agent-fleet/configs/summon-state.json` | Active cross-team summons |
| `agent-fleet/scripts/rep-router.py` | CLI for status, summon, dismiss |
| `agent-fleet/scripts/rep_filter.py` | Gateway message filter (prototype — not deployed) |
| `agent-fleet/docs/REP_SYSTEM.md` | Full architecture docs |
| `agent-fleet/scripts/fleet-manager.py` | Rep-aware fleet launcher (replaces old spacebar-fleet-manager.py) |

## Deployment Steps (from scratch)

```bash
# 1. Stop all bots
cd ${MY_REPOS}/Documents/github/agent-fleet
python scripts/fleet-manager.py deploy
# This kills all, starts core 9 with rep config

# 2. Start any that died during deploy (allow 8s between each)
python scripts/fleet-manager.py start treasury-lead
sleep 8
python scripts/fleet-manager.py start operations-lead
sleep 8
python scripts/fleet-manager.py start compliance-lead

# 3. Verify all 9 core bots online
python scripts/fleet-manager.py status
```

## Bot Startup Notes

- Each bot takes 10-15s to initialize (loading MCP servers, connecting to Spacebar).
- Bots started in quick succession (all 9 at once) often crash because MCP init + Discord WS handshake collide.
- Fix: deploy starts all 9, then manually restart the 2-3 that died with `start <name>` and 8s gaps.

## Domain Change

All bot configs were migrated from `discy.your-domain.example` to `gc.your-domain.example`:

- `spacebar-gateway.py` defaults: `discy` → `gc`
- `fleet-manager.py` URLs: localhost:3100 (bypassed DNS)
- Caddyfile: discy now proxies API calls (to support clients with stale discy URLs) but redirects web UI to gc

## Messages API 500 Fix

The channel messages endpoint had `ReferenceError: limit is not defined`. Fix added to both the compiled dist and the source:

```javascript
// Line 69 in dist/api/routes/channels/#channel_id/messages/index.js
const limit = req.query.limit ? Number(req.query.limit) : 50;
```

This is a TypeScript bug in the Spacebar source — if you rebuild (`npm run build`), the fix needs to be re-applied to the compiled output.

## Key Commands

```bash
# Deploy fleet
python scripts/fleet-manager.py deploy

# Show status with rep info
python scripts/fleet-manager.py status

# Individual bot control
python scripts/fleet-manager.py start <name>
python scripts/fleet-manager.py kill <name>

# Team activation (on-demand specialists)
python scripts/fleet-manager.py activate technology
python scripts/fleet-manager.py deactivate technology

# Rep router
python scripts/rep-router.py --status
python scripts/rep-router.py --summon bot1,bot2 <channel_id>
python scripts/rep-router.py --dismiss <channel_id> botname
```
