#!/bin/bash
"""Create a Discord thread in a channel. Usage:
  bash create-thread.sh <channel_id> <thread_name> <message_content>

Requires DISCORD_BOT_TOKEN in environment or ~/AppData/Local/hermes/.env
"""

CHANNEL_ID="${1:?Usage: create-thread.sh <channel_id> <thread_name> <message>}"
THREAD_NAME="${2:?Missing thread name}"
MESSAGE="${3:?Missing message content}"

# Load token from .env if not set
if [ -z "$DISCORD_BOT_TOKEN" ]; then
  source ~/AppData/Local/hermes/.env 2>/dev/null
fi

UA="DiscordBot (https://your-domain.example, 1.0)"
AUTH="Authorization: Bot $DISCORD_BOT_TOKEN"

echo "Posting message to channel $CHANNEL_ID..."

MSG=$(curl -s -X POST \
  -H "$AUTH" \
  -H "Content-Type: application/json" \
  -H "User-Agent: $UA" \
  "https://discord.com/api/v10/channels/$CHANNEL_ID/messages" \
  -d "$(python -c "import json; print(json.dumps({'content': '$MESSAGE'}))")")

MSG_ID=$(echo "$MSG" | python -c "import sys,json; print(json.load(sys.stdin).get('id','FAILED'))" 2>/dev/null)

if [ "$MSG_ID" = "FAILED" ]; then
  echo "Failed to send message:"
  echo "$MSG" | head -5
  exit 1
fi

echo "Message posted (ID: $MSG_ID). Creating thread..."

THREAD=$(curl -s -X POST \
  -H "$AUTH" \
  -H "Content-Type: application/json" \
  -H "User-Agent: $UA" \
  "https://discord.com/api/v10/channels/$CHANNEL_ID/messages/$MSG_ID/threads" \
  -d "$(python -c "import json; print(json.dumps({'name': '$THREAD_NAME', 'auto_archive_duration': 1440}))")")

THREAD_ID=$(echo "$THREAD" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('id','FAILED'))" 2>/dev/null)

if [ "$THREAD_ID" = "FAILED" ]; then
  echo "Failed to create thread:"
  echo "$THREAD" | head -5
  exit 1
fi

echo "✅ Thread created: $THREAD_NAME"
echo "📎 https://discord.com/channels/<discord-channel-id>/$THREAD_ID"
