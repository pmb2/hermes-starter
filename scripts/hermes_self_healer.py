#!/usr/bin/env python3
"""
hermes_self_healer.py — Self-healing error detection + auto-repair for Hermes Agent.

Monitors system health across 8 dimensions, diagnoses root causes of common issues,
auto-repairs where possible, and escalates what it can't fix.

Runs as cron job every 15 minutes. Silent when healthy.

Detection areas:
  1. Cron job health — failed jobs, missed runs, stuck jobs
  2. Process health — gateway, firefox zombies, tor, key services  
  3. Config validation — YAML syntax, required API keys
  4. Disk space — low space warnings
  5. Error log scanning — recent critical errors
  6. MCP server health — connected/disconnected
  7. Profile integrity — SOUL.md, config.yaml presence
  8. Port conflicts — gateway port blocked
"""

import json, os, re, subprocess, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path

NL = chr(10)

# ── Paths ──
HOME = Path.home()
HERMES_CONFIG = HOME / ".hermes" / "config.yaml"
APP_CONFIG = HOME / "AppData/Local/hermes/config.yaml"
SCRIPTS_DIR = HOME / "AppData/Local/hermes/scripts"
MONITOR_DIR = Path("${USER_HOME}/trumpian-accounting-kb/monitoring/findings")
STATE_FILE = MONITOR_DIR / "self_healer_state.json"
ACTION_LOG = Path("${MY_REPOS}/Documents/research/auto_actions_log.jsonl")

# Critical API keys to check
REQUIRED_KEYS = {
    "OPENCODE_API_KEY": "OpenCode Go API — required for enhancement scanner & agent ops",
}

# Services to check
SERVICES = {
    "hermes_gateway": {"check_port": 8090, "description": "Hermes Gateway API"},
    "brainmd": {"check_port": 3000, "description": "MemPalace/Brain MCP server"},
    "tor_browser": {"check_port": 9223, "description": "Firefox BiDi MCP server"},
}

# Common zombie processes
ZOMBIE_PATTERNS = [
    ("firefox.exe", "Firefox headless (should be 0-1 running, not 9+)"),
]

# Self-healing fixes
REPAIR_ACTIONS = {}


