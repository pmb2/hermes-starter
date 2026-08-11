# Buzz Desktop App — Local State Injection Pitfalls

Collected from real session failures (2026-07-26). Apply BEFORE restarting
the Desktop app after editing `managed-agents.json` or `teams.json`.

## 1. Backend Type Must Be "local" or "provider"

```
failed to parse agent store: unknown variant `none`, expected `local` or `provider`
```

The Desktop app's `ManagedAgent` struct only accepts `backend.type` of
`"local"` or `"provider"`. Setting it to `"none"` (or any other value)
crashes the parser, renames the file to `.invalid`, and loses all agents.

**Fix:** Always use `"backend": {"type": "local"}` for relay-only agents.
The "local" backend type does NOT force the Desktop to launch a subprocess
— the Desktop only starts an agent if `start_on_app_launch: true` AND an
`agent_command_override` is set. Without those, the agent is displayed but
never spawned.

## 2. Profile Overwrite — Kind 0 Is Replaceable Per Pubkey

Publishing a kind 0 (profile metadata) event with the **community admin's
secret key** overwrites the admin's own profile. Kind 0 is replaceable —
only the latest event per pubkey is stored.

```python
# DANGER: this replaces the operator's profile with "Weaver"
pauls_client.send_event(0, weaver_profile, [])
```

**Rule:** Never publish kind 0 events using the admin key for agent profiles.
The admin's key is for admin operations (9030, 30177, 30176). Each agent
must publish its own kind 0 using its own secret key.

**Recovery:** Publish another kind 0 with the admin's real profile:
```python
pauls_client.send_event(0, json.dumps({
    "display_name": "the operator",
    "name": "the operator",
    "about": "Community admin"
}), [])
```

## 3. Team Persona IDs Must Match Agent Slugs Exactly

The Desktop app validates that every `persona_id` in a team matches an
agent's `slug` in `managed-agents.json`. If they don't match, you get:

```
44 agents in this team are no longer in your agents. Edit the team to fix
it before deploying or sharing.
```

**Root cause:** The agent's `slug` field must be identical to the team's
`persona_id` entry. If the slug is `"dev-lead"` and the persona_id is `"Forge"`
(capitalized), the Desktop sees them as different. Slugs are case-sensitive.

**Fix:** Either make them match exactly, or empty the team's `persona_ids`
array to suppress the validation entirely. Empty `persona_ids` = no check,
agents still show in the sidebar under the "Unknown" fallback section.

## 4. Deduplication — Slug Uniqueness

The Desktop app identifies agents by their `slug` field, not by name.
If you accidentally write the same agent twice (e.g., once as `"dev-lead"`
and once as `"Forge"`), both entries appear in the sidebar. Remove
duplicates before reloading the app.

Normalize all slugs to lowercase kebab-case. Check for duplicates:
```python
from collections import Counter
slugs = [a.get('slug') or a['name'].lower().replace(' ', '-') for a in agents]
dupes = {s: c for s, c in Counter(slugs).items() if c > 1}
# dedupe before saving
```

## 5. Default Agent Cleanup — Welcome Team Must Go

The Buzz Desktop ships with a builtin "Welcome Team" containing Fizz, Honey,
and Bumble. Even if you remove the agents from `managed-agents.json`, the
Welcome Team `builtin-team:welcome` may re-link them if it still has their
`persona_ids` populated. **Remove the entire Welcome Team** from `teams.json`
to prevent re-association.

```python
teams = [t for t in teams if 'welcome' not in t.get('id','').lower()]
```

The builtin agent entries (`is_builtin: true`) can remain in
`managed-agents.json` — they won't appear in the sidebar if they aren't
assigned to any team.

## 6. File Backup Behaviour

When the Desktop app fails to parse `managed-agents.json`, it:
1. Renames it to `managed-agents.json.invalid`
2. Creates `managed-agents.json` from the unmodified previous version
   (or a fresh empty array if no previous version exists)
3. The `.invalid` file is preserved for debugging — check its content
   for what the Desktop rejected

Additionally, the Buzz Desktop process MAY create backup files like
`managed-agents.json.pre-backfill.bak` during normal operation. These
are safe to delete.

Recovery from a parse error:
```python
# Restore from the .invalid backup
import shutil
shutil.copy("managed-agents.json.invalid", "managed-agents.json")
# Then fix the backend.type, slug, etc.
```

## 7. Dual-Relay Sync Never Creates Cross-Relay Operations

When maintaining both a hosted relay (`*.communities.buzz.xyz`) and a local
relay (`ws://localhost:3000`), the Nostr-level registrations must be done
**per relay**. These are independent Postgres databases. A 9030 event on
Hosted does NOT register the agent on Local.

Desktop `managed-agents.json` and `teams.json` are SHARED — they point to
whichever relay the user is connected to, configurable per-agent via
`relay_url`. You only need to edit these files once; the relay_url field
tells each agent which relay to connect to.
