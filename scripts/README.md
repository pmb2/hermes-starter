# Scripts

Reusable automation that keeps a 24/7 Hermes deployment healthy. Install into your
Hermes home `scripts/` via `bash scripts/setup.sh`. Cron jobs reference these by name
(scripts resolve relative to the Hermes home `scripts/` dir).

## Buzz bridge (agent identities on a Nostr relay)

| Script | Purpose |
|--------|---------|
| `generate_buzz_keys.py` | Generate fresh Nostr keypairs for N agent identities — **run this first** |
| `update_buzz_env.py` | Write generated keys into `buzz_keys.env` |
| `buzz_agent_bridge.py` | Main bridge — supervisor connection + per-agent reply threads |
| `start_buzz_bridge.py` | Persistent wrapper — auto-restart, logs to `bridge.log` |
| `buzz_watchdog.py` | Watchdog — restarts the bridge if dead (cron every 15m) |
| `buzz_presence.py` | Presence updates per agent |
| `buzz_cleanup.py` / `buzz_import_discord.py` / `cleanup_spam.py` | Channel migration & maintenance utilities |
| `buzz-stack.sh` / `run_buzz_bridge.sh` | Stack launchers (relay + bridge) |

> No keys are shipped. Everything is generated fresh on first run — never reuse
> someone else's identities.

## Self-healing & supervision

| Script | Purpose | Cron cadence |
|--------|---------|--------------|
| `cron-guardian.py` | Detect missed cron runs, re-fire or alert | every 15m |
| `hermes_self_healer.py` | Auto-repair broken state (locks, hearthbeats, stale state) | every 15m |
| `provider-guardian.py` | Restart the model router quietly when unreachable; escalate surfaced once | every 15m |
| `guardian-angel.py` | Gateway process watchdog — restart crash loops, escalate if hopeless | every 1m |
| `model_identity.py` / `model_switch_monitor.py` | Model config identity + drift monitoring | on restart |
| `schedule_gw_bounce.py` | Scheduled graceful gateway restart | nightly |

## Operations

| Script | Purpose | Cron cadence |
|--------|---------|--------------|
| `rotate-hermes-logs.py` | Rotate mcp/gateway/agent logs | every 6h |
| `usage_dashboard.py` | Usage analytics digest | daily 9am |
| `autogit-watchdog.py` | Auto stage→commit→push for repos with `autogit` enabled | hourly |
| `workflow_runner.py` | Run multi-step workflow recipes | on demand |
| `multi_agent_launch.py` | Spawn parallel research→critique→synthesize subagents | on demand |
| `godmode_toggle.py` | Flip a config/system-prompt toggle | manual |
| `model_alert.sh` / `notify_fallback.sh` / `pulse-check.sh` | Alert & pulse helpers | watchdogs |
| `firefox-watchdog.sh` / `headroom-watchdog.sh` / `start-model-stack.sh` | Service watchers/launchers | watchdogs |

## Layout notes

- Scripts are plain Python 3 / bash — no third-party deps beyond stdlib (buzz bridge
  needs `websockets` — `pip install websockets`).
- All scripts read secrets from **environment variables** (via `.env`), never hardcoded.
- Paths use `${HERMES_HOME}` / `${USER_HOME}` / `${MY_REPOS}` env prefixes — set them
  in your shell profile if a script needs them.