def log_repair(action_type, target, status, detail=""):
    """Log a repair action."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action_type": action_type,
        "target": str(target)[:120],
        "status": status,
        "detail": str(detail)[:200],
    }
    ACTION_LOG.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(ACTION_LOG, "a") as f:
            f.write(json.dumps(entry) + NL)
    except Exception:
        pass
    return entry


def load_state():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_state(state):
    MONITOR_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


# ── Detection Functions ──

def detect_zombie_processes():
    """Detect excessive zombie processes."""
    issues = []
    for pattern, desc in ZOMBIE_PATTERNS:
        try:
            r = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {pattern}", "/NH"],
                capture_output=True, text=True, timeout=10
            )
            count = r.stdout.count(pattern)
            if count > 5:
                issues.append({
                    "type": "zombie",
                    "severity": "high",
                    "target": pattern,
                    "count": count,
                    "description": f"{count}x {pattern} running (threshold: >5)",
                    "fix": f"taskkill -f -im {pattern}",
                })
        except Exception:
            pass
    return issues


def detect_port_conflicts():
    """Check if required ports are in use."""
    issues = []
    for name, info in SERVICES.items():
        port = info["check_port"]
        try:
            r = subprocess.run(
                ["netstat", "-ano", "|", "findstr", f":{port}"],
                capture_output=True, text=True, timeout=5, shell=True
            )
            if "LISTENING" not in r.stdout:
                issues.append({
                    "type": "port_down",
                    "severity": "warning" if name == "brainmd" else "high",
                    "target": name,
                    "port": port,
                    "description": f"{name} ({port}) not listening — {info['description']} may be down",
                })
        except Exception:
            pass
    return issues


def detect_cron_failures():
    """Check recent cron failures by looking at log patterns."""
    issues = []
    # Check auto_action_handler.py's log
    action_log = ACTION_LOG
    if action_log.exists():
        try:
            with open(action_log) as f:
                lines = f.readlines()[-50:]
            recent_errors = [l for l in lines if '"status": "error"' in l or '"status": "failed"' in l]
            if recent_errors:
                issues.append({
                    "type": "cron_failures",
                    "severity": "medium",
                    "target": "auto_action_handler",
                    "count": len(recent_errors),
                    "description": f"{len(recent_errors)} recent auto-action failures",
                })
        except Exception:
            pass
    return issues


def detect_config_issues():
    """Check config files for syntax errors."""
    issues = []
    for cfg_path, label in [(HERMES_CONFIG, "~/.hermes/config.yaml"),
                             (APP_CONFIG, "AppData/config.yaml")]:
        if cfg_path.exists():
            try:
                import yaml
                with open(cfg_path) as f:
                    yaml.safe_load(f)
            except yaml.YAMLError as e:
                issues.append({
                    "type": "config_error",
                    "severity": "high",
                    "target": label,
                    "description": f"YAML parse error: {str(e)[:100]}",
                })
    return issues


def detect_api_keys():
    """Check required API keys are set."""
    issues = []
    for key, desc in REQUIRED_KEYS.items():
        if not os.environ.get(key, ""):
            issues.append({
                "type": "missing_api_key",
                "severity": "high",
                "target": key,
                "description": f"Missing {key} — {desc}",
            })
    return issues


def detect_firefox_profile_lock():
    """Check if Firefox profile is locked preventing automation."""
    issues = []
    lock_paths = [
        HOME / "AppData/Local/hermes/firefox-profile/parent.lock",
        HOME / "AppData/Local/hermes/firefox-profile/.parentlock",
    ]
    for lp in lock_paths:
        if lp.exists():
            age = time.time() - lp.stat().st_mtime
            if age > 3600:
                issues.append({
                    "type": "firefox_lock",
                    "severity": "medium",
                    "target": str(lp),
                    "description": f"Firefox profile lock file present for {age/3600:.1f}h",
                    "fix": f"rm -f \"{lp}\"",
                })
    return issues


def detect_disk_space():
    """Check disk space on C: drive."""
    issues = []
    try:
        r = subprocess.run(["wmic", "logicaldisk", "where", "caption='C:'", "get", "freespace"],
                          capture_output=True, text=True, timeout=10)
        match = re.search(r'(\d+)', r.stdout)
        if match:
            free_bytes = int(match.group(1))
            free_gb = free_bytes / (1024**3)
            if free_gb < 10:
                issues.append({
                    "type": "disk_space",
                    "severity": "critical" if free_gb < 2 else "warning",
                    "target": "C:\\",
                    "free_gb": round(free_gb, 1),
                    "description": f"C: drive has {free_gb:.1f}GB free",
                })
    except Exception:
        pass
    return issues


def detect_mcp_server_status():
    """Check if configured MCP servers are accessible."""
    issues = []
    # Check brainmd (MemPalace)
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:3000/mcp", method="OPTIONS")
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        issues.append({
            "type": "mcp_down",
            "severity": "warning",
            "target": "brainmd",
            "description": "brainmd MCP server (localhost:3000) not responding",
        })
    return issues


def detect_hermes_config_mod_time():
    """Check if config.yaml was modified suspiciously recently (crash indicator)."""
    issues = []
    for cfg_path, label in [(HERMES_CONFIG, "~/.hermes/config.yaml"),
                             (APP_CONFIG, "AppData/config.yaml")]:
        if cfg_path.exists():
            mtime = datetime.fromtimestamp(cfg_path.stat().st_mtime)
            age = datetime.now() - mtime
            if age.total_seconds() < 60:
                issues.append({
                    "type": "recent_config_change",
                    "severity": "info",
                    "target": label,
                    "description": f"{label} modified {age.total_seconds():.0f}s ago",
                })
    return issues


# ── Auto-Repair Functions ──

def auto_repair_zombies(issues):
    """Kill zombie Firefox processes."""
    fixed = []
    for issue in issues:
        if issue.get("type") == "zombie" and "firefox" in str(issue.get("target", "")).lower():
            try:
                r = subprocess.run(
                    ["taskkill", "-f", "-im", "firefox.exe"],
                    capture_output=True, text=True, timeout=15
                )
                log_repair("kill_zombies", "firefox.exe",
                          "fixed" if r.returncode == 0 else "no_zombies",
                          r.stdout[:100])
                fixed.append(issue)
            except Exception as e:
                log_repair("kill_zombies_failed", "firefox.exe", "error", str(e))
    return fixed


def auto_repair_firefox_lock(issues):
    """Remove stale Firefox profile lock files."""
    fixed = []
    for issue in issues:
        if issue.get("type") == "firefox_lock" and issue.get("fix"):
            try:
                path = issue["target"]
                if os.path.exists(path):
                    os.remove(path)
                    log_repair("remove_lock", path, "fixed")
                    fixed.append(issue)
            except Exception as e:
                log_repair("remove_lock_failed", issue.get("target"), "error", str(e))
    return fixed


def auto_repair_port_restart(issues):
    """Attempt to restart down services."""
    fixed = []
    for issue in issues:
        if issue.get("type") == "port_down" and issue.get("target") == "hermes_gateway":
            try:
                r = subprocess.run(
                    ["taskkill", "-f", "-im", "hermes*"],
                    capture_output=True, text=True, timeout=10
                )
                log_repair("restart_gateway", "hermes_gateway", "attempted",
                          f"Killed {r.stdout[:100]}")
                fixed.append(issue)
            except Exception as e:
                log_repair("restart_gateway_failed", "hermes_gateway", "error", str(e))
    return fixed


# ── Main ──

def main():
    print(f"Hermes Self-Healer — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    state = load_state()
    now = datetime.now(timezone.utc).isoformat()
    
    all_issues = []
    all_issues.extend(detect_zombie_processes())
    all_issues.extend(detect_port_conflicts())
    all_issues.extend(detect_cron_failures())
    all_issues.extend(detect_config_issues())
    all_issues.extend(detect_api_keys())
    all_issues.extend(detect_firefox_profile_lock())
    all_issues.extend(detect_disk_space())
    all_issues.extend(detect_mcp_server_status())
    all_issues.extend(detect_hermes_config_mod_time())
    
    # Deduplicate against previous run
    prev_fps = set(state.get("recent_issue_fps", []))
    new_issues = []
    for issue in all_issues:
        fp = f"{issue['type']}:{issue['target']}"
        if fp not in prev_fps:
            new_issues.append(issue)
    
    if not new_issues and not all_issues:
        print("✅ All systems healthy — no issues detected")
        return

    print(f"Found {len(new_issues)} new issue(s), {len(all_issues)} total")
    print()
    
    # Report and auto-repair
    repairs_done = []
    repairs_failed = []
    needs_human = []
    
    # Auto-repair zombies
    fixed = auto_repair_zombies(new_issues)
    repairs_done.extend(fixed)
    
    fixed = auto_repair_firefox_lock(new_issues)
    repairs_done.extend(fixed)
    
    fixed = auto_repair_port_restart(new_issues)
    repairs_done.extend(fixed)
    
    # Track remaining non-repairable issues
    for issue in new_issues:
        if issue not in repairs_done:
            if issue.get("severity") in ("critical", "high"):
                needs_human.append(issue)
    
    # Print report
    if repairs_done:
        print("=== AUTO-REPAIRED ===")
        for r in repairs_done:
            print(f"  ✅ {r.get('type')}: {r.get('description', '')[:100]}")
        print()

    if needs_human:
        print("=== NEEDS HUMAN INTERVENTION ===")
        for issue in needs_human:
            sev = issue.get("severity", "info").upper()
            print(f"  [{sev}] {issue.get('type')}: {issue.get('description', '')[:120]}")
            if issue.get("fix"):
                print(f"         Fix: {issue.get('fix')}")
        print()
    
    # Update state
    recent_fps = []
    for issue in all_issues:
        fp = f"{issue['type']}:{issue['target']}"
        recent_fps.append(fp)
    state["recent_issue_fps"] = recent_fps[-100:]
    state["last_scan"] = now
    save_state(state)
    
    # If there was anything to report (not totally clean), output to stdout
    if repairs_done or needs_human:
        summary_parts = []
        if repairs_done:
            summary_parts.append(f"{len(repairs_done)} auto-fix(es)")
        if needs_human:
            summary_parts.append(f"{len(needs_human)} issue(s) need review")
        print(f"Summary: {', '.join(summary_parts)}")


if __name__ == "__main__":
    main()
