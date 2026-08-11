# Spacebar JWT Keypair Recovery & Migration

> **Problem:** Migrating a Spacebar PostgreSQL backup to a new instance (e.g., VPS → local desktop) breaks bot authentication. Bot tokens signed with instance A's keypair are rejected by instance B with "invalid signature" — even though the DB dump, guild records, and bot users all transferred correctly.
>
> **Root cause:** Spacebar signs bot tokens with an **ES512 ECDSA keypair** stored in `jwt.key`/`jwt.key.pub` — NOT with the `jwtSecret` in `config.production.json`. Each `node start.js` run generates a fresh keypair on first boot. Moving the DB doesn't move the keys; the new instance has different keys.
>
> **Fix:** Copy the keypair files from the source instance to the destination, replacing the auto-generated files. Restart is mandatory — keys are read into memory at process startup and cached for the process lifetime.

## Key File Locations

| File | Purpose | Format |
|------|---------|--------|
| `jwt.key` | ECDSA P-521 private key | PEM, sec1 format (`BEGIN EC PRIVATE KEY`) |
| `jwt.key.pub` | ECDSA P-521 public key | PEM, SPKI format (`BEGIN PUBLIC KEY`) |

Both files live in the **Spacebar working directory** (the `cwd` where `node dist/bundle/start.js` runs, typically `/opt/spacebar/` on a VPS or `C:\path\to\spacebar\` on Windows).

## How Key Loading Works

From `dist/util/util/Token.js`:

```javascript
async function loadOrGenerateKeypair() {
    // Check for existing key files
    if (existsSync("jwt.key") && existsSync("jwt.key.pub")) {
        // Load from files
        const [privateKey, publicKey] = await Promise.all([
            readFile("jwt.key"),
            readFile("jwt.key.pub"),
        ]);
        cachedKeypair = { privateKey, publicKey, fingerprint: sha256(publicKey) };
    } else {
        // Generate fresh keypair and save to files
        const gen = generateKeyPairSync("ec", { namedCurve: "P-521" });
        cachedKeypair = { ...gen, fingerprint: sha256(gen.publicKey) };
        writeFile("jwt.key", gen.privateKey.export({ format: "pem", type: "sec1" }));
        writeFile("jwt.key.pub", gen.publicKey.export({ format: "pem", type: "spki" }));
    }
    return cachedKeypair;
}
```

**Critical detail:** `cachedKeypair` is a module-scoped singleton. Once loaded, replacing the files on disk has zero effect. Only a process restart triggers re-read.

## Token Validation Pipeline

Spacebar validates bot tokens in `checkToken()` (same source file):

```javascript
const checkToken = (token, opts) => {
    token = token.replace("Bot ", "").replace("Bearer ", "");

    // Step 1: Try HS256 (config.jwtSecret)
    jwt.verify(token, Config.get().security.jwtSecret, { algorithms: ["HS256"] }, validateUser);

    // Step 2: If HS256 fails, try ES512 (ECDSA keypair)
    loadOrGenerateKeypair().then((keyPair) => {
        jwt.verify(token, keyPair.publicKey, { algorithms: ["ES512"] }, validateUser);
    });

    // Step 3 (in validateUser callback):
    //   - Check valid_tokens_since: token.iat * 1000 < valid_tokens_since → reject
    //   - Check user disabled → reject
    //   - If payload has `did` (session_id): verify session exists in DB
};
```

## Diagnosing Token Rejection

When a bot's gateway connects but gets `HTTP Error 401: Unauthorized`, check the **Spacebar server logs** (the Node.js stdout). There are two distinct error patterns:

### Pattern A: "Invalid Token meow JsonWebTokenError: invalid signature"

**Cause:** ECDSA keypair mismatch. The token was signed with a different `jwt.key` than the one the server loaded.

**Frequency:** One log line per failed token validation attempt. A retrying bot generates 5-10+ lines per minute.

**Fix:**
```bash
# 1. Kill the Spacebar process
taskkill //PID <PID> //F         # Windows
kill <PID>                       # Linux

# 2. Verify port is free
netstat -ano | findstr :3100     # Windows — no LISTEN lines = free
ss -tlnp | grep 3100             # Linux — empty = free

# 3. Copy source keypair over auto-generated files
cp /path/to/source/jwt.key /opt/spacebar/jwt.key
cp /path/to/source/jwt.key.pub /opt/spacebar/jwt.key.pub

# 4. Verify checksums match source
md5sum /opt/spacebar/jwt.key      # Should match source
md5sum /opt/spacebar/jwt.key.pub  # Should match source

# 5. Restart Spacebar
# (depends on deployment — node direct, systemd, or npm start)
cd /opt/spacebar && node dist/bundle/start.js
```

**Verification:** Server should show `[Server] Listening on port 3100` without any `Invalid Token` lines in the log. A bot connecting should show `IDENTIFY <user_id> in <N>ms ✅` instead of `Invalid Token meow`.

### Pattern B: "Invalid Token" (no detail, no stack trace)

**Cause:** Token was issued before `valid_tokens_since` on the `users` table, or `valid_tokens_since` was reset forward (common when restoring a DB dump into a fresh instance where the system clock or migration timestamp differs).

**Fix:**
```sql
-- Reset valid_tokens_since for all bot users
UPDATE users SET valid_tokens_since = '0' WHERE bot = true;

-- Or for specific users:
UPDATE users SET valid_tokens_since = '0' WHERE username = 'chief-of-staff';
```

The `valid_tokens_since` field is checked in `checkToken()`:
```javascript
if (decoded.iat * 1000 < new Date(user.data.valid_tokens_since).setSeconds(0, 0)) {
    return void rejectAndLog(reject, 401, "Invalid Token");
}
```

Setting it to `'0'` means all tokens (past, present, future) are accepted. Reset only for bot users — human users get security from this field.

## Full Recovery Procedure

When migrating Spacebar to a new machine (e.g., VPS → local desktop):

```bash
# 1. Get source keypair
scp -i <key> ubuntu@<vps>:/opt/spacebar/jwt.key /tmp/
scp -i <key> ubuntu@<vps>:/opt/spacebar/jwt.key.pub /tmp/

# 2. Install on destination
cp /tmp/jwt.key /path/to/spacebar/jwt.key
cp /tmp/jwt.key.pub /path/to/spacebar/jwt.key.pub

# 3. Ensure DB is restored (dump from source)
#    (includes all users, guilds, members, etc.)

# 4. Reset valid_tokens_since for bot users
psql -U <user> -d spacebar -c "UPDATE users SET valid_tokens_since = '0' WHERE bot = true;"

# 5. Kill any running Spacebar process
taskkill //F //IM node.exe 2>nul && sleep 2

# 6. Verify port is free
netstat -ano | findstr :3100 | findstr LISTEN || echo "port 3100 free"

# 7. Start Spacebar
cd /path/to/spacebar && node dist/bundle/start.js

# 8. Test a bot token
curl -s http://localhost:3100/api/v9/users/@me \
  -H "Authorization: Bot <existing-token>"
# Expected: 200 with user object including {"bot": true}
# NOT: 401 "Invalid Token"
```

## Finding the Key Handling Code in the Source

If you need to trace token validation behavior at the source level:

```bash
# Find compiled files that reference ECDSA key operations
cd /path/to/spacebar
grep -rl "ecdhKeyPair\|ECDSA\|ed25519" dist/ | head -10
# → dist/util/util/Token.js  (in a standard Spacebar build)
```

This reveals the key functions:

| Function | Role |
|----------|------|
| `loadOrGenerateKeypair()` | Reads or creates `jwt.key`/`jwt.key.pub` from `process.cwd()`. Called once at first token validation. |
| `checkToken(token, opts)` | Token validation pipeline: tries HS256 (`jwtSecret`) → ES512 (keypair) → error. |
| `generateToken(id, isAdminSession)` | Signs a new JWT with the private key (ES512, `kid` = key fingerprint). |

## After-Restart Verification Checklist

After swapping keys and restarting, monitor the Spacebar stdout for these signals:

### ✅ Server Started
```
[Server] Listening on port 3100
```
If you see `Error: listen EADDRINUSE`, the old process is still alive.

### ✅ Token Accepted (Per Bot Connect)
```
[Gateway/<discord-channel-id>] IDENTIFY <discord-channel-id> in 108ms 
```
A successful IDENTIFY in under 2000ms means the token validated correctly against the keypair.

### ❌ Keys Wrong
```
Invalid Token meow JsonWebTokenError: invalid signature
```
If ANY `Invalid Token` or `invalid signature` lines appear in the Spacebar log, the keys in memory do not match the tokens' signer. Kill the process, verify the key files, and restart.

### ❌ REST 401 (Gateway-side)
```
urllib.error.HTTPError: HTTP Error 401: Unauthorized
```
If the gateway shows 401 on every REST call, either the token is wrong OR the Spacebar instance processing the request has wrong keys.

## The "Worked Once Then Stopped" Pattern

**Symptom:**
1. You copy VPS keys, restart Spacebar
2. The bot connects successfully (IDENTIFY ✅ in 80-100ms, seen in Spacebar logs)
3. Several minutes later, the bot gateway starts getting 401 errors
4. Spacebar shows `Invalid Token meow JsonWebTokenError: invalid signature`

**Root cause:** There were **two Spacebar processes** at different times:
1. The OLD process (local keys, PID `A`) has been running on port 3100 
2. You launch a NEW process (VPS keys, PID `B`) — it briefly succeeds but exits within minutes (exit code 1 or -15)
3. When PID `B` exits, the old process PID `A` resumes the port (or re-binds when B frees it)
4. The bot gateway, retrying in the background, reconnects to port 3100 — now served by PID `A` with local keys
5. `Invalid Token meow` is back

**Fix:** Verify with `netstat -ano | findstr :3100 | findstr LISTEN` to get the PID of the actual listener. Kill it by PID, not by `taskkill //IM node.exe` (which might miss a detached process). Then start fresh.

To verify only ONE Spacebar is running:
```bash
# List ALL listening processes on port 3100
netstat -ano | findstr :3100 | findstr LISTEN
# Should show exactly one row. Note the PID.
wmic process where processid=<PID> get name,processid,creationdate /format:csv
# Confirm it's a node.exe that started AFTER your key copy
```

## Fleet-Level Verification

After fixing keys and restarting Spacebar, verify the fleet connects:

```bash
# 1. Launch fleet manager
cd ${MY_REPOS}/agent-fleet/scripts
python spacebar-fleet-manager.py

# 2. Watch Spacebar log for metrics:
#    - Total gateway connections: "New connection from ::1, total 48"
#    - Successful IDENTIFYs: "IDENTIFY <user_id> in <N>ms"
#    - No Invalid Token lines

# 3. Check no bot gets 401:
grep -c "Invalid Token" /path/to/spacebar/logs
# Should return 0 after the key swap

# 4. Verify bot session status in DB:
docker exec spacebar-postgres psql -U spacebar_admin -d spacebar -c \
  "SELECT COUNT(*) FROM sessions s JOIN users u ON u.id=s.user_id WHERE u.bot=true AND s.status='online';"
# Expected: close to 39 (some may be between connect/disconnect cycles)
```

## Common Pitfalls

- **Copying keys while Spacebar is running has no effect.** Keys are read once at process start and cached. You must kill the process, wait for the port to free, replace keys, then restart. Copying keys and then hitting EADDRINUSE during restart means the OLD process is still alive with old keys.

- **Multiple Spacebar processes on the same port.** If `netstat` shows port 3100 as LISTENING but `process(action='list')` shows no running processes in your terminal session, there's a detached node.exe instance. Find it with `netstat -ano | findstr :3100` and `taskkill //PID <PID> //F`.

- **`valid_tokens_since` is in the DB, not on the keypair.** Even with the correct keypair, a `valid_tokens_since` in the future (from DB migration timestamp drift) causes silent rejection with no signature error.

- **HS256 vs ES512 confusion.** The `jwtSecret` in `config.production.json` is NOT used for bot tokens. Bot tokens use ES512 with the ECDSA keypair. The HS256 path is a v1 legacy fallback and only matches if the token header's `alg` is `"HS256"`, which no modern client sends.

## EADDRINUSE Resolution

When attempting to restart Spacebar and getting `Error: listen EADDRINUSE: address already in use :::3100`:

1. The old Spacebar process is still alive (keys in memory are the OLD ones)
2. Your key file copy never took effect
3. Even if you copied VPS keys, the running process has old keys cached

**Fix:**
```bash
# Find and kill the actual holding process
netstat -ano | findstr :3100 | findstr LISTEN
# → TCP    0.0.0.0:3100    LISTENING    <PID>
taskkill //PID <PID> //F

# Wait for cleanup
sleep 3

# Verify free
netstat -ano | findstr :3100 | findstr LISTEN || echo "Free"

# Now copy keys and restart
```
