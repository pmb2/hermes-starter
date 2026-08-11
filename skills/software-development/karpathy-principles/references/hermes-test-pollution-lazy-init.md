# Case Study: TestAcpExecAskGate Flakiness — Module-Level Side Effect → Lazy-Init

This is a concrete walkthrough of the Karpathy principles applied to a real bug in the Hermes Agent codebase. Use it as a template for your own debugging — the same pattern recurs across many Python test suites.

## The Symptom

2 tests in `TestAcpExecAskGate` failed intermittently — but only when run as part of the full ACP suite. In isolation (single-test-file runs), they always passed. This "combined suite" vs "isolation" asymmetry is the classic fingerprint of **test environment pollution from a module-level side effect**.

## Trace (Read the Source + Layer by Layer)

1. **Read the failing test** (`test_edit_approval.py` + ACP tests): the approval callback (`prompt_dangerous_approval`) was never invoked — `is_approved()` returned `True` before reaching the callback.

2. **Trace backward**: `is_approved()` checks `_permanent_approved` (the set of permanently allowed commands). If it finds a match, it returns early with `approved=True`, never reaching the callback.

3. **Trace what populates `_permanent_approved`**: `load_permanent_allowlist()` — which reads `config.yaml` via `hermes_cli.config.load_config()`.

4. **Trace when `load_permanent_allowlist()` runs**: At **module import time** (`tools/approval.py:3242`). This is a top-level call outside any function or class.

5. **The Full Stack insight**: When `test_edit_approval.py` is collected **first** by pytest, its module-level `from model_tools import handle_function_call` triggers import of `tools/approval`. This happens **before** the conftest's `_hermetic_environment` fixture can set `HERMES_HOME` to a tmpdir. So `load_permanent_allowlist()` reads the **real config** from the user's `~/.hermes/config.yaml`, loading `command_allowlist: ["delete in root path", ...]` into `_permanent_approved`.

6. **Why isolation passes**: When run in isolation, the test file imports `tools.approval` **inside** the test function (lazy import), *after* the conftest has already redirected `HERMES_HOME` to an empty tmpdir. Result: `_permanent_approved` is empty, the callback runs, test passes.

## Hypothesis (Be a Scientist)

```
Hypothesis: The module-level `load_permanent_allowlist()` call at line 3242 reads
the real config at import time, before HERMES_HOME can be isolated.
Combined-suite collection order imports the module early — isolation order doesn't.
```

**Experiment**: Remove the module-level call and make `is_approved()` / `_command_matches_permanent_allowlist()` trigger the load lazily on first access. Run the combined suite.

**Prediction**: With lazy loading, both the combined and isolated runs read config at the same time — after `HERMES_HOME` isolation. The flakiness disappears.

## The Fix (Simple over Clever)

The fix was 19 insertions, 4 deletions — a textbook "Simple over Clever" change:

```python
# 1. Add a lazily-init flag (line ~1410)
_permanent_allowlist_loaded: bool = False

# 2. In is_approved() (line ~1573) — first read path
def is_approved(session_key, pattern_key) -> bool:
    load_permanent_allowlist()   # <-- lazy-init call
    ...

# 3. In _command_matches_permanent_allowlist() (line ~1611) — second read path
def _command_matches_permanent_allowlist(command) -> bool:
    load_permanent_allowlist()   # <-- lazy-init call
    ...

# 4. Make load_permanent_allowlist() idempotent (line ~1644)
def load_permanent_allowlist() -> set:
    global _permanent_allowlist_loaded
    if _permanent_allowlist_loaded:
        return set(_permanent_approved)
    _permanent_allowlist_loaded = True
    # ... existing config loading logic ...

# 5. Remove the module-level call (was line ~3242)
# (deleted) load_permanent_allowlist()  # no longer at import time
```

**Why this is Simple over Clever**:
- No restructured test suite, no conftest changes, no new fixtures
- No mocking or monkeypatching in the test (avoids the "clever fix" trap)
- The fix matches the root cause directly: "the config-loading side effect runs at the wrong time" → "run it at the right time (lazily on first access)"
- 4 lines of logic + 2 call-site inserts — the entire fix fits in one screen

## Karpathy Principles in Action

| Principle | How it showed up |
|---|---|
| **Read the Source** | Traced the full call chain: test failure → `is_approved()` → `_permanent_approved` → `load_permanent_allowlist()` → module-level call at line 3242 |
| **Think First** | *Before* any code change: "Why does combined-collection-order import before conftest isolation but single-file import doesn't?" |
| **80/20** | ~30 min investigation (the trace+hypothesis above) → 5 min fix (19 lines). The ratio is right. |
| **Layer by Layer** | Start: test failure → one layer: approval callback → next: `is_approved()` → next: `_permanent_approved` set → next: `load_permanent_allowlist()` → next: config loading → final: import-timing difference |
| **Be a Scientist** | Single hypothesis → single experiment (run combined vs isolate, observe the config content each saw) |
| **Simple over Clever** | 4-line lazy-init flag beats restructuring the test suite, mocking the config, or introducing a test-only import guard |
| **Full Stack** | Had to understand: pytest collection order, `HERMES_HOME` env propagation, `from X import Y` vs `import X`, module-level side effects, and the config loading chain — 5 subsystems |
| **Build to Understand** | Could have written a minimal repro: `import tools.approval; print(_permanent_approved)` before and after `HERMES_HOME` override. Would have confirmed the hypothesis in 3 lines. |

## When to Use This Pattern

Apply lazy-init when you see this symptom cluster:

1. Tests pass in isolation but fail in combined suites
2. The failure involves state read from config, environment variables, or external files
3. The state is populated by a module-level function call or global variable initializer
4. The component imports a config loader or reads from `os.environ` at module scope

## Related Patterns

- **`references/python-test-pollution-tracing.md`** — the general cross-file pytest state pollution pattern (downstream scope)
- **`references/windows-path-home-test-pattern.md`** — a different source of imports-before-isolation bugs on Windows: `Path.home()` ignores `HOME`, uses `USERPROFILE`
