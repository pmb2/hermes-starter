# Thread Channel Organization in Spacebar

When migrating from Discord, Spacebar does NOT support Discord-style threads
(sub-channels with parent_id that appear inline). Thread messages imported
into the parent channel get mixed with direct messages, losing thread context.

## Solution: Dedicated Thread Channels

For each Discord thread, create a dedicated Spacebar text channel named
`<parent>-<threadname>` (e.g., `revenue-land`, `dev-debug`, `command-get-it-done`)
under the same category as the parent. Move the thread's messages into it.

## Step-by-Step

### 1. Create channels via Spacebar API

Use the **guild owner** token (regular users may lack MANAGE_CHANNELS):

```python
import urllib.request, json

token = "<guild_owner_token>"  # login as guild owner
GUILD_ID = "<discord-channel-id>"
CATEGORY_ID = "<discord-channel-id>"  # e.g. Revenue category

data = json.dumps({
    "name": "revenue-land",
    "type": 0,  # text channel
    "parent_id": CATEGORY_ID,
}).encode()

req = urllib.request.Request(
    f"https://your-domain/api/v9/guilds/{GUILD_ID}/channels",
    data=data,
    headers={"Content-Type": "application/json", "Authorization": token},
    method="POST"
)
resp = urllib.request.urlopen(req)
result = json.loads(resp.read())
new_channel_id = result["id"]
```

### 2. Move messages via DB UPDATE

After creating the channel, move the thread's messages from the parent channel
to the new channel:

```sql
UPDATE messages SET channel_id = <new_channel_id>
WHERE id IN (<comma-separated message IDs>);
```

Batch in chunks of 500 to avoid oversized queries:

```sql
UPDATE messages SET channel_id = <discord-channel-id>
WHERE id IN (<discord-channel-id>, <discord-channel-id>, ...);
UPDATE messages SET channel_id = <discord-channel-id>
WHERE id IN (<discord-channel-id>, <discord-channel-id>, ...);
```

### 3. Update last_message_id

After moving messages, update the new channel's last_message_id:

```sql
UPDATE channels SET last_message_id = (
    SELECT id::text FROM messages
    WHERE channel_id = <new_channel_id>
    ORDER BY id DESC LIMIT 1
) WHERE id = <new_channel_id>;
```

### 4. Update the channel map

Add the new channel to `channel_map.json` for the bridge:

```json
{
  "revenue-land": {
    "discord_id": "<discord-channel-id>",
    "spacebar_id": "<discord-channel-id>"
  }
}
```

## Channel Naming Convention

Use `<parent>-<threadname>` format. Keep under 32 characters (Discord limit):

| Parent | Thread Name | Channel Name |
|--------|-------------|--------------|
| revenue | Land | `revenue-land` |
| revenue | Website Landlord | `revenue-website_landlord` |
| dev | debug | `dev-debug` |
| dev | Ferm | `dev-ferm` |
| command | Get it done. | `command-get_it_done` |
| command | Secondary | `command-secondary` |

## Category Placement

Place thread channels under the same category as their parent:

| Parent Channel | Category |
|----------------|----------|
| command, ideas | General (<discord-channel-id>) |
| dev | Technology (<discord-channel-id>) |
| revenue | Revenue (<discord-channel-id>) |
| cyber | Cyber Security (<discord-channel-id>) |
| finance, investing | Finance (<discord-channel-id>) |
| legal | Legal (<discord-channel-id>) |
| sports-betting | Sports (<discord-channel-id>) |

## Pitfall: API Permission Requirements

The Spacebar API's `POST /guilds/{id}/channels` requires MANAGE_CHANNELS
permission. A regular user (even admin bitfield) may get `50013` error.
Always use the **guild owner** account for channel creation.

If the API still fails (e.g., rate limits), insert directly into the DB:

```sql
INSERT INTO channels (id, name, type, guild_id, parent_id, position)
VALUES (<snowflake>, '<name>', 0, '<guild_id>', '<category_id>', <position>);
```

Snowflake IDs can be generated with:
```python
import time
snowflake = (int(time.time() * 1000) - 1420070400000) << 22
```

## Bridge Considerations

The bridge should NOT mirror thread channel creation to Discord (or vice versa)
to avoid spam. Disable the `on_guild_channel_create` and `_handle_channel_create`
handlers in the bridge script. Channel mapping is maintained only via the
static `channel_map.json` file.
