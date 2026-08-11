# BiDi OPSEC Fallback & WEBDRIVER_BIDI Patch

## Problem: OPSEC check_fingerprint fails on Camoufox

The launcher's `check_fingerprint(port)` function in `ultimate_firefox_mcp/launcher.py`
only tried `http://127.0.0.1:{port}/json/version` (CDP endpoint). Camoufox uses
WebDriver BiDi protocol, not CDP — the endpoint returns HTTP 404.

## Fix: WebSocket upgrade handshake fallback (commit 909f608)

Added after the CDP try/except:

```python
# Try BiDi WebSocket
s = socket.socket()
s.settimeout(3)
s.connect(("127.0.0.1", port))
s.send(b"GET /session HTTP/1.1\r\nHost: 127.0.0.1:" + str(port).encode() +
       b"\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
       b"Sec-WebSocket-Key: dGVzdA==\r\nSec-WebSocket-Version: 13\r\n\r\n")
resp = s.recv(1024)
s.close()
if b"101" in resp:
    return {"connected": True, "protocol": "bidi", ...}
```

This detects BiDi by sending an HTTP Upgrade request to the `/session` endpoint.
The `101 Switching Protocols` response confirms the port speaks BiDi WebSocket.

## Problem: xul.dll patch missed WEBDRIVER_BIDI

The initial xul.dll patch only replaced `b"webdriver"` (9 bytes, 3 occurrences in
xul.dll). A fourth string `b"WEBDRIVER_BIDI"` (14 bytes, the Gecko internal
constant `BLOCKING_REASON_WEBDRIVER_BIDI`) was missed because it's uppercase
and not a JavaScript-level property.

## Discovery

Binary scan via Python `data.lower().count(b"webdriver")` found 1 remaining
instance in each xul.dll after the initial patch. Context around the match:
```
...EST"BLOCKING_REASON_WEBDRIVER_BIDI"OPENER_POLICY_...
```

## Fix (mmap patch, applied June 21, 2026)

```python
import mmap
with open(path, 'r+b') as f:
    with mmap.mmap(f.fileno(), 0) as mm:
        pos = 0
        while (pos := mm.find(b'WEBDRIVER_BIDI', pos)) != -1:
            mm[pos:pos+14] = b'W3BDRVR_BIDI__'
            pos += 14
```

## Affected binaries

All three were patched:
- `${USER_HOME}\TorBrowser\Browser\xul.dll` (162MB) — 1 WEBDRIVER_BIDI occurrence
- `${USER_HOME}\camoufox\xul.dll` (152MB) — 1 WEBDRIVER_BIDI occurrence
- `${USER_HOME}\firefox-portable\xul.dll` (172MB) — 1 WEBDRIVER_BIDI occurrence

All have `xul.dll.bak2` backups preserving the pre-patch state.

## Verification method (avoids MemoryError on 150MB+ files)

```python
import os, re
path = r'${USER_HOME}\TorBrowser\Browser\xul.dll'
with open(path, 'rb') as f:
    head = f.read(5000000)    # first 5MB
    f.seek(-5000000, 2)
    tail = f.read()           # last 5MB
total = len(re.findall(b'webdriver', head, re.IGNORECASE)) + \
        len(re.findall(b'webdriver', tail, re.IGNORECASE))
print(f'{path}: {total} remaining')
```
