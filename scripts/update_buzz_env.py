#!/usr/bin/env python3
"""Update profile .env files with channel UUIDs."""
import json
from pathlib import Path

KEYS_FILE = Path(r"${USER_HOME}\AppData\Local\hermes\scripts\buzz_keys.json")
CHANNEL_FILE = Path(r"${USER_HOME}\AppData\Local\hermes\scripts\buzz_channels.json")
PROFILES_DIR = Path(r"${USER_HOME}\AppData\Local\hermes\profiles")

chan_map = json.loads(CHANNEL_FILE.read_text()) if CHANNEL_FILE.exists() else {}
db = json.loads(KEYS_FILE.read_text()) if KEYS_FILE.exists() else {}

# Update profile .env files with channel UUIDs
for name, data in db.items():
    profile_env = PROFILES_DIR / name / ".env"
    if not profile_env.exists():
        continue
    
    env_name = name.upper().replace("-", "_")
    ch_names = data.get("channels", [])
    ch_uuids = [chan_map[c] for c in ch_names if c in chan_map]
    
    new_lines = []
    has_buzz = False
    for line in profile_env.read_text().split("\n"):
        if line.startswith("BUZZ_CHANNELS="):
            new_lines.append(f'BUZZ_CHANNELS={" ".join(ch_names)}')
            new_lines.append(f'BUZZ_CHANNEL_UUIDS={" ".join(ch_uuids)}')
            has_buzz = True
        elif line.startswith("BUZZ_CHANNEL_"):
            continue  # skip old UUID lines
        elif line.startswith("# ── Buzz") or line.startswith("# ── End Buzz"):
            continue  # will be re-added
        else:
            new_lines.append(line)
    
    if not has_buzz:
        new_lines.append("")
        new_lines.append("# ── Buzz Nostr Identity ──────────────────────────")
        new_lines.append(f'BUZZ_RELAY_URL=ws://localhost:3000')
        new_lines.append(f'BUZZ_SECRET_KEY={data["secret_key"]}')
        new_lines.append(f'BUZZ_PUBLIC_KEY={data["public_key"]}')
        new_lines.append(f'BUZZ_CHANNELS={" ".join(ch_names)}')
        new_lines.append(f'BUZZ_CHANNEL_UUIDS={" ".join(ch_uuids)}')
        new_lines.append(f'# ── End Buzz ─────────────────────────────────────')
    
    profile_env.write_text("\n".join(new_lines))
    print(f"  ✓ {name}: {len(ch_uuids)} channel(s)")

print(f"\nAll profiles updated with channel UUIDs.")
