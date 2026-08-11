# Object-DB Patch Restoration onto Evolved Files

Worked example — Hermes Agent fork, Aug 5 2026 pulse (03:50 UTC).

## Context

Aug 4 rebase executed: `reset: moving to origin/main` + 8 cherry-picks. Post-reset audit flagged 5 patches lost; one audit correction (CDP split NOT lost — lives in `tools/browser_tool.py`, not `web_server.py`/`tools/browser_cdp.py`); 4 confirmed missing:

| Lost patch | SHA | Restore cost |
|---|---|---|
| approval.py lazy-init | 622c52f98 | Cheap — clean re-apply on evolved file |
| .gitignore hardening | (old commit) | Cheap — re-add patterns |
| Hermes One model library | 83776172d | Expensive — re-extract from web_server.py |
| OmniRoute lock | 72c19a87de | Expensive — conflict review vs rewritten model_switch.py/slash_commands.py |

## Restore execution (lazy-init, the priority item)

**1. Verify all SHAs still live in object DB:**
```bash
for sha in 622c52f98 83776172d 72c19a87de c05c9f610b; do printf "%s: " "$sha"; git cat-file -t "$sha"; done
# all → "commit" — recoverable
```

**2. Read the original diff** (`git show 622c52f98 -- tools/approval.py`): 5 hunks —
- module state: add `_permanent_allowlist_loaded: bool = False` flag
- `is_approved()`: call `load_permanent_allowlist()` before aliases lookup
- `_command_matches_permanent_allowlist()`: same lazy call
- `load_permanent_allowlist()`: idempotent guard (`if _permanent_allowlist_loaded: return set(_permanent_approved)`)
- module bottom: remove `load_permanent_allowlist()` import-time call

**3. Map to NEW locations by symbol (old line numbers are dead):**
```bash
grep -n "def is_approved\|def _command_matches_permanent_allowlist\|def load_permanent_allowlist\|_permanent_approved: set" tools/approval.py
# Old diff referenced :1565/:1608/:1641/:3242 — current tree has them at
# :2483/:2517/:2551/:2232 — ~900-line upward shift from upstream subsystem strip.
# Module-level call was back at :4374.
```

**4. Re-apply with `patch`, one call per hunk** (native Windows paths for the tool). Preserve the original commit's semantics: guard placement BEFORE `with _lock:` (no deadlock), flag set BEFORE the config read, comment updated to explain laziness. Lint OK on all 5.

**5. Run the tests named in the original commit message:**
```bash
python -m pytest tests/acp/test_approval_isolation.py tests/tools/test_approval.py -q
# 99 passed in 4.57s (TestAcpExecAskGate + full approval suite)
```
Note: repo `venv/Scripts/python.exe` had NO pytest — base Python 3.11 (`python`) had pytest 9.0.3. Check `python -m pytest --version` before assuming which interpreter runs tests.

**6. Commit via message file** (avoids MSYS backtick corruption in `git commit -m`):
```bash
git add .gitignore tools/approval.py && git commit -F commit-msg.txt
# 1950f4ebd — message states "Re-applies 622c52f98 semantics on the post-rebase tree"
```

**7. Verify divergence:** Ahead 9→10, Behind 71 unchanged. Crossed lazy-init off the loss list.

## Cheap-win restore: .gitignore hardening

Old patterns were known from the prior pulse log (`.coverage*`, `.playwright-mcp/`, `fr_*.json`, `cron.db`, `openai-recording-page.yml`). Re-added with a shell append rather than `patch` (append-only file, no partial-read concern):
```bash
printf '\n# Forge hardening (restored Aug 5 2026)\n.coverage*\n.playwright-mcp/\nfr_*.json\ncron.db\nopenai-recording-page.yml\n' >> .gitignore
```
Immediate visible effect: `.playwright-mcp/` disappeared from `git status` untracked noise. Also deleted stale `hermes_cli/web_server.py.orig` (768KB Jul 20 merge artifact — flagged for removal in 2 prior pulses; `.orig` files are safe clean-deletion candidates per 4h Step 6).

## Key takeaways

1. **Cherry-pick is the wrong tool for heavily-rewritten files** — re-apply hunks by hand at symbol-grepped locations. Fast, zero conflict state, and you keep full control of semantics.
2. **The original commit message is the restore spec** — it names the bug, the callers, and the tests.
3. **Audits misremember file locations** — the CDP split false-loss cost zero restore effort only because the correction happened before any work; grep whole tree before declaring loss.
4. **Restore ordering matters** — regressions (test flakiness) and cheap wins first, conflict-heavy re-extractions deferred to a dedicated session.
