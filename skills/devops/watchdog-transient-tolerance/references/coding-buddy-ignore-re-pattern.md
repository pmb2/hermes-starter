# Coding Buddy: ignore_re + N-Consecutive Threshold (2026-08-10)

A real-world implementation of the watchdog transient-tolerance pattern.

## The Problem

Coding Buddy Watchdog (cron job `68f7ab407141`, every 5 min) detected 12+ errors per run and attempted OpenCode recovery — which failed — then spammed the Discord channel with "RECOVERY FAILED" messages. The errors were false positives:

- Discord 503 Service Unavailable (gateway transient)
- WebSocket disconnect/reconnect logs
- Asyncio "Task exception was never retrieved" noise
- Old session-DB rows with stale error data

## The Fix (3 layers)

### Layer 1: ignore_re (Performance)
```python
IGNORE_PATTERNS = [
    r"discord\.errors", r"discord\.websocket", r"discord\.gateway",
    r"WebSocket.*disconnect", r"ConnectionError.*Discord",
    r"503 Service Unavailable", r"upstream connect error",
    r"transport failure reason", r"remote connection failure",
    r"Task exception was never retrieved",
]

ignore_re = re.compile('|'.join(IGNORE_PATTERNS), re.IGNORECASE)

for line in log_lines:
    if ignore_re.search(line):
        continue  # skip false positives BEFORE detection
    if detection_re.search(line):
        # This is a real error
```

### Layer 2: Disable unreliable scan sources
The session-DB scanner (`scan_session_db`) was finding stale error rows that the time filter couldn't cleanly reject. Disabled entirely. One reliable source (log scanner, 5-min window, 300-line cap, 20-error cap) was enough.

### Layer 3: 3x consecutive failure threshold
```python
STATE_FILE = Path.home() / "AppData/Local/hermes/cron/coding_buddy_state.json"

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"consecutive_failures": 0, "last_alerted": None}

def should_alert(state):
    """Only alert on 3rd consecutive failure."""
    return state.get("consecutive_failures", 0) >= 3 and \
           state.get("consecutive_failures", 0) < 6  # cap at 3 alerts

# In the cron wrapper:
state = load_state()
if errors > 0:
    state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1
    save_state(state)
    if not should_alert(state):
        sys.exit(0)  # silent — not enough failures yet
    # ... output alert message
else:
    state["consecutive_failures"] = 0  # reset on healthy
    save_state(state)
    sys.exit(0)  # silent — healthy
```

## Result

Before: 12+ error messages, OpenCode recovery invoked every 5 min, spammed Discord.
After: Exit 0, zero output, completely silent. Only alerts after ~15 min of consecutive real errors.

## Files

- `src/supervisor.py` — ErrorDetector class with ignore_re, ErrorDetectorConfig
- `scripts/coding_buddy.py` — cron wrapper with 3x threshold + state file
- `${USER_HOME}\AppData\Local\hermes\cron\coding_buddy_state.json` — persistent state