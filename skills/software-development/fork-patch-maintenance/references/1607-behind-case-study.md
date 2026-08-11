# 1607-Behind Divergence Case Study

Concrete walkthrough of a Critical-tier fork-assesment pulse during an upstream sprint. The divergence grew from 1178 to 1607 (+429) in ~4h as upstream accelerated after a weekend lull. Upstream refactored key god-files while purely local features had zero upstream presence.

## Context

- **Fork**: 10 local patches (lazy-init, Windows path fix, as_posix, Hermes One model library, reaction re-prompt, etc.)
- **Upstream**: `NousResearch/hermes-agent`, highly active (249 commits/24h)
- **Divergence trajectory**: 429 → 555 → 827 → 963 → 1025 → 1164 → 1178 → 1607
- **Key constraint**: Push blocked (403) — 10 local commits stuck

## The "Zero-Presence" Trap

The most critical finding was the **Hermes One model library** — a purely local +164 line CRUD zone in `hermes_cli/web_server.py`. The existing skill says:

> `git show origin/main:<file> | grep -c "unique_feature_identifier"` — if 0: "zero conflict risk on this axis"

**This is wrong when the parent file was structurally refactored.** At 1607 behind, upstream had refactored `web_server.py` by -936/+263 = -673 net lines. Our feature had zero presence because the **entire embedding context** (surrounding functions, imports, line positions) was rewritten by upstream. The insertion point for our +164 lines no longer exists in the upstream version. This makes rebase conflict **guaranteed** — not zero-risk.

### Lesson

A purely local feature's risk is determined by TWO factors:
1. **Presence**: Does it exist upstream? (0 = purely local)
2. **File stability**: Did upstream refactor the parent file? (-200+ lines net change = unstable)

The risk matrix:

| Feature Presence | File Stable | File Refactored |
|-----------------|-------------|-----------------|
| Exists upstream too | Normal merge risk | Conflict probable |
| Purely local (zero-presence) | 🟢 Low risk — insertion point stable | 🔴 **Maximum risk** — insertion point eroded |

**The zero-presence finding alone is NOT sufficient.** Must also check `git diff --stat origin/main -- <parent-file>` for refactor magnitude.

### Mitigation

Before attempting a rebase with zero-presence features in refactored files:
1. **Pre-extract** the feature into a standalone module that can be imported, not injected into a god-file
2. **Or** wait for upstream to stabilize the file structure, then re-assess insertion point

## God-File Size Trend Technique

This case study is the first to systematically track **local vs upstream god-file sizes** across cycles as a proxy for conflict surface area. The technique:

```bash
# Each cycle, record both sides:
echo "=== LOCAL ==="
wc -l gateway/run.py tools/mcp_tool.py hermes_cli/web_server.py tools/approval.py
echo "=== UPSTREAM ==="
git show origin/main:gateway/run.py | wc -l
git show origin/main:hermes_cli/web_server.py | wc -l
```

At the 1607-behind checkpoint:
| File | Local | Upstream | Delta | Trend |
|------|-------|----------|-------|-------|
| gateway/run.py | 22,984 | 24,512 | -1,528 | 🔴 upstream -1,528 refactor |
| web_server.py | 19,543 | 20,216 | -673 | 🔴 upstream -673 refactor |
| mcp_tool.py | 5,913 | 6,412 | -499 | 🔴 upstream +499 additions |
| approval.py | 3,957 | 3,951 | +6 | 🟢 stable |

**Insight:** Upstream refactoring that reduces file size does NOT reduce conflict risk — it increases it. The upstream removed code we still carry locally, creating a gap that widens with every cycle.

## Multi-Branch Divergence

Always check secondary branches, not just your active one:

```bash
git rev-list --count origin/main..qa-lead/fixes  # ahead (patches on qa-lead)
git rev-list --count qa-lead/fixes..origin/main  # behind (divergence)
```

At the 1607-behind checkpoint:
- **dev-lead (main)**: 10 ahead, 1607 behind
- **qa-lead/fixes**: 7 ahead, **5,115 behind** — +406 in <3 days

The qa-lead branch diverges at the same velocity as main, staying ~3500 further behind. This means qa-lead/fixes is never catching up — it's a recovery branch that gets periodically rebased, not actively maintained.

## Patch Integrity Kit

The full set of checks run at this checkpoint:

```bash
# 1. Divergence
git rev-list --count origin/main..HEAD  # 10
git rev-list --count HEAD..origin/main  # 1607

# 2. Upstream velocity
git log --oneline HEAD..origin/main --since="24 hours ago" | wc -l  # 249

# 3. God-files trend
wc -l gateway/run.py tools/mcp_tool.py hermes_cli/web_server.py tools/approval.py

# 4. Patch integrity — check specific markers exist
git diff origin/main -- tools/approval.py | grep -c "_permanent_allowlist_loaded"  # >0 = lazy-init intact
git diff origin/main -- tools/approval.py | grep -c "operand_normalised"  # >0 = Windows path fix intact

# 5. Zero-presence feature check
git show origin/main:hermes_cli/web_server.py | grep -c "hermes_one"  # 0 = purely local

# 6. Upstream structural refactor check
git diff --stat origin/main -- hermes_cli/web_server.py  # -936/+263 = -673 net
git diff --stat origin/main -- gateway/run.py  # -1778/+250 = -1528 net

# 7. Push status
git push --dry-run origin HEAD 2>&1 | head -3

# 8. Working tree
git status --short

# 9. Secondary branch
git rev-list --count origin/main..qa-lead/fixes
git rev-list --count qa-lead/fixes..origin/main
```

## Escalation Language

When divergence breaches 1000 and keeps accelerating, the language shifts from technical assessment to explicit urgency:

- **"Rebase window closing fast"** — at velocity >20 commits/hour from 1000 behind
- **"Guaranteed conflict"** — zero-presence feature in refactored file, not probable
- **"Pre-extract before rebase"** — concrete mitigation, not just "plan a session"
- **"Recommend: rebase within 48h"** — specific timeframe with clear consequence of delay
