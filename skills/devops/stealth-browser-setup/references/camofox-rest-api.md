# Camofox REST API Reference

Camofox wraps Camoufox (Firefox fork with C++ anti-detection) behind a REST API on port 9377. All endpoints live under `http://localhost:9377`.

## Session Model

Camofox uses a **userId** + **sessionKey** model:
- `userId` = the person/agent (e.g. "the operator")
- `sessionKey` = an isolated tab group within that user's session
- Tabs created with the same userId share cookies and auth state

## Core API Patterns

### Health Check
```bash
curl -s http://localhost:9377/health
```
Returns engine name, browser state, active tab/session counts.

### Create a Tab & Navigate
```python
import json, urllib.request

TAB_ID = json.loads(urllib.request.urlopen(urllib.request.Request(
    'http://localhost:9377/tabs',
    data=json.dumps({
        'userId': 'the operator',
        'sessionKey': 'my-session',
        'url': 'https://example.com'
    }).encode(),
    headers={'Content-Type':'application/json'},
    method='POST'
), timeout=15).read()).get('tabId')
```

### Navigate an Existing Tab
```python
req = urllib.request.Request(
    f'http://localhost:9377/tabs/{TAB_ID}/navigate',
    data=json.dumps({'userId':'the operator','url':'https://next-url.com'}).encode(),
    headers={'Content-Type':'application/json'},
    method='POST'
)
resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
```

### Get Page Snapshot (accessibility tree with element refs)
```python
snap = json.loads(urllib.request.urlopen(
    f'http://localhost:9377/tabs/{TAB_ID}/snapshot?userId=the operator',
    timeout=15
).read())
snap_text = snap.get('snapshot', '')
# snap['refsCount'] = number of interactive elements found
# snap['truncated'] = True if page was too large
```

### Click Element by Ref
```python
req = urllib.request.Request(
    f'http://localhost:9377/tabs/{TAB_ID}/click',
    data=json.dumps({'userId':'the operator', 'ref': 'e25'}).encode(),
    headers={'Content-Type':'application/json'},
    method='POST'
)
urllib.request.urlopen(req, timeout=15)
```

### Type into Element
```python
req = urllib.request.Request(
    f'http://localhost:9377/tabs/{TAB_ID}/type',
    data=json.dumps({
        'userId':'the operator',
        'ref': 'e3',
        'text': 'my search query',
        'clear': True,     # clear field first
        'submit': False,   # press Enter after typing
    }).encode(),
    headers={'Content-Type':'application/json'},
    method='POST'
)
urllib.request.urlopen(req, timeout=15)
```

### Press Keyboard Key
```python
req = urllib.request.Request(
    f'http://localhost:9377/tabs/{TAB_ID}/press',
    data=json.dumps({'userId':'the operator', 'key': 'Enter'}).encode(),
    headers={'Content-Type':'application/json'},
    method='POST'
)
urllib.request.urlopen(req, timeout=15)
```

### Scroll
```python
req = urllib.request.Request(
    f'http://localhost:9377/tabs/{TAB_ID}/scroll',
    data=json.dumps({'userId':'the operator', 'direction': 'down', 'amount': 500}).encode(),
    headers={'Content-Type':'application/json'},
    method='POST'
)
urllib.request.urlopen(req, timeout=5)
```

### Evaluate JavaScript
```python
req = urllib.request.Request(
    f'http://localhost:9377/tabs/{TAB_ID}/evaluate',
    data=json.dumps({
        'userId':'the operator',
        'expression': 'document.title + " | " + document.location.href'
    }).encode(),
    headers={'Content-Type':'application/json'},
    method='POST'
)
resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
# resp['result'] contains JSON-stringified result of the expression
result = json.loads(resp.get('result', '""'))
```

### Take Screenshot
```python
screenshot = json.loads(urllib.request.urlopen(
    f'http://localhost:9377/tabs/{TAB_ID}/screenshot?userId=the operator',
    timeout=15
).read())
# screenshot['screenshot']['data'] = base64-encoded PNG
# screenshot['screenshot']['mimeType'] = 'image/png'
```

### Import Cookies into Session
```python
data = json.dumps({'cookies': [{
    'name': 'session',
    'value': 'abc123',
    'domain': '.example.com',
    'path': '/',
    'expires': -1,           # -1 = session cookie, or unix timestamp
    'httpOnly': True,
    'secure': True,
    'sameSite': 'Lax',       # Strict, Lax, or None
}]}).encode()
req = urllib.request.Request(
    f'http://localhost:9377/sessions/the operator/cookies',
    data=data,
    headers={'Content-Type':'application/json'},
    method='POST'
)
result = json.loads(urllib.request.urlopen(req, timeout=15).read())
# result['count'] = number of cookies imported
```

### Close Tab
```python
urllib.request.urlopen(urllib.request.Request(
    f'http://localhost:9377/tabs/{TAB_ID}?userId=the operator',
    method='DELETE'
), timeout=5)
```

### Destroy Full Session
```python
urllib.request.urlopen(urllib.request.Request(
    f'http://localhost:9377/sessions/the operator',
    method='DELETE'
), timeout=5)
```

## Timings

- Tab creation: ~1-2s
- Navigation + load: 1-5s (depends on page)
- Scroll + snapshot: ~0.5-1s
- Click/type/press: ~0.5s
- Cookie import (100 cookies): ~1s

## Limitations

- Tab URLs must be http/https (about:, data:, file: are blocked)
- max 500 cookies per POST to `/sessions/{userId}/cookies`
- Cookie expiry expects unix timestamps in **seconds** (Firefox stores in ms — divide by 1000)
- Large batch imports may hit 413 PayloadTooLarge — use batches of 100

## Firefox Cookie Format Conversion

Firefox stores cookie expiry in **milliseconds** (e.g. `1814631932798`). Camofox expects **seconds**. Convert:
```python
cookie['expires'] = -1 if row['expiry'] <= 0 else int(row['expiry'] / 1000)
```
Firefox value `0` = session cookie → send as `-1`.
