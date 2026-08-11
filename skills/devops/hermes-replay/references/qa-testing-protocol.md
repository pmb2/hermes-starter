# Agent Replay — E2E QA Testing Protocol

> Use this protocol whenever the agent-replay engine is modified, upgraded, or
> deployed to a new environment. Verifies that all 6 MCP tools + all CLI
> commands work end-to-end with real session data.

## Protocol (7-Step)

### 1. Record a Small Session
```bash
# Pick a session with 25-50 messages (fast to process)
# List sessions from state.db
python -c "
from agent_replay.engine import ReplayEngine
e = ReplayEngine()
for s in e.list_sessions(limit=10):
    print(f'{s.id} | {s.message_count:4d} msgs | {s.source:10s}')
"

# Record it
python -m agent_replay.cli record <session_id>

# Expected: "✓ Recorded session <id>"
```

### 2. Cached Replay — Verify Every Step
```bash
python -m agent_replay.cli replay <session_id> cached

# Verify:
# - Steps count matches expected message_count
# - Cached responses are listed (look for [CACHED] markers)
# - Duration is reasonable (< 1 second for < 50 messages)
# - No error messages
```

### 3. Verify Mode — Cross-Check Against Original
```bash
python -m agent_replay.cli verify <session_id>

# Verify:
# - Matches > 0 (all cached responses should match)
# - Mismatches == 0
# - Each cached step shows ✓ marker
```

### 4. Record a Second Session + Diff
```bash
# Record another session
python -m agent_replay.cli record <different_session_id>

# Diff against the first
python -m agent_replay.cli diff <session_a> <session_b>

# Verify:
# - Summary shows correct message counts for each session
# - Changes detected (content, role, tool_calls, added/removed)
# - Stats show meaningful diffs (message_count, tool_call_count, tokens)
```

### 5. Search — Title + Content
```bash
# Title search (should work on any session)
python -m agent_replay.cli search "cron"

# Content search (text that appears in actual LLM responses)
python -m agent_replay.cli search "DraftKings"
python -m agent_replay.cli search "sports betting"

# Edge cases
python -m agent_replay.cli search ""          # empty
python -m agent_replay.cli search "zzzzzxyznonexistent"  # gibberish

# Verify:
# - Title searches return sessions with matching keywords
# - Content searches return sessions where the cached response body matches
# - No crash on empty or gibberish queries
# - No duplicate session IDs in results
```

### 6. Info — Full Metadata
```bash
python -m agent_replay.cli info <session_id>

# Verify:
# - All fields populated: title, source, model, messages, tool calls, tokens
# - Recorded status shows correct cached response count
# - Timestamps are human-readable
```

### 7. Big Session Stress Test (100+ messages)
```bash
# Find the largest recorded session
python -c "
from agent_replay.engine import ReplayEngine
e = ReplayEngine()
sessions = e.list_recorded(limit=50)
max_s = max(sessions, key=lambda s: s['message_count'])
print(f'{max_s[\"session_id\"]} — {max_s[\"message_count\"]} msgs, {max_s[\"tool_call_count\"]} tools')
"

# Replay + verify (cached mode)
python -m agent_replay.cli replay <big_session_id> cached

# Verify:
# - All steps processed (no crash)
# - Duration still < 200ms for even 200+ step sessions
# - All cached responses served correctly

# Verify mode on big session
python -m agent_replay.cli verify <big_session_id>
# Expected: matches = cached_count, mismatches = 0
```

## MCP Server Verification

After CLI testing, verify the MCP server layer:

```bash
# 1. tools/list returns all 6 tools
echo '{"method":"tools/list","id":1,"params":{}}' \
  | python -m agent_replay.mcp_server \
  | python -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d[\"tools\"])} tools'); [print(f'  {t[\"name\"]}') for t in d['tools']]"

# 2. tools/call for each tool works
echo '{"method":"tools/call","id":2,"params":{"name":"replay_list","arguments":{"limit":3}}}' \
  | python -m agent_replay.mcp_server \
  | python -c "import sys,json; d=json.load(sys.stdin); r=d.get('result',{}); print(f'{r.get(\"total\",0)} sessions')"
```

## Common Failure Modes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| "Session not found" | Incorrect session ID (truncated) | Use full ID from `list` output |
| SQLITE_BUSY | Agent writing to state.db | Retry or wait for agent to be idle |
| All verify steps mismatched | Model changed between record/replay | Expected — detects model drift |
| Search returns 0 for content queries | Cache DB empty or search not matching | Verify response_text has the term (check with sqlite3 CLI) |
| Filtered env breaking imports | Hermes stdio env filtering | Pass PATH explicitly in config.yaml env |
