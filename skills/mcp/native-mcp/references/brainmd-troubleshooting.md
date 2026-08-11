# brain.md Troubleshooting

Server-specific diagnostic notes for **brain.md** (mi4uu/brain.md) — a local-first second brain with an MCP server at `/mcp` on port 3000.

## Version-Affected

brain.md v0.4.9 (latest as of Jul 2026). The issues below may be resolved in future versions — re-test after upgrading.

## Known Issues

### 1. FTS Search Index Never Populates

**Symptom:** `search_notes("any-term")` always returns `[]` even though `list_notes` shows 10+ notes in the vault.

**Root cause:** The FTS index file at `~/.local/share/brain.md/vault/.brain/index.json` is initialized as `{"version":1,"entries":{}}` when the vault is first created and is **never updated** with actual note content. All notes exist on disk, but the index remains permanently empty.

**Diagnostic procedure:**

```bash
# 1. Check if notes exist (this works)
curl -s http://localhost:3000/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","method":"tools/call","id":1,"params":{"name":"list_notes","arguments":{}}}'

# 2. Verify search returns nothing (broken)
curl -s http://localhost:3000/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","method":"tools/call","id":2,"params":{"name":"search_notes","arguments":{"query":"pulse"}}}'

# 3. Inspect the index file directly
cat ~/.local/share/brain.md/vault/.brain/index.json
# → {"version":1,"entries":{}}  (empty entries = broken)

# 4. Read notes by explicit path (workaround that works)
curl -s http://localhost:3000/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","method":"tools/call","id":3,"params":{"name":"read_note","arguments":{"path":"private/integration-lead-pulse-2026-07-12.md"}}}'
```

**Attempted fixes that DO NOT work:**
- Restarting brain.md — FTS index is persisted as-is and never rebuilt on startup
- Writing new notes — new content is saved to disk but the index is not updated
- Triggering `search_notes` repeatedly — index is read-only; queries never populate it

**Workaround:** Use `list_notes` (enumerate vault) + `read_note` (read by explicit path) instead of `search_notes`. These tools are backed by the filesystem directly and always return correct results. The vault is git-tracked at `~/.local/share/brain.md/vault/` — notes persist across crashes.

**Confirmed permanent across 6+ weeks of monitoring:** The FTS index has been verified empty across 4 crash/restart cycles, multiple write operations, and direct inspection of the index file on disk. No sequence of operations — restart, write, re-query — ever populates the index. It is a persistent v0.4.9 bug, not an intermittent or race-condition issue.

**Upstream resolution:** File a bug report at https://github.com/mi4uu/brain.md requesting that `search_notes` (a) rebuild the FTS index on startup if notes exist but the index is empty, or (b) fall back to filesystem grep when the index is empty.

### 2. `write_note` with Multiline Content Fails via curl

**Symptom:** Writing a note with multiline content via `curl -d` returns `Parse error: Invalid JSON` even when the JSON is syntactically valid.

**Root cause:** The multiline content string in `write_note` arguments contains embedded `\n` newlines. When passed inline via curl, the shell interpolates these literal newlines, producing an invalid JSON payload on the wire.

**Fix — use Python's `json.dumps` + `urllib.request` instead:**

```python
import json, urllib.request

payload = {
    'jsonrpc': '2.0',
    'method': 'tools/call',
    'id': 4,
    'params': {
        'name': 'write_note',
        'arguments': {
            'path': 'private/note.md',
            'content': '## Header\n\nMultiline\ncontent\nwith newlines'
        }
    }
}

data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(
    'http://localhost:3000/mcp',
    data=data,
    headers={
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream'
    }
)
resp = urllib.request.urlopen(req)
print(resp.read().decode())
```

This approach works for any `tools/call` where arguments contain multiline strings. The `Accept` header is still required (brain.md returns 406 without it).

**Alternative — escape newlines in curl:** Replace literal newlines with `\\n`:
```bash
curl -s http://localhost:3000/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","method":"tools/call","id":5,"params":{"name":"write_note","arguments":{"path":"private/test.md","content":"line1\\nline2\\nline3"}}}'
```
But this breaks with very long content — prefer Python for any note longer than one line.

### 3. Vault Data Survives Crashes (But Not Always)

**What survives:** Notes written via `write_note` persist on disk at `~/.local/share/brain.md/vault/private/`. The directory is git-tracked.

**What can be lost:**
- `.brain/index.json` content (already broken — see above)
- Any server-side state not written to disk (in-memory caches, session state)

**Verification after restart:**
```bash
# 1. List notes — should still show all vault contents
# 2. Read one specific note — verify content intact
# 3. Write a new heartbeat note — verify write path works
# 4. Read it back — confirm persistence
```

**Known false-empty signal:** Immediately after restart, `list_notes` may briefly return empty. Wait 3-5 seconds and retry before concluding data loss.

### 4. No CLI Rebuild or Admin Tools

brain.md's CLI (`~/.brain.md/bin/brainmd.exe --help`) has only 4 options:
- `--vault-dir <path>` — override vault location
- `--port <n>` — override HTTP port
- `--mcp-disabled` — disable MCP entirely
- `--version` / `--help`

