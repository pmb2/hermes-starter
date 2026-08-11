# Behavioral Drift Detection in Fork Maintenance

> How to detect runtime behavioral differences between your fork and upstream
> that no textual merge analysis can catch. Complements the conflict-zone
> assessment and semantic-change analysis in the parent skill.

## Problem

When maintaining a fork, three classes of regression can occur:

| Class | Detection Method | Examples |
|-------|-----------------|----------|
| **Textual conflict** | `git merge-tree` / trial rebase | Line-level merge failure |
| **Semantic regression** | Post-rebase diff + test suite | Pipeline ordering reverted, test counts dropped |
| **Behavioral drift** | `git diff origin/main -- <file>` + grep for runtime config | Timeout defaults changed, feature flags flipped, environment variable names changed, function signatures modified |

Behavioral drift is the hardest to catch because:
- It produces zero merge conflicts
- Tests may still pass (the adjusted value is valid, just different from expectation)
- It's invisible to `git log origin/main -- <patched-file>` — the change is in YOUR direction, not upstream's
- It accumulates across rebases as subtle shifts in runtime semantics

## When to Check for Behavioral Drift

- **After every rebase** — as a validation step alongside `git diff HEAD~N` and test suite runs
- **When `git diff origin/main -- <file>` shows unexpected changes** — if you didn't intentionally change a config default, find out when/why it was changed
- **At escalating divergence tiers** (per the escalation ladder) — behavioral drift accumulates with divergence
- **When a test suite produces new failures after a clean rebase** — the test may depend on an upstream default that shifted

## Detection Technique

### Step 1: Full diff scan

```bash
# Show ALL differences between local and upstream for a patched file
git diff origin/main -- tools/approval.py
```

Look for:
- Default value changes (`default=60` → `default=300`)
- Hardcoded constants that differ from upstream
- Config key names, environment variable names
- Feature flags that are inverted
- Function signatures that diverged
- Import paths or module references

### Step 2: Trace the divergence origin

When you spot a behavioral difference, determine whether it was intentionally changed locally or inherited from an older upstream version:

```bash
# Option A: Search git history for when a specific identifier changed
git log -p -S "_get_approval_timeout" -- tools/approval.py

# Option B: Search for a specific value change
git log -p -S "return int(_get_approval_config()" -- tools/approval.py
```

This tells you:
- If the last change was YOUR commit → intentional local divergence
- If the last change was an UPSTREAM commit → you inherited an older value and upstream changed it
- If the last change was NEITHER (stale merge-base) → the divergence has deeper roots

### Step 3: Decide whether to align

```bash
# Check upstream's current default
git show origin/main:tools/approval.py | grep -n "def _get_approval_timeout" -A 5

# Check your local default
grep -n "def _get_approval_timeout" tools/approval.py -A 5
```

| Comparison | Verdict |
|-----------|---------|
| Local changed intentionally | Keep it — document why |
| Upstream changed after our merge-base | Consider adopting upstream's value — they may have fixed a bug we don't know about |
| Divergence is accidental (inherited old value) | Align with upstream — no reason to carry stale config |

### Step 3b: Verify the subsystem is actually active at runtime

Before spending cycles on a drift analysis, confirm the drifted subsystem is **enabled in your runtime config**. A behavioral difference in a disabled subsystem is academic:

```bash
# Check the relevant config section
grep -A5 "approvals" config.yaml
```

If the subsystem is disabled (e.g. `mode: false`), the drift has **zero production impact**. Note it in the pulse log but deprioritize alignment. The patch may still be worth keeping as a safety net for future config changes, but the urgency drops.

**Common spot-check patterns by subsystem:**

| Subsystem | Config Key to Check | Disabled Signal |
|-----------|---------------------|-----------------|
| Approval gating | `approvals.mode` | `false` |
| MOA (Mixture of Agents) | `moa.enabled` | `false` |
| Slack integration | `gateway.platforms.slack.enabled` | `false` |
| TTS | `voice.enabled` | `false` |

This check is fast (one `grep`) and can save 30+ minutes of investigation on an inactive subsystem.

### Step 4: Record in the pulse log

If the behavioral drift is intentional, document the rationale in the pulse log:
- Which value differs (local vs upstream)
- Why the local divergence exists (performance, platform compat, user preference)
- Whether it changes the rebase complexity (touches the same function as a new upstream patch)

## Concrete Example: Approval Timeout Drift

During the 2026-07-23 22:22 ET dev-lead pulse at 1025 behind:

1. `git diff origin/main -- tools/approval.py` showed:
   ```
   -    return int(_get_approval_config().get("timeout", 300))
   +    return int(_get_approval_config().get("timeout", 60))
   ```
   Local defaults to 60s, upstream defaults to 300s.

2. `git log -p -S "_get_approval_timeout" -- tools/approval.py` traced the history:
   - Upstream commit `c5e841ab` ("fix(approval): honor canonical gateway timeout") initially changed FROM separate 300s `gateway_timeout` TO shared 60s `approvals.timeout`
   - Upstream LATER (in a newer commit we haven't rebased past) changed BACK to 300s default
   - Our local HEAD inherited the 60s from the intermediate state

3. **Verdict**: Accidental divergence — upstream changed to 60s then back to 300s before we rebased. The 60s came from upstream's intermediate commit, not from our local patches. Should align with upstream's 300s before rebasing.

## Pitfalls

- **Don't confuse local changes with upstream inheritance.** When you see a difference in `git diff origin/main`, it could be YOUR intentional change OR an upstream revert that you haven't caught up with. Always trace via `git log -p -S` to determine direction.
- **Don't assume all behavioral drift is bad.** Some local patches intentionally alter runtime behavior (e.g., Windows-specific timeout values, platform compat tweaks). Document the rationale.
- **Don't skip this check because the merge was "clean."** Behavioral drift is the post-clean-merge regression — it's invisible to all merge-time checks.
- **Don't rely on line numbers alone for stability.** Even when grep finds a marker at the expected position, the function around it may have changed behavior. Always read the diff context, not just the grep output.
