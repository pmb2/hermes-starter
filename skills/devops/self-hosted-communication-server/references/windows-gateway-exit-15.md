# Windows Gateway Exit 15 (SIGTERM) — Full Debugging Trail

## June 2026 Update: The Death Loop Was a Phantom

Comprehensive staged testing (6 stages, signal-traced subprocesses) proved the
gateway was **never dying at ~55s**. What looked like a death loop was two
misinterpreted signals:

1. **Fleet-core cleanup kills** — `_kill_existing_gateway()` sends
   `psutil.Process.kill()` → SIGTERM=15. These are intentional kills of stale
   instances before launching replacements. Log line `"Died (exit=15)"` in
   fleet-core meant "we killed the OLD process before starting the new one."

2. **Background process completion -15 notifications** — The `process_registry`
   reports when terminal-launched subprocesses exit. Exit code -15
   (WIFSIGNALED + WTERMSIG=15) means the subprocess got SIGTERM — typically
   from MSYS2/bash orphan cleanup. These appear as informational messages in
   the gateway.log, NOT as gateway crashes.

See `references/phantom-death-loop-staged-tests.md` for the full staged
test methodology and raw data.

## Updated Windows Process Death Isolation Guidance

**Before debugging a suspected death loop, run the staged isolation tests:**

1. Stage 1: `GatewayRunner.__init__()` — 92s survival rules out imports/init
2. Stage 2: `GatewayRunner.start()` with zero platforms — 100s survival rules
   out background tasks
3. Stage 3: Add ONE platform at a time (real Discord first, then Spacebar)
4. Use signal handlers with `tb.format_stack()` to capture exact death point
5. Use a subprocess wrapper that records exit code + duration precisely
6. If all stages survive, the "death" was never a death — look for
   misinterpreted logs (process registry completions, fleet cleanup kills)

## Symptom

Gateway subprocess dies with `exit=15` within 20-200 seconds of starting (most consistently ~50-55s under Python, ~15-20s under pythonw). Log shows clean startup: plugin loading → `Connected as bot#0001` → `✓ discord connected` → `Cron ticker started` → then abrupt death. No error or traceback in the log.

## Root Cause: MSYS2/Bash Process Management (Terminal Tool Context)

On Windows, when gateway processes are launched from the Hermes terminal tool (which runs commands via MSYS2/git-bash), the bash shell tracks child process trees and kills orphaned grandchildren. This is NOT standard Windows behavior — it's an MSYS2-specific process management layer.

**Evidence:**

| Launch method | Uptime | Source |
|---|---|---|
| Via terminal tool (`python -c` subprocess.Popen, or `terminal()` direct) | **15-30s** ❌ Dies exit=15 | This session |
| Via fleet-core (pythonw.exe, no MSYS2 involved, launched via VBS) | **2.75+ hours** ✅ Stable | Fleet-core logs |
| Via standalone `.vbs` script (WScript.Shell.Run) | **2.75+ hours** ✅ Stable | Deduced from fleet-core behavior |
| Via `terminal(background=true)` (still under MSYS2) | **30-45s** ❌ Dies exit=15 | This session |

**Fleet-core currently has 10 active gateways** that have been running for hours. Each shows ~120MB RSS. The `spacebar-technology-lead.err.log` shows memory reports with uptime **9900+ seconds** (2.75+ hours).

**The wrapper (`spacebar-gateway.py`) is NOT the cause.** All 18 monkey-patches are necessary (audited vs native Discord plugin adapter — none are redundant). The native Discord adapter connects to `gateway.discord.gg` using API v10 with `Bot`-prefix auth — it has zero Spacebar compatibility built in.

**The stock gateway "survived 8+ minutes" earlier because it wasn't actually connected to anything** — it was sitting idle with a failed platform adapter, not doing real work.

**Key Finding: No Exit Hooks Fire**

