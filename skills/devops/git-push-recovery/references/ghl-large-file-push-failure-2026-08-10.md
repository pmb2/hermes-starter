# GHL Large-File Push Failure (2026-08-10)

## Context

The GHL repo (`pmb2/GHL`) had a 177 MB `.mp4.part` file in the working tree (`How I Close $297⧸Month Clients With One 2-Minute Video [8Qgfz_zAMF0].f401.mp4.part`). This was committed by `git add -A` alongside legitimate changes (compose.yaml, route files, docs).

## Timeline

1. **Commit 1** (`7259d2f7`): `git add -A` swept in the `.part` file. Push rejected: `GH001: File exceeds 100 MB`.
2. **Attempted fix 1**: `git reset --soft HEAD~1` + `git rm --cached "How I Close..."` → `fatal: pathspec did not match any files` — the `$` and unicode in the filename caused shell mangling.
3. **Attempted fix 2**: `git reset --hard 20d6e30d` — this wiped the entire working tree changes (the legitimate route/doc changes were also lost).
4. **Recovery**: `git reflog` → found `dc30ba5c` (the lost commit) → `git cherry-pick -n dc30ba5c` restored all changes. Then `git rm --cached "How I Close"*` (glob pattern worked) removed the large file. `git commit -m "..."` + `git push origin HEAD` → **success** (commit `22183bcb`).

## Key Lessons

- **`git status --short` before `git add -A`** — catches stray large files.
- **`git reset --hard` is destructive** — prefer `git reset --soft` for fixing committed content.
- **`git cherry-pick -n`** from reflog recovers content after a botched `reset --hard`.
- **Shell globs** (`"How I Close*"`) work for `git rm --cached` where exact pathspecs fail (Windows/MSYS shell mangling of `$`, unicode, spaces).
- **Add to `.gitignore` first** to prevent re-inclusion.