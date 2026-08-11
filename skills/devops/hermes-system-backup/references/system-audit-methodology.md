# Full System Audit Methodology

> Reference for pre-migration system audits. Covers the multi-phase scan performed
> on 2026-06-25 for a Windows -> Linux migration assessment.
> Used alongside the hermes-system-backup skill's "Pre-Migration System Audit" section.

## Phase 1 — Drive Layout & Usage

```bash
df -h /c/ /d/ /e/ 2>/dev/null
```

Key metrics: size, used, free, usage %. For migration planning, note which drive holds OS vs data. In this session: C: 931G (65%), D: 2.8T (88%), E: 882G (19%).

## Phase 2 — Hermes Core Audit

Check the Hermes data directory under `~/AppData/Local/hermes/`:

```bash
# Config
ls -lh ~/AppData/Local/hermes/config.yaml
ls -lh ~/AppData/Local/hermes/.env

# State database (CRITICAL — was 2.3 GB in this session)
ls -lh ~/AppData/Local/hermes/state.db

# Other databases
ls -lh ~/AppData/Local/hermes/response_store.db
ls -lh ~/AppData/Local/hermes/kanban.db
ls -lh ~/AppData/Local/hermes/comms_tracker.db
ls -lh ~/AppData/Local/hermes/cookies-transfer.sqlite

# Sessions count
ls ~/AppData/Local/hermes/sessions/sessions.db 2>/dev/null

# Profiles, skills, plugins counts
ls ~/AppData/Local/hermes/profiles/ | wc -l
ls ~/AppData/Local/hermes/skills/ | wc -l
ls ~/AppData/Local/hermes/plugins/

# Cron jobs summary
cat ~/AppData/Local/hermes/cron/jobs.json | python -c "import sys,json; j=json.load(sys.stdin); [print(f'  {j[\"name\"]}: {j[\"state\"]} ({j[\"schedule_display\"]})') for j in j['jobs']]"

# State snapshots (pre-update backups)
ls -lt ~/AppData/Local/hermes/state-snapshots/ | head -5
```

### Key Hermes Files NOT Backed Up By Git

| File | Size (this session) | Risk |
|------|---------------------|------|
| `state.db` | 2.3 GB | CRITICAL — all conversations, agent state, council state |
| `.env` | 52 KB | CRITICAL — API keys and tokens |
| `config.yaml` | 20 KB | HIGH — system configuration |
| `comms_tracker.db` | 28 KB | HIGH — business communication records, dedup/opt-out |
| `kanban.db` | 112 KB | MEDIUM — task management state |
| `cookies-transfer.sqlite` | 512 KB | MEDIUM — browser cookies |
| `cron/jobs.json` | 188 KB | HIGH — scheduled job definitions |
| `memories/MEMORY.md`, `memories/USER.md` | — | HIGH — persistent memory |
| `SOUL.md`, `gateway_state.json`, `council-state.json` | — | MEDIUM — agent identity/state |

## Phase 3 — Git Repository Audit

### Find all git repos

```bash
# Repos in home directory
find ~/ -maxdepth 2 -type d -name ".git" 2>/dev/null | sed 's|/\.git$||'

# Repos on other drives
find ${MY_REPOS}/ -maxdepth 1 -type d -name ".git" 2>/dev/null | sed 's|/[^/]*$||' | sort -u
```

In this session: **22 git repos** on C:, **~50 git repos** on E: (plus ~25 non-git dirs).

### Check each repo for dirty/unpushed work

```bash
for d in ${USER_HOME}/*/; do
  if [ -d "$d.git" ]; then
    repo=$(basename "$d")
    remote=$(git -C "$d" remote get-url origin 2>/dev/null)
    status=$(git -C "$d" status --short 2>/dev/null | wc -l)
    unpushed=$(git -C "$d" log --oneline @{u}..HEAD 2>/dev/null | wc -l)
    echo "$repo: dirty=$status unpushed=$unpushed remote=$remote"
  fi
done
```

**Red flags from this session:**
- `firefox-phantom-mcp`: **41 dirty files** — heavy active dev, nothing pushed
- `mem0-repo`: 10 dirty files — customizations not committed
- `gbrain-repo`: 1 dirty file, **NO REMOTE SET** — data at risk
- `_project`: git remote missing/failing — repo integrity issue

### Check remote health

```bash
git -C "$d" remote -v                    # check remote URL exists
git -C "$d" rev-parse --git-dir          # verify git integrity
```

### Check non-git dirs in repo folder

```bash
for d in ${MY_REPOS}/*/; do
  [ ! -d "$d.git" ] && du -sh "$d" 2>/dev/null && echo "NO-GIT: $d"
done
```

## Phase 4 — Docker Infrastructure Audit

