# Firefox Stealth OPS — Command Reference

## Quick Launches

### Firefox (Tier 1 — accounts)
```bash
# Via MCP: auto-launched by ultimate-firefox-mcp on port 9239
# Manual:
python -m ultimate_firefox_mcp.launcher --firefox --opsec-check
```

### Camoufox (Tier 2 — anti-detection)
```bash
# 1. Launch Camoufox
"${USER_HOME}/camoufox/camoufox.exe" --remote-debugging-port 9238 --no-remote

# 2. Unified launcher (with proxy):
python -m ultimate_firefox_mcp.launcher --camoufox --proxy socks5://127.0.0.1:9050 --opsec-check
```

### Tor Browser (Tier 3 — anonymity)
```bash
# Via MCP: auto-managed by tor-browser-mcp on ports 9250/9251
# tor + browser launched together by MCP server
```

## OPSEC Verification

```bash
# Full OPSEC report on a running browser:
python -c "
from ultimate_firefox_mcp.opsec import full_opsec_report
r = full_opsec_report(cdp_port=9239)
print(f'Stealth: {r[\"stealth_summary\"]}')
print(f'WebRTC leak: {r[\"webrtc\"]}')
print(f'All clear: {r[\"overall\"][\"all_clear\"]}')
"
```

## Tor MCP Tools Quick Reference

```bash
# Rotate circuit + verify
# MCP: mcp_tor_browser_mcp_tor_rotate_identity(post_signal_sleep=15)

# Check browser health
# MCP: mcp_tor_browser_mcp_tor_browser_health
# Returns: browser_alive, tor_alive, current_url

# Recover crashed browser (tor stays up)
# MCP: mcp_tor_browser_mcp_tor_recover_browser
# Returns: success, browser_alive

# Apply stealth
# MCP: mcp_tor_browser_mcp_tor_apply_stealth(xul_patch=False, inject_js=True)

# Verify stealth (8+ checks)
# MCP: mcp_tor_browser_mcp_tor_verify_stealth
# Returns: pass_count, total_checks, per-check results
```

## Config.yaml MCP Entries

```yaml
mcp:
  ultimate-firefox-mcp:     # Tier 1: Firefox w/ accounts (port 9239)
    args: [-m, ultimate_firefox_mcp.main, --protocol, auto, --port, '9239']
    command: python
    timeout: 300
    workdir: ${USER_HOME}\ultimate-firefox-mcp

  camoufox-mcp:              # Tier 2: Camoufox (port 9238)
    args: [-m, ultimate_firefox_mcp.main, --protocol, auto, --port, '9238']
    command: python
    timeout: 300
    workdir: ${USER_HOME}\ultimate-firefox-mcp

  tor-browser-mcp:           # Tier 3: Tor (ports 9250/9251)
    args: [-m, torbrowser_mcp, --tbb-root, ${USER_HOME}/TorBrowser,
           --output-dir, ${USER_HOME}/tor-browser-outputs,
           --geckodriver-path, ${USER_HOME}/tor-browser-mcp/bin/geckodriver.exe,
           --headless]
    command: ${USER_HOME}/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe
    timeout: 300
    workdir: ${MY_REPOS}/Documents/github/tor-browser-mcp
```
