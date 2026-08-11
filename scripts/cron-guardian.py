#!/usr/bin/env python3
"""
CRON GUARDIAN v2.2 — Centralized Model Config + transient-failure tolerance
================================================================
Now reads all model config from hermes_model.py (single source of truth).
Swap models by editing model_config.json → change "active_profile".

v2.2 (2026-07-31): transient-failure tolerance — a single DNS blip / timeout
no longer pauses the whole fleet. In-cycle retry + N-cycle tolerance window
before pausing. See TRANSIENT_TOLERANCE_CYCLES below.
"""
import os, sys, json, time, re, socket, ssl, urllib.request, urllib.error, subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta

# ─── CENTRALIZED MODEL CONFIG ─────────────────────────────────────────
# ALL model settings come from hermes_model.py — one file to rule them all.
sys.path.insert(0, str(Path(__file__).parent))
from hermes_model import get_config, get_api_key, active_profile, list_profiles

_MODEL_CFG = get_config()  # active profile's config
API_BASE_URL = _MODEL_CFG["base_url"]
API_KEY_ENV = _MODEL_CFG["api_key_env"]
# Health probe model: auto/best-fast is a verified-working OmniRoute routing alias
# (2026-08-11: yunwu/gpt-5.6-sol and yunwu/deepseek-v4-flash both 503; auto/* 200).
HEALTH_CHECK_MODEL = os.environ.get("HERMES_HEALTH_MODEL", "auto/best-fast")
DEFAULT_JOB_MODEL = _MODEL_CFG["model"]
DEFAULT_JOB_PROVIDER = _MODEL_CFG["provider"]
DEFAULT_BASE_URL = _MODEL_CFG["base_url"]

# ─── PATHS ──────────────────────────────────────────────────────────────
HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / "AppData" / "Local" / "hermes"))
CRON_DIR = HERMES_HOME / "cron"
JOBS_FILE = CRON_DIR / "jobs.json"
JOBS_LOCK = CRON_DIR / ".jobs.lock"
STATE_FILE = CRON_DIR / "guardian_state.json"
REPORT_DIR = CRON_DIR / "gap-reports"
SCRIPT_DIR = HERMES_HOME / "scripts"

# Repos to scan for code changes (hardcoded for the operator)
REPO_ROOTS = [
    Path("${MY_REPOS}"),
    Path("${USER_HOME}/Documents/github"),
]

# Jobs that must NEVER be paused (infrastructure / self-preservation)
NEVER_PAUSE = {
    "Cron Guardian", "Guardian Angel", "Cron Watchdog",
    "Hermes Self-Healer", "model-health-watchdog", "welcome-back-briefing",
    "tor-circuit-rotation", "Hermes System Backup", "PIM Ingestion",
    "PIM Ingestion & Sync", "refresh-firefox-cookies",
    "buzz-bridge-watchdog", "buzz-pulse-bridge",  # bridge liveness (added 2026-08-11)
    "safety-fallback-watchdog", "Coding Buddy Watchdog", "PIM Real-Time",
    "btc-attacker", "Hermes log rotate", "gbrain-dream-cycle",
    "Usage Analytics", "stealth-browser-watchdog",
}

# ─── TRANSIENT-FAILURE TOLERANCE (v2.2) ─────────────────────────────
# A single DNS blip / timeout should NOT pause the fleet: on 2026-07-31
# 22:30 ET one `getaddrinfo failed` blip paused 54 jobs for 15 min of dark.
# Behavior: transient Tier1 error → retry once in-cycle; if still failing,
# require TRANSIENT_TOLERANCE_CYCLES consecutive failed cycles (~30 min at
# the 15-min cadence) before pausing. Non-transient failures (HTTP 4xx/5xx,
# credit exhaustion) still pause immediately.
TRANSIENT_TOLERANCE_CYCLES = 2
TRANSIENT_MARKERS = [
    "getaddrinfo", "name resolution", "temporary failure",
    "timeout", "timed out", "connection reset", "connection aborted",
    "connection refused", "network is unreachable", "no route to host",
]


