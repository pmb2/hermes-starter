# Spacebar VPS Token Generation

> **Problem:** Hermes bot profiles need valid Spacebar API tokens signed with the VPS instance's keypair. The tokens stored in `spacebar-tokens.env` (from local Docker) are signed with a different `jwtSecret` and cannot authenticate against the production VPS server.
>
> **Solution:** Generate tokens directly on the VPS using Spacebar's own ECDSA P-521 (ES512) keypair + the `sessions` table in PostgreSQL. No API calls needed — the token is signed locally and the session is inserted directly into the DB.

## Token Architecture (Spacebar v3)

Spacebar uses **ES512** (ECDSA P-521) JWT tokens, NOT HS256 with the config's `jwtSecret`. The keypair lives in two files:

| File | Location | Purpose |
|------|----------|---------|
| `jwt.key` | `/opt/spacebar/jwt.key` | ECDSA P-521 private key (PEM, sec1 format) |
| `jwt.key.pub` | `/opt/spacebar/jwt.key.pub` | ECDSA P-521 public key (PEM, SPKI format) |
| `jwtSecret` | `config.production.json` | Only used for HS256 fallback (v1 tokens), NOT for v3 token generation |

### JWT Payload Format

```json
{
  "id": "<snowflake_user_id>",
  "iat": <unix_timestamp_seconds>,
  "kid": "<sha256_of_public_key_pem>",
  "ver": 3,
  "did": "<session_id>"
}
```

| Field | Source | Notes |
|-------|--------|-------|
| `id` | `users.id` from PostgreSQL | Discord-style Snowflake ID |
| `iat` | Current time in seconds | `Math.floor(Date.now() / 1000)` |
| `kid` | SHA-256 of `jwt.key.pub` contents | `crypto.createHash('sha256').update(publicKey).digest('hex')` |
| `ver` | Hardcoded to 3 | Token format version; `generateToken()` in `@spacebar/util` sets this |
| `did` | UUID-like session ID | References `sessions.session_id` in PostgreSQL. Must be a unique string. |

### Auth Header

Spacebar strips `Bot ` and `Bearer ` prefixes before validation:

```javascript
token = token.replace("Bot ", "");
token = token.replace("Bearer ", "");
```

The `Authorization` header can be either:
- `Authorization: Bot <jwt>` (Discord-compatible)
- `Authorization: Bearer <jwt>` (OAuth2-style)
- `Authorization: <jwt>` (bare)

### Session Table

