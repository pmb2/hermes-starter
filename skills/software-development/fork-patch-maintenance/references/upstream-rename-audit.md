# Upstream Rename Audit — Verifying Local Patches Survive Symbol Renames

When the upstream fork renames a function, variable, or parameter **mid-cycle** (e.g. `allow_session` → `allow_permanent`),
verify your local patches don't need updating before the next rebase attempt. This technique was demonstrated
during the 2026-07-26 18:44 ET Forge Pulse cycle.

## When to Use

- Upstream pushed a rename that SEEMS cosmetic but could touch your patch zone
- You're tracking divergence and need to know whether rebase conflict risk has changed
- A scheduled pulse detects N new upstream commits to a file you've patched locally

## Audit Steps

**1. Fetch upstream and see your patch diff**

```bash
git fetch origin main
git diff origin/main -- path/to/file.py
```

Confirm every local patch still shows as a clean delta. Count the lines — if the diff shrinks, upstream partially absorbed your change (fine). If the diff grows with new conflicts, you have new work.

**2. Map your patch zone line numbers**

From the diff output, note the line range of each insertion — flag variables, guard calls, path-normalization blocks, etc.

**3. Find all upstream rename refs**

```bash
# Find every occurrence of the NEW name in the upstream version
git show origin/main:path/to/file.py | grep -n "new_name"
# Find every occurrence of the OLD name (should be 0 or transitional)
git show origin/main:path/to/file.py | grep -n "old_name"
```

**4. Cross-reference line numbers**

If rename refs cluster in a different region of the file (e.g. UX/prompt layer at L2300+ vs your patch zone at L2000-2250), **no conflict risk**.

If the rename touches a function **your patch calls or overrides**, you have a genuine conflict.

**5. Check function signature compatibility**

When the rename is a function parameter, only keyword-argument call sites need updating. Default-parameter-only changes are safe.

**6. Record the result in your pulse/fork log**

- ✅ No added conflict risk
- 🔴 New conflict zone identified (describe which patch is affected)

## Pitfalls

- **Line numbers drift** after every `git fetch`. Re-verify after each fetch.
- **Cosmetic renames can be a smoke screen** — check whether the rename is part of a broader refactor that changes semantics.
- **A clean diff doesn't mean a clean rebase** — the rename may be invisible in the diff but cause merge conflicts on the rebase due to surrounding code changes. Always test after the full rebase.
