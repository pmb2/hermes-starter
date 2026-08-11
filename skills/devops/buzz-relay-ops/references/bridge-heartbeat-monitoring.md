# Bridge Heartbeat Monitoring

Detecting a hung Buzz Agent Bridge process — where the PID is alive but the
event loop has stalled and no messages are being processed.

## ⚠️ Doc–Code Gap (IMPORTANT)

**The `buzz_agent_bridge.py` code does NOT print heartbeat dots (`.`).**
The skill documentation historically described "heartbeat dots every 10 seconds"
as the liveness signal, but the code tracks `last_beat` in-memory only
(updated on each received message, never logged). Consequences:

- The log file is NOT a heartbeat channel — it only gains entries when the bridge
  (re)connects (`=== Buzz Agent Bridge started ===` and the `Bridge: N ch, ... EOSE`
  banner) or when it processes an @mention / channel-rep message.
- **A healthy, idle bridge has a stale log.** The event loop's `recv()` has a
  25-second timeout; between messages nothing is written. On a quiet channel set
  the log can legitimately sit at the startup banner for hours.
- Log mtime staleness is therefore a WEAK hung-bridge signal, not a definitive one.

Until the bridge code is changed to emit a periodic heartbeat (recommended fix:
add `log.info` on a timer thread, or log the recv() timeout each cycle), do NOT
treat a stale log alone as RED.

## The Problem (real hung-bridge case)

The watchdog (`buzz_watchdog.py`) checks process liveness via `OpenProcess` +
`GetExitCodeProcess`, which returns `STILL_ACTIVE (0x103)` for any running
process — even a hung one. A bridge whose event loop has deadlocked (stuck in
an AI call to OmniRoute, deadlocked WebSocket read, etc.) passes `is_alive()`
but processes no events.

## Detecting a Hung Bridge (corrected)

A single PID-alive + log-stale check is insufficient (false positives on idle
healthy bridges). Use the confirmation procedure:

1. **PID alive?** `tasklist /FI "PID eq $(cat .../logs/buzz_bridge.pid)"` —
   expect a `python.exe` row.
2. **Log check:** `tail -5 logs/buzz_bridge.log`. If the last entry is the
   startup banner AND the log mtime is old, the bridge *may* be idle-or-hung.
3. **Disambiguate with a live probe:** send a test @mention to a channel the
   bridge monitors (or a channel-rep channel), then re-check the log within 60s.
   - Healthy bridge → log gains a `@Alias #channel: ...` line.
   - Hung bridge → no new log line, mtime unchanged.
4. Only after the probe fails do you have evidence of a hung bridge.

### Health-check snippet (non-heartbeat, PID + process-cycle based)

```python
import ctypes, os, time
from pathlib import Path

LOG = Path(r"${USER_HOME}\AppData\Local\hermes\logs\buzz_bridge.log")
PIDFILE = Path(r"${USER_HOME}\AppData\Local\hermes\logs\buzz_bridge.pid")

def _is_alive(pid: int) -> bool:
    kernel32 = ctypes.windll.kernel32
    h = kernel32.OpenProcess(0x1000, False, pid)
    if not h:
        return False
    exit_code = ctypes.c_ulong()
    ok = kernel32.GetExitCodeProcess(h, ctypes.byref(exit_code))
    kernel32.CloseHandle(h)
    return bool(ok) and exit_code.value == 0x103

def pid_is_alive() -> bool:
    if not PIDFILE.exists():
        return False
    return _is_alive(int(PIDFILE.read_text().strip()))
```

This only confirms process existence. Use it together with the live-probe step
above for a real health determination.

## Improving the Watchdog (recommended fixes)

1. **Add a true heartbeat to the bridge code.** In `buzz_agent_bridge.py`, emit
   a periodic log line (e.g. a `threading.Timer` or a log on each recv() timeout)
   so a healthy bridge is provably alive. The internal `last_beat` variable
   should become a `log.debug`/`log.info` on the 25s-timeout branch.
2. **Watchdog hung detection.** Once heartbeats exist, `buzz_watchdog.py` can
   kill-and-respawn when `age > 5min`:
   ```python
   import os, subprocess, time
   age = time.time() - os.path.getmtime(LOG)
   if age > 300:
       print(f"[buzz-watchdog] Bridge PID {pid} log stale {int(age)}s — killing")
       subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, timeout=10)
   ```

## Pulse Check Integration

When running Aegis infrastructure pulses:

1. Read PID from `logs/buzz_bridge.pid`.
2. `tasklist /FI "PID eq <pid>"` — confirm a `python.exe` row exists.
3. `tail -5 logs/buzz_bridge.log` — note the last entry.
4. **Do NOT report RED on stale log alone.** If the last line is the startup
   banner, send a probe @mention and re-check for a processing line within 60s.
5. Report RED only if PID is dead OR the probe fails to produce a log line.