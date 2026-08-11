# Headless GFX Crash Recovery

## The Problem
Tor Browser 151 headless + `--remote-debugging-port` causes a compositor crash:
```
RenderCompositorSWGL failed mapping default framebuffer, no dt
```
The browser process dies. The MCP server becomes unresponsive to browser tools.
Tor stays alive (circuits preserved, control port responds).

## Layer 1: Recovery Without Restart (commits `b5f3a62`+)
Two MCP tools handle this without restarting the MCP server:

1. **`tor_browser_health`** — check browser alive, tor alive, current URL
2. **`tor_recover_browser`** — re-launch just the browser (not tor)

### Recovery Workflow
```
tor_browser_health → browser_alive=false → tor_recover_browser → verify
```

### How It Works
`recover_browser()` on `TorBrowserDriver`:
1. Closes the old webdriver session (suppressing errors)
2. Re-launches geckodriver + Firefox via `launch_browser()` with the same config
3. Re-applies stealth JS + navigation callback
4. Tor is NEVER touched — all circuits preserved

### Cron Job Integration
The `7e8baae3c06d` cron job now calls health check → recovery → rotation → stealth
in sequence, so the MCP server self-heals after browser crashes.

## Layer 2: Full Server Auto-Restart (commits `4c408f7` + `a8c7eb5`)

When the browser crash happens DURING initial startup (before the MCP server begins serving), `tor_recover_browser` can't be called because no tools are registered yet. This is the most common failure mode — the browser GFX crashes during `webdriver.Firefox()`.

### The Silent Crash Problem
`webdriver.Firefox()` does NOT raise when the browser crashes during headless init. Selenium starts geckodriver, the browser process spawns and immediately dies from the GFX crash. Selenium considers this "session created" and returns a `webdriver.Firefox` object. The crash is detected ~9s later when stem's control socket dies (because the cascading browser crash kills the tor connection).

Before the fix, this resulted in a "clean shutdown" — no exception propagated, the server just exited normally.

### The Fix
**`server.py` (health check):** After the driver context manager enters, the server immediately probes:
```python
await asyncio.to_thread(
    lambda: driver.webdriver.execute_script("return navigator.userAgent")
)
```
If the browser is dead, this raises `BrowserLaunchError`. The exception propagates out of the `with TorBrowserDriver` block (the driver's `__exit__` does NOT suppress it).

**`cli.py` (retry loop):** `main()` wraps the server run in a crash loop:
```python
for attempt in range(max_restarts):
    try:
        asyncio.run(run_server(config, options))
        return  # clean shutdown
    except Exception as exc:
        delay = min(restart_delay * 2**attempt, 120)
        log.warning("Crash #%d: Restarting in %.1fs...", attempt+1, delay)
        time.sleep(delay)
```

### Crash Cycle Timeline
```
0s   → tor bootstrap starts
16s  → tor 100% bootstrapped, browser launch begins
26s  → browser GFX crash → stem SocketClosed → health check catches it
29s  → retry loop restarts (3s delay)
45s  → tor bootstrap starts again
61s  → tor 100% → browser launches → health check passes → server serves
```

### Config Flags
```
--max-restarts 10      # Give up after 10 consecutive crashes
--restart-delay 5.0    # First retry delay (doubles each attempt, capped at 120s)
```

### What This Fixes
| Before | After |
|--------|-------|
| Silent crash → no exception → server exits cleanly | Health check detects dead browser → raises → retry loop catches it |
| Hermes had to detect and restart the process | Server self-heals |
| Lost tor circuits on each crash | New tor daemon on each restart (fresh circuits) |
