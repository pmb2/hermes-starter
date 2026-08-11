# MCP Fleet Health Monitoring

Systematic methodology for checking the health of MCP servers in a Hermes agent fleet — the approach used by the Weaver pulse across its cycles.

## Check Order (by transport type)

1. **HTTP/SSE servers** — port probe first (fastest signal)
2. **Docker MCP containers** — `docker ps` for uptime + health
3. **Stdio servers** — directory + entry point + DB file verification
4. **Version audit** — cross-check MCP package versions against known latest
5. **One meaningful investigation** — per cycle, go deeper on one server

## Per-Server Health Checklist

### brain.md

| Check | Method | Signal |
|-------|--------|--------|
| Process alive | `curl localhost:3000/health` | `{"ok":true}` |
| Tools registered | MCP `tools/list` or health endpoint | Tools list returns |
| Vault persistence | List files in vault dir | Notes survive crashes |
| Vault path | `~/.local/share/brain.md/vault/private/` | Git-tracked (`.git` subdir) |

**Known behavioral pattern:** brain.md crashes at irregular intervals (16h–30h+ between events). The vault is **git-tracked** — notes written via the MCP `write_note` tool are stored as markdown files that survive process restarts. The HTTP config entry in `config.yaml` (`mcp_servers.brainmd → http://localhost:3000/mcp`) enables Hermes-native reconnect on restart. For full crash survivability, Dockerize with `--restart unless-stopped`.

**⚠️ FTS search index breakage:** `search_notes` has a known delayed-indexing issue that can become permanent — the tool returns `[]` even when 7+ notes exist on disk. This is not a vault data loss event; the files are intact and survivable across restarts (git-tracked). **Workaround:** use `write_note(path=...)` directly (parameter is `path`, NOT `filename`) and `read_note(path=...)` with explicit file paths. The vault lives at `~/.local/share/brain.md/vault/private/` — verify file existence with `ls` before concluding data is lost. Example workflow:

```bash
# Write (note: parameter is 'path' not 'filename')
curl -s http://localhost:3000/mcp -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","method":"tools/call","id":1,"params":{"name":"write_note","arguments":{"path":"private/example.md","content":"# Test"}}}'

# Read back
curl -s http://localhost:3000/mcp -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","method":"tools/call","id":2,"params":{"name":"read_note","arguments":{"path":"private/example.md"}}}'

# Verify files on disk
ls -la ~/.local/share/brain.md/vault/private/
```

**Vault verification:**
```bash
ls -la ~/.local/share/brain.md/vault/private/
cat ~/.local/share/brain.md/vault/private/integration-lead-pulse-$(date +%F).md
```

### open-coscientist (SakanaAI-style biomedical coscientist)

| Check | Method | Signal |
|-------|--------|--------|
| Docker status | `docker ps --filter name=open-coscientist` | `Up Xd (healthy)` |
| MCP tools | `curl localhost:8888/` | JSON with `mcp_tools[]` |
| API keys | Check response for `api_keys_configured` | `ENTREZ_EMAIL: true` |
| Integrations | Check for `indra_cogex` in status | Gateway URL listed |

Version may differ from SakanaAI AI-Scientist (v2.x) — the container image was replaced with `open-coscientist-mcp-server` (v0.1.0, FastAPI/Uvicorn).

### plane-mcp

| Check | Method | Signal |
|-------|--------|--------|
| Docker status | `docker ps --filter name=plane-mcp` | `Up Xd` |
| Port reachable | `curl localhost:8211/` | Returns (even "Not Found" = reachable) |
| SSE endpoint | `curl localhost:8211/sse` | SSE stream (bearer auth expected) |

Expects bearer token auth. 401 on SSE is normal — it means the server is responding.

### personal-intel (PIM)

| Check | Method | Signal |
|-------|--------|--------|
| DB exists | `ls -la <path>/pim.db` | File present |
| DB freshness | `stat pim.db` or `ls -la` | Modified within 24-48h |
| DB growth | Track file size across pulses | Growing = active ingestion |
| Ingestion runs | `yt_archive.log` tail | Daily 5:00 AM runs |
| Items count | SQLite query | 2300+ items, 100+ runs |

