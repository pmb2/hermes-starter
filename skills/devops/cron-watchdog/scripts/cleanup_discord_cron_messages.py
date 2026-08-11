#!/usr/bin/env python3
"""
Delete failed cron job messages from all Discord channels.
Searches for bot-authored messages containing cron failure indicators and removes them.

Requires DISCORD_BOT_TOKEN in ~/.hermes/.env or ~/AppData/Local/hermes/.env
with guilds + messages + message_content intents enabled on the bot.

Expect heavy Discord 429 rate limiting — discord.py auto-retries. A full-server
purge of hundreds of messages takes 5+ minutes. Resumable: already-deleted
messages stay deleted, so re-running continues where it left off.
"""
import discord
import asyncio
import os
import re
from datetime import datetime, timedelta

# Load token
TOKEN = None
for env_path in [
    os.path.expanduser("~/AppData/Local/hermes/.env"),
    os.path.expanduser("~/.hermes/.env"),
]:
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith("DISCORD_BOT_TOKEN="):
                    TOKEN = line.strip().split("=", 1)[1].strip("\"' ")
                    break
        if TOKEN:
            break

if not TOKEN:
    print("NO_TOKEN - check .env files")
    exit(1)

# Patterns that indicate failed cron job messages
FAILURE_PATTERNS = [
    r"cron.*fail", r"cron.*error", r"failed.*cron", r"job.*fail", r"job.*error",
    r"delivery.*fail", r"delivery.*error", r"platform.*discord.*not.*configured",
    r"rate.*limit", r"429.*rate.*limit", r"error.*deliver",
    r"traceback", r"exception",
    r"❌", r"🔴.*error", r"🔴.*fail", r"⚠️.*fail", r"⚠️.*error",
    r"system.*error", r"gateway.*error", r"timeout", r"timed.*out",
    r"script.*error", r"script.*fail", r"python.*error", r"http.*error",
    r"403.*forbidden", r"500.*internal", r"503.*service", r"504.*gateway",
    r"cronjob response",
]

compiled_patterns = [re.compile(p, re.IGNORECASE) for p in FAILURE_PATTERNS]


class CronMessageCleaner(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.messages = True
        intents.message_content = True
        super().__init__(intents=intents)
        self.deleted_count = 0
        self.checked_count = 0

    def is_failure_message(self, message):
        """Check if a message looks like a failed cron job report."""
        content = message.content.lower()

        # Skip messages from users (only clean bot messages)
        if not message.author.bot:
            return False

        for pattern in compiled_patterns:
            if pattern.search(content):
                return True

        # Cron job names in error context
        cron_keywords = ["pulse", "watchdog", "scanner", "monitor", "brief", "digest", "sync"]
        error_keywords = ["error", "fail", "exception", "timeout", "crash"]
        has_cron = any(k in content for k in cron_keywords)
        has_error = any(k in content for k in error_keywords)
        return has_cron and has_error

    async def clean_channel(self, channel):
        if not isinstance(channel, discord.TextChannel):
            return
        try:
            after = datetime.utcnow() - timedelta(days=30)
            async for message in channel.history(limit=500, after=after):
                self.checked_count += 1
                if self.is_failure_message(message):
                    try:
                        await message.delete()
                        self.deleted_count += 1
                        print(f"  Deleted from #{channel.name}: {message.content[:60]}...")
                        await asyncio.sleep(0.5)  # extra rate limit protection
                    except discord.Forbidden:
                        print(f"  No permission to delete in #{channel.name}")
                        break
                    except Exception as e:
                        print(f"  Error deleting in #{channel.name}: {e}")
        except discord.Forbidden:
            print(f"  No access to #{channel.name}")
        except Exception as e:
            print(f"  Error reading #{channel.name}: {e}")

    async def on_ready(self):
        print(f"Connected as {self.user}")
        print("Searching for failed cron job messages...")

        # Scan all guilds the bot is in (or hardcode a guild ID to scope)
        for guild in self.guilds:
            print(f"Guild: {guild.name} — scanning {len(guild.text_channels)} text channels...")
            for channel in guild.text_channels:
                print(f"Checking #{channel.name}...")
                await self.clean_channel(channel)

        print("\n=== Cleanup Complete ===")
        print(f"Messages checked: {self.checked_count}")
        print(f"Messages deleted: {self.deleted_count}")
        await self.close()


client = CronMessageCleaner()
client.run(TOKEN)
