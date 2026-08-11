#!/usr/bin/env python3
"""
Guardian Angel — Hermes Agent & Gateway Watchdog
=================================================
Monitors Hermes Agent and Hermes Gateway processes for:
  • Process health (PID alive, state file valid)
  • API responsiveness (/health endpoint)
  • Error rates in gateway/agent/error logs
  • Restart sequences (planned vs unplanned — prevents false flags)
  • Crash loops / infinite restart patterns

Auto-recovers with escalating actions, backs up config before destructive ops.

Designed to run via cron every 5 minutes.
Stateful — tracks consecutive failures, restart history, error bursts.

Usage:
    python guardian-angel.py [--check]
    python guardian-angel.py [--signal-restart]  # gateway signals planned restart
    python guardian-angel.py [--clear-restart]    # gateway signals restart complete
"""

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ─── Constants ───────────────────────────────────────────────────

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / "AppData/Local/hermes"))
SCRIPTS_DIR = HERMES_HOME / "scripts"
CONFIG_FILE = HERMES_HOME / "config.yaml"
ENV_FILE = HERMES_HOME / ".env"
GATEWAY_STATE_FILE = HERMES_HOME / "gateway_state.json"
LOGS_DIR = HERMES_HOME / "logs"
ERROR_LOG = LOGS_DIR / "errors.log"
GATEWAY_LOG = LOGS_DIR / "gateway.log"
AGENT_LOG = LOGS_DIR / "agent.log"

GUARDIAN_STATE_FILE = HERMES_HOME / "guardian-angel-state.json"
RESTART_FLAG_FILE = HERMES_HOME / "guardian-angel-restart.flag"
BACKUP_DIR = HERMES_HOME / "guardian-backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# API server health check
API_HOST = "127.0.0.1"
API_PORT = 8642
API_KEY = "hermes-jippity-016867bc4f5f6223"
API_HEALTH_URL = f"http://{API_HOST}:{API_PORT}/health"

# ─── Default Configuration ───────────────────────────────────────

DEFAULT_CONFIG = {
    "check_interval_seconds": 300,
    "missed_checks_before_action": 3,
    "restart_grace_period_seconds": 300,
    "max_restarts_per_hour": 3,
    "restart_cooldown_seconds": 600,
    "error_burst_threshold": 10,
    "error_burst_window_seconds": 3600,
    "api_timeout_seconds": 10,
    "pid_check_hard_fail": False,  # if True, missing PID=immediate action
}

# ─── Output helpers ──────────────────────────────────────────────

ET = timezone(timedelta(hours=-4))  # EDT

def now_et():
    return datetime.now(ET)

def ts():
    return now_et().strftime("%Y-%m-%d %H:%M:%S %Z")

def log(msg):
    print(f"[Guardian Angel] {ts()} | {msg}")

def warn(msg):
    print(f"[Guardian Angel ⚠] {ts()} | {msg}")

def alert(msg):
    print(f"[Guardian Angel 🔴] {ts()} | {msg}")

def ok(msg):
    print(f"[Guardian Angel 🟢] {ts()} | {msg}")

def info(msg):
    print(f"[Guardian Angel ℹ] {ts()} | {msg}")

# ─── State Management ────────────────────────────────────────────

def load_state():
    """Load guardian state from disk. Returns default on first run."""
    try:
        if GUARDIAN_STATE_FILE.exists():
            data = json.loads(GUARDIAN_STATE_FILE.read_text())
            # Ensure all keys exist
            if "version" not in data:
                data["version"] = 2
            return data
    except (json.JSONDecodeError, OSError) as e:
        warn(f"Corrupt state file, resetting: {e}")

    return {
        "version": 2,
        "last_check": None,
        "gateway": {
            "pid": None,
            "state": "unknown",
            "last_healthy": None,
            "consecutive_failures": 0,
            "restart_count_last_hour": 0,
            "last_restart": None,
            "restart_history": [],
        },
        "agent": {
            "api_healthy": False,
            "last_healthy": None,
            "consecutive_failures": 0,
        },
        "errors": {
            "last_line_timestamp": None,
            "new_errors_since_check": 0,
            "burst_start": None,
            "burst_count": 0,
            "is_bursting": False,
        },
        "restart_in_progress": False,
        "restart_started_at": None,
        "restart_timeout_count": 0,
        "action_history": [],
        "backup_last": None,
        "first_alert_sent": False,
        "last_heartbeat": None,
        "was_previously_unhealthy": False,
        "config": dict(DEFAULT_CONFIG),
    }


def save_state(state):
    """Persist guardian state to disk."""
    state["last_check"] = now_et().isoformat()
    try:
        GUARDIAN_STATE_FILE.write_text(json.dumps(state, indent=2, default=str))
    except OSError as e:
        warn(f"Failed to save state: {e}")


def load_or_init_state():
    """Load state or create fresh, merging any config changes."""
    state = load_state()
    # Merge config defaults into existing state
    cfg = dict(DEFAULT_CONFIG)
    cfg.update(state.get("config", {}))
    state["config"] = cfg
    return state


# ─── Health Checks ────────────────────────────────────────────────

def get_gateway_state():
    """Read gateway_state.json and return parsed dict or None."""
    try:
        if GATEWAY_STATE_FILE.exists():
            return json.loads(GATEWAY_STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError) as e:
        warn(f"Could not read gateway state: {e}")
    return None