def is_transient_tier1(detail):
    """True if a Tier1 failure looks transient (DNS/timeout/reset) vs a real outage."""
    d = detail.lower()
    return any(m in d for m in TRANSIENT_MARKERS)

# ─── UTILITIES ─────────────────────────────────────────────────────
def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{ts}] {msg}")


def load_env_key():
    """Read API key from centralized model config (env → .env → fallback)."""
    key = get_api_key()
    if key:
        return key
    # Fallback: try .env file directly
    env_file = HERMES_HOME / ".env"
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith(f"{API_KEY_ENV}="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    # Fallback: try OpenCode auth.json (transitional compat)
    auth_file = Path.home() / ".local" / "share" / "opencode" / "auth.json"
    if auth_file.exists():
        try:
            data = json.loads(auth_file.read_text())
            key = data.get("opencode-go", {}).get("key", "")
            if key:
                return key
        except Exception:
            pass
    return os.environ.get("DEEPSEEK_API_KEY", "")


def check_model_health():
    """
    Two-tier health check using only stdlib HTTP.
    Returns: (healthy: bool, detail: str, has_credits: bool)
    """
    api_key = load_env_key()

    # Tier 1: API reachability + auth
    try:
        req = urllib.request.Request(
            f"{API_BASE_URL}/models",
            headers={
                "User-Agent": "curl/7.68.0",
                "Authorization": f"Bearer {api_key}" if api_key else "",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status != 200:
                return False, f"Tier1 HTTP {resp.status}", False
            data = json.loads(resp.read().decode())
            models = [m.get("id") for m in data.get("data", [])]
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="ignore")[:200]
        return False, f"Tier1 HTTP {e.code}: {body}", False
    except urllib.error.URLError as e:
        return False, f"Tier1 connection error: {e.reason}", False
    except socket.timeout:
        return False, "Tier1 timeout", False
    except ssl.SSLError as e:
        return False, f"Tier1 SSL error: {e}", False
    except Exception as e:
        return False, f"Tier1 exception: {e}", False

    # Tier 2: credits / auth (requires API key)
    if not api_key:
        return True, "API reachable, no API key configured", False

    payload = json.dumps({
        "model": HEALTH_CHECK_MODEL,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 5,
    }).encode()
    try:
        req = urllib.request.Request(
            f"{API_BASE_URL}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "curl/7.68.0",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return True, "API reachable with active credits", True
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="ignore")[:300]
        if e.code == 429:
            return True, f"API reachable but credits exhausted (HTTP 429)", False
        if e.code in (401, 403):
            return True, f"API reachable but auth failed (HTTP {e.code})", False
        # HTTP 404 model_not_found is NOT an outage — just a missing model
        if e.code == 404 and ('model_not_found' in body or 'No active credentials' in body):
            return True, f"API reachable but model unavailable (HTTP 404, non-fatal)", True
        return True, f"API reachable but chat returned HTTP {e.code}: {body}", False
    except urllib.error.URLError as e:
        return True, f"API reachable but chat connection error: {e.reason}", False
    except socket.timeout:
        return True, "API reachable but chat timeout", False
    except Exception as e:
        return True, f"API reachable but chat exception: {e}", False


# ─── JOBS.JSON DIRECT I/O ──────────────────────────────────────────
def acquire_lock(timeout=10):
    """Simple spin-lock around Hermes jobs.json."""
    start = time.time()
    # Stale lock detection: if lock is older than 60s, assume it's dead
    while JOBS_LOCK.exists():
        try:
            mtime = JOBS_LOCK.stat().st_mtime
            if time.time() - mtime > 60:
                JOBS_LOCK.unlink(missing_ok=True)
                break
        except Exception:
            pass
        if time.time() - start > timeout:
            return False
        time.sleep(0.05)
    try:
        JOBS_LOCK.write_text("guardian")
        return True
    except Exception:
        return False


def release_lock():
    try:
        if JOBS_LOCK.exists() and JOBS_LOCK.read_text() == "guardian":
            JOBS_LOCK.unlink()
    except Exception:
        pass


def load_jobs():
    """Load jobs.json directly, handling UTF-8 BOM."""
    if not JOBS_FILE.exists():
        return []
    raw = JOBS_FILE.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    data = json.loads(raw.decode("utf-8", errors="ignore"))
    return data.get("jobs", [])


def save_jobs(jobs):
    """Atomic write to jobs.json."""
    tmp = JOBS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"jobs": jobs}, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(JOBS_FILE)


def get_job_state(jobs):
    """Summarize current cron landscape."""
    total = len(jobs)
    enabled = [j for j in jobs if j.get("enabled")]
    paused = [j for j in jobs if j.get("state") == "paused"]
    errored = [j for j in jobs if j.get("last_status") == "error"]
    state_error = [j for j in jobs if j.get("state") == "error"]
    return {
        "total": total,
        "enabled": enabled,
        "paused": paused,
        "errored": errored,
        "state_error": state_error,
    }


def should_pause_job(job):
    """Return True if job should be auto-paused during outage."""
    if not job.get("enabled"):
        return False
    if job.get("state") != "scheduled":
        return False
    # no_agent script jobs cost ZERO model tokens — never pause them.
    # They don't fail on model outages and are often the very watchdogs that
    # restart the fleet (buzz bridge, self-healer, etc). Pausing them left the
    # Buzz bridge dead for hours (2026-08-11 incident).
    if job.get("no_agent"):
        return False
    if job.get("script"):
        return False  # script-backed jobs never touch the model
    name = job.get("name", "")
    if any(skip.lower() in name.lower() for skip in NEVER_PAUSE):
        return False
    return True


def pause_job(job):
    job["state"] = "paused"
    job["paused_at"] = datetime.now(timezone.utc).isoformat()
    job["paused_reason"] = "Auto-paused by Cron Guardian: model unavailable"
    job["enabled"] = False


def resume_job(job):
    job["state"] = "scheduled"
    job["paused_at"] = None
    job["paused_reason"] = None
    job["enabled"] = True


# ─── GAP BRIDGE DATA COLLECTION ────────────────────────────────────
def collect_git_changes(since):
    """Scan all hardcoded repo roots for commits since outage start."""
    changes = []
    for root in REPO_ROOTS:
        if not root.exists():
            continue
        for repo_path in root.iterdir():
            git_dir = repo_path / ".git"
            if not git_dir.is_dir():
                continue
            try:
                result = subprocess.run(
                    ["git", "-C", str(repo_path), "log", "--oneline", "--since", since.isoformat(), "--all"],
                    capture_output=True, text=True, timeout=15,
                )
                if result.returncode == 0 and result.stdout.strip():
                    lines = result.stdout.strip().splitlines()
                    changes.append({
                        "repo": repo_path.name,
                        "path": str(repo_path),
                        "commits": len(lines),
                        "latest": lines[0].strip() if lines else "",
                    })
            except Exception:
                continue
    # Sort by commit count desc
    changes.sort(key=lambda x: x["commits"], reverse=True)
    return changes


def collect_pim_status():
    """Check for PIM ingestion artifacts / DB."""
    status = {"found": False, "latest": None, "count": None, "note": ""}
    # Look for a PIM DB in common spots
    candidates = [
        Path("${MY_REPOS}/hermes-config/pim.db"),
        Path(os.path.expandvars("${USER_HOME}/Documents/github/hermes-config/pim.db")),
        HERMES_HOME / "pim.db",
    ]
    for db_path in candidates:
        if db_path.exists():
            try:
                import sqlite3
                conn = sqlite3.connect(str(db_path))
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='items';")
                if cur.fetchone():
                    cur.execute("SELECT COUNT(*) FROM items")
                    status["count"] = cur.fetchone()[0]
                    cur.execute("SELECT source_type, created_at FROM items ORDER BY created_at DESC LIMIT 1")
                    row = cur.fetchone()
                    if row:
                        status["latest"] = f"{row[0]} @ {row[1]}"
                    status["found"] = True
                    status["note"] = f"PIM DB at {db_path}"
                conn.close()
            except Exception as e:
                status["note"] = f"PIM DB found but unreadable: {e}"
            break
    if not status["found"]:
        # Fallback: count cron output files from PIM-related jobs
        status["note"] = "No PIM DB found; ingestion status unavailable without DB"
    return status


def collect_email_status():
    """Use himalaya to count unread/recent emails if configured."""
    status = {"configured": False, "unread": None, "recent": None, "error": ""}
    try:
        result = subprocess.run(
            ["himalaya", "envelope", "list", "--page-size", "100"],
            capture_output=True, text=True, timeout=20,
        )
        if result.returncode == 0:
            status["configured"] = True
            lines = [l for l in result.stdout.splitlines() if l.strip() and not l.startswith("UID")]
            status["recent"] = len(lines)
            unread = [l for l in lines if "✷" in l or "UNREAD" in l.upper() or "unread" in l.lower()]
            status["unread"] = len(unread)
        else:
            status["error"] = result.stderr.strip()[:200]
    except FileNotFoundError:
        status["error"] = "himalaya not in PATH"
    except Exception as e:
        status["error"] = str(e)
    return status


def collect_cron_output_summary(since):
    """Summarize non-empty cron outputs in the outage window."""
    out_dir = CRON_DIR / "output"
    summary = {"total_nonempty": 0, "by_job": []}
    if not out_dir.exists():
        return summary
    for job_dir in out_dir.iterdir():
        if not job_dir.is_dir():
            continue
        files = []
        for f in job_dir.iterdir():
            if not f.is_file():
                continue
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
                if mtime >= since and f.stat().st_size > 0:
                    files.append((f.name, f.stat().st_size, mtime))
            except Exception:
                continue
        if files:
            files.sort(key=lambda x: x[2], reverse=True)
            summary["total_nonempty"] += len(files)
            summary["by_job"].append({
                "job_id": job_dir.name,
                "files": len(files),
                "latest": files[0][2].isoformat(),
                "latest_size": files[0][1],
            })
    summary["by_job"].sort(key=lambda x: x["files"], reverse=True)
    return summary


def collect_missed_news():
    """Look for blogwatcher output files."""
    status = {"found": False, "articles": []}
    # Common blogwatcher cache locations
    candidates = [
        HERMES_HOME / "cache" / "blogwatcher",
        Path("${MY_REPOS}/_project/data/blogwatcher"),
    ]
    for cand in candidates:
        if cand.exists():
            status["found"] = True
            files = sorted(cand.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)[:10]
            for f in files:
                try:
                    data = json.loads(f.read_text())
                    title = data.get("title") or data.get("entry", {}).get("title") or f.name
                    status["articles"].append({"title": title, "file": f.name})
                except Exception:
                    pass
            break
    return status


# ─── STATE PERSISTENCE ─────────────────────────────────────────────
def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {
        "was_paused": False,
        "last_healthy_at": None,
        "last_down_at": None,
        "pause_started_at": None,
        "recovery_count": 0,
        "transient_streak": 0,
        "last_check_at": None,
        "last_action": None,
    }


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


# ─── GAP BRIDGE REPORT ─────────────────────────────────────────────
def generate_gap_report(jobs, outage_start, outage_end, model_detail):
    state = load_state()
    duration = outage_end - outage_start
    hours = duration.total_seconds() / 3600
    days = hours / 24

    report_lines = [
        "# 🛡️ Cron Guardian — Gap Bridge Report",
        f"",
        f"**Outage start:** {outage_start.strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Outage end:**   {outage_end.strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Duration:**     {hours:.1f} hours ({days:.1f} days)",
        f"**Model status:** {model_detail}",
        f"**Recovery #:**   {state.get('recovery_count', 0)}",
        f"",
        "## 1. Missed Cron Jobs",
    ]

    errored = [j for j in jobs if j.get("last_status") == "error"]
    credit_errors = [j for j in errored if "429" in str(j.get("last_delivery_error", "")) or "credits" in str(j.get("last_delivery_error", "")).lower()]
    script_errors = [j for j in errored if j.get("script")]
    other_errors = [j for j in errored if j not in credit_errors and j not in script_errors]

    report_lines.append(f"- Total jobs: {len(jobs)}")
    report_lines.append(f"- Jobs with last_status=error: {len(errored)}")
    report_lines.append(f"  - Credit/model errors (429): {len(credit_errors)}")
    report_lines.append(f"  - Script failures: {len(script_errors)}")
    report_lines.append(f"  - Other runtime errors: {len(other_errors)}")
    report_lines.append("")

    if errored:
        report_lines.append("| Job | Error |")
        report_lines.append("|-----|-------|")
        for j in errored[:30]:
            err = str(j.get("last_delivery_error") or j.get("last_error") or "unknown")[:100].replace("|", "/")
            report_lines.append(f"| {j.get('name','?')} | {err} |")
        if len(errored) > 30:
            report_lines.append(f"| ... and {len(errored)-30} more | ... |")
        report_lines.append("")

    # Code changes
    report_lines.append("## 2. Code Changes During Outage")
    git_changes = collect_git_changes(outage_start)
    if git_changes:
        report_lines.append("| Repo | Commits | Latest |")
        report_lines.append("|------|---------|--------|")
        for c in git_changes[:30]:
            report_lines.append(f"| `{c['repo']}` | {c['commits']} | {c['latest'][:80]} |")
        if len(git_changes) > 30:
            report_lines.append(f"| ... | +{len(git_changes)-30} repos | ... |")
    else:
        report_lines.append("_No git commits detected in outage window._")
    report_lines.append("")

    # Data ingestions
    report_lines.append("## 3. Data Ingestions")
    pim = collect_pim_status()
    cron_out = collect_cron_output_summary(outage_start)
    report_lines.append(f"- PIM DB: {pim['note']}")
    if pim.get("count") is not None:
        report_lines.append(f"  - Total items: {pim['count']}")
        report_lines.append(f"  - Latest: {pim['latest']}")
    report_lines.append(f"- Non-empty cron outputs since outage start: {cron_out['total_nonempty']} files across {len(cron_out['by_job'])} jobs")
    for entry in cron_out["by_job"][:10]:
        report_lines.append(f"  - `{entry['job_id']}`: {entry['files']} file(s), latest {entry['latest']}")
    report_lines.append("")

    # Emails
    report_lines.append("## 4. Email Status")
    email = collect_email_status()
    if email["configured"]:
        report_lines.append(f"- Recent envelopes checked: {email['recent']}")
        report_lines.append(f"- Unread: {email['unread']}")
    else:
        report_lines.append(f"- Himalaya not configured or not available: {email['error']}")
    report_lines.append("")

    # News / AI updates
    report_lines.append("## 5. Missed News / AI Updates")
    news = collect_missed_news()
    if news["found"] and news["articles"]:
        for a in news["articles"][:10]:
            report_lines.append(f"- {a['title']}")
    else:
        report_lines.append("_No blogwatcher cache found or no recent articles._")
    report_lines.append("")

    # Actions taken
    report_lines.append("## 6. Auto-Actions Taken")
    report_lines.append(f"- Jobs auto-paused during outage: see state file")
    report_lines.append(f"- Jobs resumed on recovery: see state file")
    report_lines.append(f"- Errored job states repaired: see state file")
    report_lines.append("")

    report_lines.append("---")
    report_lines.append("*Report generated by Cron Guardian v2.0*")

    return "\n".join(report_lines)


# ─── COMMANDS ──────────────────────────────────────────────────────
def repair_errored_jobs(jobs):
    """Toggle pause/resume on errored jobs to clear state and reset last_status."""
    fixed = []
    for job in jobs:
        if job.get("last_status") != "error":
            continue
        if job.get("state") != "scheduled":
            continue
        # toggle
        pause_job(job)
        # immediately resume
        resume_job(job)
        job["last_status"] = None
        job["last_delivery_error"] = None
        fixed.append(job.get("name", job.get("id")))
    return fixed


def cmd_watch():
    """Main one-shot watchdog cycle."""
    log("=== Cron Guardian watch cycle ===")
    healthy, detail, has_credits = check_model_health()
    now = datetime.now(timezone.utc)
    state = load_state()
    state["last_check_at"] = now.isoformat()

    acquired = acquire_lock(timeout=15)
    if not acquired:
        log("Could not acquire jobs.json lock, skipping cycle")
        save_state(state)
        return 1

    try:
        jobs = load_jobs()
        summary = get_job_state(jobs)
        log(f"Jobs: {summary['total']} total, {len(summary['enabled'])} enabled, {len(summary['paused'])} paused, {len(summary['errored'])} errored")

        if not healthy or not has_credits:
            # ── transient-failure tolerance (v2.2) ──
            # Retry once in-cycle: DNS blips and timeouts usually self-heal
            # within seconds and should never pause 50+ jobs.
            if not healthy and is_transient_tier1(detail):
                log(f"Tier1 transient error: {detail} — retrying once in 5s")
                time.sleep(5)
                healthy, detail, has_credits = check_model_health()
                if healthy and has_credits:
                    state["transient_streak"] = 0
                    state["last_action"] = "transient error self-healed on retry"
                    log(f"Retry succeeded: {detail} — no action")
                    return 0
            # Still failing after retry? If transient, require N consecutive
            # failed cycles before pausing; non-transient pauses immediately.
            if not healthy and is_transient_tier1(detail):
                streak = state.get("transient_streak", 0) + 1
                state["transient_streak"] = streak
                if streak < TRANSIENT_TOLERANCE_CYCLES:
                    state["last_action"] = f"transient failure {streak}/{TRANSIENT_TOLERANCE_CYCLES} — fleet stays up, recheck next cycle"
                    log(f"Transient failure {streak}/{TRANSIENT_TOLERANCE_CYCLES} — NOT pausing fleet (recheck next cycle)")
                    return 1
                log(f"Transient failure streak {streak} >= {TRANSIENT_TOLERANCE_CYCLES} — treating as outage")
            elif healthy:
                state["transient_streak"] = 0
            log(f"Model DOWN: {detail}")
            if not state.get("was_paused"):
                paused_names = []
                for job in jobs:
                    if should_pause_job(job):
                        pause_job(job)
                        paused_names.append(job.get("name", job.get("id")))
                state["was_paused"] = True
                state["last_down_at"] = now.isoformat()
                state["pause_started_at"] = now.isoformat()
                state["last_action"] = f"paused {len(paused_names)} jobs"
                log(f"PAUSED {len(paused_names)} jobs")
                if paused_names:
                    print("\nPaused jobs:")
                    for name in paused_names[:50]:
                        print(f"  - {name}")
            else:
                log("Already paused; no action")
                state["last_action"] = "no action (already paused)"
        else:
            log(f"Model HEALTHY: {detail}")
            state["transient_streak"] = 0
            if state.get("was_paused"):
                # RECOVERY
                resumed_names = []
                for job in jobs:
                    if job.get("state") == "paused":
                        resume_job(job)
                        resumed_names.append(job.get("name", job.get("id")))
                # Repair errored jobs
                fixed = repair_errored_jobs(jobs)
                # Determine outage window
                outage_start = state.get("pause_started_at") or state.get("last_down_at") or (now - timedelta(days=3))
                if isinstance(outage_start, str):
                    outage_start = datetime.fromisoformat(outage_start.replace("Z", "+00:00"))
                outage_end = now
                # Save jobs before generating report
                save_jobs(jobs)
                state["was_paused"] = False
                state["last_healthy_at"] = now.isoformat()
                state["recovery_count"] = state.get("recovery_count", 0) + 1
                state["last_action"] = f"resumed {len(resumed_names)} jobs, repaired {len(fixed)} errored"
                log(f"RESUMED {len(resumed_names)} jobs, REPAIRED {len(fixed)} errored")
                # Generate and save report
                REPORT_DIR.mkdir(parents=True, exist_ok=True)
                report = generate_gap_report(jobs, outage_start, outage_end, detail)
                report_path = REPORT_DIR / f"gap-bridge-{now.strftime('%Y%m%d_%H%M%S')}.md"
                report_path.write_text(report, encoding="utf-8")
                log(f"Gap report saved: {report_path}")
                print("\n" + report)
            else:
                # Healthy and not recovering — stay silent, but repair any stale errored jobs?
                # Conservative: don't auto-repair unless we just recovered, to avoid masking real issues.
                state["last_action"] = "no action (healthy)"
                log("Healthy and not recovering — silent")

        save_jobs(jobs)
    finally:
        release_lock()
        save_state(state)

    return 0 if (healthy and has_credits) else 1


def cmd_repair():
    log("=== Cron Guardian repair mode ===")
    healthy, detail, has_credits = check_model_health()
    log(f"Model: {detail}")
    if not healthy or not has_credits:
        log("Cannot repair while model is down")
        return 1

    acquired = acquire_lock(timeout=15)
    if not acquired:
        log("Could not acquire jobs.json lock")
        return 1

    try:
        jobs = load_jobs()
        fixed = repair_errored_jobs(jobs)
        # Resume any paused jobs too
        resumed = []
        for job in jobs:
            if job.get("state") == "paused":
                resume_job(job)
                resumed.append(job.get("name", job.get("id")))
        save_jobs(jobs)
        log(f"Repaired {len(fixed)} errored jobs, resumed {len(resumed)} paused jobs")
        if fixed:
            print("Repaired:")
            for n in fixed:
                print(f"  - {n}")
        if resumed:
            print("Resumed:")
            for n in resumed:
                print(f"  - {n}")
    finally:
        release_lock()
    return 0


def cmd_gap():
    log("=== Cron Guardian gap report mode ===")
    healthy, detail, has_credits = check_model_health()
    state = load_state()
    outage_start = state.get("pause_started_at") or state.get("last_down_at") or (datetime.now(timezone.utc) - timedelta(days=3))
    if isinstance(outage_start, str):
        outage_start = datetime.fromisoformat(outage_start.replace("Z", "+00:00"))
    outage_end = datetime.now(timezone.utc)

    acquired = acquire_lock(timeout=15)
    if not acquired:
        log("Could not acquire jobs.json lock")
        return 1
    try:
        jobs = load_jobs()
        report = generate_gap_report(jobs, outage_start, outage_end, detail)
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORT_DIR / f"gap-bridge-{outage_end.strftime('%Y%m%d_%H%M%S')}.md"
        report_path.write_text(report, encoding="utf-8")
        log(f"Report saved: {report_path}")
        print(report)
    finally:
        release_lock()
    return 0


def cmd_daemon():
    log("=== Cron Guardian daemon mode ===")
    while True:
        try:
            cmd_watch()
        except Exception as e:
            log(f"ERROR in daemon cycle: {e}")
        time.sleep(300)  # 5 minutes


# ─── MAIN ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "watch"
    if mode == "watch":
        sys.exit(cmd_watch())
    elif mode == "repair":
        sys.exit(cmd_repair())
    elif mode == "gap":
        sys.exit(cmd_gap())
    elif mode == "daemon":
        sys.exit(cmd_daemon())
    else:
        print(f"Unknown mode: {mode}. Use watch|repair|gap|daemon")
        sys.exit(2)