There is no `rebuild-index`, `vacuum`, `check`, `serve`, or admin command. Server management is entirely process-lifecycle (start/kill/restart).

### 5. No Process Lifecycle Management

brain.md is a bare binary — no auto-restart, no health check, no watchdog. If it crashes:
- Port 3000 goes silent
- Process exits with no notification
- Recovery requires manual restart (Hermes cron pulse or operator action)

#### Crash Interval Pattern

Across 6+ weeks of monitoring, brain.md v0.4.9 has exhibited an irregular crash cadence with **growing intervals** that suggest a slow resource leak (memory or file handle exhaustion) rather than a random fault:

| Event | Cycle | Continuous Uptime | Cumulative |
|-------|-------|-------------------|------------|
| 1st crash | Jun 14 → Jun 22 | ~8 days | ~8 days |
| 2nd crash | Jun 22 → Jun 22 | ~10h | ~8.4 days |
| 3rd crash | Jun 23 → Jun 23 | ~16h | ~9.1 days |
| 4th crash | Jun 25 → Jul 8 | ~29h (w/ 5-day outage) | ~10.3 days |
| 5th crash | Jul 8 → Jul 13 | ~5 days | ~15.3 days |

**Pattern analysis:** Intervals are inconsistent but trending upward. The longest uptimes (~5-8 days) are separated by shorter intervals (10-16h) that then grow again. This is consistent with a process that accumulates state (e.g., not GCing old vector index entries, leaking HTTP connections, or fragmenting its internal database) until it crosses a fatal threshold. The crash is clean (exit code 0 from SIGTERM or internal exception) — no core dump or crash log is generated.

**Diagnostic recommendation:** If the crash can be caught live, capture `ps aux` memory/RSS and open file handle counts before the process dies. This would confirm or rule out the memory leak hypothesis. A Docker container with `--memory` limit + `restart: unless-stopped` would both stabilize the service and cap the resource consumption.

**Recommended solutions (in order of durability):**
1. **Hermes MCP stdio config** — Add `command: "~/.brain.md/bin/brainmd.exe"` with `args: ["--port", "3000"]` under `mcp_servers` in config.yaml. Hermes manages the process, auto-reconnects on crash.
2. **Docker container** — Containerize with `restart: unless-stopped`. Survives crashes without any agent involvement.
3. **Hermes cron pulse recovery (bridge solution)** — If the above are not yet deployed, the pulse check cron job itself can detect and restart the binary. The pulse detects the crash (port 000), restarts via `terminal(background=true)`, and verifies tools are back. This is the pattern the Weaver pulse uses — it's less durable than options 1/2 (gap between crash and next pulse) but requires no configuration changes.

## Restart Procedure

When brain.md needs a restart (crash recovery, config change):

```bash
# 1. Kill the current process
kill $(pgrep -f brainmd) 2>/dev/null   # Linux/Mac
taskkill //F //IM brainmd.exe           # Windows

# 2. Verify it's down
curl -s --connect-timeout 2 http://localhost:3000/ && echo "Still up" || echo "Down"

# 3. Start as a managed background process
# Use terminal(background=true, command="~/.brain.md/bin/brainmd.exe --port 3000")

# 4. Wait for startup (3-5 seconds)
sleep 4

# 5. Verify MCP tools are available
curl -s http://localhost:3000/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","method":"tools/call","id":1,"params":{"name":"current_datetime","arguments":{}}}'

# 6. Verify vault data survived
curl -s http://localhost:3000/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","method":"tools/call","id":2,"params":{"name":"list_notes","arguments":{}}}'
```

**Important:** Do NOT use `nohup`, `&`, or `disown` in foreground terminal commands — Hermes catches and rejects shell-level backgrounding. Always use `terminal(background=true)`.

## Tools Reference

brain.md v0.4.9 exposes **17 MCP tools**:

| Tool | Purpose | Notes |
|------|---------|-------|
| `search_notes` | FTS search | **BROKEN** — see Issue #1 |
| `similar_notes` | Semantic/vector search | Returns `RAG_DISABLED` if no vector model configured |
| `read_note` | Read by path | ✅ Works — primary workaround |
| `write_note` | Create/overwrite note | ✅ Works — content persists on disk |
| `append_note` | Append to existing note | ✅ Works |
| `list_notes` | List all notes/folders | ✅ Works |
| `current_datetime` | Server time | ✅ Works |
| `list_tags` | Tag usage counts | ✅ Works (if tags exist) |
| `get_tasks` | Aggregate tasks | ✅ Works |
| `get_backlinks` | Backlink graph | ✅ Works |
| `find_similar_tasks` | Semantic task search | Works if vector model active |
| `find_orphans` | Isolated notes | Works |
| `find_related` | Semantically close notes | Works if vector model active |
| `context_for_query` | RAG context block | Works if vector model active |
| `semantic_outline` | Topic cluster | Works if vector model active |
| `weekly_digest` | Recent topic clusters | Works |
| `compare_notes` | Similarity + diff | Works |
