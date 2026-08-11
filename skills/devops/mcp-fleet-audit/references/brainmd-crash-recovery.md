# brain.md Crash Recovery

brain.md (v0.4.9) is a bare-binary HTTP MCP server that crashes periodically with no error output. As of Jul 2026 there have been **7+ documented crash events** across pulse history. This document captures the recovery procedure and known patterns.

## Crash Signature

- **Port 3000 becomes unreachable** — `curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/mcp` returns `000`
- **No process** — `ps aux | grep brain` returns nothing
- **No stderr** — binary exits silently; no crash logs, no error messages, no core dumps
- **Data survives** — vault is git-tracked at `~/.local/share/brain.md/vault/`; all notes survive crash cycles

## Recovery Procedure

### Step 1: Verify crash

```bash
# Check port
curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://localhost:3000/mcp
# Check process
ps aux | grep -i brain | grep -v grep
# Check binary exists
ls -la ~/.brain.md/bin/brainmd.exe
```

### Step 2: Restart the binary

**Syntax matters.** `brainmd` v0.4.9 uses **flags**, not subcommands:

```bash
# CORRECT
/path/to/brainmd.exe -p 3000 -v ~/.local/share/brain.md/vault/

# WRONG — no 'serve' subcommand in this version
/path/to/brainmd.exe serve --port 3000 --vault ~/.local/share/brain.md/vault/
```

| Flag | Purpose |
|------|---------|
| `-p <n>` | HTTP port (default: 3000) |
| `-v <path>` | Vault directory (default: $XDG_DATA_HOME/brain.md/vault) |
| `--mcp-disabled` | Don't mount MCP endpoint (do not use) |

### Step 3: Use Hermes background mode

**Do NOT use nohup/nohup + &** — Hermes blocks shell-level background wrappers. Always use:

```
terminal(background=true, command="/path/to/brainmd.exe -p 3000 -v <vault>")
```

This is a long-lived process (server), so `notify_on_complete` is not needed.

### Step 4: Verify recovery

Wait ~5 seconds, then test in order:

```bash
# 1. Initialize
curl -s http://localhost:3000/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'

# 2. List tools (expect 17 tools)
curl -s http://localhost:3000/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":2,"params":{}}' | python -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d[\"result\"][\"tools\"])} tools')"

# 3. Current datetime (confirms server time)
curl -s http://localhost:3000/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","method":"tools/call","id":3,"params":{"name":"current_datetime","arguments":{}}}'
```

## Known Issues

| Issue | Details |
|-------|---------|
| **Silent crashes** | Binary exits with no error message, no stderr, no exit code signal. Crash cause unknown. |
| **No auto-restart** | No systemd/Docker supervision. After crash, stays down until manual intervention. |
| **Uptime variability** | Crashes observed as early as 6 hours after restart and as late as ~6 days. No clear trigger pattern. |
| **FTS search broken** | `search_notes` always returns `[]` — index.json has `{"entries":{}}`. Permanent v0.4.9 bug. |

## Recommended Fix (Not Yet Applied)

Dockerize brain.md to get `--restart unless-stopped` auto-recovery:

```dockerfile
FROM alpine:latest
COPY brainmd.exe /usr/local/bin/brainmd
EXPOSE 3000
CMD ["brainmd", "-p", "3000", "-v", "/vault"]
```

Then deploy with:
```bash
docker run -d --restart unless-stopped -p 3000:3000 -v ~/.local/share/brain.md/vault:/vault brainmd
```

## Relevant Pulse Context

brain.md crashes are flagged as **🔴 CRASHED** in pulse reports. After restart, status updates to **🟡 Attention Needed** (recovered but fragility noted). After 48+ hours stable, status returns to **🟢 Nominal**.
