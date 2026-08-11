# Phantom Death Loop — Staged Binary-Search Isolation (June 2026)

## The Hypothesis

The gateway appeared to die at ~55s with `exit=15` when launched via the Hermes
terminal tool. The symptom looked like a Spacebar-specific crash in the
discord.py adapter.

## The Staged Test Methodology

Instead of guessing at the cause, we isolated the failure layer-by-layer:

| Stage | What Was Tested | Expected Death? | Actual | Finding |
|-------|----------------|-----------------|--------|---------|
| 1 | `GatewayRunner.__init__()` only — imports + object creation | No | **92s alive** ✅ | Init is safe |
| 2 | `GatewayRunner.start()` with **no platforms** — background tasks only | Maybe | **100s alive** ✅ | Background tasks are safe |
| 3A | `GatewayRunner.start()` with **real Discord** adapter connected | If Discord-specific | **100s alive** ✅ | Real Discord is safe |
| 3B | `GatewayRunner.start()` with **Spacebar** config (env vars + Route.BASE patch) | ~55s if Spacebar-specific | **100s alive** ✅ | Spacebar config loading is safe |
| 3B-v2 | `GatewayRunner.start()` with **local Spacebar** (localhost:3100, API v9) | ~55s if connection issues | **Failed to connect** (token mismatch) — but process survived | Connection failure doesn't kill |
| Full | `start_gateway()` via `asyncio.run()` — same as CLI `gateway run` | ~55s | **Completed cleanly** | No death |

## Critical Insight: The Process Registry's Background Process Completion Messages

The gateway.log was filling with entries like:
```
Background process proc_xxx completed (exit code -15)
```

These are **NOT** the gateway dying. The process registry notifies the user when
a terminal-launched subprocess exits. Exit code -15 means "killed by signal 15"
(SIGTERM) — these are background terminal commands that MSYS2/bash killed as
orphans when the parent session ended. They appeared alongside `exit=15` in the
general log noise and were mistakenly attributed to the gateway.

## Fleet-Core Cleanup Kills vs Actual Crashes

The fleet-core manager has a `_kill_existing_gateway()` method that sends
`psutil.Process.kill()` — which on Windows sends `TerminateProcess` (exit code
15 = SIGTERM in MSYS2). The fleet-core log shows:

```
[bot-name] Killing stale gateway PID=12345
[bot-name] Died (exit=15)
```

This is **intentional cleanup** of a previous instance before launching a new
one, not a crash. In a staggered startup (0.5s gap), bot A's cleanup can hit
bot B's just-started process, creating the appearance of a death spiral.

## How to Reproduce the Staged Test Pattern

Use a wrapper script (`stage-wrapper.py`) that:
1. Launches the test in a subprocess via `subprocess.Popen`
2. Captures the exit code with `proc.wait(timeout=N)`
3. Logs the exact duration and exit code

Signal handlers at the top of each test:
```python
import signal, traceback as tb
def _sig_handler(signum, frame):
    stack = ''.join(tb.format_stack(frame))
    log.critical("SIGNAL %d at %.1fs\n%s", signum, time.time()-start, stack)
    sys.exit(15)
for s in (signal.SIGTERM, signal.SIGINT, signal.SIGABRT):
    try: signal.signal(s, _sig_handler)
    except: pass
try: signal.signal(signal.SIGBREAK, _sig_handler)
except: pass
```

## Key Files Referenced

- `gateway/run.py` — `GatewayRunner`, `start_gateway()`
- `gateway/config.py` — `load_gateway_config()`, PlatformConfig
- `plugins/platforms/discord/adapter.py` — DiscordAdapter, `_api_base_url`, `_api_url()`
- `tools/process_registry.py` — Background process tracking
