# Protocol Auto-Detection Sequence

The unified `ultimate-firefox-mcp` auto-detects which protocol Firefox is
exposing. This is the detection flow:

## Detection Logic (in `main.py detect_protocol()`)

```
1. Check preferred_protocol
   ├── "bidi" → try BiDi (9223) first, fall back to CDP (9222)
   ├── "cdp"  → try CDP (9222) first, fall back to BiDi (9223)
   └── "auto" (default) → BiDi first (modern protocol)

2. For each protocol check:
   ├── TCP port scan (socket.create_connection, 3s timeout)
   └── Protocol-specific probe:
       ├── BiDi: WebSocket connect to ws://host:port/session
       └── CDP:  HTTP GET http://host:port/json/version

3. Return {protocol, port, error}
```

## Port Conventions

| Port | Protocol | Server / Tool |
|------|----------|---------------|
| 9222 | CDP (default) | Firefox `--remote-debugging-port 9222` |
| 9223 | BiDi (default) | Firefox `--remote-debugging-port 9223` (BiDi mode) |
| 2828 | Marionette | Legacy firefox-devtools MCP (deprecated) |

## Behavior Per Protocol

### BiDi Mode (preferred)
- Full WebDriver BiDi protocol (Firefox 136+)
- `StealthEngine.apply()` injects 22 preload scripts
- `HumanInputEngine` for realistic keystroke/mouse timing
- 50+ tools including network interception, PDF, cookies, events

### CDP Mode (fallback)
- Chrome DevTools Protocol (older, being deprecated in Firefox)
- `inject_stealth()` runs on every page navigation + tab attach
- Basic tool set (navigation, DOM, screenshots, forms, cookies)
- Limited network interception support

## CLI Override

```bash
# Explicit protocol selection
ultimate-firefox-mcp --protocol bidi --port 9223
ultimate-firefox-mcp --protocol cdp  --port 9222

# Auto-detect (default)
ultimate-firefox-mcp
```

## Hermes Config

```yaml
  ultimate-firefox-mcp:
    args:
    - -m
    - ultimate_firefox_mcp.main
    - '--protocol'
    - 'auto'
    command: python
    timeout: 300
    workdir: ${USER_HOME}\ultimate-firefox-mcp
```