The `sessions` table stores the `session_id` (referenced in the JWT's `did` field). The token validation code looks up the session:

```javascript
decoded.did ? Session.findOne({ where: { session_id: decoded.did, user_id: decoded.id } }) : undefined
```

If `did` is present but the session doesn't exist, authentication FAILS with 401.

### Schema

```sql
\d sessions
  user_id       | bigint      | NOT NULL
  session_id    | varchar     | NOT NULL (PK)
  activities    | jsonb       | DEFAULT '[]'
  client_info   | jsonb       | DEFAULT '{}'
  status        | varchar     | DEFAULT 'offline'
  client_status | jsonb       | DEFAULT '{}'
  is_admin_session | boolean  | DEFAULT false
  created_at    | timestamp   | DEFAULT now()
```

## Generation Flow

```
1. Connect to PostgreSQL → INSERT session row (user_id, session_id)
2. Read jwt.key + jwt.key.pub from filesystem
3. Compute kid = sha256(public_key_pem)
4. Build payload { id, iat, kid, ver: 3, did: session_id }
5. Sign with jwt.key using algorithm: ES512
6. Auth header format: "Bot " + token
```

### Verification

After generating a token, verify it against the Spacebar API:

```bash
curl -s http://localhost:3100/api/v9/users/@me \
  -H "Authorization: Bot <token>"
```

**Expected response (200):**
```json
{
  "id": "<discord-channel-id>",
  "username": "chief-of-staff",
  "bot": true,
  "premium": true,
  "premium_type": 2
}
```

**Failure modes:**

| Response | Cause | Fix |
|----------|-------|-----|
| `500: Failed to decode token` | Malformed JWT (bad base64, wrong format) | Check payload structure matches v3 format |
| `401: Invalid Token meow JsonWebTokenError: invalid signature` | Wrong signing key or algorithm | Use `jwt.key` (ES512), not `jwtSecret` config |
| `401: User not found` | `id` in payload doesn't match any `users` row | Check user ID exists in DB |
| `401: Invalid Token` (no detail) | Token issued before `valid_tokens_since` or user disabled | Check `user.data.valid_tokens_since` and `user.disabled` fields |
| `401: User disabled` | `users.disabled = true` | Set `disabled = false` |

## Batch Generation

The reusable script at `scripts/generate-vps-tokens.js` handles the full batch flow:

```bash
# On VPS:
cd /opt/spacebar && node /path/to/generate-vps-tokens.js

# Custom DB URL:
DATABASE_URL="postgres://user:***@host:5432/db" node generate-vps-tokens.js

# Custom key directory:
KEY_DIR="/custom/path" node generate-vps-tokens.js
```

The script:
1. Connects to PostgreSQL and deletes old `TOK_%` sessions
2. Queries all `bot=true` users
3. Creates a session + signs a JWT for each
4. Writes `vps-bot-tokens.env` with `SPACEBAR_BOT_<NAME>=Bot <token>` format
5. Verifies the first generated token against `localhost:3100`

## Integrating Tokens into Hermes Profiles

Each Hermes profile needs a `.env.spacebar` file with the token:

```
export SPACEBAR_BOT_TOKEN=<raw_jwt_no_prefix>
export SPACEBAR_GATEWAY_URL=wss://discy.your-domain.example/
export SPACEBAR_GUILD_ID=<discord-channel-id>
export SPACEBAR_API_URL=https://discy.your-domain.example/api/v9
```

**Note:** The `.env.spacebar` file stores the **raw JWT** (without the `Bot ` prefix). The gateway adds the prefix when making API calls. The `generate-vps-tokens.js` script outputs `Bot <token>` format — strip the `Bot ` prefix when writing to `.env.spacebar`.

The Hermes adapter (discord/spacebar) constructs the auth header as:
```python
auth_headers = {"Authorization": f"Bot {token}"}
```

## Why Not Use the Config's jwtSecret?

Spacebar's `config.production.json` has a `jwtSecret` field, but this is only used for **HS256 v1 legacy tokens** (`dec.header.alg == "HS256"`). Modern Spacebar (v3) uses **ES512** tokens signed with the ECDSA keypair from `jwt.key`/`jwt.key.pub`.

The `generateToken()` function in `@spacebar/util` always uses ES512:

```javascript
async function generateToken(id, isAdminSession = false) {
  const keyPair = await loadOrGenerateKeypair(); // loads jwt.key/jwt.key.pub
  // ... creates session ...
  const payload = { id, iat, kid: keyPair.fingerprint, ver: 3, did: session_id };
  jwt.sign(payload, keyPair.privateKey, { algorithm: "ES512" });
}
```

Using the config's `jwtSecret` for HS256 signing was the v1 approach and is deprecated.

## Troubleshooting

### "Failed to decode token" with my JWT

Your JWT doesn't parse as valid JSON after base64 decoding. Common causes:
- Payload includes fields with `undefined` values (JavaScript serializes these as the string `"undefined"`)
- The `iat` or `exp` fields are not numeric
- The `id` field is not a string

### "invalid signature" with old tokens

Tokens were signed with a different Spacebar instance's key (e.g., local Docker vs VPS). **Each Spacebar instance generates a unique keypair.** Regenerate tokens on the target VPS.

### Session not found

The `did` field in your JWT references a `session_id` that doesn't exist in the `sessions` table. Either:
- The session was deleted or expired
- The token was generated on a different instance
- The DB was reset (tokens are invalidated on DB reset)
