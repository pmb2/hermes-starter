#!/usr/bin/env python3
"""Behavioral test for the watchdog transient-failure tolerance pattern.

Simulates the 2026-07-31 22:30 ET incident: a single `getaddrinfo failed`
blip. A zero-tolerance watchdog paused all 54 jobs; a tolerant one must NOT
pause on cycle 1, must pause on the 2nd consecutive transient cycle, and
must recover + reset the streak when health returns.

All I/O is redirected to a temp dir — no real jobs.json / state file is
touched. Loads the target script by path (handles hyphenated filenames).

Usage:
    python guardian-transient-tolerance-test.py [path-to-watchdog-script]

The harness expects the target module to expose: JOBS_FILE, STATE_FILE,
JOBS_LOCK, REPORT_DIR globals, check_model_health(), load_jobs()/save_jobs()
semantics via cmd_watch() or an equivalent one-shot cycle, and the constants
TRANSIENT_TOLERANCE_CYCLES / TRANSIENT_MARKERS (optional checks).
"""
import json
import sys
import tempfile
import pathlib
import importlib.util

SCRIPT = sys.argv[1] if len(sys.argv) > 1 else r"${USER_HOME}\AppData\Local\hermes\scripts\cron-guardian.py"
spec = importlib.util.spec_from_file_location("watchdog_under_test", SCRIPT)
g = importlib.util.module_from_spec(spec)
sys.modules["watchdog_under_test"] = g
spec.loader.exec_module(g)

tmp = pathlib.Path(tempfile.mkdtemp(prefix="watchdog-tolerance-test-"))
g.JOBS_FILE = tmp / "jobs.json"
g.STATE_FILE = tmp / "guardian_state.json"
g.REPORT_DIR = tmp / "gap-reports"
g.JOBS_LOCK = tmp / ".jobs.lock"
g.time.sleep = lambda s: None  # no real sleeps in test
# Keep report collectors fast/quiet
for name in ("collect_git_changes", "collect_email_status", "collect_pim_status",
             "collect_cron_output_summary", "collect_missed_news"):
    if hasattr(g, name):
        setattr(g, name, lambda *a, **k: {"found": False, "note": "test"} if "status" in name else [])

g.JOBS_FILE.write_text(json.dumps({"jobs": [
    {"id": "infra", "name": "Cron Guardian", "enabled": True, "state": "scheduled", "no_agent": True},
    {"id": "test-pulse", "name": "Test Pulse Job", "enabled": True, "state": "scheduled", "no_agent": False},
]}))

def job_enabled(jid):
    jobs = json.loads(g.JOBS_FILE.read_text())["jobs"]
    return [j for j in jobs if j["id"] == jid][0].get("enabled")

def state():
    return json.loads(g.STATE_FILE.read_text())

results = []
def check(name, cond):
    results.append((name, bool(cond)))

# ── Phase 1: single transient blip (the 2026-07-31 incident) ──
g.check_model_health = lambda: (False, "Tier1 connection error: [Errno 11001] getaddrinfo failed", False)
rc = g.cmd_watch()
check("cycle1 fleet stays up (no pause on single blip)", job_enabled("test-pulse") and not state().get("was_paused"))
check("cycle1 streak recorded", state().get("transient_streak") == 1)

# ── Phase 2: second consecutive transient cycle → now act ──
rc = g.cmd_watch()
check("cycle2 action taken (paused)", not job_enabled("test-pulse"))
check("cycle2 infra job exempt", job_enabled("infra"))
check("cycle2 was_paused", state().get("was_paused") is True)

# ── Phase 3: health returns → recovery, streak reset ──
g.check_model_health = lambda: (True, "API reachable with active credits", True)
rc = g.cmd_watch()
check("cycle3 resumed", job_enabled("test-pulse"))
check("cycle3 streak reset", state().get("transient_streak") == 0)
check("cycle3 recovery counted", state().get("recovery_count", 0) >= 1)

# ── Phase 4: non-transient failure still acts immediately ──
g.check_model_health = lambda: (True, "API reachable but auth failed (HTTP 401)", False)
rc = g.cmd_watch()
check("cycle4 non-transient acts immediately", not job_enabled("test-pulse"))
check("cycle4 exit code signals down", rc != 0)

failed = [r for r in results if not r[1]]
for name, ok in results:
    print(f"{'PASS' if ok else 'FAIL'}  {name}")
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
print("TEMP DIR:", tmp)
sys.exit(1 if failed else 0)