def pid_is_alive(pid):
    """Check if a PID is running via OS process enumeration."""
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError, SystemError):
        return False
    except PermissionError:
        return True  # process exists but we don't have permission — still alive


def check_api_health():
    """Hit the Hermes API health endpoint. Returns (healthy: bool, detail: str)."""
    try:
        import urllib.request
        req = urllib.request.Request(
            API_HEALTH_URL,
            headers={"Authorization": f"Bearer {API_KEY}"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=DEFAULT_CONFIG["api_timeout_seconds"]) as resp:
            body = resp.read().decode()
            if resp.status == 200:
                data = json.loads(body)
                return True, f"HTTP 200 — {data.get('platform', 'hermes-agent')} v{data.get('version', '?')}"
            return False, f"HTTP {resp.status}"
    except Exception as e:
        return False, str(e)


def count_nearby_hermes_processes():
    """Count hermes-related processes. Useful for detecting orphaned forks / crash cascades."""
    count = 0
    try:
        import subprocess
        r = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python*", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=10
        )
        for line in r.stdout.splitlines():
            if "hermes" in line.lower() or "hermes" in r.stderr.lower():
                count += 1
            # Just count python processes related to hermes
            for agent_kw in ["hermes", "gateway", "guardian"]:
                if agent_kw in line.lower():
                    count += 1
        return count
    except Exception:
        return -1


