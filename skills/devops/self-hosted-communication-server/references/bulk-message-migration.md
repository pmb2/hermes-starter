# Bulk Message Migration — Discord to Spacebar

Complete end-to-end workflow for a full Discord→Spacebar message sweep,
covering thread discovery, delta export, author resolution, bulk import with
dedup, and post-import cleanup.

## 1. Thread Audit (Discovery)

Discord has two sources of threads. **Both must be checked.**

### Guild-Level Active Threads (catches all active threads at once)

```python
active = api_get(f"/guilds/{guild_id}/threads/active")
for t in active.get("threads", []):
    all_threads[t["id"]] = t
```

This single call returns ALL currently-active threads regardless of parent
channel. In one real migration, switching from per-channel archived search
to the guild-level active endpoint discovered **31 additional threads** with
10,000+ messages that the per-channel approach completely missed.

### Per-Channel Archived Threads (catches historical threads)

```python
for c in text_channels:
    for scope in ["public", "private"]:
        archived = api_get(f"/channels/{c['id']}/threads/archived/{scope}")
        for t in archived.get("threads", []):
            if t["id"] not in all_threads:
                all_threads[t["id"]] = t
```

Deduplicate by thread ID — many threads appear in both the active and
archived endpoints.

## 2. Full Export (All Channels + Threads)

Export ALL messages from each channel and each discovered thread using
`before`-cursor pagination (newest → oldest):

```python
def get_all_msgs(path_prefix):
    msgs = []
    before = None
    while True:
        suffix = f"&before={before}" if before else ""
        data = api_get(f"{path_prefix}?limit=100{suffix}")
        if not data or len(data) == 0:
            break
        msgs.extend(data)
        if len(data) < 100:
            break
        before = data[-1]["id"]
        time.sleep(0.3)
    return msgs
```

**Rate limit handling:** On HTTP 429, honor the `Retry-After` header and retry.
Without this, large threads (10,000+ messages) will fail partway through.

**Thread channel IDs:** Each thread has its own channel ID (the `id` field in
the thread metadata). Use `/channels/{thread_id}/messages` to get messages
from that thread.

## 3. Delta Export (Messages Since Last Run)

After the initial full export, subsequent runs should only fetch messages
newer than the last exported message ID (using `after` cursor):

```python
all_new = []
after = last_exported_id
while True:
    data = api_get(f"/channels/{thread_id}/messages?limit=100&after={after}")
    if not data or len(data) == 0:
        break
    all_new.extend(data)
    if len(data) < 100:
        break
    after = data[-1]["id"]
    time.sleep(0.25)
```

**Checkpoints:** Save the `last_message_id` for each thread after each export
so the next run knows where to start.

## 4. Author Resolution

Discord author IDs as message `author_id` cause foreign key violations on
insert because those Discord users don't exist in the Spacebar `users` table.

**Step 1: Find missing authors**
```python
all_author_ids = set()
for m in messages:
    aid = m.get("author", {}).get("id", "0")
    if aid:
        all_author_ids.add(aid)

cur.execute("SELECT id::text FROM users")
existing_users = {r[0] for r in cur.fetchall()}
missing_authors = all_author_ids - existing_users
```

**Step 2: Create placeholder users**
```sql
INSERT INTO users (
  id, username, discriminator, bot, verified, disabled, deleted,
  created_at, flags, public_flags, purchased_flags, premium_usage_flags,
  rights, data, fingerprints, desktop, mobile, premium, premium_type,
  bio, system, nsfw_allowed, mfa_enabled, webauthn_enabled
)
VALUES (<discord_author_id>, '<username>', '0000', false, false, false, false,
  now(), 0, 0, 0, 0, 0, '{}'::jsonb, '{}', false, false, false, 0,
  '', false, false, false, false)
ON CONFLICT (id) DO NOTHING;
```

**Tip:** Use `psycopg2` on the VPS to batch-create missing users before the
message import, avoiding round-trip latency for each one.

## 5. Bulk Import

The Spacebar `messages` table schema differs from Discord's raw message JSON.
The correct INSERT template is:

```python
INS = """INSERT INTO messages
(id, channel_id, guild_id, author_id, content, timestamp,
 embeds, reactions, type, flags, mention_everyone, tts, message_snapshots)
VALUES (%s::bigint, %s::bigint, %s::bigint, %s::bigint, %s, %s,
  '[]'::jsonb, '[]'::jsonb, 0, 0, false, false, '[]'::jsonb)
ON CONFLICT (id) DO NOTHING"""
```

**Critical column differences from Discord API JSON:**
- No `mentions`, `mention_roles`, `attachments`, `pinned` columns (discard them)
- `embeds` must be `'[]'::jsonb` (NOT NULL)
- `reactions` must be `'[]'::jsonb` (NOT NULL) — Spacebar iterates with `.forEach()`
- `message_snapshots` must be `'[]'::jsonb` (NOT NULL)
- `type` default 0, `flags` default 0
- Strip NUL (`\x00`) bytes from content before insert (PostgreSQL rejects them)

**Dedup:** `ON CONFLICT (id) DO NOTHING` handles re-runs safely — the
`messages` table has a PRIMARY KEY on `id`.

**Thread-to-channel mapping:** Thread messages from Discord go to the
parent Spacebar channel. Strip the thread context — Spacebar doesn't
support Discord-style threads.

## 6. Post-Import Cleanup

After all messages are imported, two fields need updating:

```sql
UPDATE channels c SET last_message_id = (
    SELECT m.id::text FROM messages m
    WHERE m.channel_id = c.id
    ORDER BY m.id DESC LIMIT 1
) WHERE EXISTS (
    SELECT 1 FROM messages m WHERE m.channel_id = c.id
);

UPDATE guilds SET member_count = (
    SELECT count(*) FROM members WHERE guild_id = guilds.id
);
```

Without this, Fermi won't scroll to recent messages and the API reports
`member_count: 1` even with 100+ members.

## 7. Verification

```sql
-- Total messages
SELECT count(*) FROM messages WHERE guild_id='<guild_id>';

-- Per-channel breakdown
SELECT c.name, count(m.id) as msgs
FROM messages m JOIN channels c ON c.id=m.channel_id
WHERE m.guild_id='<guild_id>' AND c.type=0
GROUP BY c.name ORDER BY msgs DESC;

-- Check last_message_ids updated
UPDATE channels c SET last_message_id = (...) ...;
```

Also verify from the Spacebar API:
```bash
curl -s https://domain/api/v9/channels/<channel_id>/messages?limit=3 \
  -H "Authorization: Bearer $(get-token)"
```

The 3 most recent messages should appear.
