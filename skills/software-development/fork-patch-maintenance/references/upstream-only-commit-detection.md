# Upstream-Only Commit Detection — Case Study

> Case study from the Hermes Agent Forge pulse (@ 2026-07-28, 1978 behind).
> Demonstrates detection of upstream commits that represent important fixes or
> hardening the fork is missing — performance improvements, security gaps, and
> upstream trajectory characterization.

## Background

The Hermes Agent fork (10 ahead, 1978 behind origin/main) tracks local patches
and upstream divergence across pulse cycles. The standard fork-patch-maintenance
workflow verifies local patches survive (section 4) but does not systematically
detect important upstream-only commits that the fork lacks.

This session uncovered three such gaps:

## 1. CDP URL Startup-Fix — Ancestry Check

**Upstream commit**: `731aa0ccc9` (Teknium, Jul 26 2026)
"fix(browser): stop stale cdp_url from stalling every startup by 10+ seconds"

**What it does**: Splits `_get_cdp_override()` into `_get_cdp_override_raw()`
(no network I/O, used by schema assembly gates) and `_get_cdp_override()`
(performs HTTP /json/version resolution, used only on actual connection paths).
A stale `browser.cdp_url` in config would previously cause ~7 serial blocking
socket connects (10s timeout each) before the CLI banner rendered — measured
15.1s of an 18s launch on a real Windows install.

**Detection**:

```bash
# The fix commit exists on origin/main but may or may not be in our branch
git merge-base --is-ancestor 731aa0ccc9 HEAD && echo "IN BRANCH" || echo "NOT IN BRANCH"
# → NOT IN BRANCH — we're missing this performance improvement
```

**Root cause**: The commit landed on origin/main after the fork's last merge
point. It was visible via `git log --oneline --all --grep="cdp_url"` but
filtering with `--all` returned results from origin/main too, creating a
false sense that it was already applied.

**Impact if missed**: On next fresh install or config-reset scenario with a
stale CDP endpoint, startup would stall ~15s with no visible error. The fix
must be cherry-picked or included in the next rebase.

**Verification that the fix wasn't already applied**:

```bash
# Also check: does our browser_tool.py already have _get_cdp_override_raw?
grep -n "_get_cdp_override_raw" tools/browser_tool.py || echo "NO raw variant"
# No match = the split hasn't been applied to our version
```

## 2. Bitwarden Encrypted Cache Security Gap

**Upstream commit**: `e89216e7f5` (fix(secrets): harden encrypted Bitwarden cache)

**What it does**: Adds `bws_cache.enc.json` to `build_write_denied_paths()` in
`agent/file_safety.py` — two lines protecting the encrypted Bitwarden Secrets
Manager disk cache from accidental write access.

**Detection**:

```bash
# Check if upstream has lines we don't
git diff origin/main -- agent/file_safety.py | grep "bws_cache"
# → "+" lines for bws_cache.enc.json that only exist in upstream version

# Count our local references
grep -c "bws_cache.enc.json" agent/file_safety.py
# → 0 (we only have the old unencrypted bws_cache.json)

# Confirm upstream has them
git show origin/main:agent/file_safety.py | grep -n "bws_cache.enc.json"
# → Lines 50-51 in upstream's build_write_denied_paths()
```

**Characterization**: This is a divergence gap, not a regression — upstream
added this hardening after the fork point. On rebase, the correct action is
to KEEP these lines (they don't conflict with our patches). The gap only
exists because our fork predates the hardening.

**Security-tier gap**: LOW severity (doesn't expose cached data) but should
still be preserved on rebase to match upstream's security posture.

## 3. Upstream Sprint Characterization

Beyond individual commits, characterizing the overall upstream direction
helps predict rebase complexity:

```bash
# Count all upstream commits since last pulse
git log --oneline origin/main --not HEAD --since="2026-07-27T19:00:00" | wc -l
# → 36 commits in ~13h (Tuesday morning EDT)

# Categorize by keyword
git log --oneline origin/main --not HEAD --since="2026-07-27T19:00:00" > /tmp/upstream.txt
grep -ci 'desktop\|tauri\|pane\|tab\|sidebar\|composer' /tmp/upstream.txt
# → 12+ desktop/Tauri UI commits

# Check for god-file impact
grep -ci 'gateway/run\|mcp_tool\|web_server\|approval' /tmp/upstream.txt
# → 1 (CDP fix in browser_tool.py, the rest are desktop only)
```

**Findings from this sprint**:
- **Primary direction**: Desktop platform build-out (status bar, resume search,
  artifacts preview, composer, pane tabs, split sashes, Home bucket) — 33%
  of commits
- **No god-file impact**: None of the 36 commits touch gateway/run.py,
  web_server.py, mcp_tool.py, or approval.py — zero conflict overlap
- **One cross-cutting fix**: CDP URL startup perf in browser_tool.py (important
  to cherry-pick, but doesn't conflict with our 10 local patches since none
  touch browser_tool.py)

## How This Transformed the Pulse Report

Without upstream-only commit detection, the report would have said:
> "Divergence at 1978. All 10 patches intact. No firefighting."

With it, the report revealed:
- 🔴 CDP URL fix NOT in branch (actionable: needs cherry-pick)
- ⚠️ Bitwarden gap confirmed (actionable: must keep during rebase)
- 🟢 Desktop sprint — no conflict overlap (reassuring: reduces rebase scope)

## Key Lessons

1. **`git merge-base --is-ancestor` is the correct ancestry check** — filters
   out origin/main commits that look local via `--all` greps
2. **Security hardening gaps are invisible to standard patch-integrity checks**
   because the fork never touched those lines — they're purely upstream additions
3. **Sprint characterization turns raw commit counts into actionable insight**
   — a "desktop sprint" and a "god-file refactor sprint" have very different
   implications for rebase scheduling
4. **The pulse cadence is what makes this detection possible** — without
   regular checks, you'd only discover the performance gap when a fresh
   install mysteriously stalls at startup
