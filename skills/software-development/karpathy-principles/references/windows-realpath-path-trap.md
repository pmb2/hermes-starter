# Windows `os.path.realpath` Unix-Path Resolution Trap

> **Applies to**: "Read the Source, Luke" and "Be a Scientist" principles
> **Discovered**: Forge Pulse 2026-07-15 — approval.py `_is_verification_artifact_cleanup` regression on Windows
> **Updated**: 2026-07-19 — Added Approach D (check-order reorder + splitdrive fallback)

## The Bug

```python
import os, tempfile
# On Windows:
os.path.realpath("/tmp")           # Returns 'C:\\tmp' (NOT the temp directory!)
os.path.realpath(tempfile.gettempdir())  # Returns 'C:\\Users\\<you>\\AppData\\Local\\Temp'
```

`os.path.realpath('/tmp')` on Windows does **NOT** resolve to the system temp directory. Instead, it takes the Unix-style path `/tmp`, treats it as a path on the **current drive**, and returns `C:\\tmp` (current drive root + `tmp`). This is completely unrelated to `tempfile.gettempdir()` which actually returns the real Windows temp directory.

## Why It Breaks

Code that compares a command operand against the resolved temp directory will fail silently on Windows:

```python
def _is_verification_artifact_cleanup(command: str) -> bool:
    # ...
    operand = "/tmp/hermes-verify-example.py"
    temp_dir = os.path.realpath(tempfile.gettempdir())  # → "C:\\tmp" (not "/tmp"!)
    basename = os.path.basename(operand)
    if operand != os.path.join(temp_dir, basename):     # "/tmp/... != C:\\tmp\\..."
        return False  # MISMATCH on Windows!
```

The comparison `"/tmp/hermes-verify-example.py" != "C:\\tmp\\hermes-verify-example.py"` fails because one is a Unix-style forward-slash path and the other is a Windows-style backslash path with a drive letter.

## Root Cause

1. **`os.path.realpath` is a path-resolver, NOT a temp-directory resolver.** On Unix, `/tmp` happens to be the real temp directory. On Windows, `/tmp` is just the path `\tmp` on the current drive — no special meaning.

2. **The path format mismatch**: The command operand is in Unix format (`/tmp/...`) because it came from a shell command string, while `os.path.realpath` returns a Windows-native path (`C:\\tmp\\...`). These never `==` compare equal.

3. **`tempfile.gettempdir()` returns the actual Windows temp dir** while `os.path.realpath('/tmp')` returns the drive-rooted `\tmp`. Two completely different locations.

## Detection

Run this one-liner to confirm the trap exists in your environment:

```bash
python -c "import os,tempfile; print('realpath(/tmp):', os.path.realpath('/tmp')); print('gettempdir():', tempfile.gettempdir())"
```

On Windows, these will differ. On Unix, they'll likely match (or `/tmp` may be a symlink to `/private/tmp`).

## The Fixes

### Approach A: Normalize the operand
```python
temp_dir = os.path.realpath(tempfile.gettempdir())
normalized_operand = os.path.realpath(operand)  # Normalize both sides
target = os.path.realpath(operand)
if os.path.dirname(target) != temp_dir:
    return False
```

### Approach B: Resolve Unix-style paths before comparison
```python
from pathlib import Path
temp_dir = os.path.realpath(tempfile.gettempdir())
operand_path = Path(operand).resolve()
if str(operand_path.parent) != temp_dir:
    return False
```

### Approach C: Mock `tempfile.gettempdir` to return a drive-rooted path in tests
When writing tests on Windows, ensure the mock return value is a platform-consistent path:
```python
# Bad: returns C:\tmp on Windows, /tmp on Unix
with mock.patch("tempfile.gettempdir", return_value="/tmp"):

# Good: platform-appropriate temp dir
with mock.patch("tempfile.gettempdir", return_value=str(tmp_path)):
```

### Approach D: Reorder checks in a multi-check function (RECOMMENDED)

When the function has TWO checks — one for exact path match and one for realpath resolution — the ordering matters. Reverse the checks: resolve through `realpath` FIRST, then check raw dirname with `splitdrive` fallback:

```python
def _is_verification_artifact_cleanup(command: str) -> bool:
    # ...
    operand = argv[2]
    temp_dir = os.path.realpath(tempfile.gettempdir())
    basename = os.path.basename(operand)

    # Check 1: Resolve the operand — verify it lands in the canonical temp dir
    target = os.path.realpath(operand)
    if os.path.dirname(target) != temp_dir:
        return False

    # Check 2: Is the operand a DIRECT child (no subdirectory tricks)?
    # The raw dirname must match. splitdrive handles Windows /tmp → C:\tmp.
    operand_dir = os.path.dirname(os.path.normpath(operand))
    expected_dir = os.path.normpath(temp_dir)
    if operand_dir != expected_dir:
        _, tail_op = os.path.splitdrive(operand_dir)
        _, tail_exp = os.path.splitdrive(expected_dir)
        if tail_op != tail_exp:
            return False

    return re.fullmatch(r"hermes-(?:verify|ad-hoc)-[A-Za-z0-9_.-]+", basename) is not None
```

**Why this works:** Check 1 uses `realpath` on BOTH sides (operand + temp_dir), so the Windows `/tmp`→`C:\tmp` mapping is applied consistently — they match. Check 2 then guards against subdirectory/`..` traversal by comparing the RAW dirname, with `splitdrive()` to strip drive-letter differences that would cause false mismatches.

**Why the ordering matters:** The original code checked raw-path-match FIRST (`operand == os.path.join(temp_dir, basename)`), which always fails on Windows because the path formats differ. By reversing the checks, you resolve both sides to the same canonical format before the exact-path safety check, while still catching subdirectory tricks via the raw dirname comparison.

## Related Patterns

- **`Path.home()` ignoring `HOME`** — see `references/windows-path-home-test-pattern.md` for the companion pattern where Windows path resolution deviates from Unix convention.
- **Shell path pipeline** — see `references/windows-acp-test-patterns.md` Pattern 1 for CRLF byte inflation from shell pipelines.

## Test Discovery Workflow

When a test fails on Windows with a path comparison assertion. Also use the following diagnostic when a **multi-check function** has a path-comparison regression on Windows:

1. Run the specific test verbosely: `python -m pytest tests/path/to/test.py -xvs`
2. Identify which path comparisons are happening and in what **order**
3. Check if any comparison uses `os.path.realpath` on one side but not the other
4. Check the CHECK ORDERING — if an early check compares a Unix-style path against a Windows realpath result, it always fails; the later check (which might work) never runs
5. Apply **Approach D** (reorder checks) as the primary fix
6. Verify with: all original tests on Linux + the Windows-specific realpath test
7. Check for **pre-existing Windows test incompatibilities** — some tests that pass on Linux may have always failed on Windows because `rm -f C:\...` doesn't match the `\brm\s+(-[^\s]*\s+)*/` pattern (no leading `/` on Windows drive paths). Run the test on the unmodified upstream to confirm it's pre-existing, not introduced by your fix.
