# NTFS Lazy Timestamp Flush — mtime Memoization Serves Stale Data (Windows)

Full worked example from the Hermes Agent codebase (Sentry pulse, 2026-08-01,
commit `d9d0aeec5`). The SKILL.md section gives the condensed version; this
file has the reproduction, the forensics traps, and two adjacent Windows/MSYS
gotchas encountered along the way.

## The bug

`GatewayRunner._extract_honcho_cache_busting_config` memoized by
`memo_key = (str(path), st_mtime_ns)`. A test wrote `honcho.json`, called the
extractor twice (memo hit, 1 parse), then rewrote the file and called again —
expecting a re-parse. The third call was wrongly served from the memo.

## Empirical verification (before any fix)

```python
import tempfile, pathlib, time
p = pathlib.Path(tempfile.mkdtemp()) / 'honcho.json'
p.write_text('{}')
m1 = p.stat().st_mtime_ns
p.write_text('{\n  "changed": true\n}')
m2 = p.stat().st_mtime_ns
print(m1 == m2)          # True  ← two writes, identical mtime
time.sleep(0.01)
m3 = p.stat().st_mtime_ns
print(m1 == m3)          # True  ← still identical after 10ms
```

NTFS updates file timestamps via the cache manager's dirty-metadata flush, not
synchronously on write/close. Two writes within the flush window report the
SAME `st_mtime_ns`, so a memo keyed only on `(path, mtime_ns)` never changes
and serves stale config. This is a real production edge case on Windows (a
config edited twice within the flush window), not just a test artifact.

## The fix (root cause, not test-patch)

Add `st_size` to the memo key — file size changes instantly on content change,
with no timing dependence:

```python
try:
    st = path.stat()
    mtime_ns = st.st_mtime_ns
    size = st.st_size
except OSError:
    mtime_ns = None
    size = 0
memo_key = (str(path), mtime_ns, size)
```

Result: flaky test went from failing 3/4 runs → passing 6/6 consecutive runs.

## Forensics trap: false-correlation bisect

The flake appeared to correlate with a specific test file:
- `test_agent_cache.py + my_new_file.py` → FAIL
- `test_agent_cache.py + other_file.py` → PASS

This looked like MY new file caused it. It did not — the suspect test ran
FIRST in the pair (arg order), and the flake was phase-dependent. Proof:
running the suspect test **alone 4 times** gave `pass, fail, fail, fail` (3/4
failing) — it was flaky independent of any other file.

**Rule: when a bisect implicates your change but the test is timing-sensitive,
reproduce in isolation repeatedly (5-6 runs) before concluding causation.**

## Adjacent gotcha: `git worktree add /tmp/x` on Windows/MSYS

`git worktree add /tmp/hermes-head1 HEAD~1` from git-bash creates the worktree
at `C:/tmp/hermes-head1`, but bash's `/tmp` maps elsewhere (e.g.
`C:\Users\...\AppData\Local\Temp`), so `cd /tmp/hermes-head1` fails — and you
silently re-run the tests in the CURRENT checkout, producing a worthless
comparison that looks valid. Get the real path programmatically:

```bash
WT=$(git worktree list --porcelain | grep "^worktree" | tail -1 | cut -d' ' -f2)
cd "$WT" && <run tests>
# cleanup: rm -rf <real-path> && git worktree prune
```

Also: `git -C /c/Users/...` absolute MSYS paths SILENTLY FAIL on Windows
(reported as "not a git repository" with stderr suppressed → misleadingly empty
`git status`). Always `cd` first and use relative paths. (Both are also
documented in the `windows-cross-platform-debugging` skill.)

## Adjacent: parent-process env leakage into tests ("Called 0 times")

Same session, different failure: `test_busy_session_ack.py` failed with
`Expected '_send_with_retry' to have been called once. Called 0 times.` —
the parent (cron/gateway) environment had `HERMES_GATEWAY_BUSY_ACK_ENABLED=false`,
and the test never isolated from it. One `echo $HERMES_GATEWAY_BUSY_ACK_ENABLED`
identified it instantly; forcing it to `true` made the test pass. Fix: module
autouse fixture `monkeypatch.delenv(...)`. Fast diagnostic rule: when several
tests in a file fail with the same "expected call but 0 calls" assertion,
check for a config env flag first — it suppresses the very behavior asserted.
