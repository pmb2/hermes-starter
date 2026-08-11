# Hosted Relay Agent Registration Protocol (v2 — CORRECTED)

**Originally documented as impossible. We proved it works.**

This reference documents how to register managed agents on a Block-hosted Buzz
relay (`wss://*.communities.buzz.xyz`) using Nostr events — no Desktop app required.

## Discovery

The Buzz relay source code at `crates/buzz-core/src/kind.rs` reveals these
event kinds for agent management:

| Kind | Constant | Purpose |
|------|----------|---------|
| 9030 | `RELAY_ADMIN_ADD_MEMBER` | Add a pubkey as a community member |
| 9031 | `RELAY_ADMIN_REMOVE_MEMBER` | Remove a community member |
| 30177 | `KIND_MANAGED_AGENT` | Register a managed agent (parameterized replaceable) |
| 10100 | `KIND_AGENT_PROFILE` | Agent profile metadata (parameterized replaceable) |
| 30176 | `KIND_TEAM` | Team definition — group agents together |

## Registration Flow

### Step 1: RELAY_ADMIN_ADD_MEMBER (9030) — CRITICAL UNLOCK

```python
client.send_event(9030, "", [["p", agent_pubkey_hex, "member"]])
```

- Must be published by the **community owner's key only**
- Without this, the agent key gets `restricted: not a relay member`
- This populates the relay's `channel_members` table

### Step 2: KIND_MANAGED_AGENT (30177)

```python
profile = json.dumps({"display_name": "Forge", "about": "Dev lead"})
client.send_event(30177, profile, [["d", "dev-lead"]])
```

- Parameterized replaceable — keyed by `["d", agent_name]`
- Content is JSON with display_name and about fields

### Step 3: Agent Publishes Own Kind 0 (from agent's own key)

After the admin registers the agent (steps 1-2), the agent connects with
ITS OWN secret key and publishes a kind 0 profile:

```python
agent_client = BuzzClient(agent_secret_key, relay_url=HOSTED_RELAY)
agent_client.connect()  # NIP-42 auth now succeeds
agent_client.send_event(0, profile_json, [])
```

**Key insight:** Step 1 is the critical unlock. Without it the agent gets
`restricted: not a relay member`. With it, the agent key is a full community
member with its own Nostr identity.

### Step 4 (Optional): KIND_TEAM (30176) — Group Agents

Create a team to organize agents. The Desktop app may use teams for display:

```python
team_tags = [
    ["d", "team-name"],
    ["name", "AI Agent OS"],
    ["about", "The complete fleet"],
    ["p", agent_pubkey_1, "role1"],
    ["p", agent_pubkey_2, "role2"],
    # ... one p-tag per agent
]
client.send_event(30176, json.dumps({"name": "Team Name"}), team_tags)
```

## Batch Registration Pattern

```python
for name, agent_data in db.items():
    apk = agent_data['public_key']
    profile = json.dumps({"display_name": name, "about": "..."})
    
    # Admin: register member + managed agent
    admin_client.send_event(9030, "", [["p", apk, "member"]])
    admin_client.send_event(30177, profile, [["d", name]])
    
    # Agent: connect independently and publish own profile
    agent_client = BuzzClient(agent_sk, relay_url=HOSTED)
    agent_client.connect()
    agent_client.send_event(0, profile, [])
    agent_client.close()
    
    time.sleep(0.15)  # rate limit
```

## ✅ SOLVED: Desktop App Agent Display — Local State Injection

**UPDATE (2026-07-26): The Desktop app display limitation is now SOLVED.**
Agents registered on the relay WILL appear in the Desktop sidebar by injecting
entries into the Desktop app's local state files.

### Root Cause

The Buzz Desktop app (Tauri 2 + React) stores agent configs in **local files**
on the user's machine, not on the relay. After Nostr-level registration, the
relay knows the agents but the Desktop app doesn't — and only shows agents
that have local entries in its `managed-agents.json`.

### v3 Update (2026-07-26): "Unknown Agent" Fix & Channel Ownership

Two additional learnings from the final integration pass:

**The "Unknown Agent" section** appears when custom (non-builtin) agents lack
`agent_command_override` and `provider_binary_path`. The Desktop app can't
determine what binary to launch, so it falls back to an "Unknown" bucket.
Fix is documented in Step 3 below.

**Channel ownership mapping** — each agent should be assigned channels that
match its role. See `references/channel-ownership-map.md` for the full
agent→channels mapping used in production.

### Injection File Locations

**Windows:** `%APPDATA%/xyz.block.buzz.app/agents/`
- `managed-agents.json` — Array of agent objects (each with Nostr pubkey, relay URL, system prompt, slug, backend config)
- `teams.json` — Array of team objects referencing agents via `persona_ids` array

**macOS/Linux (likely):** `~/Library/Application Support/xyz.block.buzz.app/agents/`

### Injection Format

Each agent entry in `managed-agents.json`:
```json
{
  "pubkey": "<64-char hex>",
  "name": "dev-lead",
  "display_name": "Forge",
  "slug": "dev-lead",
  "relay_url": "wss://your-relay.communities.buzz.xyz",
  "system_prompt": "You are Forge, part of the AI Agent OS. Dev lead...",
  "acp_command": "buzz-acp",
  "agent_command": "",
  "backend": {"type": "local"},
  "start_on_app_launch": false,
  "auto_restart_on_config_change": true,
  "is_builtin": false,
  "is_active": false,
  "respond_to": "owner-only",
  "parallelism": 24,
  "turn_timeout_seconds": 320,
  "name_pool": ["Forge"]
}
```

### Team Linking

