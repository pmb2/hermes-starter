# Agent Replay — Search Upgrade & QA Testing (June 25-26, 2026)

## Search Upgrade (June 25, 2026)

### What Changed
The `ReplayEngine.search()` function was enhanced to search across **cached
response content** in addition to the existing title/tag search.

### Before
Search only used `LIKE` queries against the `recorded_sessions` table (title,
notes, tags). Queries like "DraftKings" or "sports betting" returned zero
results even though those terms appeared in cached LLM responses.

### After
Two-phase search:
1. **Phase 1** — existing `LIKE` search against `recorded_sessions` (title/tags)
2. **Phase 2** — `JOIN` against `cached_responses.response_text` with `LIKE`, 
   deduplicated against phase 1 results

### Verification
- 9/9 ad-hoc verification checks passed
- "DraftKings" now finds sports-betting-pulse sessions
- "sports betting" now finds sessions
- Empty/gibberish queries handled gracefully
- No deduplication in results

### Files Changed
- `src/agent_replay/engine.py` — search function enhanced (lines 533-550)

---

## Comprehensive E2E QA Testing (June 25, 2026)

Ran full 7-step quality assurance on the agent-replay system before declaring
it operational. See `references/qa-testing-protocol.md` for the repeatable
protocol.

### Test Results

| Step | Test | Result |
|------|------|--------|
| 1 | Record fresh sessions (26 msgs, 42 msgs) | ✅ |
| 2 | Cached replay — 26 steps, 138ms | ✅ 3 cached responses |
| 3 | Verify mode — cross-check original | ✅ 3/3 matches, 0 mismatches |
| 4 | Diff two different sessions | ✅ 31 message diffs, 4 stat diffs |
| 5 | Search by title + content | ✅ "DraftKings", "sports betting" |
| 6 | Info metadata | ✅ All fields populated |
| 7 | Big session stress test (202 msgs) | ✅ 19/19 matches, 0 mismatches, 145ms |

### MCP Server Verification
- tools/list returns all 6 tools
- tools/call round-trip works for replay_list
- Server registered in Hermes config.yaml (active after restart)

---

## Wiring into Hermes

The agent-replay MCP server was added to Hermes' main config.yaml
(`${USER_HOME}\AppData\Local\hermes\config.yaml`) under `mcp_servers:`.

Server will be active after next Hermes restart (MCP servers are discovered
at startup only). The 6 tools will appear as `mcp_agent_replay_*` in every
conversation.

Package installed via `pip install -e ${USER_HOME}/hermes-replay` (editable
dev install from local source).
