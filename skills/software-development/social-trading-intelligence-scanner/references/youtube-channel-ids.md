# YouTube channel IDs for trading scanners

Resolved 2026-08-08 via `yt-dlp ytsearchN:` (handle pages may 404).

| Creator | Handle | channel_id |
|---------|--------|------------|
| analyst Cameron - Warrior Trading | @RossCameronWarriorTrading | `UCBayuhgYpKNbhJxfExYkPfA` |
| Humbled Trader | @HumbledTrader | `UCcIvNGMBSQWwo1v3n-ZRBCw` |
| SMB Capital | @SMBCapital | `UCg3B_joekBGJ1s_4fRjsMKA` |
| Option Alpha | @OptionAlpha | `UCQAvjhqp559qSQx2dcg9WVg` |
| tastylive | @tastylive | `UCLJiSMXJ9K-1AOTqIqdXJgQ` |
| projectoption | @projectoption | `UCYOHtOzMZGwXBLZX1Ltf78g` |

## Resolve recipe

```bash
yt-dlp "ytsearch5:analyst Cameron Warrior Trading" \
  --flat-playlist --dump-single-json --no-warnings --ignore-errors
```

Read `entries[].channel_id` / `entries[].channel`. Prefer IDs that appear on multiple recent videos from the same uploader.

RSS once you have UC id:

```
https://www.youtube.com/feeds/videos.xml?channel_id=UC...
```

## Notes

- Brand rename: tastytrade → tastylive in public branding
- ProjectFinance / projectoption naming: use the uploader string from yt-dlp, not assumed handle
- Never ship placeholder UC ids; missing id should error soft and rely on search queries
