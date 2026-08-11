# Spacebar Guild Members QueryParam Crash Fix

## Error Pattern

```
QueryFailedError: invalid input syntax for type bigint: "undefined"
```

Full response:
```json
{"code":500,"message":"QueryFailedError: invalid input syntax for type bigint: \"undefined\"","request":"GET /api/v9/guilds/.../members?after=undefined&limit=1"}
```

The error kills the **entire server process** — not just the single request — because the route handler has no try/catch.

## Root Cause

The guild members route at `src/api/routes/guilds/#guild_id/members/index.ts` has:

```typescript
const after = req.query.after;
const query = after ? { id: MoreThan(after) } : {};
```

When any client/bot sends `GET /api/v9/guilds/:id/members?after=undefined` or `after=...` or any non-numeric string:
1. `req.query.after` = the string `"undefined"` (truthy)
2. `MoreThan("undefined")` passes it type-unsafely to PostgreSQL
3. PostgreSQL throws `22P02: invalid input syntax for type bigint`
4. The uncaught exception crashes the process

The same bug exists in the channels messages route on `after`, `before`, and `around` params.

## Fix

Validate query params as proper snowflakes (all-numeric strings) before passing to TypeORM:

```typescript
// Only accept valid snowflake IDs
const after = typeof req.query.after === 'string' && /^\d+$/.test(req.query.after) ? req.query.after : undefined;
const query = after ? { id: MoreThan(after) } : {};
```

Same pattern for `before`, `around`:

```typescript
const isValidSnowflake = (v: unknown): v is string =>
    typeof v === 'string' && /^\d+$/.test(v);
const after = isValidSnowflake(req.query.after) ? req.query.after : undefined;
const before = isValidSnowflake(req.query.before) ? req.query.before : undefined;
const around = isValidSnowflake(req.query.around) ? req.query.around : undefined;
```

## Files to Patch

| File | Type | Notes |
|------|------|-------|
| `src/api/routes/guilds/#guild_id/members/index.ts` | Source | Survives rebuild |
| `dist/api/routes/guilds/#guild_id/members/index.js` | Compiled | Immediate effect |
| `src/api/routes/channels/#channel_id/messages/index.ts` | Source | Same bug in 3 params |
| `dist/api/routes/channels/#channel_id/messages/index.js` | Compiled | Same bug in 3 params |

## Important: Module Caching

Patching compiled `.js` files while the server IS running does NOTHING. Node.js caches `require()`d modules in memory. You MUST **restart the server process** for patches to take effect.

## Server Death Spiral

When Spacebar crashes from this uncaught exception:
1. Server process dies
2. All 13+ bot WebSocket connections drop
3. Bots auto-reconnect to a new server process
4. Bot clients that maintain state may re-request guild members
5. If `after` param wasn't sanitized client-side, it crashes AGAIN
6. Repeat → infinite crash loop

**Break the spiral by:**
1. Patch the route handler (both source + compiled)
2. Kill ALL `node` Spacebar processes (`pkill -f "dist/bundle/start"` or `taskkill`)
3. Start fresh server
4. Restart bot fleet
