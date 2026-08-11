# Spacebar Channel Permission Overwrites (PostgreSQL)

> SQL format for restricting channel access to specific bots/roles. Use when implementing the "one rep per channel" pattern — each channel accessible only by its designated bots.

## Permission Value Reference

| Permission | Decimal | Bit |
|-----------|---------|-----|
| `VIEW_CHANNEL` | 1024 | 1<<10 |
| `SEND_MESSAGES` | 2048 | 1<<11 |
| `READ_MESSAGE_HISTORY` | 65536 | 1<<16 |
| **Combined (view + send + history)** | **68608** | 1024\|2048\|65536 |
| `ADMINISTRATOR` | 8 | 1<<3 |

[... full content from above ...]
