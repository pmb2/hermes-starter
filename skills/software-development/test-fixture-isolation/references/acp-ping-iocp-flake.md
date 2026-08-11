# ACP Ping Suppression — IOCP Proactor Pipe Race (WinError 6)

## Symptom

```
FAILED tests/acp/test_ping_suppression.py::test_bare_ping_request_produces_proper_response_and_no_stderr_noise
OSError: [WinError 6] The handle is invalid
```

Full traceback:
```
self._register_with_iocp(conn)
  _overlapped.CreateIoCompletionPort(obj.fileno(), self._iocp, 0, 0)
OSError: [WinError 6] The handle is invalid
```

## Root Cause

The ACP test suite creates async subprocess pipes via `asyncio.create_subprocess_exec(...)`. On Windows, the IOCP proactor tries to register the pipe handle with the completion port, but the pipe transport's `__del__` fires during test teardown and closes the file descriptor before the proactor's registration call completes. This is a race between asyncio internals — the test itself does nothing wrong.

## Status

- Pre-existing. Consistently reproducible on native Windows Python 3.11
- NOT a regression from any code change
- 8 sibling tests in the same file pass cleanly
- Identified in Sentry pulse 2026-07-29

## Mitigation Options (in priority order)

1. **Skip on Windows** — `@pytest.mark.skipif(sys.platform.startswith("win"), reason="IOCP proactor pipe handle race")`
2. **Pipe retry wrapper** — catch `OSError` + `WinError 6` in the test's setup and retry with a fresh subprocess
3. **Ignore** — the failure is cosmetic; the test checks ping suppression formatting, not a correctness boundary

## Related Files

- `tests/acp/test_ping_suppression.py`
- `hermes-agent/acp_adapter/` — the ACP server under test
