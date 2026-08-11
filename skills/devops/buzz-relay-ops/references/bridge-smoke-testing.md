# Bridge Smoke Testing — End-to-End Verification

Quick protocol for verifying the Buzz Agent Bridge is routing correctly.
Can be run any time without impacting production traffic.

## Prerequisites

- Bridge daemon running (PID from `logs/buzz_bridge.pid`)
- OmniRoute healthy (`curl -s http://localhost:20128/healthz → ok`)
- Relay accessible (`ws://localhost:3000`)
- `nostr_protocol` Python library installed

## One-Shot Test Script

```python
import json, sys, time
from pathlib import Path

ROOT = Path(r"${USER_HOME}\AppData\Local\hermes\scripts")
sys.path.insert(0, str(ROOT))

KEYS = json.loads((ROOT / "buzz_keys.json").read_text())
CHANS = json.loads((ROOT / "buzz_channels.json").read_text())
LOG = Path(r"${USER_HOME}\AppData\Local\hermes\logs\buzz_bridge.log")

from nostr_protocol import Keys
from buzz_client import BuzzClient

# Generate a throwaway keypair (NOT in AGENT_PUBKEYS — bridge will respond)
throwaway = Keys.generate()
test_secret = throwaway.secret_key().to_hex()

client = BuzzClient(test_secret, relay_url="ws://localhost:3000")
assert client.connect(), "Connect failed"

# Test 1: Channel rep (no @) — "status check" in #development → Dev Lead
dev_uuid = CHANS["development"]
client.send_event(9, "status check", [["h", dev_uuid]])

# Test 2: @mention override — "@Forge what's the git status?" in #engineering → Forge
eng_uuid = CHANS["engineering"]
client.send_event(9, "@Forge what's the git status?", [["h", eng_uuid]])

# Test 3: Admin channel rep — "what's the fleet status?" in #admin → Chief
admin_uuid = CHANS["admin"]
client.send_event(9, "what's the fleet status?", [["h", admin_uuid]])

time.sleep(10)
client.close()

# Verify in bridge log
lines = LOG.read_text().strip().split("\n")
for line in lines[-10:]:
    print(line)  # Expect: @Dev, @Forge, @Chief routing + "replied:" lines
```

## Expected Output

```
@Dev #development: status check
@Forge #engineering: @Forge what's the git status?
@Chief #admin: what's the fleet status?
  replied: ...
  replied: ...
  replied: ...
```

All three routing paths must appear:
1. **Channel rep** (`#development` → `Dev` = development-lead) — no @ needed
2. **@mention override** (`@Forge` in `#engineering` → Forge) — overrides channel rep
3. **Admin channel rep** (`#admin` → `Chief` = chief-of-staff) — no @ needed

## What "replied: N" Means

The `replied:` lines show the first ~40 characters of the AI-generated reply.
- `replied: 1` — the AI returned "On it." (the fallback when OmniRoute returns empty)
- `replied: We` — the AI returned a real reply starting with "We are..."
- No `replied:` line after 10 seconds means the AI call failed or OmniRoute is down

## Debugging Failed Tests

| Symptom | Cause | Fix |
|---------|-------|-----|
| Bridge log shows nothing | Bridge not connected to relay | Check PID file, tasklist, watchdog |
| `@Dev #development: status check` logged but no `replied:` | OmniRoute down | `curl localhost:20128/healthz` |
| `replied: 1` (single char) | AI returned empty → fallback "On it." | Check OmniRoute model combo |
| Duplicate replies | Two bridge instances running | Kill all, reset PID file, let watchdog respawn |

## Pitfalls

- **Throwaway keys must be truly throwaway.** The bridge filters out `AGENT_PUBKEYS` — messages from any agent key will be silently dropped. Always generate a fresh `Keys.generate()` for each test.
- **The bridge checks `AGENT_PUBKEYS` BEFORE the @mention check.** Even if you use `@Chief` from an agent key, it won't be routed. The agent-to-agent communication path is not supported by the bridge (agents talk via the relay, not via the bridge).
- **Wait at least 8 seconds** after sending before checking the log. The AI call is threaded (do_reply runs in a background daemon thread) and the OmniRoute API call takes 3-5 seconds.
- **The bridge does NOT print heartbeat dots** (doc–code gap). The only evidence of liveness is `@Agent #channel: content` routing lines followed by `replied:` lines. An idle bridge has no log output.
- **After testing, the throwaway pubkey is still in the relay's event store.** This is harmless — the events are just kind 9 text messages. No cleanup needed.