### System-level summary

```bash
docker system df
docker system df -v   # detailed per-image/volume breakdown
docker ps -a | wc -l  # total containers (running + stopped)
docker images | wc -l # total images
```

**This session:** 159 images (236.7 GB), 89 containers (48 running), 66 volumes (329.9 GB).

### Identify volumes by stack

```bash
docker volume ls --filter name=<stack-name>
```

### Key volume patterns and what they contain

| Volume pattern | Risk | Contains |
|----------------|------|----------|
| `*_postgres_data` | CRITICAL | Main application databases |
| `*_twenty_pg_data` | CRITICAL | Twenty CRM database |
| `*_n8n_data` | CRITICAL | n8n workflow automations |
| `*_budibase_data` | HIGH | Low-code app data |
| `*_mautic_*` | HIGH | Marketing/CRM data |
| `*_authentik_data` | HIGH | Authentication config |
| `*_call_recordings` | HIGH | Voice call audio files |
| `*_comfyui-output` | HIGH | Generated video/image outputs |
| `*_minio_data` | HIGH | S3-compatible object storage |
| `*_lead_scrape_artifacts` | MEDIUM | Scraped lead data |
| `*_redis_data` | LOW | Cache (redownloadable) |
| `*_ollama_data` | LOW | Model weights (redownloadable) |

### Third-party / non-hermes Docker stacks found in this session

- **agency-stack** (26 named volumes + unnamed) — twenty, n8n, budibase, faster-whisper, mautic, fonoster, livekit, authentik, qwen-tts, voice-copilot
- **job-agent** — twenty_pg_data, server_local_data
- **yt-animations** — comfyui (models, output, user), fishspeech-models, ollama-data
- **reseller-os** — pgdata, minio_data
- **car-detailing** — postgres-data, redis-data
- **bookends (supabase)** — db, storage
- **memory stack** — postgres_data, redis_data, minio_data
- **searxng** — searxng-data, redis-data
- **councilOS** — qdrant_data

## Phase 5 — Additional Data Stores

```bash
# n8n standalone (not in Docker)
ls -lh ~/.n8n/database.sqlite

# Freelance automation profiles
ls -la ~/.freelance-automation/
ls -la ~/freelance-automation/

# Browser profiles
ls -d ~/.camofox/ ~/.cloakbrowser/ ~/TorBrowser/ 2>/dev/null

# Memory systems
ls -d ~/.mempalace/ ~/.mem0/ 2>/dev/null

# SSH keys
ls -la ~/.ssh/ 2>/dev/null

# AI tool configs
ls -d ~/.gbrain/ ~/.claude/ ~/.codex/ ~/.opencode/ ~/.cursor/ 2>/dev/null

# System config
ls -d ~/.config/ ~/.docker/ 2>/dev/null

# Important home-directory projects
ls -d ~/freelance-automation/ ~/whonix-mcp/ 2>/dev/null
```

## Phase 6 — Backup Status Classification

Classify each item:

| Classification | Meaning | Action |
|---------------|---------|--------|
| **Git-backed** | Pushed to GitHub, recoverable | Verify remote exists |
| **Git-backed + dirty** | Has uncommitted work | Commit + push before migration |
| **Not backed up — CRITICAL** | Must be manually copied | Copy to external media |
| **Redownloadable** | Can be re-fetched | Document what + versions |
| **NOT backed up — HIGH** | Important but not critical | Copy or document |

## Phase 7 — Pre-Migration Action Plan (Ordered)

1. **Commit & push** all dirty repos
2. **Fix broken git repos** — re-init missing remotes
3. **Backup state.db** to external media (~2.3 GB)
4. **Dump Postgres DBs** from Docker containers (`pg_dumpall`)
5. **Tar Docker volumes** with alpine sidecar containers
6. **Copy `.env`** — contains all provider tokens
7. **Copy SSH keys** (`~/.ssh/`)
8. **Export n8n workflows** from `~/.n8n/database.sqlite`
9. **Take final Hermes snapshot**
10. **Save Docker image list** for rebuild reference
11. **Document compose file locations** for each stack

## Pitfalls from this session

- **`du -sh ~/` on multi-TB home dirs times out** — use targeted per-directory scans instead
- **Git remote can be missing even when `.git/` exists** — always verify with `git remote -v`
- **Docker Desktop on Windows** stores volumes inside WSL2 VM, not on the native filesystem — backup strategy differs from native Linux
- **`docker system df -v`** shows volume sizes but times out on large output — use targeted queries
- **State.db is 2GB+** — too large for GitHub. Schema-only backup, or direct file copy to external drive
- **Some repos have NO remote** (`gbrain-repo`) — check all repos, not just ones with push history
