# Inline vs Extracted Restore — the Half-Restore Trap

Worked example — Hermes Agent fork, Aug 7 2026 dev-lead pulse (05:20 UTC).

## Context

The Hermes One model library (originally extracted in `83776172d` into
`hermes_cli/hermes_one_model_library.py` + thin wrappers + 11 tests) was lost in
the Aug 4 reset. The standing restore action flagged it across 4 consecutive
pulses. When checked, the working tree contained a re-add — but in the WRONG
form:

- `hermes_cli/web_server.py` had the full 164-line `HERMES_ONE_MODEL_LIBRARY_COMPAT_V1`
  block re-added INLINE (mtime Aug 7 00:03, uncommitted)
- `hermes_cli/hermes_one_model_library.py` — MISSING
- `tests/test_hermes_one_model_library.py` — MISSING

Someone had restored the feature but not the design. The god-file grew back by
the exact 78 lines the extraction had removed, and test coverage was gone.

## Detection

```bash
ls hermes_cli/hermes_one_model_library.py tests/test_hermes_one_model_library.py
# ls: cannot access ... No such file or directory   ← module + tests absent

git diff --stat hermes_cli/web_server.py
# +164 insertions — a big inline block, not an import + thin wrappers
```

The original commit's design is the spec: `git show <sha> -- <file>` shows how it
wired the import and kept only the 4 FastAPI route handlers as delegating wrappers.

## Fix — restore the extracted form

**1. Pull module + tests from object DB (verbatim, no reimplementation):**
```bash
git show 83776172d:hermes_cli/hermes_one_model_library.py > hermes_cli/hermes_one_model_library.py
git show 83776172d:tests/test_hermes_one_model_library.py > tests/test_hermes_one_model_library.py
```

**2. Verify logic parity before replacing the inline block.** Extract the helper
function bodies from BOTH the inline block and the object-DB module, and diff
them — identical bodies = safe swap:

```python
import re, subprocess
src = open('hermes_cli/web_server.py', encoding='utf-8').read()
block = src[src.index('# --- HERMES_ONE_MODEL_LIBRARY_COMPAT_V1'):src.index('# --- /HERMES_ONE_MODEL_LIBRARY_COMPAT_V1')]
old = subprocess.run(['git','show','83776172d:hermes_cli/hermes_one_model_library.py'],
                     capture_output=True, text=True).stdout
# extract def _hermes_one_* bodies from both, compare — 6/7 IDENTICAL,
# 1 apparent diff was an extraction artifact (trailing decorator), bodies equal
```

**3. Replace the inline block with import + thin wrappers.** Keep the 4 route
handlers verbatim; move the 7 helpers out. Watch the splice:
- the end-marker line `# --- /HERMES_ONE_MODEL_LIBRARY_COMPAT_V1 -----...` must be
  captured WHOLE — slicing only the marker text and leaving its trailing dashes
  behind splits the line and produces an `IndentationError` on the dashes
- always `ast.parse()` the result before running anything

**4. EOL check after ANY raw Python write on Windows.** Text-mode
`open(path, "w")` converted the repo's LF file to CRLF and the diff blew up to
`17786 insertions(+), 17700 deletions(-)` — the real change was +86. Fix: read
bytes, `replace(b"\r\n", b"\n")`, write bytes; then `git diff --stat` must show
small deltas again. (Hermes `patch`/`write_file` tools preserve EOLs; prefer them
for tracked files.)

**5. Test + commit:**
```bash
python -m pytest tests/test_hermes_one_model_library.py -q   # 11 passed in 0.55s
git add hermes_cli/web_server.py hermes_cli/hermes_one_model_library.py tests/test_hermes_one_model_library.py
git commit -F msg.txt   # 882ceb61b — "restore ... in extracted-module form"
```
Final state: `web_server.py` +86 (import + 4 wrappers), module 3.5KB, 11 tests
green, divergence ahead 11→12, behind unchanged.

## Key takeaways

1. **A restored feature in the wrong FORM is a half-restore.** Check the object
   DB for the original module/tests before accepting a working-tree re-add.
2. **The original commit's diff is the wiring spec** — use `git show <sha> -- <file>`
   to see how it was structured, not just what it did.
3. **Logic-parity diff (inline vs object-DB bodies) makes the swap safe** — a
   faithful inline re-add converts cleanly because the bodies are identical.
4. **Tracked-file edits on Windows: EOL corruption is the #1 silent diff bomb.**
   Verify `git diff --stat` magnitude after every raw Python write.
5. **Incomplete restore work found in the tree is a restore-in-progress signal** —
   finish it in the original design rather than committing the inline form
   (which would re-create the god-file problem the extraction solved).
