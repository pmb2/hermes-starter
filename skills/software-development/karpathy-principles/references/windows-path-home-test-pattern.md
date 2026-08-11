# Windows `Path.home()` Test Debugging Pattern

> **Applies to**: "Read the Source, Luke" and "Understand the Full Stack" principles

## The Bug

A test monkeypatches `HOME` expecting `Path.home()` or `os.path.expanduser("~")` to pick it up — then the test fails on Windows.

**Root cause**: On Windows, `Path.home()` and `os.path.expanduser("~")` **ignore the `HOME` env var entirely**. They use `USERPROFILE` (or `HOMEDRIVE` + `HOMEPATH`). This is a documented CPython implementation detail that never matches Unix convention.

## The Fix

Always patch `USERPROFILE` alongside `HOME`:

```python
monkeypatch.setenv("HOME", str(tmp_path))
monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows compat
```

Three variants appear in the codebase depending on context:

### Variant A: Test with monkeypatch fixture (most common)
```python
def test_something(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows
```

### Variant B: `patch.dict` with `os.environ`
```python
with patch.dict(os.environ, {"HOME": str(tmp_path), "USERPROFILE": str(tmp_path)}):
    ...
```

### Variant C: Selective pop with canonical expected value
```python
patched = {k: v for k, v in os.environ.items() if k not in {"HOME", "USERPROFILE", "LOCALAPPDATA"}}
# Use _get_platform_default_hermes_home() for expected value instead of hardcoding
```

## Files That Have Needed This Fix

Recurring across Forge pulse cycles (tracked):

| Test file | Pattern | Times lost in rebase |
|-----------|---------|---------------------|
| `tests/agent/lsp/test_workspace.py` | Variant A | 15+ cycles |
| `tests/hindsight/test_post_setup.py` (4 tests) | Variant A | 5+ cycles |
| `tests/agent/test_context_references.py` | Variant A | 4 cycles |
| `tests/tools/test_approval.py` | Variant B | 3 cycles |

## Why It Keeps Getting Lost

1. **Upstream reverts**: The fix is applied as a local patch. Upstream maintainers (primarily macOS/Linux) don't face the bug, so they occasionally revert the Windows compat layer or overwrite the test file with a POSIX-centric version.
2. **Rebase losses**: During large rebases (50+ commits), these 1-line changes are easy to miss in conflict resolution.
3. **New tests added without fix**: Upstream adds a new test that calls `Path.home()` without `USERPROFILE` — the pattern must be applied to the new test.

## Detection

When a test fails on Windows with an assertion involving `Path.home()` or `os.path.expanduser("~")`:

```bash
# Run the failing test with verbose output
python -m pytest tests/path/to/test.py -x -v --timeout=60

# Check if the error involves path resolution via home
# Common error: assert False is True  (path doesn't exist)
#             or assert some_path.exists()  (file written to wrong location)
```

If the test monkeypatches `HOME` but not `USERPROFILE`, it's this bug.

## Prevention

When reviewing or writing any test that uses `monkeypatch.setenv("HOME", ...)` or `patch.dict` with `HOME`:

1. **Add `USERPROFILE` in the same batch** — it's two characters and prevents a Windows-specific CI failure.
2. **Add a comment** explaining why: `# Windows compat: Path.home() uses USERPROFILE`
