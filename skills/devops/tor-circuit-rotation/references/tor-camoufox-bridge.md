# tor_camoufox_bridge MCP Server

Bridge MCP server that wraps both Tor Browser and Camoufox stealth browser under one interface.

## Tool Prefix

All tools are exposed as `mcp_tor_camoufox_bridge_*`.

## Available Tools

| Tool | Description |
|------|-------------|
| `bridge_status()` | Report active engine (tor/camoufox) and status of both |
| `bridge_switch(engine)` | Switch active engine |
| `browser_navigate(url)` | Navigate Tor Browser to URL |
| `browser_snapshot()` | Request accessibility snapshot (acknowledgment only — no content returned) |
| `browser_new_identity()` | Send NEWNYM for circuit rotation |
| `browser_click(ref)` | Click element in Tor Browser |
| `browser_type(ref, text)` | Type text into element |
| `camoufox_start()` | Start Camoufox browser engine |
| `camoufox_stop()` | Stop Camoufox browser engine |
| `camoufox_status()` | Check if Camoufox is running |
| `camoufox_navigate(url)` | Navigate Camoufox to URL |
| `camoufox_snapshot()` | Get snapshot from Camoufox |
| `camoufox_screenshot()` | Take screenshot from Camoufox |

## Known Behaviors

### Snapshot Returns Acknowledgment Only
The `browser_snapshot()` tool returns the string `"Snapshot requested from Tor Browser"` as a confirmation, not actual page content or accessibility tree data. Do not rely on it for extracting page text.

### Camoufox Server May Be Down
`camoufox_start()` may fail with `WinError 10061` (connection refused) if the Camoufox backend server is not running. This is expected on cron sessions.

### Tor Ports (Windows, PID 5804 observed)
| Port | Protocol | Purpose |
|------|----------|---------|
| 9250 | SOCKS5 | Tor SOCKS proxy for HTTP/S traffic |
| 9251 | Raw TCP | Tor control protocol (no SOCKS, no initial banner) |

Both ports are owned by `tor.exe`.

### Tor Control Protocol Authentication
The control port uses **cookie authentication**. Cookie file location:
`C:\Users\<USER>\AppData\Local\Temp\torbrowser-driver-*\tor-data\control_auth_cookie`
The cookie path changes each time the bridge server restarts (subdirectory is random).

Authentication sequence:
```
→ PROTOCOLINFO
← 250-PROTOCOLINFO 1
← 250-AUTH METHODS=COOKIE,SAFECOOKIE COOKIEFILE="..."
→ AUTHENTICATE <hex_cookie>
← 250 OK
→ <command>
```

### Useful Tor Control Commands
```
SIGNAL NEWNYM                    — Request new circuits
GETINFO circuit-status           — List all circuits with relay paths
GETINFO status/circuit-established — 1 if circuits are built
GETINFO address                  — Detected public address
GETINFO version                  — Tor version
GETINFO uptime                   — Seconds since tor started
```

### Exit IP Verification via SOCKS5
The SOCKS5 port 9250 works with curl. Three reliable endpoints:

**JSON API (preferred — no HTML parsing):**
```bash
curl --socks5-hostname 127.0.0.1:9250 -s https://check.torproject.org/api/ip
# Returns: {"IsTor":true,"IP":"192.42.116.111"}
```

**Plain text (fast):**
```bash
curl --socks5-hostname 127.0.0.1:9250 -s https://api.ipify.org
curl --socks5-hostname 127.0.0.1:9250 -s https://icanhazip.com
```

**HTML page (may 403 from some exit nodes):**
```bash
curl --socks5-hostname 127.0.0.1:9250 https://check.torproject.org/
```
Grep for exit IP: `grep -E 'Your IP address|strong' | sed 's/<[^>]*>//g'`

### Circuit Rotation Verification
After `SIGNAL NEWNYM`, wait ~15-25 seconds for new circuits to build. Verify by:
1. Checking exit IP via SOCKS5 proxy (changed?)
2. Checking `GETINFO circuit-status` for new circuit IDs and closed old ones
3. Counting BUILT circuits (expect count to drop initially, then rebuild)

### Non-Tor IP
```bash
curl -s https://ipinfo.io/ip
```
This goes through the regular internet, not Tor.

## Pitfalls

### Dual tor.exe Processes
There may be TWO tor.exe processes. Check with:
```bash
netstat -ano | grep LISTENING | grep -E "9250|9251|9151"
```
- **Primary (active):** PID with `-f -` in its command line. SOCKS on `:9250`,
  control on `:9251`. This is the one to use.
- **Secondary (DisableNetwork=1):** Started from torrc, control on `:9151`. Its
  `__SocksPort` (`:9250`) is already held by the primary, so enabling the network
  on this process fails. Ignore it and work with the primary on port 9251.

### `GETINFO circuit-count` Unrecognised
Tor 0.4.9.9 does not recognise `GETINFO circuit-count`. Parse `GETINFO circuit-status`:
```bash
curl -s ... | grep ' BUILT ' | wc -l
```