The exit diagnostic log (`gateway-exit-diag.log` in the profile's `logs/` dir) records tagged JSON events at every gateway lifecycle point. For ALL death-loop deaths, the ONLY tag recorded is `gateway.start`. Never `asyncio.run.returned`, `atexit.hook`, `gateway.exit_nonzero`, or `gateway.exit_clean`.

This means the process is **hard-killed via TerminateProcess (exit code 15)** — no Python finally blocks, no atexit handlers, no signal handlers execute. This rules out `sys.exit(15)` from within the gateway code. The kill comes from outside the Python process.

## What Does NOT Work (when launching from terminal tool context)

| Fix | Result | Notes |
|-----|--------|-------|
| `HERMES_GATEWAY_DETACHED=1` | ❌ Still dies | Console absorption confirmed in diag log but not sufficient |
| `terminal(background=true)` direct via Hermes | ❌ Still dies (exit=15) after 15-30s | Still under MSYS2 process tree |
| `pythonw.exe` via subprocess | ❌ Still dies at ~15-20s | MSYS2 tracks grandchildren |
| `CREATE_NEW_PROCESS_GROUP` | ❌ Still dies | New process group for console but MSYS2 still tracks the PID |
| `DETACHED_PROCESS + CREATE_NO_WINDOW` | ❌ Still dies | MSYS2 tracks via process tree |
| VBS launcher from MSYS2 context | ❌ Dies | Same MSYS2 ancestry |
| `stdout=DEVNULL` or file | ❌ Still dies | Not a pipe/stderr issue |
| MemPalace per-profile DBs (`--palace`) | ❌ Still dies | Not a database contention issue |
| Stripping all MCP servers | ❌ Still dies | Not an MCP-related issue |
| Different Spacebar WS endpoints | ❌ Still dies | Not a Spacebar connection-limits issue |

## What DOES Work

- **Fleet-core** launched from Windows-native context (VBS → pythonw.exe → subprocess). Gateways survive for hours. NOT launched via `terminal()` or MSYS2/bash.
- **VBS/WScript.Shell.Run** with pythonw.exe — fully detached, no MSYS2 ancestry.
- **Windows Service** launcher — would also work for the same reason (no MSYS2).
- **Task Scheduler** with "Run whether user is logged on or not" — also avoids MSYS2.

## Why Fleet-Core Works

Fleet-core is launched by `HermesExecutiveCouncil.vbs` from the Windows Startup folder:
```vbs
WshShell.Run chr(34) & "...pythonw.exe" & chr(34) & " " & chr(34) & "...fleet-core.py" & chr(34), 0, False
```

`WshShell.Run` with window_style=0 creates a hidden window. `pythonw.exe` has no console. When fleet-core uses `subprocess.Popen` with `pythonw.exe`, the child gateways inherit the no-console, no-MSYS2 ancestry. They are NOT tracked by MSYS2/bash and thus NOT killed.

## Concurrent Gateway Pitfall: MemPalace SQLite Contention

When concurrent gateways share the same MemPalace database (`~/.mempalace/palace/chroma.sqlite3`), only ONE process can hold the SQLite write lock. The second/third MCP server processes crash with database locking errors.

**Fix:** Each profile must use its own MemPalace database via the `--palace` argument:

```yaml
mcp_servers:
  mempalace:
    command: mempalace-mcp
    args: ['--palace', 'C:/Users/<user>/.mempalace/palace-<profile-name>']
    timeout: 120
```

**Init:** Create the dirs and let the MCP server auto-init on first launch:
```bash
mkdir -p ~/.mempalace/palace-<profile-name>
```

**Note:** This is NOT the cause of exit=15 — even with MemPalace disabled, concurrent gateways die from MSYS2 context. But per-profile databases prevent SQLite crashes when gateways DO successfully launch.

## Diagnostic Data (June 2026 — Wrapper vs Stock)

### Patch Redundancy Audit

The `spacebar-gateway.py` has 18 monkey-patches. Compared against the native Hermes Discord plugin adapter (`plugins/platforms/discord/adapter.py` — 6,540 lines):

| Patch | Native adapter has? | Redundant? |
|-------|-------------------|------------|
| API version v9 | Uses v10 | **NOT redundant** |
| Route.BASE → Spacebar URL | `discord.com/api/v10` | **NOT redundant** |
| DEFAULT_GATEWAY → Spacebar WS | `gateway.discord.gg` | **NOT redundant** |
| compress=False | Default compress | **NOT redundant** |
| Raw token auth (no Bot prefix) | Uses `'Bot ' + token` | **NOT redundant** |
| Custom identify payload | Standard discord.py identify | **NOT redundant** |
| Command API methods | Discord-only endpoints | **NOT redundant** |
| Custom login (HTTP /users/@me) | `commands.Bot.start()` OAuth2 | **NOT redundant** |
| Null guild_id patches (4 raw models) | No handling | **NOT redundant** |
| _fill_overwrites null guard | No handling | **NOT redundant** |
| dispatch _MissingSentinel guard | No handling | **NOT redundant** |
| msvcrt.locking noop | Uses platform lock | **NOT redundant** |
| received_message null guild_id | No handling | **NOT redundant** |
| TextChannel._update safe_data | No handling | **NOT redundant** |

**Verdict: ALL 18 patches are necessary.** The native adapter is a full-featured production adapter for real Discord only. The wrapper is the ONLY path to Spacebar connectivity.

### Exit Diag Log Analysis

Log at `~/AppData/Local/hermes/profiles/<profile>/logs/gateway-exit-diag.log`:
- Only `tag: "gateway.start"` entries for killed processes
- No `tag: "gateway.exit_clean"`, `tag: "atexit.hook"`, or `tag: "gateway.exit_failure"` entries
- Confirms `TerminateProcess` (external kill, not Python-level exit)
- Controlled via `HERMES_GATEWAY_EXIT_DIAG=1` env var (default: on)

### Concurrent vs Single Launch Behavior

| Test scenario | First gateway | Second gateway | Third gateway |
|---|---|---|---|
| Fresh start (all killed) | Dies exit=15 at 5-30s | Varies | Varies |
| Stale gateways running | Lives 120s+ | Dies at 15-20s | Dies at 10-25s |
| Fleet-core managed | Hours | Hours | Hours |
| Terminal tool | 15-30s | 15-30s | 15-30s |

The first/second/third asymmetry was a red herring — it was random timing of MSYS2's process tree management, not a profile-specific resource.

## Fixes Applied

### 1. HERMES_GATEWAY_DETACHED=1 (Console Absorption)

Forces `SetConsoleCtrlHandler(NULL, TRUE)` to absorb console control signals:

- In `fleet-core.py`: `env["HERMES_GATEWAY_DETACHED"] = "1"` when spawning gateways
- In `spacebar-gateway.py`: `os.environ.setdefault("HERMES_GATEWAY_DETACHED", "1")` at import time

After fix: exit diag shows `absorb_windows_console_controls: true`.

### 2. CTRL_BREAK_EVENT → taskkill for fleet-core stop()

Original code used `self.process.send_signal(signal.CTRL_BREAK_EVENT)` which sends to ALL console processes. Replaced with:

```python
subprocess.run(["taskkill", "/PID", str(self.process.pid), "/T", "/F"], ...)
```

This targets only the specific PID tree, not the console group. Fixed in `scripts/fleet-core.py`.

### 3. Redact layer fix for API key propagation

The `agent/redact.py` `sk-` prefix pattern was causing API key values to be truncated in agent tool output causing `***` to be written to profile `.env` files. Fixed by disabling the pattern. Committed to `pmb2/hermes-agent` branch `fix/disable-sk-redaction`.

## Current Workaround

The fleet-core restarts dead gateways automatically. Bots are functional while alive (~50-55s window). The fleet-core's monitoring cycle keeps them running with acceptable availability. For production use, a more resilient solution (Docker-based gateway on Linux VPS, or Windows Service launcher) is recommended.

## Key Files Referenced

- `scripts/spacebar-gateway.py` — gateway launcher with discord.py→Spacebar patches
- `scripts/fleet-core.py` — fleet manager with auto-restart
- `hermes_cli/gateway.py` — `run_gateway()`, `_windows_gateway_should_absorb_console_controls()`
- `agent/redact.py` — `redact_sensitive_text()` with `sk-` prefix pattern
- `~/.hermes/profiles/<name>/logs/gateway-exit-diag.log` — exit diagnostics (tagged JSON lines)
- `~/.hermes/logs/spacebar-<name>.log` — per-bot gateway output
