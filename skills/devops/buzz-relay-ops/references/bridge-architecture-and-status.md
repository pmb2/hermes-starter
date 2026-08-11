# Buzz Agent Bridge — Architecture and Status

## Live System

| Component | Status |
|-----------|--------|
| Hosted relay | `wss://your-relay.communities.buzz.xyz` |
| AI backend | OmniRoute at `localhost:20128` (model: `oc/deepseek-v4-flash-free`) |
| Bridge daemon | `buzz_agent_bridge.py` via `start_buzz_bridge.py` wrapper |
| Channels monitored | 58 |
| Agents managed | 47 |
| Key store | `buzz_keys.json` |
| Channel map | `buzz_channels.json` |

## Quick Status Checks

```bash
# Is the bridge process alive?
ps aux | grep buzz_agent_bridge

# Is OmniRoute healthy?
curl -s --max-time 2 http://localhost:20128/healthz

# Read the restart wrapper's log
tail -20 ${HERMES_HOME}/scripts/bridge.log

# Check the bash wrapper log
tail -50 ${HERMES_HOME}/logs/buzz_bridge.log

# Read the bash wrapper's PID
cat ${HERMES_HOME}/logs/buzz_bridge.pid
```

## Startup Banner

A successful bridge start prints:
```
Bridge: 58 ch, 47 agents, 48 EOSE
.
.
```

The `58 channels` refers to the REQ subscriptions sent (not every subscription
gets a unique EOSE). The `47 agents` is the count of entries in the REV alias
map. Heartbeat dots print every 10 seconds while the event loop runs.

## Startup Sequence (Order Matters)

1. **OmniRoute** must be running first (AI backend for agent replies)
2. Bridge connects with the operator's key (operator key, registered on hosted relay)
3. Bridge sends NIP-42 AUTH response with signed kind 22242
4. Bridge sends REQ for each channel UUID filtered by kind 9
5. Bridge drains EOSE responses (EOSE = end of stored events)
6. Main event loop starts — prints heartbeat dots

If any step fails, the entire connection is dropped and retried with
exponential backoff (1s → 2s → 4s → ... → 30s max).

## Agent Key Routing

Each agent replies from ITS OWN Nostr key, proving identity:

```
User @mentions Forge in #engineering
  → Bridge sees @dev-lead in content
  → Looks up dev-lead's sekret_key from buzz_keys.json
  → Opens a temporary BuzzClient with dev-lead's key
  → Sends kind 9 reply as dev-lead
  → Tags: [e, original_event_id], [p, author_pubkey], [h, channel_uuid]
  → Closes temporary connection
```

This means every agent has its own Nostr identity in the channel. Messages
from other agents' pubkeys are automatically skipped (anti-loop).

## Running the Bridge

From the `scripts/` directory:

```bash
# Production (with restart wrapper):
python start_buzz_bridge.py
# Logs to: bridge.log

# Direct (for debugging):
python -u buzz_agent_bridge.py
# Prints heartbeat and @mention activity to stdout

# Bash wrapper (auto-restart, PID tracking):
bash run_buzz_bridge.sh
# Logs to: ${HERMES_HOME}/logs/buzz_bridge.log
```

## Troubleshooting

### "X auth failed"
the operator's key is not registered on the hosted relay. Run the agent registration
protocol (9030 RELAY_ADMIN_ADD_MEMBER) first.

### "X connection dead"
WebSocket disconnected. Auto-reconnect kicks in with exponential backoff.
Check if the hosted relay is reachable:
```
curl -s --max-time 5 -H "Upgrade: websocket" -H "Connection: Upgrade" http://your-relay.communities.buzz.xyz
```

### @mentions detected but no reply sent
Likely OmniRoute is down. Check:
```bash
curl -s http://localhost:20128/healthz
```
If not "ok", restart the OmniRoute server.

### Duplicate replies for the same event
The SEEN set was cleared (exceeded 10,000 entries). This is normal for long
runs — events older than the last 10,000 can be re-processed. The agent
pubkey filter still prevents full loops.
