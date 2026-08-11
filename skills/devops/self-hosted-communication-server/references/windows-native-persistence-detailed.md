# Windows Native Persistence (Non-Docker)

When Spacebar runs as a bare Node.js process (not Docker), use the **Startup folder VBS approach** to ensure the server + SSH tunnel survive reboots. This works without admin rights (unlike `nssm`, `sc.exe`, or `schtasks` which all require elevation on Windows).

### Architecture

```
Windows boots → User logs in → Startup folder runs:
   └── SpacebarStack.vbs (hidden, no console)
       └── start-stack.bat (minimized)
           ├── start /min "SpacebarServer" ... node dist/bundle/start.js
           │   └── auto-restart loop (3s delay on crash)
           └── start /min "SpacebarTunnel" ... ssh -R 0.0.0.0:3001:localhost:3001
               └── auto-restart loop (5s delay on drop)
```

### File 1: `start-stack.bat`

Place at the Spacebar repo root. It launches both processes in minimized windows with auto-restart loops:

```batch
@echo off
cd /d "${MY_REPOS}\Documents\github\spacebar"
if not exist "logs" mkdir "logs"

REM ── SSH Tunnel (reconnect loop) ──
start /min "SpacebarTunnel" cmd /c ^
  ":tunnel^
  echo [%%date%% %%time%%] Starting SSH tunnel... >> "logs\tunnel.log"^
  "C:\Program Files\Git\usr\bin\ssh.exe" -i "${USER_HOME}\.ssh\oracle_vps" ^
    -o StrictHostKeyChecking=no ^
    -o ServerAliveInterval=30 ^
    -o ServerAliveCountMax=3 ^
    -o ExitOnForwardFailure=yes ^
    -o TCPKeepAlive=yes ^
    -N -R 0.0.0.0:3001:localhost:3001 ubuntu@129.153.156.190 >> "logs\tunnel.log" 2>&1^
  echo [%%date%% %%time%] Tunnel exited, reconnecting in 5s... >> "logs\tunnel.log"^
  timeout /t 5 /nobreak >nul^
  goto tunnel"

REM ── Spacebar Server (auto-restart loop) ──
set NODE_ENV=production
set PORT=3001
set DATABASE=postgres://spacebar_admin:***@127.0.0.1:5432/spacebar

start /min "SpacebarServer" cmd /c ^
  ":server^
  echo [%%date%% %%time%] Starting Spacebar... >> "logs\server.log"^
  "C:\Program Files\nodejs\node.exe" --enable-source-maps dist/bundle/start.js >> "logs\server.log" 2>&1^
  echo [%%date%% %%time%] Server exited, restarting in 3s... >> "logs\server.log"^
  timeout /t 3 /nobreak >nul^
  goto server"
```

**🚨 Batch caret escaping:** The `^` line continuations inside `cmd /c` need doubled `%%` for `%date%` and `%time%`. The outer `start /min` uses `"Title" cmd /c ^ ...` syntax.

### File 2: `SpacebarStack.vbs`

