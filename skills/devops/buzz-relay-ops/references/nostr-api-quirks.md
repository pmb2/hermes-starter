# Nostr Protocol API Quirks (nostr_protocol Python library)

Library: `pip install nostr-protocol`  
Module: `from nostr_protocol import Keys, EventBuilder, Kind, Tag, Timestamp`

## Type Map

| Nostr Concept | Python Type | Key Methods |
|--------------|-------------|-------------|
| Private key | `SecretKey` (opaque) | — |
| Public key | `PublicKey` | `.to_hex()`, `.to_bech32()` |
| Event ID | `EventId` | `.to_hex()` |
| Signature | `str` (bare hex) | Already a string, no `.to_hex()` |
| Event | `Event` | `.id()`, `.author()`, `.kind()`, `.tags()`, `.content()`, `.signature()`, `.verify()` |
| Timestamp | `Timestamp` | `.as_secs()`, `.now()` |
| Tag | `Tag` | `.as_vec()`, `Tag.parse(list)` |

## Critical: str() vs .to_hex()

This is the most common bug:

```python
# WRONG — produces "EventId { inner: ... }" debug format
str(event.id())         # → "EventId { inner: P..."
str(event.author())     # → "PublicKey { inner: P..."

# RIGHT — produces hex string relay expects
event.id().to_hex()      # → "bc29af95bf1a2ec1..."
event.author().to_hex()  # → "9d207110b721e158..."

# signature is ALREADY a hex string
event.signature()        # → "7bab4021653e346e..." (bare str)
# WRONG
event.signature().to_hex()  # → AttributeError: 'str' object has no attribute 'to_hex'
```

## Tag Construction

`Tag.parse()` takes a **single list argument**:

```python
# ✅ CORRECT
Tag.parse(["h", "engineering"])
Tag.parse(["challenge", "abc123"])
Tag.parse(["p", pubkey_hex])

# ❌ WRONG — "This class has no default constructor"
Tag("h", "engineering")
Tag(["h", "engineering"])
Tag.parse("h", "engineering")
```

## EventBuilder Usage

```python
# Text note (kind 1)
builder = EventBuilder.text_note("hello", [])
event = builder.to_event(keys)

# Arbitrary kind with tags
builder = EventBuilder(Kind(kind_number), "content", [tag1, tag2])
event = builder.to_event(keys)
```

## NIP-42 Auth (the correct way)

`EventBuilder.auth(challenge, relay_url)` creates a kind 22242 event. Call `.to_event(keys)` to sign:

```python
challenge = "abc123..."  # received from relay's ["AUTH", "<challenge>"]
ev = EventBuilder.auth(challenge, relay_url).to_event(keys)

# Send over WebSocket:
ws.send(json.dumps(["AUTH", json.loads(ev.as_json())]))
```

This is the ONLY correct approach — do NOT manually construct kind 22242 events.

## sign_schnorr() — NOT sign()

`Keys` has NO `.sign()` method. The correct method is `.sign_schnorr(message_bytes)`:

```python
# ✅ CORRECT
sig_hex = keys.sign_schnorr(b"message bytes")  # returns bare hex str (64 chars)
# ❌ WRONG — AttributeError: 'Keys' object has no attribute 'sign'
keys.sign(event_id)
```

`sign_schnorr` takes raw bytes, not EventId objects. Returns a bare hex `str` (no `.to_hex()`).

## to_event() handles everything

`EventBuilder.to_event(keys)` automatically:
- Computes the event `id` field (correct SHA-256 serialization)
- Signs with the key's Schnorr signature
- Sets `pubkey`, `created_at`, `kind`, `tags`, `content`, `sig`
- Returns a complete `Event` object

```python
ev = builder.to_event(keys)
ev_id = ev.id().to_hex()       # event ID hex
ev_sig = ev.signature()        # already hex str
ev_json = ev.as_json()         # serialized JSON string
```

## Keys.sign() does not exist

The `nostr_protocol` library removed `Keys.sign()`. Use `Keys.sign_schnorr(bytes)` for raw signing, or prefer `EventBuilder.to_event(keys)` for event signing.

## Signature class does not exist

There is no `Signature` class — `from nostr_protocol import Signature` raises `ImportError`. Signatures are bare hex `str` values returned by `Keys.sign_schnorr()` or `Event.signature()`.

## Key Generation and Loading

```python
# Generate new
keys = Keys.generate()
sk_hex = keys.secret_key().to_hex()     # 64-char hex
pk_hex = keys.public_key().to_hex()     # 64-char hex

# Load from existing secret key
keys = Keys.parse(sk_hex)

# Verify event
event.verify()  # → True/False
```
