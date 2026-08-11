# `/sessions` Command Deep Dive

## Source of Truth

**Registry:** `hermes_cli/commands.py` line 118:
```python
CommandDef("sessions", "Browse and resume previous sessions", "Session"),
```

Available everywhere — not cli_only, not gateway_only.

## CLI Implementation

In `cli.py:HermesCLI`, the `/sessions` command flows through:

1. `process_command()` → resolves "sessions" via `resolve_command()`
2. `_show_recent_sessions(reason="history")` — main entry point
3. `_list_recent_sessions(limit=10)` — data fetching
4. `session_db.list_sessions_rich(source="cli", exclude_sources=["tool"], limit=limit)`

### `_show_recent_sessions()` output format (lines 6304-6321):

```
Recent sessions:

  #    Title                            Preview                                  Last Active    ID
  ───  ────────────────────────────────  ────────────────────────────────────────  ─────────────  ────────────────────────
  1    law team                         [Voice message: "Okay..."                  2 min ago      20260529_083351_...
  2    Some title                       Some preview...                           1 hour ago     20260528_...

  Use /resume <number>, /resume <session id>, or /resume <session title> to continue.
  Example: /resume 2
```

The current session is excluded by ID match (`s["id"] != self.session_id`).

### Discovery from This Session

When the user typed `/sessions` in a Discord gateway context:
1. First response: raw `session_search()` data dump — functional but didn't match CLI expectation
2. User repeated the command 4 times — signal that the first attempt wasn't right
3. Root cause: I didn't check the Hermes command registry (`COMMAND_REGISTRY`) to understand what the command should ACTUALLY do
4. The fix: look up the canonical definition, find the CLI handler, and match the expected output format

## Gateway Mapping

```
User: /sessions
Agent: session_search()  # browse shape (no args)
       → format results as titled table
       → prompt /resume <id>

User: /sessions <query>
Agent: session_search(query="<query>", limit=10)
       → show matching sessions
       → prompt /resume <id>
```

## Verification

- The canonical command list is at `hermes_cli/commands.py` — check here first for any unknown command
- `resolve_command()` (in the same file) handles alias resolution and prefix matching
