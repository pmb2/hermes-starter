# Portfolio Audit Workflow — tested recipe (2026-08-07, pmb2 audit)

Read-only audit of local + GitHub repo portfolio. Produces findings with evidence and prioritized recommendations. **Never edit anything during the audit.**

## Step 1 — GitHub-side metadata (gh CLI)

```bash
gh repo list pmb2 --limit 200 --json name,updatedAt,pushedAt,isArchived,primaryLanguage,description \
  --jq '.[] | select(.isArchived==true) | .name'          # archived set
```

Staleness = days since `pushedAt` (fall back to `updatedAt`).
- >270d, not archived → archive candidate
- >365d → strong archive candidate
- `description == null` → professionalization gap (bulk-fix later with `gh repo edit`)

## Step 2 — Local scan (bash; do NOT use `git -C` on MSYS paths)

```bash
#!/bin/bash
for root in ${USER_HOME} ${USER_HOME}/Documents/github ${USER_HOME}/Projects \
            ${USER_HOME}/PycharmProjects ${MY_REPOS}; do
  [ -d "$root" ] || continue
  for d in "$root"/*/ ; do
    [ -d "$d/.git" ] || continue            # note: skips worktrees (.git is a file)
    ( cd "$d" && {
        remote=$(git remote get-url origin 2>/dev/null); [ -z "$remote" ] && remote="(none)"
        last=$(git log -1 --format=%cs 2>/dev/null || echo "?")
        dirty=$(git status --porcelain 2>/dev/null | wc -l)
        branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
        echo "$last|$remote|$dirty|$branch|$d"
      } )
  done
done > scan.out
```

Key points learned:
- `git -C /e/.../dir` fails with "cannot change to ... No such file or directory" on git-bash even when the path exists. `cd "$d" && git ...` inside a subshell works. Never use `git -C` with MSYS paths.
- Native Python (`execute_code`) may not resolve `/c/...`/`/e/...` paths — do the scan in bash, write a `|`-delimited file, post-process in Python by reading the file.
- Remote detection: `git remote get-url origin`; if empty try `git remote -v` first line; mark `(none)` for local-only.
- 155 repos across 5 roots scanned in seconds.

## Step 3 — Python post-processing

```python
# normalize remote: strip https://github.com/ | git@github.com: | trailing .git, lowercase
# duplicate clones: group by normalized remote, count >1 → report each clone (age, dirty, path)
# local stale: age > 120d since last local commit
# GH-only: GH repos whose lowercase name not in set of local remote names (lowercased!)
# local-only: remote == (none)
```

Pitfalls encoded here:
- **Case-insensitive matching** for GH↔local cross-reference — `CsFloat` vs `csfloat` mismatch caused false "GH-only" positives.
- **Dirty counts matter**: flag clones with uncommitted work (e.g. website-landlord E: 18 dirty) before recommending deletion — un-pushed local work is the real risk in cleanup.
- Local `git log` date can be NEWER than GH `pushedAt` → local work un-pushed. Verify with `git status`/push check before any cleanup.

## Step 4 — Deliverable shape

- Findings with evidence (repo names, days-since-push, paths, dirty counts)
- Prioritized recommendations (P0 archive/delete, P1 descriptions/docs, P2 governance)
- Governance model suggestion: one canonical location per repo, archive-at-180d policy, naming convention (no case-variant duplicates), monthly cron audit.

## Audit results snapshot (2026-08-07, for drift detection)

- GitHub: 116 repos, 10 archived; 42 non-archived stale (>270d); ~81 without description.
- Local: 155 repos; 12 duplicate remote pairs (bookends, Fermi, GHL/ghl-merge-temp, ai-scientist, project-sites, hermes-config, ms-prompt-collection, solumina-agent, trumpian-accounting-kb, website-landlord, ComfyUI, twenty tmp clones); 55 GH-only repos; 6 temp dirs on E: (`_tmp_*`, `_docker_temp`, `_project`).
- `BookEnds_bak/` on E: is NOT a git repo — 14KB stale docs backup.
- Inventory skills drift: `project-inventory` claims 126 repos / "7 archived forks" — live API says 116/10 with a different archived set. Re-verify skill claims against API each audit.
