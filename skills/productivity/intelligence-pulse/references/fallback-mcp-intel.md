# Tier 3 Fallback: MCP Tools as Intelligence Source

**Use when:** Both `intelligence_collector.py check-new` AND direct PIM DB SQLite queries hang (MCP server holds exclusive DB lock). MCP tools talk to the running server process and return instantly regardless of SQLite lock state.

## Available MCP Tool Fallbacks

### git-stars MCP — Recently Starred & Owned Repos

These tools work even when `gitmcp.db` is on the same locked filesystem as `pim.db` because they query via the running MCP server process, not raw SQLite.

```python
# List most recent starred repos (top N by stars)
mcp_git_stars_list_managed_repos_tool(repo_type="starred", limit=10)

# List owned repos (shows what the user has been creating lately)
mcp_git_stars_list_managed_repos_tool(repo_type="owned", limit=10)

# Search for project-relevant repos
mcp_git_stars_search_repos(query="agent OR mcp OR model OR gateway", limit=10)

# Full health + stats
mcp_git_stars_health_status_detailed()
```

**Limitations:**
- Returns repos already in the managed index — doesn't show currently-starring activity in real-time
- No bookmark/YouTube/email data — only GitHub repos
- `starred_at` field may be `None` if the ingestion didn't capture timestamps

### personal-intelligence MCP — Health & Stats

```python
# Get health stats (total counts, distribution)
mcp_personal_intelligence_health_status_detailed()
```

**Limitations:**
- May return errors if the MCP server itself is unhealthy (`'str' object has no attribute 'isoformat'` observed June 8, 2026)
- No direct saved_item query capability via MCP — the search/list tools were designed for repo management, not PIM content

### gbrain MCP — Knowledge Base Queries

the operator's gbrain contains notes, companies, people, and structured takes. When PIM is down, gbrain can substitute for recent activity intelligence:

```python
# What's been salient lately
mcp_gbrain_get_recent_salience(days=7, limit=10)

# Anomalies (unusual activity bursts)
mcp_gbrain_find_anomalies(since="today", lookback_days=30, sigma=3.0)

# Search for project-relevant knowledge
mcp_gbrain_query(query="bookends OR construct-manage OR bizdev", limit=5)
```

## When to Use This Fallback Chain

1. **Run Tier 1** (intelligence_collector.py) with `timeout=20` — if no output in 20s, bail.
2. **Run Tier 2** (PIM sqlite3 direct) with `timeout=10` — if it hangs 10s, MCP has the lock.
3. **Run Tier 3** immediately — git-stars health + list_managed_repos + gbrain salience. All three return in under 5s combined.
4. **Report honestly:** "PIM DB locked by MCP server — couldn't query bookmarks/YouTube/email directly. Intelligence limited to GitHub repo data and gbrain salience."

## What You Lose in Tier 3

| Data Source | Available in Tier 3? | Replacement |
|-------------|---------------------|-------------|
| Firefox bookmarks | ❌ | gbrain salience may surface recently-saved items |
| YouTube saved videos | ❌ | — |
| GitHub starred repos | ✅ | git-stars MCP tools work |
| Email AI news | ❌ | — |
| X/Twitter bookmarks | ❌ | — |
| PIM full-text | ❌ | — |
| PIM project tags | ❌ | — |
| Project activity (git) | ✅ | Still works via terminal() — independent of MCP |
| User sessions | ✅ | session_search() — independent of MCP |
| BizDev pipeline | ✅ | bizdev-agent MCP tools — independent of MCP |

**Bottom line:** Tier 3 gives you GitHub repo intelligence + git activity + user session history + BizDev pipeline status. Enough for a meaningful pulse, but without bookmark/YouTube/email content you won't find cross-project connections from saved items.
