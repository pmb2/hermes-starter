# Lost-Patch Restorability Probe

**Context:** after a reset / force-pull / rebase-onto-origin wipes the local stack, patches "lost" from `git log --oneline origin/main..HEAD` may still be recoverable from the object database. Before attempting any cherry-pick restore, probe each lost SHA — this predicts clean-apply vs conflict-resolution and prevents wasted restore attempts.

**Verified Aug 7 2026** (Hermes Agent dev-lead pulse, post-Aug-4-reset recovery).

## The Probe (~30s per SHA)

```bash
git cat-file -t <sha>                        # "commit" → object still in DB; error → gone forever
git show <sha> --stat --oneline | head -12   # which files the patch touches and how big
ls <file1> <file2> ...                       # do the patch's target files still exist in the current tree?
```

## Interpretation

| Probe result | Verdict | Restore plan |
|---|---|---|
| SHA valid, target files exist, upstream barely touched them | ✅ Clean | Straight cherry-pick |
| SHA valid, target files exist but rewritten upstream | 🟡 Conflict | Re-apply intent on upstream's new structure, manual resolution — NOT a blind cherry-pick |
| SHA valid, target file deleted upstream | ❌ Modify/delete | Re-implement intent on whatever replaced it, or drop if the code is gone |
| `git cat-file -t` errors | ❌ Gone | Re-extract from working tree (inline copy) or from the old commit's blob |

## Worked Example (Aug 7 2026)

Standing action was restoring the OmniRoute lock patch (`72c19a87de`) after the Aug 4 reset:

```bash
$ git cat-file -t 72c19a87de
commit                                        # ← still in object DB, restorable

$ git show 72c19a87de --stat --oneline | head -12
72c19a87d fix: lock model switching to OmniRoute router
 gateway/slash_commands.py  |  15 ++++++
 hermes_cli/model_switch.py | 116 ++++++++++++++++++++++++++++++++++++++++++++-
 2 files changed, 129 insertions(+), 2 deletions(-)

$ ls hermes_cli/model_switch.py gateway/slash_commands.py
hermes_cli/model_switch.py                    # ← exists, but upstream rewrote it (divergence 293 behind)
```

**Verdict:** patch is restorable but `hermes_cli/model_switch.py` was rewritten upstream since the reset → expect conflict review, plan a semantic re-apply on the new structure rather than a clean cherry-pick. This matches the per-patch audit's "modify/delete" and "semantic drift" classifications — the probe is the post-reset fast-path version of that audit.

## Triage Output

Running the probe across all N lost SHAs converts "which of my lost patches can I restore right now" from guesswork into a triage list:

1. Clean restores first (cherry-pick, low risk, quick wins)
2. Rewritten-target patches second (each needs a conflict-review pass)
3. Deleted-target patches last (re-implement or drop)
4. Missing objects → re-extract from working tree / old blobs

Same spirit as the per-patch rebase-readiness audit in SKILL.md, but for post-reset recovery rather than pre-rebase readiness.
