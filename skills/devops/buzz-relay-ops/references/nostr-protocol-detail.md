# Nostr Protocol Details — Buzz Relay Interaction

Session transcript: end-to-end setup of block/buzz relay with NIP-42 auth,
channel creation, and message flow using the Python `nostr_protocol` library.

## Library Quirks

### `nostr_protocol` (Python FFI bindings)

| Operation | Correct API |
|-----------|------------|
| Generate keys | `Keys.generate()` |
| Parse secret key | `Keys.parse(hex_str)` |
| Get public key hex | `keys.public_key().to_hex()` |
| Get event ID hex | `event.id().to_hex()` |
| Get author hex | `event.author().to_hex()` |
| Get signature | `event.signature()` (already hex string) |
| Create tag | `Tag.parse(["h", "value"])` |
| Create event | `EventBuilder(Kind(9), "content", [tags...])` |
| Sign event | `builder.to_event(keys)` |
| Timestamp now | `event.created_at().as_secs()` |
| Timestamp from lib | use `Timestamp.now()` or `Timestamp.from_secs(int)` |

### WRONG patterns that fail:

```python
# ❌ str(event.id()) → "EventId { inner: ... }" — debug format, NOT hex!
# ✅ event.id().to_hex()

# ❌ Tag("h", "engineering") → "This class has no default constructor"
# ✅ Tag.parse(["h", "engineering"])

# ❌ Keys.from_sk(hex) → AttributeError
# ✅ Keys.parse(hex)

# ❌ event.public_key() → AttributeError
# ✅ event.author()

# ❌ PublicKey or EventId from str() — gives debug representation
# ✅ .to_hex() for hex string
```

## NIP-42 Auth Flow

```
1. Connect WebSocket to ws://localhost:3000

2. Receive:  ["AUTH", "<challenge_hex>"]

3. Build kind 22242 event:
   kind: 22242
   content: ""
   tags: [["challenge", "<challenge>"], ["relay", "ws://localhost:3000"]]
   Sign with profile's secret key

4. Send:  ["AUTH", <event_dict>]

5. Receive:  ["OK", "<event_id>", true, ""]  → authenticated
```

## Channel Creation (kind 9007)

```python
tags = [
    ["h", str(uuid4())],           # ← YOU generate this UUID
    ["name", "engineering"],       # ← required, non-empty
    ["visibility", "open"],        # open or closed
    ["channel_type", "stream"],    # stream or forum
    ["about", "Description"],      # optional
]

event = make_event(keys, 9007, "", tags)
ws.send(json.dumps(["EVENT", event]))
# Response: ["OK", "<event_id>", true, ""] → created!
```

The channel UUID is what you sent in the `h` tag. Save the UUID → name mapping.

## Channel Message (kind 9)

```python
tags = [["h", "<channel_uuid>"]]  # ← UUID, not name!

event = make_event(keys, 9, "Hello!", tags)
ws.send(json.dumps(["EVENT", event]))
# Response: ["OK", "<event_id>", true, ""] → accepted!
```

## Query Events

```python
ws.send(json.dumps(["REQ", "sub1", {
    "kinds": [9],
    "authors": ["<pubkey_hex>"],
    "limit": 10,
}]))
# Receives: EVENT + EVENT + ... + EOSE
```

## Event ID Computation (NIP-01)

The `id` field must match `sha256(JSON.stringify(serialized))` where serialized is:

```python
import json, hashlib
serialized = json.dumps(
    [0, pubkey, created_at, kind, tags, content],
    separators=(',', ':'),  # ← NO WHITESPACE
    ensure_ascii=False,
)
event_id = hashlib.sha256(serialized.encode()).hexdigest()
```

The `separators=(',', ':')` is critical. Default `json.dumps` adds spaces after `,` and `:`, which produces a different hash.

## Relay Architecture

```
buzz relay (port 3000, Rust)
  ├── Postgres (events + FTS search)
  ├── Redis (pub/sub + presence)
  └── MinIO (Blossom media storage)

Auth: NIP-42 required for all EVENT/REQ/COUNT operations
Channels: NIP-29 group chat (kind 9)
Channel creation: kind 9007
```

## Key Relay Config

```yaml
# Environment variables
BUZZ_BIND_ADDR: 0.0.0.0:3000
BUZZ_HEALTH_PORT: "8080"
DATABASE_URL: postgres://buzz:password@postgres:5432/buzz
REDIS_URL: redis://:password@redis:6379
BUZZ_S3_ENDPOINT: http://minio:9000
BUZZ_AUTO_MIGRATE: true
```
