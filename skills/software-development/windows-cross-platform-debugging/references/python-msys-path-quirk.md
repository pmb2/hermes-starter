# Python Native from MSYS: Path Quirk

When running `python` from the `terminal` tool (MSYS git-bash) on this Windows host, **Python is the native Windows build, NOT an MSYS-aware build**. This means MSYS path translation does NOT occur for command-line arguments passed to Python.

## The Trap

```bash
# MSYS bash: /e/ is a virtual mount for E:\
python ${MY_REPOS}/scripts/script.py   # FAILS
```

Python receives the literal path `${MY_REPOS}/...` and interprets it relative to the current drive (typically `C:\`), resolving to `C:\e\yourdata\...` — which does not exist.

## The Fix

Use a **Windows-native path** — any of these work:

```bash
python "${MY_REPOS}/scripts/script.py"   # forward-slash Windows path — ✅
python E:\\yourdata\\scripts\\script.py   # backslash — ✅
python ${USER_HOME}/AppData/...            # MSYS /c/... works for C: drive because
                                            # C:\e\yourdata\... happens to match
                                            # the current dir — DO NOT RELY ON THIS
```

The safest pattern is always `"X:/path/to/file"` with the drive letter, colon, and forward slashes. The drive letter must match the real Windows drive.

## Why This Happens

MSYS git-bash translates paths **for MSYS-aware programs** (bash itself, git built for MSYS, grep, find, etc.), but **NOT for native Windows programs** like the official Python installer build. Python resolves `/e/...` as an absolute path on the current Windows drive (`C:\e\...`), not as a virtual mount to `E:\`.

## Test This

```bash
# Should work — native path
python -c "import os; print(os.path.exists('${MY_REPOS}'))"

# Should fail — MSYS path, no translation
python -c "import os; print(os.path.exists('${MY_REPOS}'))"
```

## Scope

This affects:
- `python some_script.py` calls with MSYS-style path arguments
- `python -m module` with MSYS-style config paths
- Any native-Windows tool called from MSYS bash with path arguments

It does NOT affect:
- `cd` / `ls` / `git` / `grep` — these are MSYS-aware and handle translation
- The `terminal` tool — it runs in MSYS bash and translates paths for MSYS programs

## Workaround: `cygpath`

If `cygpath` is available, it can convert MSYS paths to Windows paths:
```bash
win_path=$(cygpath -w "${MY_REPOS}/scripts/script.py")
# win_path = "${MY_REPOS}\scripts\script.py"
python "$win_path"
```

Though direct `"E:/..."` syntax is simpler and more reliable.
