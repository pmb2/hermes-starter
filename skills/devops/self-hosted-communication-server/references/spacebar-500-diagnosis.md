# Spacebar Internal 500 Error Diagnosis

When the Spacebar server returns HTTP 500 on common endpoints, the root cause is typically a JavaScript runtime error or a database query bug specific to the Spacebar version. These are NOT configuration or deployment issues — they are Spacebar implementation bugs.

## Common 500 Errors

### 1. Messages endpoint: `TypeError: (intermediate value).difference is not a function`

**Endpoint:** `GET /channels/{id}/messages?limit=N`

**Full error:**
```json
{"code":500,"message":"TypeError: (intermediate value).difference is not a function"}
```

**Root cause:** A bug in the Spacebar API method that fetches messages and computes a `difference` operation on a Set or Map. The `(intermediate value)` pattern indicates a method-chain call where `.difference()` is being called on a value that doesn't have that method — likely a Set that should have been an Array, or vice versa. This is a core Spacebar code bug, not a data/config issue.

**Symptoms:**
- Client can't load message history for ANY channel (not just specific ones)
- The error appears on every `messages?limit=N` request
- Newly sent messages are stored but can't be retrieved via REST
- WebSocket dispatch of MESSAGE_CREATE may still work (messages appear in real-time but not on refresh)

**Impact:** Message history is completely broken. The bot/the operator can send messages successfully (POST returns 201), but neither can read past messages. The client shows empty channels.

**Diagnosis:**
```bash
curl -s "https://discy.your-domain.example/api/v9/channels/{channel_id}/messages?limit=5" \
  -H "Authorization: $TOKEN" | head -200
```

**No workaround** — this is a Spacebar source code bug. Options:
- Fix the JS source in `dist/api/.../Message.js` (find and fix the `.difference` call)
- Wait for a Spacebar release that patches this
- Use WebSocket-based message retrieval instead of REST
- Switch to real Discord API temporarily

### 2. Guild members endpoint: `QueryFailedError: invalid input syntax for type bigint: "undefined"`

**Endpoint:** `GET /guilds/{id}/members`

**Full error:**
```json
{"code":500,"message":"QueryFailedError: invalid input syntax for type bigint: \"undefined\""}
```

**Root cause:** A PostgreSQL query in the members endpoint is passing the JavaScript value `undefined` as a `bigint` parameter. PostgreSQL's type system rejects `undefined` because it expects a numeric string or null. This happens when a Spacebar route handler tries to use a query parameter that wasn't provided (e.g., `limit` or `after`), and the JavaScript value `undefined` gets stringified into the SQL.

**Symptoms:**
- Guild member list cannot be fetched via REST API
- Bot membership verification fails
- Admin panel may show 0 members

**Impact:** Cannot enumerate guild members via REST. WebSocket-based member presence may still work.

**No workaround** — same as above, this is a Spacebar code bug.

### 3. Failed to decode token / 401

**May appear as 500 instead of 401** when token validation throws instead of returning HTTP 401.

**Fix:** Use the full, correct JWT token. Truncated or placeholder tokens ("eyJhbG...aD40") will fail. Always read the actual token from the profile `.env` file:
```bash
TOKEN=$(grep "^DISCORD_BOT_TOKEN=" ~/AppData/Local/hermes/profiles/chief-of-staff/.env | sed 's/^DISCORD_BOT_TOKEN=//' | tr -d '\r\n ')
```

## WebSocket Behavior

The Spacebar WebSocket gateway is independent of the REST API. When REST endpoints return 500, the WebSocket may still function for:
- Real-time message dispatch (MESSAGE_CREATE events)
- Presence updates
- Typing indicators

**However**, Spacebar may have a separate bug where MESSAGE_CREATE events are NOT forwarded to bot clients connected via WebSocket. The bot connects and authenticates successfully (shown as online), but never receives any message events.

**Diagnosis:** Check gateway output for any event processing after startup:
```
process(action='log', session_id='...')  # should show more than startup lines
```
If no new lines appear after 60+ seconds (cron ticker should fire), the bot is not receiving WebSocket events.

## Bot Message Flow Check

When bots are online but not responding, verify message flow at each layer:

1. **REST POST works?** — Bot can send messages via API
   ```bash
   curl -s -X POST "https://discy.your-domain.example/api/v9/channels/{id}/messages" \
     -H "Authorization: $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"content":"test"}'
   ```

2. **WebSocket connected?** — Bot shows online in client
   ```bash
   curl -s "https://discy.your-domain.example/api/v9/gateway"
   # → {"url":"ws://localhost:3100/"}
   ```

3. **DM channel exists?** — Bot has open DM with the operator
   ```bash
   curl -s "https://discy.your-domain.example/api/v9/users/@me/channels" \
     -H "Authorization: $TOKEN" | python -c "import sys,json; d=json.load(sys.stdin); [print(f'{r.get(\"username\",\"?\")} id={r.get(\"id\")} chan={c.get(\"id\")}') for c in d for r in c.get('recipients',[]) if not r.get('bot')]"
   ```

4. **Bot receives events?** — Check gateway output for any new lines after startup. If `process(action='poll')` shows no new output for 5+ minutes, WebSocket events are not reaching the bot.

If layer 3 works (DM exists) but layer 4 fails (no events received), the Spacebar instance has a WebSocket event routing bug — it doesn't dispatch MESSAGE_CREATE events to bot WebSocket connections. This is a Spacebar limitation, not a configuration issue.

## Summary

| Error | Endpoint | Type | Recovery |
|-------|----------|------|----------|
| `.difference is not a function` | messages | JS bug in Spacebar | Patch Spacebar source or switch to real Discord |
| `invalid input syntax for bigint: "undefined"` | members | SQL bug in Spacebar | Patch Spacebar source or use DB queries instead |
| `Failed to decode token` | any | Auth | Use full JWT from .env file |
| No WebSocket events to bots | WSS | Spacebar WS routing bug | Patch Spacebar or use alternative message delivery |
