#!/usr/bin/env python3
"""Generate Nostr keypairs for all Hermes profiles + create buzz channels."""
import json, sys, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from buzz_bridge import generate_nostr_key
from nostr_protocol import Keys

# Profile → buzz channel mapping
PROFILE_CHANNELS = {
    "chief-of-staff": ["general", "admin", "management"],
    "development-lead": ["dev", "engineering", "coding", "architecture"],
    "intelligence-lead": ["intel", "intelligence"],
    "research-lead": ["research"],
    "operations-lead": ["ops", "operations", "infrastructure"],
    "security-lead": ["security", "compliance"],
    "creative-lead": ["creative", "design", "content"],
}

# Generate keys
keys_db = {}
for name, channels in sorted(PROFILE_CHANNELS.items()):
    k = generate_nostr_key(name)
    keys_db[name] = {
        "secret_key": k["secret_key"],
        "public_key": k["public_key"],
        "bech32": k["public_key_bech32"],
        "channels": channels,
    }

# Save to JSON
out = Path(__file__).parent / "buzz_keys.json"
out.write_text(json.dumps(keys_db, indent=2))
print(f"Saved {len(keys_db)} keys to {out}")

# Also create a .env format for easy import
env_path = Path("C:\\Users\\<you>\\AppData\\Local\\hermes") / "buzz_keys.env"
with open(env_path, "w") as f:
    f.write(f"# Buzz Nostr Keys — Generated {os.path.basename(__file__)}\n")
    f.write(f"# BUZZ_RELAY_URL=ws://localhost:3000\n\n")
    for name, data in sorted(keys_db.items()):
        env_name = name.upper().replace("-", "_")
        f.write(f"BUZZ_SK_{env_name}={data['secret_key']}\n")
        f.write(f"BUZZ_PK_{env_name}={data['public_key']}\n")
    f.write(f"\n# Channel assignments\n")
    for name, data in sorted(keys_db.items()):
        env_name = name.upper().replace("-", "_")
        f.write(f"BUZZ_CHANNELS_{env_name}={' '.join(data['channels'])}\n")

print(f"Saved .env to {env_path}")

# Print summary
print(f"\n{'='*60}")
print(f"{'Profile':30s} {'Public Key':40s} {'Channels'}")
print(f"{'='*60}")
for name, data in sorted(keys_db.items()):
    pk = data["public_key"][:16] + "..."
    ch = ",".join(data["channels"][:3])
    print(f"{name:30s} {pk:40s} {ch}")
print(f"{'='*60}")
print(f"Total: {len(keys_db)} profiles with Nostr identities")
