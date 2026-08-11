# the operator's Repo Map for Pulse Checks

Canonical list of project repos, their locations, priority tier, and known edge cases. Updated as repos are added or moved.

## Priority → Repo Mapping

### P0 — Must Focus
| Repo | Path | Status | Last Verified |
|------|------|--------|---------------|
| **BookEnds** | `${MY_REPOS}/bookends/` | ✅ Active git repo. Canonical path is lowercase `bookends` (though case-insensitive FS resolves both forms). Last 5 commits: nginx/Træfik simplification, Supabase OAuth PKCE fix, beta consent flow. 1 unstaged file (package-lock.json). **Remote: `pmb2/bookends`** on `main` branch. Committed May 26 — recent work, not cold. The directory `BookEnds_bak/` at the same level is an older copy; ignore it. | May 27 |
| **constructManage** | `${MY_REPOS}/constructManage/` | ✅ Active git repo. 5 recent commits: admin dashboard overhaul, FOSS maps, JSON data migration from Supabase, demo mode fixes. **20+ unstaged files as of May 27** — Codex CLI session in progress (`.codex-tmp/` and `.next/` dirs from 07:15–14:50). Last commit message explicitly says "incomplete features" — follow-up needed. | May 27 |

### P1 — Important
| Repo | Path | Status | Last Verified |
|------|------|--------|---------------|
| **TwitchFarm** | `${MY_REPOS}/TwitchFarm/` | ✅ Git repo, single commit `updates :)`. Files present (78KB app.py, email providers, account creation). No recent activity since creation. | May 26 |
| **yt-animations** | `${MY_REPOS}/yt-animations/` | ✅ Git repo. Last commit May 22-23: "Major pipeline overhaul: AnimateDiff video, LTX/FLUX model support, refined prompts, and production docs." | May 26 |
| **model-gateway** | `${MY_REPOS}/model-gateway/` | ✅ Active. Comprehensive README/ROADMAP, privacy-firewall integration, pytest suite. 4 recent commits. | May 26 |
| **agent-universe** | `${MY_REPOS}/agent-universe/` | ✅ Active (ShadowForge Swarm architecture — 89 files, 13 directories). Multiple recent commits across orchestration, voice, OSINT teams. | May 26 |
| **hermes-config** | `${MY_REPOS}/hermes-config/` | ✅ Git repo, config/mgmt base. Monthly priorities file added May 23. | May 26 |
| **git-mcp** | `${MY_REPOS}/git-mcp/` | ✅ Git repo, submodule updates recently. | May 26 |

### P2 — Later / P3 — Blocked
| Repo | Path | Notes |
|------|------|-------|
| **bch-lotto** | `${MY_REPOS}/bch-lotto/` | Bitcoin Cash project (Burn Bounty) |
| **solumina-agent** | Internal contract | BLOCKED — no platform access |

## Priorities File Location
`${MY_REPOS}/hermes-config/roadmap/monthly-priorities.md`
- Markdown table with checkbox tracking
- Last updated: May 23, 2026
- Source: Discord voice conversation

## Common Pulse Check Commands

```bash
# Full scan — ALL repos (catches hyperfocus detours the fixed list misses)
cd ${MY_REPOS}
for d in */; do
  echo "=== $d ==="
  if [ -d "$d/.git" ]; then
    echo "  Recent: $(git -C "$d" log --oneline -1 --since='3 days ago' 2>/dev/null || echo 'none')"
  else
    echo "  NOT a git repo"
    echo "  Remote: $(gh repo view pmb2/$(basename "$d") --json name,updatedAt 2>/dev/null | head -2 || echo 'no remote')"
  fi
done

# Quick focused check (use when only P0/P1 matter)
for d in BookEnds constructManage TwitchFarm yt-animations model-gateway agent-universe hermes-config git-mcp; do
  echo "=== $d ==="
  (cd "$d" 2>/dev/null && git log --oneline -5 --since="24 hours ago" 2>/dev/null) || echo "(no git repo or no activity)"
  (cd "$d" 2>/dev/null && git status --short 2>/dev/null) || true
  echo ""
done

# Check if a directory is a git repo
test -d "$REPO_DIR/.git" && echo "is git repo" || echo "NOT a git repo"

# Check if stale GitHub remote exists for P0 projects
gh repo view pmb2/bookends --json name,updatedAt,url
```

