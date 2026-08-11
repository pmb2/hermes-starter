# Headless GFX Crash — tor-browser-mcp Context

## Symptoms

- MCP server `tor_status` returns `{"running": false, "error": ""}` (tor dead)
- OR MCP tools time out after 300s (browser dead but tor alive)
- geckodriver.log contains:
  ```
  RenderCompositorSWGL failed mapping default framebuffer, no dt
  ```
- Tor bootstraps 100% and circuit establishes normally (15-20s)
- Browser launch succeeds (webdriver session created)
- 9-60s later the browser process exits, killing the stem controller connection
- Multiple firefox.exe orphans accumulate (observed: 83+ over time)

## Observed Timing (the operator's system)

| Condition | Time-to-crash | Notes |
|-----------|---------------|-------|
| Stock xul.dll, headless | ~9s | Control socket dies, browser exits immediately |
| Patched xul.dll, headless | ~3-5min | Extended window, but crash still inevitable |
| Headed mode (not headless) | Unknown | Not tested on this system |

## Detecting in the Field

```bash
# 1. Check if tor is alive
python -c "
from stem.control import Controller
c = Controller.from_port(port=9251)
c.authenticate()
print('Tor alive:', c.is_alive())
print('Circuits:', len(c.get_circuits()))
c.close()
"

# 2. Check if browser/webdriver is alive
# If mcp_tor_browser_mcp_browser_navigate times out, browser is dead
# If mcp_tor_browser_mcp_tor_status returns running=true, tor is alive

# 3. Count firefox orphans
MSYS_NO_PATHCONV=1 tasklist.exe /FI "IMAGENAME eq firefox.exe" /FO CSV /NH 2>/dev/null | wc -l
```

## Workaround: Tor-Only Operations

When the browser is dead but tor is alive, these MCP tools still work:
- `tor_status` — check bootstrap, circuit count
- `tor_new_identity` / `tor_rotate_identity` — rotate circuits
- `tor_circuit_status` — list circuits
- `tor_exit_node_info` — check exit node
- `tor_circuit_health` — uptime, traffic, health metrics
- `tor_check_identity` — **NEEDS** browser (will time out)

These MCP tools require the browser:
- All `browser_*` tools
- `tor_check_identity` (navigates check.torproject.org)
- `tor_apply_stealth` (injects JS into page)
- `tor_verify_stealth` (evaluates JS in page)

## Recovery Steps

```bash
# Full clean restart cycle:
# 1. Kill ALL MCP + tor + firefox processes
MSYS_NO_PATHCONV=1 taskkill.exe /F /IM tor.exe
MSYS_NO_PATHCONV=1 taskkill.exe /F /IM firefox.exe  
MSYS_NO_PATHCONV=1 taskkill.exe /F /IM geckodriver.exe

# 2. Find and kill torbrowser-mcp process
powershell -Command "Get-CimInstance Win32_Process -Filter \"CommandLine like '%torbrowser_mcp%'\" | Select-Object ProcessId | ForEach-Object { taskkill /F /PID \$_.ProcessId }"

# 3. Clean stale session dirs
rm -rf /tmp/torbrowser-driver-*/

# 4. Wait for Hermes to restart (5-15s)
# 5. Test: mcp_tor_browser_mcp_tor_status should return running=true
```

## Root Cause Hypothesis

Firefox 151's headless mode + `--remote-debugging-port` triggers a GPU
compositor initialization path that fails on systems without a D3D device
or with software rendering. The SWGL (software WebGL) fallback fails with
"failed mapping default framebuffer."

The xul.dll patch removes `navigator.webdriver` but does NOT touch any
compositor or GPU code, so it doesn't fix the underlying crash — it only
extends the timing because the patched binary changes Firefox's startup
initialization order slightly.

See `firefox-stealth-automation` skill's `references/firefox-151-gfx-crash.md`
for deeper research on this class of crash.
