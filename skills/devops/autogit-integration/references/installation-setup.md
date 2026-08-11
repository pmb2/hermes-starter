# autogit Installation & Setup (June 12, 2026)

## Installation

```bash
npm install -g @davidondrej/autogit
# → v0.6.0, zero-dependency ESM, Node >=18
```

## Hook Wiring

```bash
autogit setup
```

Writes to:
| Agent | File |
|-------|------|
| Claude Code | `~/.claude/settings.json` |
| Codex CLI / OpenCode | `~/.codex/hooks.json` |
| Cursor | `~/.cursor/hooks.json` |
| Pi | `~/.pi/agent/extensions/autogit.ts` |

OpenCode shares the Codex hooks.json — same binary lineage, no separate setup.

**Post-setup:** OpenCode/Codex requires `/hooks` trust inside the running session before hooks fire. Cursor and Claude Code work immediately.

## Repos Enabled

```bash
cd /path/to/repo && autogit on --public-ok
```

| Repo | Path |
|------|------|
| yt-animations | `${MY_REPOS}/Documents/github/yt-animations/` |
| agent-fleet | `${MY_REPOS}/Documents/github/agent-fleet/` |
| spacebar | `${MY_REPOS}/Documents/github/spacebar/` |
| auto-resume | `${MY_REPOS}/Documents/github/auto-resume/` |
| Fermi | `${MY_REPOS}/Documents/github/Fermi/` |
| git-mcp | `${MY_REPOS}/Documents/github/git-mcp/` |

## Hermes Integration

- **Skill:** `devops/autogit-integration` — tells the Hermes agent to run `autogit ship` after changes
- **Watchdog:** no-agent cron job `autogit-watchdog` (every 30m)
- **Script:** `~/.hermes/scripts/autogit-watchdog.sh` — iterates all opted-in repos, ships unstaged changes

## Secret Scan Behavior

Confirmed working — during initial setup, autogit blocked a push of agent-fleet gateway logs containing JWTs:

```
✗ autogit: blocked — possible secrets in the diff:
    scripts/logs/chief-of-staff-gateway.log: JWT
    scripts/logs/operations-lead-gateway.log: JWT
    ... (26 JWT findings across gateway logs)
```

Fix: add log directories to `.gitignore` in agent-fleet, or use `--force-secrets`.

## Verification

```bash
autogit status          # shows hooks status + current repo state
autogit --version       # 0.6.0
```
