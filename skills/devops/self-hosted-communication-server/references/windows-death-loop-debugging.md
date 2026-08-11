# Windows Gateway Death Loop Debugging

## Symptom: Exit=15 at ~55s

When Hermes Spacebar gateways consistently exit with `exit=15` at ~55s after launch:

### ⚠️ 2026-06-07 Correction: The "Death Loop" Was a Phantom

**The gateway was never dying at 55s.** What looked like a death loop was two unrelated signal-15 events being conflated with gateway crashes:

1. **Fleet-core cleanup kills.** `_kill_existing_gateway()` calls `psutil.Process.kill()` which sends SIGTERM (signal 15) to stale gateway instances before restarting. Fleet-core logs "Died (exit=15)" for the *killed* process — the current batch was always stable. 6 staged tests (init-only, start-no-platforms, start+real-Discord, start+Spacebar-failed, full start_gateway()) ALL survived 100s+.

2. **Background process -15 notifications.** Terminal subprocesses launched by the agent get SIGTERM from MSYS2/bash orphan cleanup. The process_registry reports these in gateway.log as `Background process proc_xxx completed (exit code -15)` — informational messages, NOT the gateway crashing.

**Evidence that debunked the loop:**
- ai-agency.log showed Spacebar gateways with uptimes of 5400s, 9600s, 10800s (3+ hours)
- GatewayRunner with real Discord connected → 100s+ survival
- GatewayRunner with no platforms (all background tasks running) → 100s+ survival
- `start_gateway()` via `asyncio.run()` → completed cleanly
- The only actual "death" was the `_acquire_platform_lock()` rejecting a duplicate instance (exit code 0, not 15)

**When you see "exit=15" in fleet-core logs, check:**
- Is the PID in the log the CURRENT batch's PID or the one that was just killed by `_kill_existing_gateway()`?
- Do gateway.log entries show the same bot *actually* being productive between restarts? (message processing, task completions)
- Is there a `process_registry: Recovered detached process` entry at startup? Those are old orphaned processes, not fresh gateway launches.
- Run a staged isolation test (see `systematic-debugging/references/windows-process-death-isolation.md`) to confirm the gateway itself survives before attempting any fix.

### What Exit=15 Means on Windows

- **Exit code 15** = `TerminateProcess(handle, 15)` was called by another process
- On Windows, `os.kill(pid, signal.SIGTERM)` (SIGTERM=15) maps to `TerminateProcess(handle, 15)`
- `psutil.Process.terminate()` also sends signal 15
- `taskkill /F` gives exit code 1 (not 15)
- `subprocess.Popen.kill()` gives exit code 9
- The dying process's cleanup handlers (atexit, try/finally, logging) do NOT fire — it's a hard kill

### Incremental Isolation Technique

When debugging a consistent process death, use this ladder to isolate the root cause:

1. **Noop dummy** — replace gateway with `time.sleep(5)` in a loop. If it lives, the death is in the gateway code itself, not external.
2. **Asyncio dummy** — replace gateway with `asyncio.sleep(5)` in an event loop. If it lives, the death is not from the asyncio event loop itself.
3. **Minimal dependency test** — run only the core library (e.g., raw discord.py + Spacebar WebSocket) without the application framework. If it lives, the death is in the application layer.
4. **Production code with noop core** — patch the application's main runner to skip its real work. Run and observe.

If steps 1-3 all live but step 4 dies, the death is inside the application's runtime code (not in external factors, not in the network library, not in the event loop).

### MemPalace ChromaDB SQLite Locking

**Problem:** Multiple concurrent gateways sharing the same MemPalace ChromaDB (`~/.mempalace/palace/chroma.sqlite3`) causes SQLite write contention. Only ONE SQLite writer is allowed at a time. Secondary gateways crash with hard termination.

**Fix:** Give each profile its own MemPalace palace directory:

1. Create per-profile palace dirs:
```bash
mkdir -p ~/.mempalace/palace-<profile-name>
```

2. Configure `mempalace-mcp` with `--palace` flag in each profile's `config.yaml`:
```yaml
mcp_servers:
  mempalace:
    command: mempalace-mcp
    args: ['--palace', 'C:/Users/<user>/.mempalace/palace-<profile-name>']
    timeout: 120
```

3. **YAML path quoting:** Use single quotes for Windows paths in YAML. Double quotes with backslashes trigger YAML escape sequence parsing (`\U` is interpreted as Unicode escape). Use forward slashes or single quotes:
   - ✅ `args: ['--palace', 'C:/Users/user/.mempalace/palace-profile']`
   - ❌ `args: ["--palace", "C:\Users\user\.mempalace\palace-profile"]` (triggers `ScannerError: expected escape sequence of 8 hexadecimal numbers`)

### Fleet-Core Death Loop Management

When fleet-core logs show "Died (exit=15)" with restarts in the 100-160 range:

- The fleet-core monitor calls `process.poll()` every 15 seconds
- When poll returns non-None (exit code 15), it logs the death and restarts
- The `_kill_existing_gateway()` method uses `psutil.Process.kill()` which sends SIGTERM=15 — this exit code can appear in logs even for gateways killed BY fleet-core itself during startup
- **The death loop is self-reinforcing:** fleet-core kills stale PIDs → those show exit=15 → fleet-core restarts → new instance dies → cycle continues
- **Key distinction:** gateways can be stable for 2+ hours when launched directly, but die when managed by fleet-core + certain additional configs (MemPalace, MCP server failures, etc.)

### Profiling the 55s Death

If the death is consistently at ~55s and is inside the GatewayRunner code:

- Check background tasks with timers around 55s:
  - Platform reconnect watcher (10s initial delay, 30s loop = fires at 10s, 40s, 70s)
  - Handoff watcher (every 2s)
  - Kanban dispatcher (every 60s)
  - Cron ticker (every 60s, not likely at 55s)
- Gateway-exit-diag.log shows `tag: "gateway.start"` but NO `tag: "gateway.exit_*"` entries — the process is hard-killed before Python cleanup
- The most reliable workaround is resilience in the fleet-core wrapper (fast restart), not root-causing the exact line in 20K lines of gateway code