Place in `Startup` folder (`C:\Users\<User>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\`). Runs the batch file invisibly (no console window):

```vbs
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "${MY_REPOS}\Documents\github\spacebar\start-stack.bat", 0, False
```

The `0` parameter means "hide window" (invisible). `False` means "don't wait for return" (non-blocking).

### What to Expect at Next Boot

1. System boots, user logs in
2. Windows processes all Startup items (VBS and .cmd files)
3. `SpacebarStack.vbs` launches silently → two minimized cmd windows start for Spacebar + tunnel
4. Spacebar takes ~45-60 seconds to register all API routes before the port opens
5. Other Startup .cmd files (Hermes gateways, etc.) run in parallel
6. Within ~90 seconds of login, the full stack is operational

### Verifying After Reboot

```bash
# Check if Spacebar is listening
netstat -ano | grep LISTENING | grep 3001

# Check if API responds
curl -s http://localhost:3001/api/v9/auth/login

# Check logs
cat ${MY_REPOS}/spacebar/logs/server.log | tail -5
cat ${MY_REPOS}/spacebar/logs/tunnel.log | tail -5
```

### Diagnosis: "502 Bad Gateway" Chain

When `discy.your-domain.example` returns 502 or the Fermi client shows `TypeError: can't access property "at", res.errors is undefined`, the issue is usually in the proxy chain. Diagnose layer by layer:

```bash
# Layer 1: Is the local Spacebar API running?
curl -s -o /dev/null -w "%{http_code}" http://localhost:3001/api/v9/auth/login
# → 401 = good (server up, needs auth header)
# → 000 = dead — restart or check logs

# Layer 2: Is the SSH tunnel alive?
# Check on local machine:
ps aux | grep "ssh.*-R.*3001" | grep -v grep
# → should show at least one ESTABLISHED connection

# Check on VPS (if accessible):
ssh -i ~/.ssh/key ubuntu@<vps> "ss -tlnp | grep 3001"
# → should show sshd listening with a PID

# Layer 3: Is Caddy proxying correctly?
curl -s -o /dev/null -w "%{http_code}" https://discy.your-domain.example/api/v9/auth/login
# → 401 = full chain working
# → 502 = dead tunnel or wrong backend port
# → 000 = Caddy not responding

# Layer 4: Check for port mismatch
netstat -ano | grep LISTENING | grep -E "3001|3100"  # local
ssh ... "ss -tlnp | grep -E '3001|3100'"              # VPS
```

See `references/windows-native-persistence.md` for full session detail and the complete setup walkthrough.

### 🚨 Spacebar process stuck (listening but not responding)

The `sb-bundle` Node.js process can enter a state where it **accepts TCP on port 3100** (`ss -tlnp` shows LISTEN) but **never responds to HTTP requests** — `curl http://localhost:3100/api/v9/gateway --max-time 5` returns `000` (no data) rather than a connection refused or normal 200.

**This is NOT the normal startup delay.** Normal startup (45-60s of route registration) eventually produces a 200 response. When the process is stuck, it:
- Accepts the TCP handshake (connection established)
- Never sends any HTTP data (curl times out at 5s with `000`)
- Logs unusual messages like `Handling presence update after disconnect` repeatedly
- May log `Gateway connection rejected: No IP address found.`

**Diagnosis — distinguish stuck vs starting vs dead:**

```bash
# 1. Is the port open?
ss -tlnp | grep 3100
# → LISTEN = process alive but possibly stuck
# → (nothing) = process died

# 2. Does the API respond?
curl -s -o /dev/null -w '%{http_code}' --max-time 10 http://localhost:3100/api/v9/gateway
# → 200 = healthy
# → 000 = stuck (TCP accepted, no HTTP data)
# → connection refused = process dead

# 3. Check logs for the stuck pattern
tail -20 /opt/spacebar/spacebar.log | grep -i 'handling presence\|No IP address\|undefined'
# → "Handling presence update after disconnect" repeated = stuck
# → "Gateway connection rejected: No IP address found." = stuck
# → "[Monitoring] Request route path was undefined?" = partially hung
```

**Fix — kill and restart clean:**

```bash
# 1. Kill the stuck process by PID
kill <pid>
# Or if multiple instances:
kill $(pgrep -f 'sb-bundle') 2>/dev/null

# 2. Wait for port to clear
sleep 2
ss -tlnp | grep 3100 || echo "Port 3100 free"

# 3. Restart from the project directory
cd /opt/spacebar
nohup node --enable-source-maps dist/bundle/start.js >> spacebar.log 2>&1 &

# 4. Verify startup (allow 10-15s for initial bind)
sleep 10
curl -s -o /dev/null -w '%{http_code}' --max-time 10 http://localhost:3100/api/v9/gateway
# → Should return 200 within ~10s (route registration in progress)
# → If still 000 after 60s, it's stuck again — kill + retry
```

**Prevention:** The cron watchdog (every 5min: `pgrep -f "dist/bundle/start"`) auto-restarts the process if it fully dies, but CANNOT detect the stuck-but-listening state because `pgrep` matches the process name. Consider adding an HTTP-level health check to the watchdog.

**Root cause:** Unknown — possibly a WebSocket connection storm from many bots (39+) reconnecting simultaneously, overwhelming the event loop. The `Handling presence update after disconnect` log suggests the gateway handler is stuck in an infinite loop processing stale presence updates.

### 🚨 Node.js OOM crash under gateway connection load

When running Spacebar locally with many concurrent gateway connections (~44+ from 39 bot gateways), Node.js can crash with:

```
#
# Fatal process out of memory: Zone
#
----- Native stack trace -----
 1: 00007FF6E82820AD
...
```

**Symptom:** The process terminates with exit code 3 and `Fatal process out of memory: Zone`. The server logs show many `Handling presence update after disconnect` and `[WebSocket] closed` messages before the crash, indicating the gateway is struggling to handle presence state for all connected bot clients.

**Root cause:** Node.js's default `max-old-space-size` is ~4GB on 64-bit systems. With 44+ concurrent WebSocket connections, each with presence tracking, the heap overflows the Zone allocation region.

**Fix — increase Node.js heap limit:**
```bash
# Start with 8GB heap (adjust based on available RAM)
cd /path/to/spacebar
NODE_OPTIONS="--max-old-space-size=8192" node --enable-source-maps dist/bundle/start.js

# For persistent runs (Windows start-stack.bat):
set NODE_OPTIONS=--max-old-space-size=8192
"C:\Program Files\nodejs\node.exe" --enable-source-maps dist/bundle/start.js
```

**Memory sizing guideline:**
- 4GB default ≈ comfortable for ~20-30 concurrent gateway connections
- 8GB ≈ good for ~60-80 connections
- Requires sufficient free RAM on host

**Prevention:**
- Add `NODE_OPTIONS=--max-old-space-size=8192` to `.env` or startup script
- For Windows native persistence, add to `start-stack.bat`'s `set NODE_OPTIONS=...` before launching node
- Monitor with Windows Task Manager → check `node.exe` memory growth as bots connect

**🪟 Windows background-process note:** When using Hermes `terminal(background=true)`, the process tool tracks `bash.exe` (the shell wrapper), not `node.exe`. To find the real server process: `tasklist.exe //FI "IMAGENAME eq node.exe"` and look for high-memory PIDs.

### 🚨 PostgreSQL password mismatch after DB restore

When you `pg_dump` and `psql restore` a Spacebar database to a new machine (or re-create the schema on the same machine), the PostgreSQL role password may stop working even though the data restored cleanly. This happens because:

- The dump includes the password hash for the role, but the new cluster's `pg_hba.conf` or scram-scram algorithm may not match
- Multiple parallel Spacebar instances writing to the same DB can corrupt the session state

**Symptom:** `psql -h 127.0.0.1 -U hamilton -d spacebar -c 'SELECT count(*) FROM users;'` fails with authentication error, but `sudo -u postgres psql` works. Spacebar logs show `Error: listen EADDRINUSE`.

**Fix — reset the role password:**

```bash
sudo -u postgres psql -c "ALTER USER hamilton WITH PASSWORD 'the-original-password-from-env';"
```

This resynchronizes the password hash with the scram-scram storage format. Spacebar can then authenticate using its `DATABASE=postgres://hamilton:password@...` connection string.

**Diagnosis — confirm password mismatch is the issue:**

```bash
# Does the DB accept connections at all?
PGPASSWORD='the-password' psql -h 127.0.0.1 -U hamilton -d spacebar -c 'SELECT 1;'
# → If this fails, ALTER USER is needed
```

When a Spacebar process is killed with `taskkill /F`, in-flight user registrations may persist with corrupted password hashes. The user exists in the DB (email already registered), but login fails with "Invalid login or password".

**Diagnosis:** Registration returns `EMAIL_ALREADY_REGISTERED`, login returns `INVALID_LOGIN`.

**Fix — delete corrupted records directly from PostgreSQL:**

```python
import psycopg2
conn = psycopg2.connect('postgres://user:***@127.0.0.1:5432/spacebar')
cur = conn.cursor()
cur.execute("DELETE FROM users WHERE username IN ('user1','user2')")
conn.commit()
```

After deletion, re-register with the same credentials — they'll create fresh records with valid password hashes.

### 🚨 CONFIG_PATH required for native (non-Docker) Spacebar

Spacebar has TWO config loading modes:

- **Docker** — `CONFIG_PATH=/app/config.production.json` (set in compose)
- **Native** (Node process on bare metal) — if `CONFIG_PATH` is NOT set, config loads from the **database** via `pairs = await validateConfig()`, not from `config.json`

The DB config may have different defaults (rate limiting enabled, registration disabled) that don't match the `config.json` file. **Setting `CONFIG_PATH` is the only reliable way to use a JSON config file on native Spacebar.**

```bash
export CONFIG_PATH='config.json'
export DATABASE='postgres://user:***@127.0.0.1:5432/spacebar'
npm start
```

On the running process, verify with startup logs:

```
[Config] Using CONFIG_PATH rather than database: config.json
```

If you see `[Config] Loading configuration...` without the CONFIG_PATH line, it's reading from the DB.

### 🚨 Bot token authentication fails after Spacebar migration (ECDSA keypair mismatch)

When you migrate a Spacebar instance (dump DB, restore on another machine), all existing bot tokens may produce **401 Unauthorized** on login, even though the DB was restored correctly.

**Root cause:** Spacebar signs bot tokens with an **ECDSA P-521 keypair** (ES512 algorithm) loaded from `jwt.key` (private) and `jwt.key.pub` (public) in the repo root. On first startup, if these files don't exist, Spacebar generates a **new keypair**. The old tokens were signed with the previous instance's key and are rejected by the new instance.

**Diagnosis — check if the keys match:**

```bash
# Compare fingerprints
openssl pkey -in /path/to/spacebar/jwt.key -pubout -outform DER | openssl dgst -sha256
# Run on both old and new instance; fingerprint must match
```

Or check the startup log for `[JWT] Generating new keypair` — if you see this, the keys were freshly generated and old tokens are invalid.

**Fix A — Copy keys from the old instance (preserves all existing tokens):**

```bash
scp user@old-instance:/opt/spacebar/jwt.key /path/to/local/spacebar/jwt.key
scp user@old-instance:/opt/spacebar/jwt.key.pub /path/to/local/spacebar/jwt.key.pub
# Then restart Spacebar — it will load the copied keys instead of generating new ones
```

### Pitfall — `valid_tokens_since` rejects tokens even when keys match

After migrating the database, check `users.data -> valid_tokens_since`. If this timestamp is newer than the token's JWT `iat` (issued-at) claim, Spacebar rejects the token regardless of keypair match. This typically happens after a password/token reset on the origin instance.

**Symptom:** Server logs show `Invalid Token meow JsonWebTokenError: invalid signature` even though ECDSA key fingerprint matches (`openssl pkey -in jwt.key -pubout -outform DER | openssl dgst -sha256`). The `invalid signature` message is misleading — the real cause is the IAT timestamp check, not a crypto mismatch.

**Fix — reset `valid_tokens_since` to epoch for all bots:**

```sql
UPDATE users SET data = jsonb_set(data, '{valid_tokens_since}', '"1970-01-01T00:00:00.000Z"') WHERE bot = true;
```

Run this after DB restoration but before starting the gateway fleet. Any JWT token ever issued becomes valid again.

**Fix B — Regenerate bot tokens via the API (no old-key access needed):**

1. Ensure the admin user has sufficient **rights** in the database:
   ```sql
   UPDATE users SET rights = 1759218604441599 WHERE username = 'admin-username';
   ```
   (Value `1759218604441599` = full admin rights in Spacebar's permission system.)

2. Login as admin to get a token:
   ```bash
   curl -s -X POST http://localhost:3100/api/v9/auth/login \
     -H "Content-Type: application/json" \
     -d '{"login":"admin","password":"***"}' | jq -r '.token'
   ```

3. For each bot, find its application ID (same as user ID for bots), then regenerate:
   ```javascript
   // Node.js
   const res = await fetch(
     'http://localhost:3100/api/v9/applications/{user_id}/bot',
     { method: 'PATCH', headers: { 'Authorization': adminToken } }
   );
   const { token } = await res.json();
   ```

4. Update each profile's `.env` with the new `DISCORD_BOT_TOKEN=...`

**Pitfall — application ownership:** The admin user must own the application or have `MANAGE_APPLICATIONS` permission. If the app is owned by the bot user itself (common in Spacebar), the admin needs sufficient rights (`1759218604441599` covers everything). Without adequate rights, the API returns `{"code":20012,"message":"You are not authorized to perform this action on this application"}`.

**Pitfall — ECDSA key file paths:** `jwt.key` and `jwt.key.pub` are resolved relative to the **current working directory** at startup (the Spacebar repo root), NOT the `dist/bundle/` directory. Verify the files exist where Node.js is running.

### 🚨 Docker Postgres pg_hba.conf ordering — trust rule must come BEFORE scram-sha-256

When Docker PostgreSQL starts for the first time, it configures `host all all all scram-sha-256` as the default catch-all rule at the BOTTOM of `pg_hba.conf`. If you append a trust rule with `echo ... >> pg_hba.conf`, the `scram-sha-256` rule still matches FIRST (PostgreSQL processes `pg_hba.conf` top-down and uses the first match).

**Correct approach — insert BEFORE the scram-sha-256 line:**

```bash
sed -i '/^host all all all scram-sha-256/i\host all all all trust' /var/lib/postgresql/data/pg_hba.conf
```

Then reload:
```bash
psql -U postgres -c "SELECT pg_reload_conf();"
```

Or use a fresh container with explicit trust:
```bash
docker run -d --name my-postgres -p 5434:5432 \
  -e POSTGRES_PASSWORD=*** postgres:16-alpine
# Then exec in and fix pg_hba.conf ordering
```

**Diagnosis:** If `SELECT 1 as test` via Node.js `pg` library returns `ERROR: SASL: SCRAM-SERVER-FIRST-MESSAGE: client password must be a string` even after setting `host all all all trust`, the ordering is wrong. Verify with:
```bash
docker exec postgres-container sh -c 'cat /var/lib/postgresql/data/pg_hba.conf | grep "^host"'
```

You should see the trust line BEFORE any scram-sha-256 line.

**Note:** The standard Docker PostgreSQL image uses `trust` for `127.0.0.1/32` and `::1/128` already, but connections arriving through Docker's port-mapping NAT do NOT come from `127.0.0.1` — they come from the Docker bridge gateway IP (e.g., `172.17.0.1`). This is why the catch-all `host all all all` rule applies and why the ordering matters.

### 🚨 Node.js 20 ES2025 Set Method Crash (`.difference()`, `.symmetricDifference()`, `.intersection()`)

Spacebar source code uses ES2025 Set methods that are **Node 22+ only**. On Node 20 (which many VPS instances like Oracle free tier ship with), `--harmony-set-methods` does NOT exist as a flag — Node 20 doesn't recognize it and ignores it silently. Any call to:
- `new Set(...).symmetricDifference(new Set(...))` — channel tag updates
- `new Set(...).intersection(new Set(...))` — registration flow
- `new Set(...).difference(new Set(...))` — TypeORM Message entity queries

...throws `TypeError: (intermediate value).difference is not a function` and returns a 500.

**Diagnosis — confirm Node version + affected code:**

```bash
node --version                     # Must be 22+ for native Set methods
node -e "console.log(typeof new Set([1]).difference)"   # undefined on Node 20
node --harmony-set-methods -e "..."  # BAD OPTION on Node 20 — flag not recognized
```

**Fix — patch each affected file with a manual polyfill:**

Search ALL files under `dist/` for ES2025 Set methods:
```bash
grep -rn '\.symmetricDifference\|\.intersection\|\.difference(' dist/ --include='*.js' | grep -v '\.map' | grep -v node_modules
```

For each occurrence, replace the native method with a manual implementation. Three patterns:

**Pattern A — `.symmetricDifference()`** (channels index — tag updates):
```javascript
// Before:
const changed = new Set(channel.applied_tags || []).symmetricDifference(new Set(payload.applied_tags));

// After — IIFE returning a Set:
const changed = (() => {
  const a = new Set(channel.applied_tags || []);
  const b = new Set(payload.applied_tags);
  const result = new Set();
  a.forEach(x => { if(!b.has(x)) result.add(x); });
  b.forEach(x => { if(!a.has(x)) result.add(x); });
  return result;
})();
```

**Pattern B — `.intersection()`** (register route):
```javascript
// Before:
const blockedCategories = new Set(categories).intersection(new Set(register.blockIpDataCoThreatTypes));

// After — filter on first set:
const blockedCategories = new Set(
  [...new Set(categories)].filter(x => new Set(register.blockIpDataCoThreatTypes).has(x))
);
```

**Pattern C — `.difference()`** (Message entity, possibly in node_modules):
```javascript
// Before:
someSet.difference(otherSet);

// After — filter out elements in the second set:
const result = new Set([...someSet].filter(x => !otherSet.has(x)));
```

After patching, verify no remaining ES2025 Set calls and restart:
```bash
grep -rn '\.difference\|\.symmetricDifference\|\.intersection\|\.union\|\.isSubsetOf\|\.isSupersetOf\|\.disjointFrom' dist/ --include='*.js' | grep -v '\.map' | grep -v node_modules | grep -v 'snowflake\|isValidSnowflake'
# If empty → all patched
sudo systemctl restart spacebar
```

**Polyfill alternative:** Rather than patching each file, add a global polyfill at the top of `dist/bundle/start.js` that injects missing Set methods. However, this is fragile because Node 20 doesn't allow modifying `Set.prototype` for built-in methods in strict mode. The per-file patch approach is more reliable.

### 🚨 Raw Query Params in TypeORM `MoreThan`/`LessThan` (PostgreSQL 22P02)

Spacebar's API endpoints that use `req.query.after`/`before`/`around` directly in TypeORM's `MoreThan()`/`LessThan()` without validation will crash the server (or at minimum return 500) when a client sends garbage like `?after=undefined`, `?after=...`, or any non-numeric string.

**The two vulnerable patterns to search for:**

```javascript
// ❌ Pattern A — raw assignment (guild members, mentions)
const after = req.query.after;
// "undefined" string is truthy → MoreThan("undefined") → SQL crash

// ❌ Pattern B — template-literal coercion (channel messages)
const after = req.query.after ? `${req.query.after}` : undefined;
// "undefined" is truthy, template produces "undefined" → same crash
```

**Search your codebase:**
```bash
grep -rn "req\\.query\\.\\(after\\|before\\|around\\)" --include='*.js' --include='*.ts' dist/ src/ | grep -v "snowflake\\|isValidSnowflake\\|test(\\|\.map"
```

**Fix — snowflake regex validation at every read site:**

```javascript
// ✅ Safe pattern — only accepts all-numeric snowflake strings
const after = typeof req.query.after === 'string' && /^\d+$/.test(req.query.after)
  ? req.query.after
  : undefined;
const query = after ? { id: MoreThan(after) } : {};
```

Same for `before` and `around` parameters. **Every site** is independently vulnerable — fix all of them.

**Routes that needed this fix (Jun 2026 session):** `guilds/:id/members`, `channels/:id/messages`, `users/@me/mentions`. Check for others in new versions.

**Restart required after patch:** Node.js caches `require()`d modules. Patching a compiled `.js` file while the server runs has NO effect. You must restart the server process.

### 🚨 Caddy + Config Domain Consolidation

When switching from one domain to another (e.g., `discy` → `gc`):

**🚨 Critical: 301 redirects break CORS for clients with stale URLs.** If the Fermi client has the old domain cached in localStorage (see `references/fermi-service-worker-cache.md`), any API call to the old domain receives a 301 redirect response — which has NO `Access-Control-Allow-Origin` header. The browser blocks the call with "Cross-Origin Request Blocked: The Same Origin Policy disallows reading the remote resource" before the redirect is followed.

**Fix — proxy API paths on the old domain instead of redirecting them:** Keep the redirect for non-API paths (web UI), but proxy `/api/*`, `/.well-known/*`, `/avatars/*`, `/files/*`, `/cdn/*`, and WebSocket connections to the backend. This way CORS headers from the origin flow through:

```caddy
# Old domain — proxy API paths (preserves CORS), redirect everything else
old-domain.example.com {
    encode gzip

    @api path /api/*
    handle @api { reverse_proxy backend:3100 }

    @ws {
        header Connection *Upgrade*
        header Upgrade websocket
    }
    handle @ws { reverse_proxy backend:3100 }

    @assets path /avatars/* /files/* /cdn/*
    handle @assets { reverse_proxy backend:3100 }

    @wellknown path /.well-known/spacebar*
    handle @wellknown { reverse_proxy backend:3100 }

    # Redirect the web UI
    handle { redir https://new-domain.example.com{uri} 301 }
}
```

This ensures API calls from stale clients get a proper CORS response, while browsers visiting the old URL in the address bar still end up on the new domain.

**Step 1 — Caddy config:** Follow the pattern above — proxy API paths, redirect UI paths.

**Step 2 — Spacebar config:** Update ALL URL references in `config.production.json`:
```bash
grep -c 'old-domain' /opt/spacebar/config.production.json
```
Fields to update: `general.serverName`, `gateway.endpointPublic/Private`, `cdn.endpointPublic/Private`, `api.endpointPublic/Private`, `general.image`.

**Step 3 — Reload Caddy + restart Spacebar:** `docker exec <caddy> caddy reload` then `sudo systemctl restart spacebar`.

**Step 4 — Verify:** old domain returns 301, gateway URL shows new domain.

**Step 5 — Users hard refresh (Ctrl+Shift+R)** to clear cached client state.

### 🚨 Spacebar TypeORM migration crash (`42P07`): When Spacebar is restarted on an already-seeded database, TypeORM migrations try `CREATE TABLE` (without `IF NOT EXISTS`) on existing tables. This throws `QueryFailedError: relation already exists` and aborts startup.
  
  **🚨 Critical: `DB_SYNC=false` is truthy in JavaScript!** TypeORM's code checks `!!process.env.DB_SYNC` for `synchronize: true/false`. The string `"false"` is non-empty, so `!!"false"` evaluates to **`true`** — meaning `DB_SYNC=false` in an env var **enables sync, it does not disable it**. To disable sync, either omit the `DB_SYNC` env var entirely or set it to an empty string `""`.
  
  **Root fix:** The crash happens when BOTH `DB_SYNC=true` AND `APPLY_DB_MIGRATIONS=true` are set. TypeORM's auto-sync creates all tables, then migrations run `CREATE TABLE` on already-existing tables. **Disable migrations** (not sync) for a pre-seeded DB:
  - Set `APPLY_DB_MIGRATIONS=false`
  - Remove `DB_SYNC` entirely (or don't set it — sync defaults to off)
  - The existing tables (created by a prior sync) work fine for querying without sync or migrations
  
  **Alternative (native PostgreSQL on Windows):** On this Windows machine, native PostgreSQL 16 at `127.0.0.1:5432` (trust auth for IPv4) has a `spacebar` database with **all 72 migrations already recorded** in the `migrations` table. Running Spacebar natively with `APPLY_DB_MIGRATIONS=true` (or unset) works perfectly — migrations are already marked complete. Connect with `DATABASE=postgres://postgres@127.0.0.1:5432/spacebar` (use `127.0.0.1`, NOT `localhost` — see PostgreSQL auth pitfall below). Verify with:
  ```bash
  psql -h 127.0.0.1 -U postgres -d spacebar -c "SELECT count(*) FROM migrations"
  # → 72
  ```
  
  **⚠️ Docker wedge risk:** If this container has `restart: always` or `restart: unless-stopped`, the crash-loop will re-stress the WSL2 ext4.vhdx until the named pipe wedges and all `docker` commands hang. See `### Fix D — Nuclear Recovery` above and `references/docker-desktop-wsl-wedge-recovery.md`.
- **Port 3001 conflict**: Spacebar defaults to port 3001. On this machine, `car-detailing-caldiy-web-1` maps host 3001→container 3000 (Cal.com). Resolve by running Spacebar on a different port: `export PORT=3100` and update `config.production.json` endpoints to match. Also check for other services: Cal.com, Node.js dev servers, and Docker WSL relay (`wslrelay.exe`) all compete for ports.
- **Native Spacebar with Docker PostgreSQL**: You can combine a native Node.js Spacebar with Docker PostgreSQL. Connect with `DATABASE=postgres://postgres@127.0.0.1:5432/spacebar` (use `127.0.0.1`, NOT `localhost` — Windows resolves `localhost` to IPv6 `::1` which uses a different auth path). The Docker container must publish port 5432 to the host.
- **Spacebar startup time**: First native start takes ~45-60 seconds (route registration). Don't treat the wait as a hang. Kill stale PIDs with `taskkill //F //PID <n>` before restarting if the port is held.
- **Gateway spacebar-gateway.py needs explicit env**: The wrapper reads `DISCORD_BOT_TOKEN` from environment variables, NOT from the profile's `.env` file. When running manually, `set -a && source ~/.../.env && set +a` before invoking the script, or export `DISCORD_BOT_TOKEN` directly. The `start-all-spacebar-agents.bat` batch file handles this correctly.
- **Docker on Windows**: ghcr.io pulls can fail with 500 errors on Docker Desktop. Fall back to npm bundle.
- **Docker port reservation**: Even after `docker compose down`, Docker Desktop's WSL relay (`wslrelay.exe`) retains port mappings. Using `netstat -ano | grep LISTENING` won't show a container but `wslrelay.exe` holds the port. Kill it with `taskkill //F //PID <pid>`.
- **PostgreSQL on Windows: localhost vs 127.0.0.1**: On Windows, `localhost` resolves to IPv6 `::1` which uses password auth (scram-sha-256 per pg_hba.conf), while `127.0.0.1` uses trust auth (if configured). Always use `127.0.0.1` in the DATABASE connection string for local dev. Verify: `host all all 127.0.0.1/32 trust` must be in `pg_hba.conf`.
- **Port conflicts**: Kill stale Node processes before restarting (`taskkill /F /PID <pid>` on Windows).
- **JWT secret**: If `security.jwtSecret` is null, login tokens cannot be decoded. Generate one in config.
- **Registration succeeds, login fails**: Check the `where` clause in login.ts — it may not search by username.
- **Database trust**: On local Windows PostgreSQL, set pg_hba.conf to `trust` for 127.0.0.1 to avoid password prompts in dev.
- **PostgreSQL password in .env**: If pg_hba.conf uses `trust` for local connections, the password field is ignored.
- **Absolute rate limit is separate**: `limits.rate.enabled: false` does NOT disable `limits.absoluteRate.register` (25/hr default). Disable both for bulk registration.
- **`\"bot\": true` rejected**: Spacebar's schema uses `additionalProperties: false`. Sending `\"bot\": true` returns a 50035 validation error. Register bots as regular users.
- **Guild `description` field rejected**: Spacebar's guild creation endpoint also uses `additionalProperties: false`. Omitting `description` from the POST body fixes `{\"code\":50035,\"message\":\"Invalid Form Body\"}`. Create guilds with `{\"name\":\"Guild Name\"}` only.
- **Duplicate users block login**: Spacebar's `User.findOneOrFail()` can return any matching user when multiple accounts share the same username (from repeated registrations or DB restores). If login returns `INVALID_LOGIN` for a known password, check for duplicates: `SELECT id FROM users WHERE username='X' ORDER BY created_at DESC`. Delete older copies, keeping only the most recently created one. See `references/login-troubleshooting.md`.
- **Python bcrypt != Node.js bcrypt**: Python's bcrypt library generates `$2b$` hashes that Node.js cannot verify, even though `bcrypt.checkpw()` returns True in Python. Always generate password hashes using Node.js `require('bcrypt').hashSync(pw, 10)` when updating Spacebar user passwords via the DB. See `references/login-troubleshooting.md`.
- **PostgreSQL password desync after restore**: After `pg_dump` + restore to a new cluster, the role password may stop working. Fix: `sudo -u postgres psql -c "ALTER USER hamilton WITH PASSWORD 'the-password';"` then restart Spacebar after killing ALL stale processes with `fuser -k 3100/tcp`. See `references/login-troubleshooting.md`.
- **Guild owner mismatch**: Re-running deploy scripts creates a new admin user, but the guild stays owned by the old admin's ID. Delete-recreate from DB is the cleanest fix.
- **Bash JSON escaping**: Double-escaped variables (`\\\\\\\"${var}\\\\\\\"`) in curl -d strings are error-prone. Use Python or `jq` for JSON construction in scripts.
- **MSYS path translation on Windows git-bash**: When calling `python -c "..."` from a bash script, MSYS translates `${MY_REPOS}/...` paths differently for bash (which understands them) vs Python (which receives them untranslated). Python may raise `FileNotFoundError` on paths that `ls` shows as existing. **Fix:** Use a temp Python script file (`cat > /tmp/script.py << 'PYEOF' ... PYEOF`) and pass paths as `sys.argv`, avoiding inline Python with shell-expanded paths.
