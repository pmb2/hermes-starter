# Stale WebDriverBiDiServer.json — Headless BiDi Silent Failure

## Symptom

Headless Firefox launches successfully (shows "You are running in headless mode") but **never binds the BiDi WebSocket on the requested port**. The process stays alive for 30-60 seconds then exits without error. No `WebDriver BiDi listening on ws://...` message appears.

Checking the port:
```
$ netstat -ano | grep 9239
(empty — port never opened)
```

## Root Cause

The profile directory contains a `WebDriverBiDiServer.json` from a PREVIOUS Firefox session that launched on a DIFFERENT port or protocol:

```json
{"ws_host": "127.0.0.1", "ws_port": 9223}
```

When Firefox starts, it reads this file and attempts to resume the BiDi server on the port from the previous session. If the new launch uses `--remote-debugging-port 9239`, there's a **port mismatch**. Firefox silently fails to bind the new port and never starts BiDi.

If the file points to the CORRECT port (9239), this issue does NOT occur. The problem only happens when the profile was previously used on a different port (e.g., testing on 9222 or 9223).

## Diagnosis

```bash
# Check for stale BiDi server state in the automation profile
cat "${HERMES_HOME}/firefox-profile/WebDriverBiDiServer.json"
# Expected: empty or CORRECT port
# If it shows a different port (e.g., 9223 instead of 9239):
#   → STALE — needs cleanup

# Check for stale Marionette port
cat "${HERMES_HOME}/firefox-profile/MarionetteActivePort"
# If exists, stale — needs cleanup
```

## Fix

Delete both state files before launching:

```bash
rm -f "${HERMES_HOME}/firefox-profile/WebDriverBiDiServer.json"
rm -f "${HERMES_HOME}/firefox-profile/MarionetteActivePort"
```

## Prevention

The `ensure_firefox()` function in `_firefox_bidi.py` and the `ingest-chatgpt-grok.sh` script both delete these files automatically before each headless launch. If you're launching Firefox MANUALLY (e.g., for testing), remember to clean these first.

Also clean stale `parent.lock` at the same time — it has the same blocking effect:

```bash
rm -f "${HERMES_HOME}/firefox-profile/parent.lock"
rm -f "${HERMES_HOME}/firefox-profile/WebDriverBiDiServer.json"
rm -f "${HERMES_HOME}/firefox-profile/MarionetteActivePort"
```

## Verification

After cleanup and relaunch, verify the BiDi port opened:

```bash
sleep 3 && netstat -ano | grep 9239
# Should show: LISTENING
```

Then test a WebSocket connection:

```python
import websockets, json, asyncio
async def test():
    ws = await websockets.connect('ws://127.0.0.1:9239/session')
    await ws.send(json.dumps({'id': 1, 'method': 'session.new', 'params': {'capabilities': {'alwaysMatch': {'webSocketUrl': True}}}}))
    resp = await asyncio.wait_for(ws.recv(), timeout=10)
    data = json.loads(resp)
    if 'sessionId' in data.get('result', {}):
        print(f"BiDi OK: {data['result']['sessionId'][:16]}...")
    await ws.close()
asyncio.run(test())
```
