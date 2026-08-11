#!/usr/bin/env python3
"""
Reusable Spacebar gateway fleet launcher.

Starts bot gateways with a CLEAN environment dict (avoids stale env-var
inheritance from the parent shell). Requires a .env.spacebar.local file
with SPACEBAR_BOT_<NAME>=<token> exports and a SPACEBAR_API_BASE setting.

Usage:
    python start-fleet.py [profile1 profile2 ...]
    # Defaults to core council if no profiles specified
"""
import subprocess, time, os, re, json, base64, sys

FLEET_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATEWAY_SCRIPT = os.path.join(FLEET_DIR, "scripts", "spacebar-gateway.py")
HERMES_BASE = os.environ.get("HERMES_HOME_BASE", 
    os.path.expanduser("~/AppData/Local/hermes"))
TOKEN_FILE = os.path.join(FLEET_DIR, ".env.spacebar.local")
API_BASE = os.environ.get("SPACEBAR_API_BASE", "http://localhost:3100/api/v9")
WS_URL = os.environ.get("SPACEBAR_WS_URL", "ws://localhost:3100/")

# Read token file
tokens = {}
if os.path.isfile(TOKEN_FILE):
    with open(TOKEN_FILE) as f:
        for line in f:
            m = re.match(r"export SPACEBAR_BOT_(\w+)=(\S+)", line.strip())
            if m:
                profile_name = m.group(1).lower().replace("_", "-")
                tokens[profile_name] = m.group(2)

# Default fleet: core council
DEFAULT_FLEET = [
    "chief-of-staff", "technology-lead", "operations-lead", "intelligence-lead",
    "growth-lead", "treasury-lead", "counsel-lead", "compliance-lead", "portfolio-lead",
]

profiles = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_FLEET

# Build clean env
def build_env(token):
    env = {
        "DISCORD_BOT_TOKEN": token,
        "HERMES_HOME_BASE": HERMES_BASE,
        "SPACEBAR_API_BASE": API_BASE,
        "SPACEBAR_WS_URL": WS_URL,
        "HERMES_GATEWAY_BUSY_ACK_ENABLED": "false",
    }
    # Copy essential system vars
    for k in ("PATH", "HOME", "USERPROFILE", "APPDATA", 
              "LOCALAPPDATA", "SYSTEMROOT", "COMSPEC"):
        if k in os.environ:
            env[k] = os.environ[k]
    return env

started = []
for profile in profiles:
    if profile not in tokens:
        print(f"SKIP {profile}: no token found")
        continue
    
    token = tokens[profile]
    log_file = os.path.join(FLEET_DIR, "scripts", "logs", f"{profile}-gateway.log")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    open(log_file, "w").close()
    
    try:
        proc = subprocess.Popen(
            ["python", GATEWAY_SCRIPT, profile],
            stdout=open(log_file, "a"), stderr=subprocess.STDOUT,
            cwd=FLEET_DIR, env=build_env(token),
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
        )
        started.append((profile, proc.pid))
        print(f"  {profile:25s} PID {proc.pid}")
    except Exception as e:
        print(f"  {profile:25s} FAILED: {e}")
    time.sleep(1)

print(f"\nStarted {len(started)} gateways")
