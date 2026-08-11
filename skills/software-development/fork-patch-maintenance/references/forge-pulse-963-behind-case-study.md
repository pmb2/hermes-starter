# Case Study: Forge Pulse — Divergence Breach 963 Behind

**Context:** Forge (Hermes Core Engineer) maintaining 10 local patches against an active upstream (hermes-agent). Upstream aggressively evolves while local patches are stuck due to push-blocked (403) state.

## Trigger

Pulse at 18:48 ET on 2026-07-23. Previous pulse at 14:00 ET reported 827 behind. Time for the next cycle.

## Assessment Walkthrough

### Step 1: Baseline

```bash
cd ~/AppData/Local/hermes/hermes-agent
git fetch origin
echo "Ahead:  $(git rev-list --count origin/main..HEAD)"   # → 10
echo "Behind: $(git rev-list --count HEAD..origin/main)"    # → 963 (+136 in 5h)
git status --short                                           # → clean (2 ignorables)
```

**Finding:** Divergence jumped from 827 to 963 — highest ever recorded. Upstream was active despite evening hours.

### Step 2: Upstream Activity Scan

```bash
git log --oneline origin/main --since="2026-07-23T14:00:00-04:00" | head -10
```

Upstream commits were all Slack integration + Bedrock + security — **none touched our patched files** (approval.py, web_server.py, mcp_tool.py, gateway/run.py). Divergence increase was purely from non-conflicting work.

### Step 3: File-Level Conflict Assessment

```bash
# Check net change magnitude for each patched file
git diff --stat origin/main -- tools/approval.py
# → 80 lines (43+ 37-) — includes OUR local patches

git diff --stat origin/main -- hermes_cli/web_server.py
# → 849 lines (220+ 629-) — STRUCTURAL REFACTOR!

git diff --stat origin/main -- tools/mcp_tool.py
# → 747 lines (128+ 619-) — ALSO STRUCTURAL REFACTOR!
```

**Critical discovery:** Even though no new upstream commits touched our files in the last 5h, the upstream had massively refactored `web_server.py` (-629 lines) and `mcp_tool.py` (-619 lines) in earlier commits. Our model library CRUD at L18982-19143 intersects with `start_server()` parameter changes upstream made. This changes the rebase assessment from "line-level" to "structural".

### Step 4: Patch Integrity

```bash
grep -n "_permanent_allowlist_loaded" tools/approval.py
# → L2038, L2271-2274 — intact

grep -n "operand_normalised" tools/approval.py
# → L1984-1994 — intact (drive-letter injection fix)
```

Both critical patches confirmed present at expected positions.

### Step 5: Escalation

```
Pulse timeline:
T-4 (Jul 22 14:33): 429 behind → 🟡
T-3 (Jul 22 18:35): 555 behind → 🔴
T-2 (Jul 23 10:00): 827 behind → 🔴
T-1 (Jul 23 14:00): 827 behind → 🔴
T   (Jul 23 18:48): 963 behind → 🔴 (new record)
```

Delta positive for 5 consecutive pulses. "Safe to defer" window permanently closed.

### Step 6: Complexity Classification

- 963 behind → 🔴 Critical (exceeds 800 threshold)
- Upstream -629 lines in web_server.py (structural refactor intersecting our patch zone)
- Upstream -619 lines in mcp_tool.py
- Both critical patches stripped by upstream in approval.py (structural conflict)
- **Final tier: 🔴 Critical** — estimated 2-4 hour dedicated session needed

## Key Lessons

1. **Scan the diff --stat, not just the log.** The upstream -629/-619 line refactors in web_server.py and mcp_tool.py weren't new in this 5h window — they had landed in earlier commits. But re-checking the SIZE of the gap in this cycle revealed they were much larger than the ~80-line stat suggested for approval.py alone.

2. **God-file refactors change the game.** A -629 line change to web_server.py can shift insertion zones by hundreds of lines. Even if grep finds the markers at "expected" positions, a trial rebase would likely fail because the refactored upstream code is structured differently.

3. **Track both count AND structure.** The escalation ladder has two axes: the behind-count (963) AND the structural complexity (god-file refactors). Both independently warrant the Critical tier.

4. **Don't trust line-level stability across pulses.** Our existing focus on line-level grep verification for approval.py was necessary but insufficient — the web_server.py structural refactor was the actual escalation trigger.
