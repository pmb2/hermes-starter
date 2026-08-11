# Geckodriver WebDriver HTTP API Fallback (verified 2026-08-11)

When the Ultimate Firefox MCP cannot connect (Firefox 153+ `--remote-debugging-port`
serves `httpd.js` instead of CDP/BiDi), geckodriver's **plain HTTP WebDriver API**
is a working, dependency-free fallback — no selenium install needed. Verified live
against Firefox 153.0.3 + geckodriver v0.37.1 (npm-installed wrapper).

## 1. Start geckodriver

```bash
geckodriver --port 4444 --log fatal 2>&1 &
```

- npm-installed wrapper: `~/AppData/Roaming/npm/geckodriver`
- Health check: `curl -s http://127.0.0.1:4444/status` → `{"value":{"ready":true}}`
- **Pitfall:** the wrapper takes `--log fatal` (NOT `--log-level fatal` — that
  errors with "unexpected argument" and exits 64). `--port` conflicts when a
  previous instance lingers → error 10048; kill stale geckodriver first.

## 2. Create a session

```bash
curl -s -X POST http://127.0.0.1:4444/session \
  -H "Content-Type: application/json" \
  -d '{"capabilities":{"alwaysMatch":{"browserName":"firefox"}}}'
```

Returns `{"value":{"sessionId":"<uuid>","capabilities":{...}}}`. Firefox version
comes back as e.g. `153.0.3`.

Optional prefs (stealth-ish, matches the MCP profile):
```json
{"capabilities":{"alwaysMatch":{"browserName":"firefox","moz:firefoxOptions":{
  "args":["--disable-gpu"],
  "prefs":{"dom.webdriver.enabled":false,"useAutomationExtension":false,
           "general.useragent.override":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0"}}}}}
```

## 3. Navigate + inspect

```bash
SID=<sessionId>

# Navigate (POST, not GET)
curl -s -X POST http://127.0.0.1:4444/session/$SID/url \
  -H "Content-Type: application/json" -d '{"url":"https://example.com"}'

# Title
curl -s http://127.0.0.1:4444/session/$SID/title

# Page source (first N chars)
curl -s http://127.0.0.1:4444/session/$SID/source
```

## 4. Cleanup

```bash
curl -s -X DELETE http://127.0.0.1:4444/session/$SID
taskkill //F //IM geckodriver.exe 2>/dev/null; taskkill //F //IM firefox.exe 2>/dev/null
```

## Notes / gotchas

- **No MCP tools needed** — plain curl or Python `requests` against the WebDriver
  REST API. Use this from `terminal`/`execute_code` when browser MCP is down.
- Session is **stateless per POST** — re-create if the session dies.
- This gets you navigation + DOM inspection. For form fill/click, use the standard
  WebDriver element endpoints (`/element` + POST, or drive via the MCP once
  reconnected).
- Firefox spawned by geckodriver is a fresh ephemeral profile — **saved logins
  (500+ in the operator's main profile) are NOT available.** For logged-in sessions,
  prefer fixing the MCP path or `computer_use` + Chrome with the real profile.
