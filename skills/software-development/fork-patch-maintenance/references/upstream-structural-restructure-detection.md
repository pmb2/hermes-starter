# Upstream Structural Restructure Detection

> How to detect when upstream is making wholesale architectural changes
> (directory deletions, module rewrites, 2000+ line CL-level removals)
> that affect your fork beyond the file-level refactors covered by the
> parent skill's conflict-zone assessment.

## Problem

The standard fork patch maintenance flow checks `git diff origin/main -- <patched-file>` for each file you patched. This catches file-level god-file refactors (-200+ line changes) in overlapping zones. But it misses two structural restructure patterns:

| Pattern | What Happens | Detection Gap |
|---------|-------------|---------------|
| **Directory deletion** | Upstream deletes an entire module directory (e.g., `dashboard_auth/`, `feature_flags/`). Your import statements now reference deleted paths — no file-level overlap needed. | `git diff origin/main -- <patched-file>` returns zero changes, yet `from hermes_cli.dashboard_auth import ...` will fail at runtime. |
| **CL-level structural rewrite** | Upstream rewrites a 10K+ line module, removing 2400+ lines (e.g., `main.py -2477`, `config.py -780`). Even if your patches touched different zones, the code around them is completely reorganized — grep markers survive but insertion logic is wrong. | Grep finds `_permanent_allowlist_loaded` at L2031, but the rebase fails because the function context around it was restructured. |

## Detection Techniques

### 1. Whole-Directory Existence Scan

Run this on every pulse when divergence exceeds 400 behind — regardless of whether your patched files show diff stat changes:

```bash
cd <fork-root>
git fetch origin 2>/dev/null

# Find files that exist locally but were deleted upstream
# Focus on directories you import from
for d in <key-directories>; do
  local=$(git ls-tree HEAD --name-only -r "$d" 2>/dev/null | wc -l)
  upstream=$(git ls-tree origin/main --name-only -r "$d" 2>/dev/null | wc -l)
  echo "$d: local=$local upstream=$upstream"
  if [ "$upstream" -eq 0 ]; then
    echo "  ⚠️ ENTIRE DIRECTORY DELETED UPSTREAM"
  elif [ "$local" != "$upstream" ]; then
    missing=$(comm -23 <(git ls-tree HEAD --name-only -r "$d" | sort) <(git ls-tree origin/main --name-only -r "$d" | sort) | head -5)
    echo "  ⚠️ Files missing upstream:"
    echo "$missing"
  fi
done
```

Key directories to check — any that your patches, imports, or tooling reference:
- `hermes_cli/` (common when custom CLI modules were added)
- `tools/` (common when custom tools were added)
- `gateway/` (common for custom gateway adapters)
- `hermes_cli/dashboard_auth/` (upstream may have deleted this)
- Any directory you added that might have been independently reorganised upstream

### 2. CL-Level Net Change Magnitude

Check the *total* diff stat, not just per-file. A cluster of -500+ changes across a single directory indicates a structural rewrite even if your patched files show 0 overlap:

```bash
echo "=== WIDE DIFF STAT ==="
git diff --stat origin/main | sort -t'|' -k2 -rn | head -20
echo "=== TOTAL ==="
git diff --stat origin/main | tail -1
```

Signals that trigger "directory-level critical" tier:
- Any single file with -500+ lines AND 50+ files changed total
- A directory that lost 2+ files (entire files deleted, not just trimmed)
- Total diff stat exceeding -2000 lines with 20+ files touched
- Import chains that touch deleted modules (e.g., `from hermes_cli.dashboard_auth.*`)

### 3. Purely-Local Feature Absence Verification

For features you KNOW are local-only (e.g., a custom CRUD zone, a platform-specific module, a config path override), verify they have **zero presence upstream**:

```bash
git show origin/main:<file> | grep -c "unique_feature_identifier"
# Exit 0 (nonzero count): feature references exist upstream — analysis needed
# Exit 1 (zero count): feature is purely local — zero conflict risk on this axis
```

This is the inverse of the patch-integrity check: instead of confirming OUR patches survive, we confirm UPSTREAM hasn't independently implemented something resembling our local feature. If they did, we may need to decide: adopt theirs, keep ours, or reconcile.

### 4. Upstream Author / Brand-New-Feature Detection

When you see large upstream changes, check whether they're from the core team or from contributors. A surge of contributor-origin commits may indicate an upstream code-drive or hackathon — these don't signal direction changes:

```bash
git log --format="%an: %s" origin/main --since="<last-pulse>" -- . | sort | uniq -c
```

If most changes come from 1-2 core maintainers, it's sustained refactoring work (higher risk). If spread across 10+ names, it's a contributor burst (lower risk — many touch only their own feature areas).

## Concrete Example: hermes_cli/ Restructuring at 1164 Behind

During the 2026-07-24 11:08 ET dev-lead pulse:

1. **Divergence**: 1164 behind (+139 in 13h). Previous pulse at 22:22 ET was 1025.

2. **Standard file-level check** (would have missed the real problem):
   ```bash
   git diff --stat origin/main -- tools/approval.py   # → 80 lines — our patches
   git diff --stat origin/main -- hermes_cli/web_server.py  # → 896 lines — expected
   ```
   These only showed our patched files. The real story was upstream's architectural changes.

3. **CL-level scan** caught the restructure:
   ```bash
   git diff --stat origin/main | sort -t'|' -k2 -rn | head -10
   ```
   ```
   hermes_cli/main.py           | 2477 ++++++++----------------------  ← -2477!
   hermes_cli/config.py         | 780 ++--------                      ← -780!
   hermes_cli/auth.py           | 467 +-----                          ← -467!
   hermes_cli/kanban_db.py      | 566 +------                         ← -566!
   tools/mcp_tool.py            | 755 ++++++++----------------------- ← -755!
   ```
   **Total: 36 files changed, 602 insertions(+), 3163 deletions(-)** — this is a structural rewrite.

4. **Directory existence scan** revealed:
   - `hermes_cli/dashboard_auth/` — locally present, upstream deleted (3 files, -691 lines)
   - `hermes_cli/_early_recovery.py` — locally present, upstream deleted (-226 lines)
   - `tools/tts_streaming.py` — locally present, upstream trimmed -222 lines

5. **Purely-local feature verification**:
   ```bash
   git show origin/main:hermes_cli/web_server.py | grep -c "hermes_one"
   # → Exit 1 (zero matches) — Hermes One model library is purely local
   ```

6. **Decision**: Despite grep markers surviving at expected positions for both critical patches (approval.py lazy-init flag at L2031, path fix at L1980-1994), and zero files deleted from our patch zones, the upstream restructure was so aggressive that the tier was raised from "Critical (file-level)" to "Critical (directory-level)" — requiring a structured multi-phase rebase session.

### Key Lessons

1. **Don't trust per-file diff stat alone** when divergence exceeds 800. Always run the wide diff stat to detect CL-level restructuring.
2. **Directory deletions are invisible to standard patch-zone checks.** Your import of `hermes_cli.dashboard_auth` silently becomes dead code after upstream deletes the directory.
3. **Purely-local feature verification is the mirror of patch-integrity checks.** Both are needed: "our patches survive" AND "upstream didn't create something that supercedes our feature."
4. **The upstream author fingerprint matters.** 284 commits from 2 core maintainers in 24h means a focused refactoring drive — higher risk than the same commit count spread across 15 contributors.