The `teams.json` file ties agents to teams via `persona_ids` (matches agent `slug`):
```json
{
  "id": "AI Agent OS",
  "name": "AI Agent OS",
  "description": "The complete AI Agent OS fleet",
  "persona_ids": ["dev-lead", "qa-lead", "integration-lead", "docs-lead", ...],
  "is_builtin": false
}
```

### Full Procedure

1. **Nostr-level registration** (required for connectivity):
   - Community owner publishes RELAY_ADMIN_ADD_MEMBER (9030) for each agent pubkey
   - Community owner publishes KIND_MANAGED_AGENT (30177) for each agent
   - Each agent independently connects and publishes its own kind 0 profile
   - Register agents in a team via KIND_TEAM (30176) with p-tags per agent
   - Agents connect as channel members (verified on hosted relay)

2. **Desktop-level injection** (required for UI display):
   - Add each agent to `managed-agents.json` with its pubkey, relay URL, and system prompt
   - Update `teams.json` — add agent slugs to the team's `persona_ids` array
   - Clear default agents (Fizz/Honey/Bumble) from team assignments so user can delete them
   - Close and reopen the Buzz Desktop app to see agents in the sidebar

3. **Fix "Unknown Agent" categorization post-injection:**
   - Agents initially appear under an "Unknown" section because the Desktop app
     doesn't recognize their `agent_command` or `backend` config for non-builtin agents.
   - **Fix:** Set these fields on each custom agent entry:
     ```json
     "agent_command_override": "buzz-agent",
     "provider_binary_path": "C:\\\\Users\\\\<user>\\\\AppData\\\\Local\\\\Buzz\\\\buzz-agent.exe",
     "persona_source_version": "2",
     "persona_id": "<slug>",
     "is_active": false
     ```
   - `agent_command_override` tells the Desktop app which ACP wrapper binary to use.
     `buzz-agent.exe` ships with every Buzz Desktop install at `AppData/Local/Buzz/`.
   - `provider_binary_path` gives the absolute path to the ACP wrapper.
   - `persona_source_version: "2"` flags the agent as having a known config format.
   - `persona_id` should equal `slug` — the Desktop uses this to link the agent to its team.
   - After these fields are set, agents move from the "Unknown" bucket to their designated team.
   - ⚠️ **Deduplication pitfall:** The Desktop app distinguishes agents by their `slug` field.
     If you write entries with both lowercase-slug (`"dev-lead"`) AND Title Case names
     (`"Forge"`) the Desktop sees them as different agents. Normalize ALL slugs to
     lowercase kebab-case. Remove duplicate entries before reloading the app.

4. **Clean up unassigned default agents:**
   - After clearing the Welcome team's `persona_ids`, Fizz/Honey/Bumble show as unassigned
   - User can then delete them from the Desktop app UI (right-click → Delete)
   - They remain in `managed-agents.json` as builtin entries but with no team link

5. **Verification:**
   - After injection, agents appear in the Desktop sidebar under their team
   - Each agent shows its display_name, relay connection, and system prompt
   - Agents can be started/managed from the Desktop UI
   - Default agents show as unassigned and can be removed

### Dual Relay Sync

When maintaining both a hosted relay (`wss://*.communities.buzz.xyz`) and a
local relay (`ws://localhost:3000`), keep them in sync with the same registration:

1. **Connect as community owner on each relay separately** — auth is independent
2. **Run the same registration commands on both:**
   - 9030 admin add member (each agent)
   - 30177 managed agent (each agent)
   - Agent kind 0 (from agent's own key)
   - 30176 team (with all agent p-tags)
3. **Desktop `managed-agents.json` and `teams.json`** — shared between relays
   (the relay_url field is per-agent, so agents can connect to either relay)
4. **Postgres `channel_members` on local relay** — add agents directly:
   ```sql
   INSERT INTO channel_members (community_id, channel_id, pubkey, role, invited_by)
   SELECT 'community-uuid', c.id, decode('<agent_pubkey_hex>', 'hex'), 'member', decode('<owner_pubkey_hex>', 'hex')
   FROM channels c;
   ```
5. **Duplicate detection** — query existing events BEFORE creating new ones
   to avoid duplicate managed agent or team registrations

### What Still Does NOT Work

- **Fizz/Honey/Bumble deletion:** Created by Desktop onboarding with unknown keypairs, cannot delete from relay
- **Kind 39000 channel metadata on hosted relay:** `restricted: unknown event kind`
- **Kind 5 delete of other authors' events:** `invalid: must be event author`
- **Unscoped queries on hosted relay (no `authors:` filter):** Returns empty

## What Else Does NOT Work

| Approach | Reason |
|----------|--------|
| Publishing all kind 0 events under owner's key | Kind 0 is replaceable — only 1 per pubkey sticks |
| Auth tag delegation on kind 0 | Same replaceable-event issue |
| Connecting as agent key without 9030 | `restricted: not a relay member` |
| Kind 39000 channel metadata | `restricted: unknown event kind` |
| Kind 5 delete of other agents' events | `invalid: must be event author` |

## Verification Query

```python
results = client.query({'kinds': [0, 30177, 10100], 'limit': 200}, timeout=10)
# Expected: multiple agent kind 0 events from DIFFERENT pubkeys
# Expected: multiple 30177 managed agent events
```

## Error Messages Reference

| Scenario | Relay Response |
|----------|---------------|
| Agent connects before 9030 | `restricted: not a relay member` |
| Agent publishes before 9030 | `auth-required: not authenticated` |
| 9030 published correctly | Accepted |
| Agent connects after 9030 | Accepted |
| Kind 39000 on hosted relay | `restricted: unknown event kind` |