## Untracked Repos (Hyperfocus Detour Radar)

These repos exist in the github directory with recent activity but are NOT in the tracked P0/P1 list. Recent commits here may signal scope creep:
- **auto-resume** — Had a commit recently (`fix: MCP server auto-init`). May be P1/P2 work.
- **OSINT-agent** — Had a recent commit. Part of agent ecosystem research.
- **ghl** / **ghl-merge-temp** — GHL/GoHighLevel integration work.
- **leads**, **sales**, **car-detailing**, **mobile-mechanic**, **website-landlord**, **tele** — Side projects/experiments with occasional commits.
- **ComfyUI** — MLOps/infra repo, used for yt-animations pipeline.
- **claude-code**, **councilOS**, **shadowforge-swarm**, **openclaw**, **plane** — Agent ecosystem exploration repos.
- **bch-lotto** — Bitcoin Cash (Burn Bounty P2), parked.
- **n8n** — Workflow automations, parked.
- **vibe-coding** — Rapid prototyping, active May 2026.

When the full scan reveals recent commits in 4+ of these, flag it as infrastructure sprawl / scope creep.

## ADHD Pattern Detection Reference

Look for these patterns in session history + git activity:

| Pattern | Signal | Action |
|---------|--------|--------|
| **Hyperfocus detour** | Deep P1 session (100+ messages) when P0 untouched | Redirect to P0 in next pulse |
| **Infrastructure sprawl** | Deploying new services/stacks in a research session | Flag scope creep |
| **Cold P0** | No P0 commits for 3+ days while P1 active | Escalate in pulse |
| **Scaffold but no git** | Directory has README/ROADMAP but no .git | Flag as stall risk |
| **WIP sprawl** | Multiple commits across different repos same day | Recommend single focus |
| **Partially committed** | `git status --short` shows modified files not yet committed | Suggest commit/push |

## BizDev Pipeline Check (P0 Cash Gen)

Use the BizDev Agent MCP tool directly in each pulse. Key metrics to report:

```bash
# Via MCP tool: mcp_bizdev_agent_bizdev_dashboard()
# Returns JSON with:
#   total_target_companies, total_contacts, decision_makers,
#   active_contracts, total_outreach, pending_followups,
#   pipeline_value_min, pipeline_value_max,
#   contracts_won, contracts_lost
```

**RED FLAGS (escalate in pulse):**
- `total_outreach = 0` — pipeline populated but nobody contacted
- `contracts_won = 0` after 4+ active contracts — no conversions
- `pending_followups = 0` when total_outreach > 0 — dropped leads

## Quick Scan Script (combine everything)

```bash
# Full pulse scan: git status + priority check + bizdev check
echo "=== GIT ACTIVITY ==="
cd ${MY_REPOS}
for d in */; do
  [ -d "$d/.git" ] && git -C "$d" log --oneline -1 --since='3 days ago' 2>/dev/null
done
echo "=== PRIORITY FILE ==="
cat ${MY_REPOS}/hermes-config/roadmap/monthly-priorities.md
```

## May 2026 Special Cases

- **Bookends path confusion**: Both `${MY_REPOS}/bookends/` (lowercase) and `${MY_REPOS}/BookEnds_bak/` (mixed-case, _bak suffix) exist. The ACTIVE git repo is `bookends/` (lowercase). `BookEnds_bak/` is an older deployment-only copy with no `.git/`. When scanning repos, the `for d in */` loop will show `BookEnds_bak` as "NOT a git repo" — do NOT flag this as a stall risk for the P0 project. The real repo is just a different directory.
- **CoWork-OS deployed** on port 18789 (May 24 session) with AgentField (8081), OpenViking (1933), 4 worker agents. May persist or may have been torn down — verify with `docker ps` if referenced.
