# Post-Reset Loss Audit — Case Study

> Aug 4 2026 Hermes Agent Forge pulse. Demonstrates the full aftermath audit when
> a fork's local stack is wiped by a forced reset — detection, loss enumeration,
> recoverability verification, and classification.

## The Event

Previous pulse (Aug 3 22:54 UTC): **4226 behind, 24 ahead**, rebase hold standing.
Next pulse (Aug 4 19:35 UTC): **64 behind, 8 ahead** — a 4162-commit collapse in
~21 hours. Normal upstream activity cannot reduce behind-count; a collapse of this
magnitude is a forced reset event.

## Step 1 — Reflog Reconstruction

```bash
git reflog -15 --date=short
# 9692e12d2 HEAD@{2026-08-04}: cherry-pick: fix(gateway): godmode APPDATA fallback...
# 75404f9a6 HEAD@{2026-08-04}: cherry-pick: fix(gateway): commit /godmode handler...
# 610c475d0 HEAD@{2026-08-04}: cherry-pick: fix(acp): skip Windows IOCP race...
# 4f5ed7627 HEAD@{2026-08-04}: commit: fix(cron): restore foreign-venv site-packages filter lost in reset
# 6004038fc HEAD@{2026-08-04}: commit: fix(qa-lead): restore scripts/__init__.py + approval Windows cleanup checks lost in reset
# 3aeff239b HEAD@{2026-08-04}: reset: moving to origin/main   ← THE EVENT
```

Reading: someone reset the branch to origin/main, then cherry-picked/re-created
8 high-value fixes. Two commit messages literally say "lost in reset" — the
operator knew restoration was incomplete. That is the tell for Step 5.

## Step 2 — Loss Surface

- Stack before: 24 ahead (from pulse log). Stack after: `git rev-list --count origin/main..HEAD` = 8. → 16 commits unaccounted for.
- `git log --oneline origin/main..HEAD` = the 8 restored fixes (godmode ×2, ACP, cron venv filter, honcho memo, busy-ack, cgroup, scripts/__init__ + approval cleanup).
- All other local commits from previous pulse "Key Persistent Fixes" list = loss candidates.

## Step 3 — Recoverability (the decisive cheap check)

```bash
for sha in 83776172d 72c19a87de 622c52f98 c05c9f610b 914f45cc7; do
  git cat-file -t $sha && echo "$sha recoverable" || echo "$sha GONE"
done
# → all 5: "commit ... recoverable"
```

After `git reset --hard`, the commits remain in the object DB (reflog holds them
~90 days). All five lost patches were recoverable — the audit upgraded from
"rewrite from scratch" (hours) to "cherry-pick / re-apply" (minutes).

## Step 4 — Classification (still needed vs obsoleted)

| Lost patch | Check | Verdict |
|---|---|---|
| approval.py lazy-init (622c52f98) | `grep -n '# Load permanent allowlist' tools/approval.py` → module-level call BACK at :4373; upstream also has it at :4380 | **Still needed** — Windows ACP flake risk returns |
| Hermes One model library (83776172d) | `git log --all --oneline -- hermes_cli/hermes_one_model_library.py` → empty; `grep -c HERMES_ONE hermes_cli/web_server.py` → 0; upstream never had it | **Feature regression** — file exists in NO reachable commit |
| OmniRoute lock (72c19a87de) | `grep -c omniroute hermes_cli/model_switch.py gateway/slash_commands.py` → 0 | **Still needed** — router lock gone |
| CDP startup split (c05c9f610b) | `grep -n '_get_cdp_override' hermes_cli/web_server.py tools/browser_cdp.py` → 0 | **Still needed** — 15s startup stall returns |
| file_safety.py as_posix (914f45cc7) | `git ls-files | grep -i file_safety` → file MOVED `tools/` → `agent/`; `grep -n as_posix agent/file_safety.py` → :662 present | **Carried by relocation** — verify tests, no re-apply needed |

Key sub-lessons:
- **File relocation check:** upstream moved `tools/file_safety.py` → `agent/file_safety.py`. Grepping the old path would have falsely reported the patch lost. Always `git ls-files` for the file first.
- **`git log --all --oneline -- <file>` empty** = file exists in NO reachable commit → genuine feature regression, not a rebase conflict. (The Hermes One extraction was local-only, so its absence from both local and upstream trees meant the feature was simply gone.)

## Step 5 — "Lost in reset" Tell

Commit messages containing "lost in reset" (`6004038fc`, `4f5ed7627`) prove the
operator knew about losses and restored a *subset*. The restored set = what they
valued most. Old-stack commits absent from BOTH the restored set AND the current
tree = the real loss surface to enumerate. Cross-check every entry from the last
pulse's "✅ All N patches intact" list.

## Step 6 — WIP Verification

Working tree after reset carried uncommitted work (resets only move HEAD/index):
- `cron/lifecycle_guard.py` (+12, NUL-byte guards) + `tools/terminal_tool.py` (+50, `_read_local_script_text`) + new `tests/cron/test_lifecycle_guard_binary_scan.py`
- Ran `python -m pytest tests/cron/test_lifecycle_guard_binary_scan.py -q` → **4 passed**. Green WIP → report "commit it now before the next reset."
- Stale `.orig` artifact: `hermes_cli/web_server.py.orig` (768KB, dated Jul 20 — weeks old) → clean-deletion candidate, not a reset casualty.

## Outcome

Report classified as 🔴 Issue Found: rebase executed, 5 patches lost, all
recoverable. Next Action: cherry-pick/re-apply the 4 still-needed patches
(lazy-init, Hermes One, OmniRoute lock, CDP split), re-add .gitignore hardening,
commit the green WIP fix first. Because the base is now current (64 behind vs
4226), restoration is low-risk cherry-picking — the rebase risk inversion after
a forced reset.
