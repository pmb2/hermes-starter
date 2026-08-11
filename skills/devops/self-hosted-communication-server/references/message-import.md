# message-import.md — Importing Discord Messages into Spacebar

## Required Message Fields

Spacebar's `messages` table has several NOT NULL columns that must be set correctly when importing messages directly via SQL:

| Column | Type | Import Value | Notes |
|--------|------|-------------|-------|
| `id` | bigint | Discord message ID | Must be a unique snowflake |
| `channel_id` | bigint | Spacebar channel ID | Must match an existing channel in the guild |
| `guild_id` | bigint | Spacebar guild ID | Must match the guild |
| `author_id` | bigint | User ID | Must match an existing user in the DB |
| `content` | varchar | Message text | Can include markdown and emoji |
| `timestamp` | timestamp | Discord ISO timestamp | e.g. `2026-05-30T20:55:24.391000+00:00` |
| `embeds` | jsonb | `'[]'::jsonb` | Array of embed objects |
| `reactions` | jsonb | `'[]'::jsonb` | **Must be array, NOT object** |
| `type` | integer | `0` | 0 = DEFAULT |
| `flags` | integer | `0` | |
| `mention_everyone` | boolean | `false` | |
| `tts` | boolean | `false` | |
| `pinned_at` | timestamp | `NULL` | |
| `message_snapshots` | jsonb | `'[]'::jsonb` | Array of message snapshots |

## CRITICAL: `reactions` Must Be Array

The most common import error: using `'{}'::jsonb` for reactions (empty object)
instead of `'[]'::jsonb` (empty array). Spacebar's message serialization calls
`.forEach()` on the reactions field, which fails on objects:

```json
{"code": 500, "message": "TypeError: (x.reactions || []).forEach is not a function"}
```

**Fix existing messages:**
```sql
UPDATE messages SET reactions = '[]'::jsonb WHERE reactions = '{}'::jsonb;
```

## Import SQL Template

```sql
INSERT INTO messages (id, channel_id, guild_id, author_id, content, timestamp,
    embeds, reactions, type, flags, mention_everyone, tts,
    pinned_at, nonce, message_reference, message_snapshots)
VALUES (
    %s::bigint,           -- message ID
    %s::bigint,           -- channel ID
    %s::bigint,           -- guild ID
    %s::bigint,           -- author ID
    %s,                   -- content (text)
    %s,                   -- timestamp
    '[]'::jsonb,          -- embeds
    '[]'::jsonb,          -- reactions (MUST be array)
    0,                    -- type
    0,                    -- flags
    false,                -- mention_everyone
    false,                -- tts
    NULL,                 -- pinned_at
    NULL,                 -- nonce
    NULL,                 -- message_reference
    '[]'::jsonb           -- message_snapshots
)
ON CONFLICT (id) DO NOTHING;
```

## Author Mapping

When messages from Discord are authored by users that don't exist in Spacebar's DB
(e.g. "Hermes Agent", "the.engineer"), map them to a fallback user (e.g. "architect"
or the user who performed the migration). Create mismatched Discord authors as users
in Spacebar if they need to retain message attribution.

## Thread Messages

Thread messages from Discord lack a `channel_id` that maps directly to a Spacebar
text channel. Import them into their parent channel (the text channel the thread
was created from). Prefix the content or add a note if thread attribution matters.

## Duplicate Prevention

Use `ON CONFLICT (id) DO NOTHING` to safely re-run imports. Messages with IDs
that already exist in the DB are skipped.
