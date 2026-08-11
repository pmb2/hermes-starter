# Firefox BiDi Bridge Diagnostics (registered-but-blind)

Real case (Weaver pulse 2026-08-08): `ultimate-firefox-mcp` tools were registered in-session
for the first time ever, but `list_tabs` failed with
`Cannot detect Firefox: No Firefox found on BiDi:9239 or CDP:9239` (`INTERNAL_ERROR`).
The bridge was connected to Hermes but blind — a port mismatch, not a crash.

## Symptom

- Bridge MCP tools appear in the tool catalog (`tool_search` finds `mcp__ultimate_firefox_mcp__*`)
- First read-only call errors: `No Firefox found on BiDi:<cfg-port> or CDP:<cfg-port>`
- No crash, no connection error — the server is up, it just can't see the browser

## Diagnosis ladder

```bash
# 1. Confirm registration ≠ function: call a read-only tool
#    mcp__ultimate_firefox_mcp__list_tabs  →  the error names the port it's probing

# 2. Find the real listener (compare against the port in the error)
netstat -ano | grep LISTENING | grep -E ":(9223|9239)\s"

# 3. Identify the process owning the live port
powershell -NoProfile -Command "Get-Process -Id <pid> | Select-Object Id,ProcessName,Path | Format-List"

# 4. Read the browser's actual launch args — this is the smoking gun
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"ProcessId=<pid>\" | Select-Object CommandLine | Format-List"
# Expect: firefox.exe --headless --no-remote --profile <hermes-profile> --remote-debugging-port 9223

# 5. Enumerate ALL headless instances (duplicate check — same profile+port = lock risk)
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='firefox.exe'\" | Where-Object { \$_.CommandLine -notmatch 'contentproc' } | Select-Object ProcessId,CommandLine | Format-List"

# 6. Compare against the config's expected port
grep -A6 -iE "firefox|bidi" ~/AppData/Local/hermes/config.yaml   # args: --port <N>, PIM_BIDI_PORT
```

## BiDi endpoint liveness semantics (avoid false negatives)

| Probe | Response | Meaning |
|-------|----------|---------|
| `POST /session` (JSON body) | `400 The handshake request must use GET method` | **ALIVE** — spec-correct WebDriver BiDi (the real handshake is a GET WebSocket-upgrade) |
| `GET /session` with `Accept: text/websocket` | `400` | endpoint alive; needs proper WS upgrade headers |
| `GET /json/version` | `404` HTML page | BiDi-only, NOT CDP — do not interpret as dead |
| Connection refused | — | truly down |

## Fix

1. Align the bridge: change `--port 9239` → the live port (or relaunch the browser on the
   configured port) in the MCP server's config args AND any `*_BIDI_PORT` env vars
   (e.g., `PIM_BIDI_PORT`).
2. Kill duplicate headless instances on the same profile/port (`taskkill //F //PID <dup>`)
   — two instances with one `--remote-debugging-port` means only one binds; the loser holds
   the profile lock and can break the winner.
3. Restart Hermes so the stdio bridge re-detects the browser.

## Related gotcha (same workflow)

Pulse instructions may tell you to run `python ${MY_REPOS}/.../script.py` from git-bash.
MSYS path translation breaks this — Windows Python receives `E:\e\yourdata\...` and fails
`can't open file`. Always invoke with the literal Windows path:
`python "${MY_REPOS}/.../script.py"`.

## Resolution epilogue (2026-08-10/11) — structural root cause + VERIFIED WORKING

The port mismatch was only half the story. Even with ports aligned, the bridge could never
detect Firefox because of two code-level bugs in `ultimate-firefox-mcp` itself:

1. **websockets 15.0.1 API break**: `_check_bidi` called
   `websockets.connect(..., timeout=)` but ws15 renamed the kwarg to `open_timeout` →
   TypeError → the check silently returned False → "Cannot detect Firefox" forever.
   The CDP fallback was ALSO dead because Firefox 129+ removed `/json/version`.
   Fix: `websockets.connect(..., open_timeout=timeout)` (main.py).
2. **`_flatten` NoneType crash**: Firefox returns `children: null` in the tree; the code
   used `ctx.get("children", [])`, which yields `None` (the default only fires when the
   KEY is absent, not when its value is null) → `for child in None` crash in the
   flatten helper. Fix: `(ctx.get("children") or [])` (tools/__init__.py).

After fixing both, relaunch a fresh headless Firefox (killed-bridge session-slot
exhaustion can leave the old browser unusable) and re-verify.

**Canonical end-to-end proof (first-ever full round-trip, Aug 11 2026):**
```
1. mcp__ultimate_firefox_mcp__list_tabs        → baseline (about:home context)
2. mcp__ultimate_firefox_mcp__navigate
     {"url": "https://example.com", "wait": "complete", "timeout": 20}
                                               → success + navigation_id
3. mcp__ultimate_firefox_mcp__list_tabs        → tab URL now https://example.com/
```
If those three calls round-trip, the bridge is production-ready for browse/QA workflows.
Note: `curl http://localhost:9223` → 000 is NOT a down signal — BiDi is a WebSocket
GET-upgrade, not HTTP. The bridge's liveness check IS the tool call itself.

Diagnostic summary across the full incident (Aug 8 → Aug 11): registered tools ≠
functional bridge (port mismatch) ≠ code-correct bridge (websockets 15 + None-flatten).
After a structural fix, always re-verify with the 3-call round-trip, not just
`list_tabs` returning success.
