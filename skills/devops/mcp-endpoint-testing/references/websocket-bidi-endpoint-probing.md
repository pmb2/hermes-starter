# WebSocket/BiDi Endpoint Probing — ultimate-firefox-mcp bridge case study (Aug 2026)

Real-world diagnosis chain: the Firefox BiDi bridge reported "Cannot detect Firefox: No Firefox found on BiDi:9239 or CDP:9239" for weeks, even after the port was aligned. Three stacked root causes, each discovered by moving the error forward one stage.

## Root cause 1: websockets 15 `connect()` API break (silent detection failure)

- Bridge `_check_bidi` called `websockets.connect("ws://127.0.0.1:9239/session", timeout=T)`.
- websockets 14.0 renamed the open-handshake kwarg `timeout` → `open_timeout`; 15.0 removed the old name.
- The legacy kwarg falls into `**kwargs` (client.py line ~325 `**kwargs: Any`) → `loop.create_connection(factory, **kwargs)` → `TypeError: BaseEventLoop.create_connection() got an unexpected keyword argument 'timeout'`.
- The call sits in `try/except Exception: return False` → detection always False → "Cannot detect Firefox" forever.
- CDP fallback was ALSO dead: Firefox 129+ removed CDP entirely; `GET /json/version` → 404.
- Fix: `open_timeout=timeout` in `_check_bidi` (ultimate_firefox_mcp/main.py).
- Verification: direct probe with `open_timeout` → "BIDI CONNECT OK"; with `timeout` → TypeError. See SKILL.md probe snippet.

## Root cause 2: `children: null` flatten crash

- After detection passed, `list_tabs` failed with `'NoneType' object is not iterable`.
- Firefox `browsingContext.getTree` returns `"children": null` (key present, null value) for leaf contexts — confirmed in live response: `{"children": null, "context": "...", "url": "about:home", ...}`.
- `_flatten` used `ctx.get("children", [])` → returns `None` (the default only applies when the key is MISSING) → `for child in None` → TypeError.
- Fix: `for child in (ctx.get("children") or []):` in `_flatten` (tools/__init__.py). Note browser.py's `_flatten_contexts` was already safe (`children = ctx.get("children", []); if children:` guard).

## Root cause 3: BiDi session-slot exhaustion after hard-killing the client

- After `taskkill /F` on the bridge, the next `session.new` failed: `BiDi command 'session.new' (id=1) failed: session not created - Maximum number of active sessions`.
- Firefox's remote agent holds ONE active BiDi session per browser process; a hard-killed client never released the slot (WS close without `session.end`).
- Fix: relaunch a fresh browser — `python -m ultimate_firefox_mcp.launcher --port 9239 --headless` from the project dir. Its `kill_orphans(port)` clears the port first. The launcher CLI crashes at `json.dumps(result)` (non-serializable Popen handle in the result dict) — cosmetic; the browser launches and binds the port anyway.

## Verification path (what actually proved each fix)

1. `netstat -ano | grep LISTENING` — port 9239 owned by firefox.exe PID 93172, launched `--remote-debugging-port 9239 --no-remote --disable-gpu --new-instance about:blank`.
2. `curl http://localhost:9239/` → "httpd.js is up and serving requests!" — the BiDi remote agent's own banner (built on Mozilla httpd.js). This is the ALIVE signal; NOT a foreign server.
3. `curl http://localhost:9239/json/version` → 404 — CDP gone.
4. `curl http://localhost:9239/session` → 400 — endpoint present, needs WS upgrade.
5. Python `websockets.connect(..., open_timeout=8)` → handshake OK. With `timeout=8` → TypeError (root cause 1 reproduced).
6. Kill bridge → Hermes MCP client auto-respawned it (new PID) → error moved past detection to the flatten crash (root cause 2).
7. Patch flatten → error moved to session.new rejection (root cause 3).
8. Relaunch fresh Firefox → `list_tabs` returned success with the `about:home` context — first working bridge call ever.

## Operational patterns worth keeping

- **Kill-and-respawn hot-loads patches**: patch the server source, `taskkill /F /PID <server>`, Hermes' MCP client auto-reconnects (exponential backoff) and spawns the patched instance — no Hermes restart required. The error message changing after respawn is the signal the new code is live.
- **Duplicate MCP server instances**: check for both venv and hermes-runtime pythons hosting the same server: `Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -like '*<server>*'}`. Kill all copies; Hermes respawns a single one.
- **Error-progression debugging**: each fix moved the failure one stage further (detection → flatten → session) — a clean way to confirm root causes independently.
