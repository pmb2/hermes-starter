# Trilium ETAPI Auth Debugging

Trilium's ETAPI uses SHA-256 hashed tokens. The hash encoding is
**base64**, not hex — a common source of auth failures when injecting
tokens manually.

## How It Works

Trilium stores tokens in the `etapi_tokens` table:

| Column | Description |
|---|---|
| `etapiTokenId` | UUID for identifying the token |
| `name` | Human-readable name (e.g. "hermes-agent") |
| `tokenHash` | SHA-256 of the raw token, encoded as **base64** |
| `isDeleted` | Soft delete flag |

When a request comes in, the server:

1. Reads the `Authorization` header
2. Strips `Bearer ` prefix if present
3. Splits on `_` — if 2 parts, it's `<etapiTokenId>_<raw>` format
4. SHA-256 hashes the raw token portion as **base64**
5. Compares against `tokenHash` in the database

## The Hash Encoding Bug

```python
import hashlib

raw_token = "my-secret-token"

# ✓ CORRECT — Trilium uses base64 encoding:
correct_hash = hashlib.sha256(raw_token.encode()).digest("base64")
# Returns: "9XncXOZMX7g+VTh2v47L2lRpAhPj+LCNK7UjTd0AkS4="

# ✗ WRONG — hex encoding (common assumption):
wrong_hash = hashlib.sha256(raw_token.encode()).hexdigest()
# Returns: "f579dc5ce...f74024b92e"  ← won't match
```

## How to Generate a Valid Token

Use the same approach Trilium uses internally:

```python
import hashlib, secrets

raw = secrets.token_hex(32)  # 64-char hex string
token_hash = hashlib.sha256(raw.encode()).digest("base64")
print(f"Token: {raw}")
print(f"Auth header: Bearer {raw}")
```

For manual DB injection (when the UI isn't accessible):

```python
# Insert into SQLite
import sqlite3, hashlib, secrets, datetime

token = secrets.token_hex(32)
token_hash = hashlib.sha256(token.encode()).digest("base64")
token_id = secrets.token_hex(10)
now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

db = sqlite3.connect("document.db")
db.execute(
    "INSERT INTO etapi_tokens (etapiTokenId, name, tokenHash, utcDateCreated, utcDateModified, isDeleted) VALUES (?, ?, ?, ?, ?, 0)",
    (token_id, "my-token", token_hash, now, now)
)
db.execute(
    "INSERT INTO entity_changes (entityName, entityId, hash, isErased, changeId, componentId, instanceId, isSynced, utcDateChanged) VALUES (?, ?, ?, 0, ?, ?, ?, 1, ?)",
    ("etapi_tokens", token_id, "injected", token_id, "desktop", "script", now)
)
db.commit()
print(f"Token: {token}")  # Use this in Authorization header
```

## Auth Header Formats Trilium Accepts

| Format | Example |
|---|---|
| Raw token | `Authorization: tMwKRE8sfwJqWdsE6RYbq2gJp/ea+mMLInd3fuIif6w=` |
| Bearer prefix | `Authorization: Bearer tMwKRE8sfwJqWdsE6RYbq2gJp/ea+mMLInd3fuIif6w=` |
| API-created format | `Authorization: Bearer <etapiTokenId>_<raw>` |
| Basic auth (internal) | `Authorization: Basic ZXRhcGk6<base64-token>` |

## Debugging Checklist

- [ ] Token hash uses **base64**, not hex
- [ ] Token is NOT deleted in the DB (`isDeleted = 0`)
- [ ] Entity change is recorded for the etapi_tokens row
- [ ] Server was restarted after DB injection
- [ ] Trilium config has `noAuthentication=false` (auth is ON)
- [ ] `curl -s <url>/etapi/app-info -H "Authorization: Bearer $TOKEN"` returns app info
- [ ] MCP env var `TRILIUM_TOKEN` is set in `.env`
- [ ] MCP env var `TRILIUM_URL` points to the correct port (default 8080, actual may be 8090)

## ETAPI Routes Reference

| Method | Path | Purpose |
|---|---|---|
| POST | `/etapi/create-note` | Create a new note (not `/etapi/notes` — that's GET only) |
| GET | `/etapi/notes/<id>` | Get note metadata |
| GET | `/etapi/notes?search=<query>` | Search notes (not `/etapi/search/search`) |
| GET | `/etapi/notes/<id>/content` | Get note body content |
| PUT | `/etapi/notes/<id>/content` | Set note body content |
| PATCH | `/etapi/notes/<id>` | Update note metadata (title, type, mime) |
| DELETE | `/etapi/notes/<id>` | Delete a note |
| POST | `/etapi/branches` | Clone a note to another parent |
| GET | `/etapi/notes/history` | List recently modified notes |
| GET | `/etapi/app-info` | Health check / version info |
