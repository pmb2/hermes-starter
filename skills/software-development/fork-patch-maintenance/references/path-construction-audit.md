# Path-Construction Pattern Audit — `agent/` Directory (2026-07-26)

Full audit of `agent/` in the Hermes Agent codebase for `str(Path(...))` patterns that could produce backslash paths on Windows and cause cross-platform comparison failures.

## Method

```bash
grep -rn 'str(Path(' agent/ --include='*.py' | grep -v __pycache__ | grep -v '.pyc'
```

## Results: 3 Matches Found

### 1. `agent/copilot_acp_client.py:417` — 🟢 Low Risk

```python
self._acp_cwd = str(Path(acp_cwd or os.getcwd()).resolve())
```

**Assessment**: Stores the resolved cwd for use as `subprocess.Popen(cwd=...)` argument. Subprocess `cwd` parameter accepts backslash paths on Windows. **Not used in any path comparison**. No fix needed.

### 2. `agent/ssl_verify.py:56` — 🟢 Low Risk

```python
ca_path = str(Path(effective_ca).expanduser())
if os.path.isfile(ca_path):
    return ssl.create_default_context(cafile=ca_path)
```

**Assessment**: `Path.expanduser()` produces a platform-native path. `os.path.isfile()` handles backslashes. `ssl.create_default_context()` accepts native paths. **No comparison with forward-slash paths**. No fix needed.

### 3. `agent/verification_evidence.py:423` — 🟢 Low Risk

```python
cwd=str(Path(cwd or ".").resolve()),
root=str(facts.get("root") or Path(cwd or ".").resolve()),
```

**Assessment**: Both stored as record data, not compared against forward-slash path components. No fix needed.

## Conclusion

The `agent/` directory is clean — all 3 `str(Path(...))` instances are safe for cross-platform use. The `as_posix()` fix in `file_safety.py` (commit `914f45cc7`) was correctly scoped.
