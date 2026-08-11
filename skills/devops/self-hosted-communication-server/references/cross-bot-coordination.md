# Cross-Bot Coordination Model — One Rep Per Channel

## Problem

Multiple Hermes profiles (each a separate gateway process) share a Spacebar guild. When the operator posts in #general, every bot that can see the channel responds — creating chaos. When bots need to talk to each other (CoS → Intel), messages are silently dropped.

## Solution: One Rep Per Channel + DISCORD_ALLOW_BOTS

### 1. DISCORD_ALLOW_BOTS=all (Critical Fix)

**Root cause:** The Hermes Discord adapter's `on_message` handler (line 791 in `plugins/platforms/discord/adapter.py`) filters messages from OTHER bots. Default is `"none"` — ALL bot-originated messages are dropped unless @mentioned.

```python
if getattr(message.author, "bot", False):
    allow_bots = os.getenv("DISCORD_ALLOW_BOTS", "none").lower().strip()
    if allow_bots == "none":
        return  # ← silently drops ALL messages from other bots
```

**Fix:** Set `DISCORD_ALLOW_BOTS=all` in every council bot's `.env`.

### 2. One Rep Per Channel — Channel Assignment

Each channel has ONE designated "rep" bot that responds without @mention. All other bots either exclude the channel via `allowed_channels` or keep `require_mention: true`.

| Channel | Rep Bot | Config |
|---------|---------|--------|
| `#command` | Chief of Staff | `require_mention: false`, all others `require_mention: true` |
| `#intelligence` | Intelligence Lead | `require_mention: false`, others exclude or mention-only |
| `#finance` | Finance Lead | `require_mention: false`, others exclude or mention-only |
| `#operations` | Operations Lead | `require_mention: false`, others exclude or mention-only |
| `#general` | Chief of Staff only | Only CoS has `allowed_channels` include general |

**Per-bot config.yaml pattern:**

```yaml
discord:
  require_mention: false       # Rep responds freely in home channel
  auto_thread: false            # No threads (Spacebar limitation)
  allowed_channels:             # Channels this bot monitors
    - <discord-channel-id>       # #command (always allow)
    - <discord-channel-id>       # #intelligence (home channel)
```

Non-rep bots use `require_mention: true` (default) and narrower `allowed_channels`.

### 3. @Mention Override

When the operator @mentions a specific bot (e.g., `@Operations-Lead`), that bot joins the conversation regardless of `require_mention`. The adapter's `on_message` handler checks `message.mentions` — if the bot is mentioned, `mention_prefix` is True, bypassing the `require_mention` gate (lines 4743-4747 of adapter.py).

### 4. Thread Context Inference

When a bot participates in a thread and the operator replies in the same thread, the bot's `ThreadParticipationTracker` marks the thread — subsequent messages in that thread are treated as free-response (no @mention needed).

This works within a single gateway process only. Cross-bot threads (where the operator starts a conversation in one bot's channel and wants a different bot to respond) require @mention of the target bot.

### 5. Implementation Pattern

```bash
# For each bot, set these in ~/AppData/Local/hermes/profiles/<name>/.env:
echo "DISCORD_ALLOW_BOTS=all" >> .env        # Critical for cross-bot messages
echo "DISCORD_ALLOW_ALL_USERS=true" >> .env   # Accept all users
echo "GATEWAY_ALLOW_ALL_USERS=true" >> .env   # Generic fallback
echo "DISCORD_AUTO_THREAD=false" >> .env       # No threads per Spacebar limitation
```

Then restart each gateway to pick up the changes.
