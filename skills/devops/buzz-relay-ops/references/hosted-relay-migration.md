# Hosted Relay Migration — Session Reference

Concrete reproduction recipe and error messages from migrating a local buzz relay
(`ws://localhost:3000`) to Block's managed hosted relay (`wss://*.communities.buzz.xyz`).

## Relay URL Structure

```
wss://<name>.communities.buzz.xyz
```

No path prefix needed. Standard Nostr WebSocket protocol.

## Error: kind 39000 rejected on hosted relay

```
EVENT REJECTED: restricted: unknown event kind
```

The hosted relay does not accept kind 39000 (group metadata) events.
Channel descriptions must be set through the Buzz Desktop app UI.

## Error: kind 5 deletion requires event author

```json
["OK", "<event_id>", false, "invalid: must be event author"]
```

On hosted relays, only the original event author can delete their events.
Community owners cannot delete events authored by auto-generated keys
even with proper NIP-OA auth tag proof.

## Error: Query returns 0 without author filter

Queries like `{"kinds": [9007], "limit": 100}` return 0 results on hosted
relays without an `authors` filter:

```python
# BROKEN — returns 0 on hosted
results = client.query({"kinds": [9007], "limit": 100})

# WORKS
results = client.query({"authors": [pubkey], "kinds": [9007], "limit": 100})
```

## Default Agents Created by Buzz Desktop

| Name | Pubkey (prefix) | Event ID | Can Delete? |
|------|-----------------|----------|-------------|
| Fizz | `ef9f1f200854d154...` | `0e4f70eddaaedcf6...` | ❌ different author |
| Honey | `3849c4c0dffa7c6e...` | `cd0cd152b8389835...` | ❌ different author |
| Bumble | `ef3400c17f9e853b...` | `83e866c728031938...` | ❌ different author |

Each has `auth` tag linking to community owner but the `pubkey` field is
a generated key whose private key no one holds.

## Default Channels Created by Buzz Desktop

| Name | Event ID | Can Delete? |
|------|----------|-------------|
| Welcome | `e865991c7b8d3e01...` | ✅ authored by community owner |
| welcome-everyone | `5bbe64ba5e3c3e85...` | ✅ authored by community owner |
| general (1st) | `a4e610e872a11766...` | ✅ authored by community owner |

### Duplicate General Channel Trap

The Buzz Desktop onboarding creates a `#general` channel with a specific UUID
AUTOMATICALLY. When you also create `#general` via kind 9007 during migration,
you end up with TWO `#general` channels — one with the Desktop-generated UUID
and one with your migration-generated UUID. The Desktop app may show only one.

**Detection:**
```python
# Query existing channels BEFORE creating new ones
existing = client.query({"authors": [pubkey], "kinds": [9007], "limit": 100})
existing_names = {}
for evt in existing:
    name = ""
    h_uuid = ""
    for t in evt.get("tags", []):
        if t[0] == "name": name = t[1]
        if t[0] == "h": h_uuid = t[1]
    if name:
        existing_names[name] = h_uuid

# If general already exists, reuse its UUID
if "general" in existing_names:
    chans["general"] = existing_names["general"]
    print(f"Reusing existing UUID: {existing_names['general'][:12]}...")
```

**Fix:** After creating all channels, query the relay for the ACTUAL UUIDs and
update your local map to match the relay's view:

```python
mismatch = 0
for name, expected_uuid in local_chans.items():
    actual_uuid = existing_names.get(name, "")
    if actual_uuid != expected_uuid:
        mismatch += 1
        print(f"MISMATCH #{name}: relay={actual_uuid[:12]}... local={expected_uuid[:12]}...")
```

## Populating Channels with History After Migration

After channels are created on the hosted relay, populate each with a
kickoff/context message. Use a CHANNEL_MAP dict that pairs channel names
with the owning profile and a context message:

```python
CHANNEL_MAP = {
    "engineering": ("dev-lead", "Engineering channel — agent engine dev, code reviews."),
    "devops": ("qa-lead", "DevOps channel — CI/CD, infrastructure, monitoring."),
    # ... one entry per channel
}

for ch_name, (profile, message) in CHANNEL_MAP.items():
    ch_uuid = chans.get(ch_name)
    if not ch_uuid:
        continue
    client.send_event(9, message, [["h", ch_uuid]])
    time.sleep(0.3)  # rate limit
```

Post with rate limiting (~3/sec) to avoid overwhelming the relay. 57 channels
at 0.3s spacing takes ~17 seconds.

## Profile .env Update After Migration

```env
# Before (local relay)
BUZZ_RELAY_URL=ws://localhost:3000
BUZZ_CHANNEL_UUIDS=83d29edd-27bd-4d30-8b00-...

# After (hosted relay)
BUZZ_RELAY_URL=wss://your-relay.communities.buzz.xyz
BUZZ_CHANNEL_UUIDS=<new-uuid-1> <new-uuid-2> ...
BUZZ_HOSTED_RELAY=wss://your-relay.communities.buzz.xyz
```

Update all 47 profile .env files in batch — replace RELAY_URL, regen CHANNEL_UUIDS
from the new channel map, and optionally add BUZZ_HOSTED_RELAY as a reference.

## Smoke Test Steps

```python
from buzz_client import BuzzClient, load_profile_key
sk = load_profile_key("the operator")  # community owner's key
client = BuzzClient(sk, relay_url="wss://<name>.communities.buzz.xyz")
ok = client.connect()
assert ok, "Auth failed on hosted relay"

# Send channel message
eid = client.send_channel_message("general", "Smoke test")
assert eid, "Message send failed"

# Query back
results = client.query({"authors": [client.pubkey], "kinds": [9], "limit": 1})
assert len(results) > 0, "Query returned empty"

client.close()
```