**Staleness report:** If DB hasn't changed in 48h+, check if Firefox watch source is still active. A plateau after a growth surge (e.g., 21→32MB in 2 days) may indicate the pipeline completed an initial catch-up phase and is now in steady-state with fewer new sources.

### git-stars

| Check | Method | Signal |
|-------|--------|--------|
| DB exists | `ls -la <path>/gitmcp.db` | File present |
| DB freshness | `ls -la` or `stat` | Modified within 24h |
| Data present | Look for `all_starred_data.json` | File exists |

### tradesignals

| Check | Method | Signal |
|-------|--------|--------|
| Entry point | `python -c "import mcp_server"` from project dir | Imports cleanly |
| DB location | `insider-trading/data/signals.db` | File on disk |
| DB staleness | Check `stat` modification time | **Known concern**: 44+ days stale |
| Signal agents | SQLite query on `signals.db` | 6 agents (the operator, admin, product-lead, verifier, assistant, data-lead) |
| Data source | May need manual re-trigger | No new signals since initial setup |

**Path note:** The server lives at `finance-team/signals-mcp/mcp_server.py` but the DB is at `finance-team/insider-trading/data/signals.db` — not a subdirectory of the server project.

## Docker Fleet Health Check

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

**Look for:**
- `Up Xd` or `Up X hours` (not `Exited` or `Restarting`)
- `(healthy)` label where expected
- Port mappings are present and non-conflicting
- 0 stale/exited MCP containers

**Known false positive:** `agency-stack-livekit-agent` may show "unhealthy" even when the service works — health check config issue, not actual outage.

## Stdio Server Integrity Check

For each stdio-based MCP server, verify:
1. **Directory exists** at the path specified in config.yaml
2. **Entry point file** (`mcp_server.py`, `server.py`, `app/main.py`) is present
3. **DB file** (if applicable) exists and has reasonable size
4. **Import test** — `python -c "import mcp_server"` from project directory

Common stdio servers and their entry points:

| Server | Entry Point | DB | Notes |
|--------|------------|-----|-------|
| personal-intel | `app/main.py` | `pim.db` | Package structure |
| git-stars | `app/main.py` | `gitmcp.db` | FastMCP |
| gptr-mcp | `server.py` | (external redis) | FastMCP |
| bizdev-agent | `mcp_server.py` | SQLite DB | Standalone script |
| job-agent | `mcp_server.py` | PostgreSQL | Stack includes front+db+redis |
| ai-scientist | Python package | (external data/) | Full project structure |
| camofox-browser | `mcp_server.py` | (REST API) | At `E:/.../camofox-browser/` |
| remotion-render | `remotion_mcp.server` | (Node) | Ensure no shadow `mcp/` dir |
| signals-mcp (tradesignals) | `mcp_server.py` | `insider-trading/data/signals.db` | DB not in project dir |

## Version Audit

Track installed package versions against known latest:

```bash
# Check key MCP packages
pip show <package> 2>/dev/null | grep Version
npx <package> --version 2>/dev/null
```

| Package | Track Location | Version Format |
|---------|---------------|----------------|
| `chrome-devtools-mcp` | npm global or local | Semver (1.5.0) |
| `@remotion/mcp` | npm global or local | Semver (4.0.484) |
| `@upstash/context7-mcp` | npm global or local | Semver (3.2.3) |
| `headroom-ai` | pip | Semver (0.26.0) |
| gbrain | brain health endpoint | Semver (0.42.40.0) |
| `open-coscientist` | Docker | v0.1.0 (biomedical fork) |

## Pulse Report Formatting (Discord)

```
🧵 **Weaver Pulse** | <date> <time> ET

━━━━━━━━━━━━━━━━━━━━━━

**🟢 MCP Fleet — Nominal**

**🧠 brain.md** ✅ status — details
• Sub-bullet findings
• Specific numbers

**🐳 Docker Fleet** ✅ status
• key containers

**💾 Stdio Servers** — status for each

**🔧 Investigation**: one meaningful thing done

**📦 Version Audit**: package @ version

━━━━━━━━━━━━━━━━━━━━━━
✅ Checked @ <timestamp>
```

Keep under 1500 chars. Use emoji section headers, compact bullets, bold key names, `backticks` for files/commands.

## Session-Specific Files

- `profiles/integration-lead/PULSE.md` — historical pulse log for Weaver
