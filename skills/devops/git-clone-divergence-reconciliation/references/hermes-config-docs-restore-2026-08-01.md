# Worked Example — Aug 1 2026: hermes-config docs/ restore

## Scenario

Canonical C: clone (`master`, configured as `skills.external_dirs`) was missing
the ENTIRE `docs/` portfolio (20 files, ~3.3K lines) that existed only on the
E: clone's `vps-hybrid` branch. C: master had only `docs/findings/` (newer
diagnostic writeups). This had been the open "Next Action" for three consecutive
Scribe pulses before it was resolved.

## What each side had

| Side | Branch | Has | Missing |
|------|--------|-----|---------|
| C: (`~/Documents/github/hermes-config`) | master (canonical) | `docs/findings/` (cliproxyapi-grok-omniroute diagnostic), CONFIG-TOGGLE toggle, YunWu routing commits | entire `docs/` portfolio |
| E: (`${MY_REPOS}/...`) | vps-hybrid | `docs/README.md`, `BRIDGE_SETUP.md`, `HERMES_RELEASE_NOTES.md`, `RESTORE_GUIDE.md`, `FOSS_TIER1_TRACKER.md`, `TERMINAL_SPAM_FIX.md`, `HERMES_CUSTOMIZATIONS.md`, `architecture/`, `guides/`, `reference/` (10 files) | `docs/findings/`, newer master commits |

Both clones point at the same remote (`https://github.com/pmb2/hermes-config.git`),
and the remote DID have `vps-hybrid` (at `ce9b1d0`) — the branch was pushed even
though the E: local clone was stale.

## Commands that worked

```bash
# 1. Remote had the branch all along
git ls-remote --heads origin          # → ce9b1d0 refs/heads/vps-hybrid

# 2. Fetch by name — NOT by MSYS path
git fetch origin vps-hybrid:refs/remotes/origin/vps-hybrid

# 3. Size the gap — one-sided diff confirms pure addition
git diff --stat origin/vps-hybrid master -- docs/ | tail -20
# → 21 files changed, 479 insertions(+), 3277 deletions(-) — everything deleted
#   from master's perspective = everything missing from master

# 4. Additive restore
git checkout origin/vps-hybrid -- docs/
# → 20 files added; docs/findings/ preserved untouched

# 5. Update index + CHANGELOG, commit
# docs/README.md: "14 files + 3 subdirectories" → "15 files + 4 subdirectories",
#   added findings/ row to Subdirectories table
# CHANGELOG.md: entry under [Unreleased] > Fixed
git commit -m "docs: restore full docs/ portfolio onto canonical master"
# → 7c9ebc7
```

## Commands that FAILED (and why)

```bash
# MSYS path fetch — git.exe is a Windows-native EXE, no path translation
git fetch ${MY_REPOS}/hermes-config vps-hybrid
# → fatal: '${MY_REPOS}/...' does not appear to be a git repository

# Python script with MSYS path — same class of failure
python ${MY_REPOS}/_project/scripts/append-digest.py ...
# → can't open file 'C:\e\yourdata\...' (path mangled to C:\e\)
# Fix: python "${MY_REPOS}/Documents/github/_project/scripts/append-digest.py"
```

## Outcome

- Commit `7c9ebc7` on canonical master: 20 files restored, `docs/findings/` preserved
- Canonical master became a superset of vps-hybrid for all documentation
- Remaining divergence documented for the lead: CONFIG-TOGGLE toggle + YunWu routing
  config commits exist on master only — that's a merge decision, not a docs task

## Lessons

1. Always check `git ls-remote --heads origin` before assuming you need to fetch
   from a local clone path — the divergent branch is usually already on the remote
2. A one-sided `git diff --stat` (all deletions) is the signature of a missing
   subtree — the restore is a pure addition, zero conflict risk
3. `git checkout origin/<branch> -- <dir>/` is the surgical tool: adds the missing
   tree, leaves local-only files alone. Reserve full merges for when you actually
   want everything from the other branch
4. Docs restore is not complete until the index doc + CHANGELOG reflect it —
   otherwise the next pulse re-flags the same gap
