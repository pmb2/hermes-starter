# Messages Endpoint `limit` Bug Fix

## Error Pattern

Fermi client returns 500 when loading a channel:

```
XHR GET https://.../api/v9/channels/<discord-channel-id>/messages?limit=100
HTTP/2 500

{ "code": 500, "message": "ReferenceError: limit is not defined" }
```

Client then crashes with:
```
TypeError: response is not iterable
    putmessages channel.ts:2931
```

## Root Cause

The messages route handler at `dist/api/routes/channels/#channel_id/messages/index.js` **declares `limit` in the route schema** (the `query:` block that enables swagger docs + validation), but the **handler function body never extracts it from `req.query.limit`**. The variable `limit` is referenced at:

```javascript
if (limit < 1 || limit > 100)
    throw new lambert_server_1.HTTPError("limit must be between 1 and 100", 422);
...
take: limit,
```

But no `const limit = ...` line exists in the handler scope — it's a straightforward missing variable declaration.

## Fix

Add the missing line after the `after` variable assignment, before the `if (limit)` check:

```diff
    const after = isValidSnowflake(req.query.after) ? req.query.after : undefined;
+   const limit = req.query.limit ? Number(req.query.limit) : 50;
    if (limit < 1 || limit > 100)
```

### Applying the Patch

```bash
# File path on VPS:
# /opt/spacebar/dist/api/routes/channels/#channel_id/messages/index.js

# Insert after line ~69 (the `after` assignment)
sed -i "69a\\    const limit = req.query.limit ? Number(req.query.limit) : 50;" \
  /opt/spacebar/dist/api/routes/channels/\#channel_id/messages/index.js
```

## Important: Module Caching

Node.js caches `require()`d modules in memory. Patching the `.js` file on disk alone does NOT fix the running server. You MUST **restart the server process** for the patch to take effect:

```bash
sudo systemctl restart spacebar.service
```

## Verification

```python
import json, urllib.request

data = json.dumps({"login":"backus-admin","password":"***"}).encode()
req = urllib.request.Request("https://gc.your-domain.example/api/auth/login", data=data, 
    headers={"Content-Type":"application/json"})
token = json.loads(urllib.request.urlopen(req).read())["token"]

req = urllib.request.Request(
    "https://gc.your-domain.example/api/channels/<channel_id>/messages?limit=100",
    headers={"Authorization": token}
)
resp = urllib.request.urlopen(req)
data = json.loads(resp.read())
print(f"OK - {len(data)} messages")
```

## Related

Same route file also has the snowflake validation bug (see `guild-members-crash-fix.md`). Both `after`/`before`/`around` validation AND the `limit` declaration must be functional for the messages endpoint to work.