def scan_logs_for_errors(state):
    """
    Scan errors.log for new errors since last check.
    Returns (new_error_count, last_timestamp, sample_errors).
    """
    try:
        if not ERROR_LOG.exists():
            return 0, None, []

        content = ERROR_LOG.read_text(errors="replace")
        lines = content.strip().split("\n")
        if not lines or (len(lines) == 1 and not lines[0]):
            return 0, None, []

        last_check_ts = state["errors"]["last_line_timestamp"]
        new_errors = 0
        sample_errors = []
        last_seen = None

        # On first-ever check, only establish baseline — don't count anything
        if last_check_ts is None:
            # Find the last timestamp in the log
            for line in reversed(lines):
                match = re.match(r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', line)
                if match:
                    return 0, match.group(1), []  # baseline established, no new errors
            return 0, None, []

        # Parse log lines looking for ERROR entries with timestamps
        for line in lines:
            if not line.strip():
                continue
            # Try to extract timestamp from log lines like:
            # 2026-06-25 12:09:52,535 ERROR [...]
            match = re.match(r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', line)
            if match:
                line_ts = match.group(1)
                last_seen = line_ts
                if line_ts <= last_check_ts:
                    continue  # already seen this or older
                # Count only ERROR level, not WARNING
                if " ERROR " in line or line.strip().startswith("ERROR"):
                    new_errors += 1
                    if len(sample_errors) < 5:
                        sample_errors.append(line[:200])

        return new_errors, last_seen, sample_errors
    except Exception as e:
        warn(f"Error scanning logs: {e}")
        return 0, None, []


def get_gateway_state_summary():
    """Quick summary of current gateway state from json file."""
    gs = get_gateway_state()
    if not gs:
        return {"running": False, "pid": None, "state": "unknown", "platforms_connected": []}

    platforms = list(gs.get("platforms", {}).keys())
    state = gs.get("gateway_state", "unknown")
    pid = gs.get("pid")

    return {
        "running": state == "running",
        "pid": pid,
        "state": state,
        "platforms_connected": platforms,
        "restart_requested": gs.get("restart_requested", False),
        "start_time": gs.get("start_time"),
    }


# ─── Restart Signal Protocol ─────────────────────────────────────

def signal_restart(reason="manual"):
    """Called by the gateway (or admin) to announce a planned restart.
    Prevents the Guardian Angel from treating this as an unplanned outage."""
    try:
        payload = {
            "timestamp": now_et().isoformat(),
            "reason": reason,
            "expected_downtime_seconds": 60,
            "old_pid": None,
        }
        # Capture current gateway PID
        gs = get_gateway_state()
        if gs and gs.get("pid"):
            payload["old_pid"] = gs["pid"]
        RESTART_FLAG_FILE.write_text(json.dumps(payload, indent=2))
        log(f"Restart signal written — reason: {reason}")
        return True
    except Exception as e:
        warn(f"Failed to write restart flag: {e}")
        return False


def clear_restart_signal():
    """Called by the gateway after it's fully back up and healthy."""
    try:
        if RESTART_FLAG_FILE.exists():
            RESTART_FLAG_FILE.unlink()
            log("Restart signal cleared — gateway reported back online")
        return True
    except Exception as e:
        warn(f"Failed to clear restart flag: {e}")
        return False


def is_restart_flagged(state):
    """Check if a planned restart is in progress by checking the flag file only."""
    if RESTART_FLAG_FILE.exists():
        return True
    return False


def get_restart_plan():
    """Read the restart flag file and return the plan dict."""
    try:
        if RESTART_FLAG_FILE.exists():
            return json.loads(RESTART_FLAG_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {}


# ─── Backup ──────────────────────────────────────────────────────

def backup_critical_config():
    """Backup config.yaml, .env, and gateway state before any destructive action."""
    timestamp = now_et().strftime("%Y%m%d_%H%M%S")
    backup_subdir = BACKUP_DIR / timestamp
    backup_subdir.mkdir(parents=True, exist_ok=True)

    files_to_backup = {
        "config.yaml": CONFIG_FILE,
        "env.txt": ENV_FILE,
        "gateway_state.json": GATEWAY_STATE_FILE,
        "guardian_state.json": GUARDIAN_STATE_FILE,
    }

    backed_up = []
    for name, src in files_to_backup.items():
        if src.exists():
            try:
                shutil.copy2(str(src), str(backup_subdir / name))
                backed_up.append(name)
            except OSError as e:
                warn(f"Backup failed for {name}: {e}")

    # Also back up gateway_state.json and errors.log tail
    if ERROR_LOG.exists():
        try:
            # Save last 500 lines of error log
            content = ERROR_LOG.read_text(errors="replace")
            lines = content.strip().split("\n")
            tail = "\n".join(lines[-500:])
            (backup_subdir / "errors-tail.log").write_text(tail)
            backed_up.append("errors-tail.log")
        except OSError:
            pass

    # Prune backups older than 7 days
    try:
        for d in sorted(BACKUP_DIR.iterdir()):
            if d.is_dir():
                try:
                    age = time.time() - d.stat().st_mtime
                    if age > 604800:  # 7 days
                        shutil.rmtree(str(d))
                except OSError:
                    pass
    except OSError:
        pass

    return backup_subdir, backed_up


# ─── Recovery Actions ────────────────────────────────────────────

def action_restart_gateway(state):
    """Attempt a graceful gateway restart via hermes CLI. Returns success bool."""
    info("ACTION: Restarting Hermes Gateway (graceful)...")
    try:
        # Backup first
        backup_subdir, backed_up = backup_critical_config()
        info(f"Backed up {len(backed_up)} files to {backup_subdir.name}")

        result = subprocess.run(
            ["hermes", "gateway", "restart"],
            capture_output=True, text=True, timeout=120,
        )
        success = result.returncode == 0
        if success:
            ok("Gateway restart command issued successfully")
            # Record restart
            gs = get_gateway_state()
            state["gateway"]["restart_history"].append({
                "time": now_et().isoformat(),
                "action": "restart_gateway",
                "result": "success",
                "old_pid": gs.get("pid") if gs else None,
            })
            state["gateway"]["last_restart"] = now_et().isoformat()
            state["gateway"]["restart_count_last_hour"] += 1
        else:
            warn(f"Gateway restart command failed: {result.stderr[:200]}")
            state["gateway"]["restart_history"].append({
                "time": now_et().isoformat(),
                "action": "restart_gateway",
                "result": f"failed: {result.stderr[:100]}",
            })
        return success
    except subprocess.TimeoutExpired:
        warn("Gateway restart command timed out")
        state["gateway"]["restart_history"].append({
            "time": now_et().isoformat(),
            "action": "restart_gateway",
            "result": "timeout",
        })
        return False
    except Exception as e:
        warn(f"Gateway restart error: {e}")
        return False


def action_force_restart_gateway(state):
    """Force kill and restart the gateway. More aggressive."""
    alert("ACTION: Force-restarting Hermes Gateway...")
    try:
        backup_subdir, backed_up = backup_critical_config()
        info(f"Backed up {len(backed_up)} files to {backup_subdir.name}")

        # Force kill current gateway process
        gs = get_gateway_state()
        if gs and gs.get("pid"):
            try:
                os.kill(gs["pid"], signal.SIGTERM)
                time.sleep(3)
                if pid_is_alive(gs["pid"]):
                    os.kill(gs["pid"], signal.SIGKILL)
                    time.sleep(1)
                ok(f"Killed old gateway PID {gs['pid']}")
            except (OSError, ProcessLookupError) as e:
                warn(f"Could not kill PID {gs['pid']}: {e}")

        # Update state file to mark as stopped
        if gs:
            gs["gateway_state"] = "stopped"
            GATEWAY_STATE_FILE.write_text(json.dumps(gs, indent=2))

        # Restart via hermes CLI
        result = subprocess.run(
            ["hermes", "gateway", "restart"],
            capture_output=True, text=True, timeout=120,
        )
        success = result.returncode == 0
        if success:
            ok("Force restart completed")
        else:
            # Fallback: try starting directly
            warn("CLI restart failed, trying direct start")
            result2 = subprocess.run(
                ["hermes", "gateway", "run", "--detach"],
                capture_output=True, text=True, timeout=30,
            )
            success = result2.returncode == 0

        state["gateway"]["restart_history"].append({
            "time": now_et().isoformat(),
            "action": "force_restart_gateway",
            "result": "success" if success else "failed",
        })
        return success
    except Exception as e:
        warn(f"Force restart error: {e}")
        return False


def action_backup_and_report(state):
    """Backup and report status without restarting. Used when thresholds met but cooldown applies."""
    info("ACTION: Backup + status report (no restart — cooldown active)")
    backup_subdir, backed_up = backup_critical_config()
    return backup_subdir, backed_up


def action_escalate_to_operator(state, reason, details=""):
    """
    Escalate to the operator. Prints a formatted alert that will be delivered by the cron delivery system.
    """
    alert(f"ESCALATION: {reason}")
    if details:
        print(f"  Details: {details}")

    gs_summary = get_gateway_state_summary()

    print()
    print("═══════════════════════════════════════════════════════")
    print("  🔴 GUARDIAN ANGEL — ESCALATION REQUIRED")
    print("═══════════════════════════════════════════════════════")
    print(f"  Time:           {ts()}")
    print(f"  Reason:         {reason}")
    print(f"  Gateway PID:    {gs_summary.get('pid')}")
    print(f"  Gateway State:  {gs_summary.get('state')}")
    print(f"  Platforms:      {', '.join(gs_summary.get('platforms_connected', []))}")
    print(f"  API Health:     {'🟢' if state['agent']['api_healthy'] else '🔴'}")
    print(f"  Fail Streak:    {state['gateway']['consecutive_failures']}")
    if details:
        print(f"  Details:        {details}")
    action_history = state.get("action_history", [])
    if action_history:
        last_action = action_history[-1]
        print(f"  Last Action:    {last_action.get('time','?')} — {last_action.get('action','?')}")
        print(f"  Last Result:    {last_action.get('result','?')}")
    if RESTART_FLAG_FILE.exists():
        plan = get_restart_plan()
        print(f"  ⚠ Restart flag present (since {plan.get('timestamp','?')})")
    print("═══════════════════════════════════════════════════════")
    print()
    print("  Requested actions:")
    if "3 restarts" in reason.lower() or "loop" in reason.lower():
        print("  • ⛔ Blocking auto-restart — crash loop detected")
        print("  • Manual intervention required")
        print("  • Check gateway log for errors")
        print("  • Run: hermes gateway restart")
    elif "timeout" in reason.lower():
        print("  • Check if gateway process is hung")
        print("  • Run: taskkill //F //PID <pid> && hermes gateway run")
    else:
        print("  • Review error logs: ~/AppData/Local/hermes/logs/")
        print("  • Run: hermes doctor")
    print()


# ─── Main Check Cycle ────────────────────────────────────────────

def run_check(state):
    """
    Run one full Guardian Angel check cycle.
    Returns a dict with results for reporting.
    """
    report = {
        "timestamp": ts(),
        "gateway_healthy": False,
        "api_healthy": False,
        "errors_found": 0,
        "restart_in_progress": False,
        "action_taken": None,
        "needs_escalation": False,
        "escalation_reason": None,
        "message_lines": [],
    }
    report_msg = report["message_lines"]

    cfg = state["config"]

    # ── 1. Check restart flag ──
    restart_flagged = is_restart_flagged(state)
    restart_plan = get_restart_plan() if restart_flagged else {}

    if restart_flagged:
        restart_started = state.get("restart_started_at")
        if not restart_started:
            # This is the first check detecting the restart
            state["restart_in_progress"] = True
            state["restart_started_at"] = now_et().isoformat()
            state["restart_timeout_count"] = 0
            info(f"Gateway restart signaled — reason: {restart_plan.get('reason', 'unknown')}")
            report_msg.append(f"ℹ Gateway restart in progress (reason: {restart_plan.get('reason', 'unknown')})")

        # Check if restart is taking too long
        restart_start_dt = datetime.fromisoformat(state["restart_started_at"])
        elapsed = (now_et() - restart_start_dt).total_seconds()
        grace = cfg.get("restart_grace_period_seconds", 300)

        if elapsed > grace:
            state["restart_timeout_count"] += 1
            if state["restart_timeout_count"] >= cfg.get("missed_checks_before_action", 3):
                # Restart timed out — escalate
                report["needs_escalation"] = True
                report["escalation_reason"] = f"Restart timeout — {elapsed:.0f}s elapsed (> {grace}s grace period, {state['restart_timeout_count']} checks)"
                report_msg.append(f"🔴 Restart taking too long ({elapsed:.0f}s) — escalating")
                return report
            else:
                report_msg.append(f"⚠ Restart still in progress ({elapsed:.0f}s / {grace}s grace) — check {state['restart_timeout_count']}/{cfg['missed_checks_before_action']}")
        else:
            report_msg.append(f"🔄 Restart in progress ({elapsed:.0f}s / {grace}s grace)")

        report["restart_in_progress"] = True
        # Don't do failure counting during planned restarts
        return report

    # If restart was in progress but flag is gone now, clear state
    if state.get("restart_in_progress") and not restart_flagged:
        info("Restart appears complete (flag cleared)")
        state["restart_in_progress"] = False
        state["restart_started_at"] = None
        state["restart_timeout_count"] = 0
        # Reset consecutive failures — restart was successful
        state["gateway"]["consecutive_failures"] = 0
        report_msg.append("🟢 Restart completed successfully")

    # ── 2. Check Gateway Process ──
    gateway_summary = get_gateway_state_summary()
    gs = get_gateway_state()

    # Fallback: if state file is missing/empty, scan running processes directly
    gateway_running = gateway_summary["running"] and pid_is_alive(gateway_summary["pid"])
    if not gateway_running and gateway_summary.get("pid") is None:
        # State file missing/empty — scan for running hermes processes instead
        import subprocess as _sp
        try:
            _r = _sp.run(
                ["tasklist", "/FI", "IMAGENAME eq python*", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=10
            )
            for _line in _r.stdout.splitlines():
                if "gateway" in _line.lower():
                    gateway_running = True
                    break
            if not gateway_running:
                # Also check by python + hermes paths
                for _line in _r.stdout.splitlines():
                    if "hermes" in _line.lower():
                        gateway_running = True
                        break
        except Exception:
            pass
        if gateway_running:
            info("Gateway process detected via process scan (state file empty/missing)")
            state["gateway"]["consecutive_failures"] = 0
            state["gateway"]["state"] = "running"
            state["gateway"]["last_healthy"] = now_et().isoformat()
            report["gateway_healthy"] = True
            report_msg.append(f"🟢 Gateway process detected via scan")

    state["gateway"]["pid"] = gateway_summary["pid"]

    if gateway_running:
        ok(f"Gateway process running (PID: {gateway_summary['pid']})")
        state["gateway"]["state"] = "running"
        state["gateway"]["last_healthy"] = now_et().isoformat()
        state["gateway"]["consecutive_failures"] = 0
        report["gateway_healthy"] = True
        report_msg.append(f"🟢 Gateway process UP (PID {gateway_summary['pid']})")
    else:
        warn(f"Gateway NOT healthy — state={gateway_summary['state']}, pid={gateway_summary['pid']}")
        state["gateway"]["consecutive_failures"] += 1
        report_msg.append(f"🔴 Gateway DOWN — state={gateway_summary['state']}")

        if state["gateway"]["consecutive_failures"] >= cfg["missed_checks_before_action"]:
            # Cooldown check — don't restart too frequently
            last_restart = state["gateway"].get("last_restart")
            cooldown_ok = True
            if last_restart:
                last_restart_dt = datetime.fromisoformat(last_restart)
                cooldown_ok = (now_et() - last_restart_dt).total_seconds() > cfg["restart_cooldown_seconds"]

            # Check restart rate
            restart_hist = state["gateway"].get("restart_history", [])
            recent_restarts = [
                r for r in restart_hist
                if (now_et() - datetime.fromisoformat(r["time"])).total_seconds() < 3600
            ]
            state["gateway"]["restart_count_last_hour"] = len(recent_restarts)
            restart_rate_ok = len(recent_restarts) < cfg["max_restarts_per_hour"]

            if not restart_rate_ok:
                report["needs_escalation"] = True
                report["escalation_reason"] = f"Crash loop detected — {len(recent_restarts)} restarts in last hour (max {cfg['max_restarts_per_hour']})"
                report_msg.append(f"🔴 Crash loop — {len(recent_restarts)} restarts in 1h")
                action_escalate_to_operator(state, f"Crash loop — {len(recent_restarts)} restarts in last hour")
            elif not cooldown_ok:
                info("Cooldown active — backing up and reporting instead of restarting")
                backup_subdir, backed_up = action_backup_and_report(state)
                report["action_taken"] = f"backup_only (cooldown) -> {backup_subdir.name}"
                report_msg.append(f"📁 Backup saved (cooldown active, skipped restart)")
            else:
                # Try to restart
                report_msg.append("🔄 Attempting gateway restart...")
                success = action_restart_gateway(state)
                if success:
                    report["action_taken"] = "restart_gateway"
                    report_msg.append("🟢 Restart command issued")
                else:
                    # Try force restart
                    report_msg.append("⚠ Graceful restart failed, trying force restart...")
                    success = action_force_restart_gateway(state)
                    if success:
                        report["action_taken"] = "force_restart_gateway"
                        report_msg.append("🟢 Force restart issued")
                    else:
                        report["needs_escalation"] = True
                        report["escalation_reason"] = "Both graceful and force restart failed"
                        report_msg.append("🔴 All restart attempts failed — escalating")
                        action_escalate_to_operator(state, "All restart attempts failed")

    # ── 3. Check API Health ──
    api_ok, api_detail = check_api_health()
    state["agent"]["api_healthy"] = api_ok
    if api_ok:
        state["agent"]["last_healthy"] = now_et().isoformat()
        state["agent"]["consecutive_failures"] = 0
        report["api_healthy"] = True
        if not gateway_running:
            report_msg.append(f"🟢 API endpoint responding despite gateway state issue")
    else:
        state["agent"]["consecutive_failures"] += 1
        report_msg.append(f"🔴 API health check failed: {api_detail}")

        if gateway_running and state["agent"]["consecutive_failures"] >= cfg["missed_checks_before_action"]:
            # Gateway is running but API is down — could be a hang or partial failure
            report["needs_escalation"] = True
            report["escalation_reason"] = f"API unresponsive ({cfg['missed_checks_before_action']} checks) — gateway process alive but not serving"
            report_msg.append(f"🔴 API down {state['agent']['consecutive_failures']} consecutive checks — gateway process zombie?")
            action_escalate_to_operator(state, "API unresponsive while gateway process running — possible zombie")

    # ── 4. Check Error Logs ──
    new_errors, last_seen, samples = scan_logs_for_errors(state)
    state["errors"]["new_errors_since_check"] = new_errors
    state["errors"]["last_line_timestamp"] = last_seen
    report["errors_found"] = new_errors

    if new_errors > 0:
        # Track bursts
        if not state["errors"]["burst_start"]:
            state["errors"]["burst_start"] = now_et().isoformat()
            state["errors"]["burst_count"] = 0
        state["errors"]["burst_count"] += new_errors
        state["errors"]["is_bursting"] = True

        report_msg.append(f"⚠ {new_errors} new error(s) in logs")
        for s in samples[:3]:
            report_msg.append(f"  └ {s[:150]}")

        # Check for error burst
        burst_threshold = cfg["error_burst_threshold"]
        burst_window = cfg["error_burst_window_seconds"]
        burst_start_dt = datetime.fromisoformat(state["errors"]["burst_start"])
        burst_elapsed = (now_et() - burst_start_dt).total_seconds()

        if state["errors"]["burst_count"] >= burst_threshold and burst_elapsed < burst_window:
            report_msg.append(f"⚠ Error burst: {state['errors']['burst_count']} errors in {burst_elapsed:.0f}s (threshold: {burst_threshold})")
            if state["errors"]["burst_count"] >= burst_threshold * 3:
                # Severe burst — escalate
                if not report["needs_escalation"]:
                    report["needs_escalation"] = True
                    report["escalation_reason"] = f"Severe error burst: {state['errors']['burst_count']} errors"
    else:
        # No new errors — reset burst tracking
        state["errors"]["burst_start"] = None
        state["errors"]["burst_count"] = 0
        state["errors"]["is_bursting"] = False

    # Prune old restart history (keep last 24h)
    restart_hist = state["gateway"].get("restart_history", [])
    state["gateway"]["restart_history"] = [
        r for r in restart_hist
        if (now_et() - datetime.fromisoformat(r["time"])).total_seconds() < 86400
    ]

    # Prune action history (keep last 50)
    state["action_history"] = state.get("action_history", [])[-50:]

    # ── 5. Periodic Backup (every 24h or on significant events) ──
    last_backup = state.get("backup_last")
    should_backup = False
    if not last_backup:
        should_backup = True
    else:
        try:
            backup_dt = datetime.fromisoformat(last_backup)
            if (now_et() - backup_dt).total_seconds() > 86400:
                should_backup = True
        except (ValueError, TypeError):
            should_backup = True

    if should_backup:
        backup_subdir, backed_up = backup_critical_config()
        state["backup_last"] = now_et().isoformat()
        report_msg.append(f"📁 Periodic backup saved ({len(backed_up)} files)")

    # ── 6. Proactive Notifications ──
    # First healthy check — tell the operator we're on watch
    if report["gateway_healthy"] and report["api_healthy"] and not state.get("first_alert_sent"):
        state["first_alert_sent"] = True
        report["is_first_healthy"] = True
        report["force_report"] = True
        info("First healthy baseline — sending onboarding notification")

    # Recovery from unhealthy state
    if report["gateway_healthy"] and report["api_healthy"] and state.get("was_previously_unhealthy"):
        state["was_previously_unhealthy"] = False
        report["is_recovered"] = True
        report["recovery_detail"] = "All systems back online after previous issue"
        report["force_report"] = True
        info("System recovered — sending recovery notification")

    # Mark as unhealthy if anything's wrong
    if not report["gateway_healthy"] or not report["api_healthy"] or report["errors_found"] > cfg["error_burst_threshold"]:
        state["was_previously_unhealthy"] = True

    # Periodic heartbeat every 30 min (6 checks) when healthy
    last_hb = state.get("last_heartbeat")
    if report["gateway_healthy"] and report["api_healthy"] and report["errors_found"] == 0:
        send_hb = False
        if not last_hb:
            send_hb = True
        else:
            try:
                hb_dt = datetime.fromisoformat(last_hb)
                if (now_et() - hb_dt).total_seconds() > 1800:  # 30 min
                    send_hb = True
            except (ValueError, TypeError):
                send_hb = True
        if send_hb:
            state["last_heartbeat"] = now_et().isoformat()
            report["is_heartbeat"] = True
            report["force_report"] = True
            info("Sending heartbeat — all clear")

    return report


# ─── Reporting ───────────────────────────────────────────────────

def format_report(report, state):
    """Format the check result for delivery. Returns markdown string or None for silence."""
    lines = []
    msg = report.get("message_lines", [])
    now = now_et()

    # ── Determine report type ──
    if report.get("restart_in_progress"):
        header_type = "restart"
    elif report.get("needs_escalation"):
        header_type = "escalation"
    elif report.get("gateway_healthy") and report.get("api_healthy") and report.get("errors_found") == 0:
        # Filter routine messages
        routine_msgs = [m for m in msg if not m.startswith("🟢 Gateway process UP") and not m.startswith("📁 Periodic backup") and not m.startswith("🔵 All clear")]
        if not routine_msgs and not report.get("force_report"):
            # Nothing to report — silent
            return None
        # Check if this is a periodic heartbeat
        if report.get("is_heartbeat"):
            header_type = "heartbeat"
        elif report.get("is_first_healthy"):
            header_type = "first_healthy"
        elif report.get("is_recovered"):
            header_type = "recovery"
        else:
            header_type = "status"
    else:
        header_type = "degraded"

    # ── Header ──
    if header_type == "restart":
        restart_plan = get_restart_plan()
        reason = restart_plan.get("reason", "unknown")
        elapsed = 0
        if state.get("restart_started_at"):
            elapsed = (now - datetime.fromisoformat(state["restart_started_at"])).total_seconds()
        lines.append(f"🔄 **Guardian Angel — Restart Monitor**")
        lines.append(f"")
        lines.append(f"Planned restart — reason: `{reason}`")
        lines.append(f"Elapsed: {elapsed:.0f}s / {state.get('config', DEFAULT_CONFIG).get('restart_grace_period_seconds', 300)}s grace")
        lines.append(f"")
        lines.append(f"| Component | Status |")
        lines.append(f"|-----------|--------|")
        lines.append(f"| Gateway   | 🔄 Restarting |")
        lines.append(f"| API       | 🟡 Watching  |")
        lines.append(f"")
        lines.append(f"⏱ Monitoring restart — will escalate if >{state.get('config', DEFAULT_CONFIG).get('restart_grace_period_seconds', 300)}s")

    elif header_type == "escalation":
        lines.append(f"🔴 **Guardian Angel — Escalation Required**")
        lines.append(f"")
        lines.append(f"**{report.get('escalation_reason', 'Unknown issue')}**")
        lines.append(f"")
        lines.append(f"| Component | Status |")
        lines.append(f"|-----------|--------|")
        lines.append(f"| Gateway   | {'🔴 DOWN' if not report.get('gateway_healthy') else '🟢 UP'} |")
        lines.append(f"| API       | {'🔴 DOWN' if not report.get('api_healthy') else '🟢 OK'} |")
        lines.append(f"| Errors    | {'⚠ ' + str(report['errors_found']) if report['errors_found'] > 0 else '🟢 None'} |")

    elif header_type == "first_healthy":
        lines.append(f"🛡 **Guardian Angel is now on watch**")
        lines.append(f"")
        lines.append(f"| Component | Status | Detail |")
        lines.append(f"|-----------|--------|--------|")
        lines.append(f"| Gateway   | 🟢 ONLINE  | PID {state['gateway']['pid']} |")
        lines.append(f"| API       | 🟢 ONLINE  | port {API_PORT} |")
        lines.append(f"| Config    | 📁 Backed up | {BACKUP_DIR} |")
        lines.append(f"")
        lines.append(f"Checking every 5 minutes. Silent when healthy — I'll only speak up when something's wrong.")
        lines.append(f"Use `guardian-angel.py --signal-restart` before planned restarts to avoid false flags.")

    elif header_type == "heartbeat":
        lines.append(f"🛡 **Guardian Angel** — All Clear")
        lines.append(f"")
        lines.append(f"| Component | Status | Detail |")
        lines.append(f"|-----------|--------|--------|")
        lines.append(f"| Gateway   | 🟢 ONLINE  | PID {state['gateway']['pid']} |")
        lines.append(f"| API       | 🟢 ONLINE  | port {API_PORT} |")
        lines.append(f"| Errors    | 🟢 None since last check |")
        lines.append(f"")
        lines.append(f"Uptime: {state['gateway'].get('last_healthy','?')[:16]} — no issues detected.")
        lines.append(f"Next routine check in 5 min. 🔄")

    elif header_type == "recovery":
        lines.append(f"🟢 **Guardian Angel — System Recovered**")
        if report.get("recovery_detail"):
            lines.append(f"")
            lines.append(f"**{report['recovery_detail']}**")
        lines.append(f"")
        lines.append(f"| Component | Status | Detail |")
        lines.append(f"|-----------|--------|--------|")
        lines.append(f"| Gateway   | 🟢 ONLINE  | PID {state['gateway']['pid']} |")
        lines.append(f"| API       | 🟢 ONLINE  | port {API_PORT} |")
        up_since = state['gateway'].get('last_healthy','')[:16] if state['gateway'].get('last_healthy') else '?'
        lines.append(f"| Up Since  | {up_since} |")

    elif header_type == "degraded":
        lines.append(f"🟡 **Guardian Angel — Degraded**")
        lines.append(f"")
        lines.append(f"| Component | Status | Detail |")
        lines.append(f"|-----------|--------|--------|")
        gw_st = "🔴 DOWN" if not report.get("gateway_healthy") else "🟢 UP"
        api_st = "🔴 DOWN" if not report.get("api_healthy") else "🟢 OK"
        lines.append(f"| Gateway   | {gw_st} | PID {state['gateway']['pid'] or '—'} |")
        lines.append(f"| API       | {api_st} | port {API_PORT} |")
        err_st = f"⚠ {report['errors_found']} new" if report['errors_found'] > 0 else "🟢 None"
        lines.append(f"| Errors    | {err_st} | streak {state['gateway']['consecutive_failures']} |")
        if state["gateway"]["restart_count_last_hour"] > 0:
            lines.append(f"| Restarts  | ⚠ {state['gateway']['restart_count_last_hour']}/h | last: {(state['gateway'].get('last_restart','') or '')[:16]} |")

    else:  # status
        lines.append(f"🛡 **Guardian Angel — Pulse**")
        lines.append(f"")
        gw_st = "🟢 UP" if report.get("gateway_healthy") else "🔴 DOWN"
        api_st = "🟢 OK" if report.get("api_healthy") else "🔴 DOWN"
        lines.append(f"| Component | Status | Detail |")
        lines.append(f"|-----------|--------|--------|")
        lines.append(f"| Gateway   | {gw_st} | PID {state['gateway']['pid'] or '—'} |")
        lines.append(f"| API       | {api_st} | port {API_PORT} |")
        err_st = f"⚠ {report['errors_found']} new" if report['errors_found'] > 0 else "🟢 None"
        lines.append(f"| Errors    | {err_st} | streak {state['gateway']['consecutive_failures']} |")
        if state["gateway"]["restart_count_last_hour"] > 0:
            lines.append(f"| Restarts  | ⚠ {state['gateway']['restart_count_last_hour']}/h | last: {(state['gateway'].get('last_restart','') or '')[:16]} |")

    lines.append("")

    # ── Message log ──
    for m in msg:
        if m:
            lines.append(f"• {m}")

    # ── Escalation note ──
    if header_type == "escalation":
        lines.append("")
        lines.append("**🔴 Action needed** — Manual intervention required. Check gateway logs.")
        lines.append("**Commands:** `hermes gateway status` | `hermes doctor` | `hermes cron list`")

    # ── Restart history ──
    if not report.get("restart_in_progress"):
        restart_hist = state["gateway"].get("restart_history", [])
        recent = [r for r in restart_hist if (now - datetime.fromisoformat(r["time"])).total_seconds() < 86400]
        if recent:
            lines.append("")
            lines.append(f"**Restart history (24h):** {len(recent)} restart(s)")
            for r in recent[-3:]:
                lines.append(f"  • {r['time'][:16]} — {r['action']} → {r.get('result','?')}")

    # ── Footer ──
    lines.append("")
    lines.append(f"*Guardian Angel · next check in ~5 min · {ts()}*")

    return "\n".join(lines)


# ─── CLI Entry Points ────────────────────────────────────────────

def cmd_signal_restart():
    """--signal-restart: Gateway signals a planned restart."""
    reason = sys.argv[2] if len(sys.argv) > 2 else "scheduled"
    if signal_restart(reason):
        print("OK")

def cmd_clear_restart():
    """--clear-restart: Gateway signals restart complete."""
    if clear_restart_signal():
        print("OK")

def cmd_check():
    """--check or default: Run one full guardian check cycle."""
    state = load_or_init_state()
    try:
        report = run_check(state)
        if report:
            # Save action to history
            if report.get("action_taken"):
                state["action_history"].append({
                    "time": now_et().isoformat(),
                    "action": report["action_taken"],
                    "result": "triggered",
                })
            save_state(state)

            formatted = format_report(report, state)
            if formatted:
                print(formatted)
            else:
                # Silent — nothing to report. Print nothing.
                pass
        else:
            save_state(state)
    except Exception as e:
        alert(f"Guardian Angel check failed: {e}")
        traceback.print_exc()
        print()
        print(f"🔴 **Guardian Angel — Internal Error** @ {ts()}")
        print(f"Check failed: {e}")
        print(f"Traceback: {traceback.format_exc()[:500]}")
        save_state(state)
        sys.exit(1)


def cmd_status():
    """--status: Print current state summary without running checks."""
    state = load_state()
    print(f"Guardian Angel State @ {ts()}")
    print(json.dumps(state, indent=2, default=str))

def cmd_force_backup():
    """--backup: Force a backup now."""
    subdir, files = backup_critical_config()
    print(f"Backup saved to {subdir}")
    for f in files:
        print(f"  ✓ {f}")
    print(f"Total: {len(files)} files")


# ─── Main ────────────────────────────────────────────────────────

def cmd_daemon():
    """--daemon: Run as a persistent background process, checking every 60s."""
    import time as time_module
    
    state = load_or_init_state()
    log(f"Guardian Angel daemon started — checking every 60s")
    check_interval = state.get("config", DEFAULT_CONFIG).get("check_interval_seconds", 60)
    
    consecutive_loops = 0
    while True:
        try:
            report = run_check(state)
            if report:
                if report.get("action_taken"):
                    state["action_history"].append({
                        "time": now_et().isoformat(),
                        "action": report["action_taken"],
                        "result": "triggered",
                    })
                save_state(state)
                formatted = format_report(report, state)
                if formatted:
                    print(formatted)
                    sys.stdout.flush()
            else:
                save_state(state)
            consecutive_loops = 0
        except Exception as e:
            consecutive_loops += 1
            warn(f"Daemon check failed ({consecutive_loops}x): {e}")
            traceback.print_exc()
            if consecutive_loops > 5:
                alert(f"Daemon failing repeatedly — last check error: {e}")
                consecutive_loops = 0  # reset to avoid infinite loop
        
        # Sleep 60s between checks
        try:
            time_module.sleep(60)
        except KeyboardInterrupt:
            log("Daemon shutting down (SIGINT)")
            break
        except Exception:
            break


def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "--daemon":
            cmd_daemon()
        elif cmd == "--signal-restart":
            cmd_signal_restart()
        elif cmd == "--clear-restart":
            cmd_clear_restart()
        elif cmd == "--check":
            cmd_check()
        elif cmd == "--status":
            cmd_status()
        elif cmd == "--backup":
            cmd_force_backup()
        elif cmd == "--help":
            print("Guardian Angel — Hermes Agent & Gateway Watchdog")
            print()
            print("Usage:")
            print("  guardian-angel.py                    Run check (default)")
            print("  guardian-angel.py --check            Run check")
            print("  guardian-angel.py --daemon           Run as persistent background daemon")
            print("  guardian-angel.py --signal-restart [reason]  Signal planned restart")
            print("  guardian-angel.py --clear-restart     Signal restart complete")
            print("  guardian-angel.py --status            Show current state")
            print("  guardian-angel.py --backup            Force backup now")
            print("  guardian-angel.py --help              This help")
        else:
            cmd_check()
    else:
        cmd_check()


if __name__ == "__main__":
    main()
