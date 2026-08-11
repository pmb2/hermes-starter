# Cron Jobs

Hermes' built-in scheduler runs durable jobs on a tick. This kit ships:

- **`starter-jobs.json`** — 6 seed jobs (watchdogs + pulses) you can import directly
- Generic prompt files in `../prompts/` for your own daily briefs and scans

## Import the seed jobs

1. Stop the gateway: `hermes gateway stop` (scheduler reads `jobs.json` at tick time)
2. Copy the seed into your Hermes home cron dir:
   ```bash
   cp cron/starter-jobs.json ~/AppData/Local/hermes/cron/jobs.json   # Windows
   # or: cp cron/starter-jobs.json ~/.hermes/cron/jobs.json          # Linux/macOS
   ```
   (If you already have jobs, merge the arrays — each entry has a unique `id`.)
3. `hermes gateway start` → jobs begin scheduling.

Or create jobs interactively:

```bash
hermes cron create 'every 15m' --no-agent --script cron-guardian.py
hermes cron list
```

## Seed jobs

| Job | Schedule | Type | What it does |
|-----|----------|------|--------------|
| Heartbeat Pulse | every 4h | agent | Light status report; silent when healthy |
| Guardian Sweep | every 15m | script | Missed-run detection for other jobs |
| Self-Healer | every 15m | script | Clears stale locks/state, repairs broken cron state |
| Log Rotation | every 6h | script | Rotates gateway/mcp/agent logs |
| Usage Dashboard | daily 9am | script | Token/session usage digest |
| Buzz Watchdog | every 15m | script (disabled) | Restarts the Buzz bridge if dead — enable if you run Buzz |

## Delivery

Seed jobs deliver to `local` (saved to `~/AppData/Local/hermes/cron/output/`).
Set `deliver` to `discord:<channel-id>` or `origin` once your gateway channels exist.

## Notes

- Cron scripts resolve **relative to your Hermes home `scripts/`** — the same dir
  `setup.sh` installs into. "Script not found"? The file must live there, not in a
  nested path.
- `no_agent: true` jobs run the script directly — zero tokens, ideal for watchdogs.
- Jobs run in fresh sessions with no chat context — prompts must be self-contained.