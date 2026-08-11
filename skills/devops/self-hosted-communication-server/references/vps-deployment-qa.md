# VPS Deployment QA Checklist

End-to-end QA checklist for verifying a Spacebar+Fermi stack deployed to a public domain via VPS reverse proxy. Run every layer after deployment.

## Layer 1: DNS

```bash
nslookup gc.your.domain
# → Must resolve to VPS IP address
```

## Layer 2: TLS / Caddy

```bash
curl -sv https://gc.your.domain/api/v9/gateway --max-time 15 2>&1 | grep -E "SSL|TLS|HTTP/|200|error|refused"
# → Must show TLS handshake, HTTP/1.1 200 OK
# → No "certificate error" messages
```

## Layer 3: Spacebar API (VPS-local)

SSH into the VPS and check the local Spacebar:

```bash
# Is Spacebar listening? Check for MULTIPLE processes
pgrep -f 'dist/bundle/start' 2>/dev/null
# → Should show exactly ONE PID. Multiple PIDs = stale instances, will cause EADDRINUSE.
# Fix if multiple:
#   fuser -k 3100/tcp && sleep 2 && <restart-spacebar>

ss -tlnp | grep 3100
# → Must show LISTEN with node PID

# Does the gateway endpoint return the correct PUBLIC URL?
curl -s http://localhost:3100/api/v9/gateway
# → Must show {"url":"wss://gc.your.domain/"} (NOT ws://localhost:3100/)

# Does login work?
curl -s -X POST http://localhost:3100/api/v9/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login":"architect","password":"TestPass123!"}'
# → Must return a token
```

**Common failure:** Gateway returns `ws://localhost:3100/` instead of the public domain.
**Fix:** Update `config.production.json` → `gateway.endpointPublic` to `wss://gc.your.domain/` and restart Spacebar.

## Layer 4: Caddy Reverse Proxy

Test through the public domain:

```bash
# API reachable?
curl -s -o /dev/null -w "%{http_code}" https://gc.your.domain/api/v9/gateway --max-time 10
# → 200

# Well-known discovery
curl -s https://gc.your.domain/.well-known/spacebar --max-time 10
# → {"api":"https://gc.your.domain/api/v9"}

# Well-known v2 (some Fermi clients check this)
curl -s -o /dev/null -w "%{http_code}" https://gc.your.domain/.well-known/spacebar-v2 --max-time 10
# → 200 or 404 (404 is OK if Caddy falls through to Spacebar's handler)

# Instance info
curl -s https://gc.your.domain/api/v9/policies/instance -H "Authorization: <admin-token>" --max-time 10
# → Should return instance config JSON
```

**Common failure:** API returns 502 (Bad Gateway).
**Fix:** Caddy cannot reach the backend. Check that Spacebar is listening on the port Caddy is proxying to (usually 3100). On Docker Caddy, the target is `172.17.0.1:3100` (Docker gateway IP), not `localhost:3100`.

## Layer 5: WebSocket

Test that WebSocket connections work through the reverse proxy:

```python
import asyncio, websockets, json

async def test_ws():
    uri = 'wss://gc.your.domain/'
    async with websockets.connect(uri, ping_interval=None) as ws:
        # Should receive OP 10 (Hello) with heartbeat_interval
        resp = await asyncio.wait_for(ws.recv(), timeout=10)
        data = json.loads(resp)
        assert data['op'] == 10, f"Expected OP 10, got {data['op']}"
        print(f"WebSocket OK: OP 10, heartbeat={data['d']['heartbeat_interval']}ms")

asyncio.run(test_ws())
```

**Common failure:** Connection refused or timeout.
**Fix:** Caddy's `@ws` handler must match WebSocket upgrade headers:
```caddy
@ws {
    header Connection *Upgrade*
    header Upgrade websocket
}
handle @ws {
    reverse_proxy 172.17.0.1:3100
}
```

## Layer 6: Fermi Client

```bash
# Fermi page loads
curl -sL https://gc.your.domain --max-time 15 | grep "<title>"
# → Must show page title (e.g. "the operator")

# instances.json serves correct URLs
curl -s https://gc.your.domain/instances.json --max-time 10
# → All URLs must reference gc.your.domain, NOT old domains or localhost
```

**Common failure:** instances.json still points to old domain.
**Fix:** Update both `dist/webpage/instances.json` AND `src/webpage/instances.json`, then **restart Fermi** (it caches instances.json at startup).

**Common failure:** "This instance has likely sent the incorrect links" in Fermi.
**Fix:** The Spacebar gateway endpoint URL's hostname must match the API URL's hostname. Verify both in config match the public domain.

## Layer 7: Guild Data

```bash
# Login to get a token
TOKEN=$(curl -s -X POST https://gc.your.domain/api/v9/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login":"admin","password":"pass"}' | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))")

# Check guilds
curl -s -H "Authorization: $TOKEN" https://gc.your.domain/api/v9/users/@me/guilds --max-time 10
# → Must list the migrated guild(s)

# Check channels
curl -s -H "Authorization: $TOKEN" https://gc.your.domain/api/v9/guilds/<guild-id>/channels --max-time 10
# → Must show correct categories and text channels

# Check messages
curl -s -H "Authorization: $TOKEN" https://gc.your.domain/api/v9/channels/<channel-id>/messages?limit=5 --max-time 10
# → Must show imported messages
```

## Quick Go/No-Go Command

```bash
echo "=== GO/NO-GO: gc.your.domain ==="
curl -svo /dev/null https://gc.your.domain/api/v9/gateway --max-time 15 2>&1 | grep -E "< HTTP|SSL|TLS"
curl -s https://gc.your.domain/api/v9/gateway --max-time 10
curl -s https://gc.your.domain/.well-known/spacebar --max-time 10
curl -sL https://gc.your.domain --max-time 15 | grep -o "<title>[^<]*</title>"
echo "=== END ==="
```
