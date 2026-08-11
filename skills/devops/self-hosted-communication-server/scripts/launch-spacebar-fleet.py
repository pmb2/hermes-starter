#!/usr/bin/env python3
"""
Universal Spacebar Fleet Launcher.
Scans ALL Hermes profiles with bot tokens and launches their gateways.
Creates .env.spacebar for any profile that has a token but no spacebar env file.

Usage:
  python launch-spacebar-fleet.py

Requirements:
  - Hermes agent installed with profiles in ~/AppData/Local/hermes/profiles/
  - spacebar-gateway.py at ${MY_REPOS}/Documents/github/agent-fleet/scripts/
  - Each profile has a bot token in .env or .env.spacebar
"""
import subprocess, os, sys, time, ctypes, json

profiles_dir = os.path.expanduser('~/AppData/Local/hermes/profiles')
hermes_venv = os.path.expanduser('~/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe')
gateway_script = '${MY_REPOS}/Documents/github/agent-fleet/scripts/spacebar-gateway.py'

DEFAULT_CONFIG = {
    'SPACEBAR_API_URL': 'http://localhost:3100/api/v9',
    'SPACEBAR_GATEWAY_URL': 'ws://localhost:3100/',
    'DISCORD_AUTO_THREAD': 'false',
    'DISCORD_REQUIRE_MENTION': 'false',
    'DISCORD_ALLOWED_USERS': '*',
    'GATEWAY_ALLOW_ALL_USERS': 'true',
}

SKIP_PROFILES = {'the operator', 'default', 'hermes-agent'}

kernel32 = ctypes.windll.kernel32

def is_pid_alive(pid):
    """Windows-safe PID existence check using ctypes."""
    if not pid: return False
    h = kernel32.OpenProcess(0x400, False, pid)
    if not h: return False
    kernel32.CloseHandle(h)
    return True

def find_token(profile_dir):
    """Find a bot token in profile's .env.spacebar or .env."""
    # Check .env.spacebar first
    env_sb = os.path.join(profile_dir, '.env.spacebar')
    if os.path.exists(env_sb):
        with open(env_sb) as f:
            for line in f:
                line = line.strip()
                if line.startswith('export SPACEBAR_BOT_TOKEN') or line.startswith('SPACEBAR_BOT_TOKEN'):
                    tok = line.split('=', 1)[1].replace('export', '', 1).strip().strip("'\" \t\r\n")
                    if len(tok) > 10: return tok
    # Fallback to .env
    env_file = os.path.join(profile_dir, '.env')
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                for prefix in ['SPACEBAR_BOT_TOKEN=', 'DISCORD_BOT_TOKEN=', 'BOT_TOKEN=', 'CLIENT_TOKEN=']:
                    if line.startswith(prefix):
                        tok = line[len(prefix):].strip().strip("'\" \t\r\n")
                        if len(tok) > 10: return tok
    return None

def ensure_env(profile_dir, token):
    """Create .env.spacebar if missing, returns True if created."""
    env_sb = os.path.join(profile_dir, '.env.spacebar')
    if os.path.exists(env_sb): return False
    guild_id = '<discord-channel-id>'
    cfg = os.path.join(profile_dir, 'config.yaml')
    if os.path.exists(cfg):
        with open(cfg) as f:
            for line in f:
                if 'guild_id' in line or 'guildId' in line:
                    gid = line.split(':', 1)[1].strip()
                    if gid: guild_id = gid
    with open(env_sb, 'w') as f:
        f.write(f"export SPACEBAR_BOT_TOKEN={token}\n")
        f.write(f"export SPACEBAR_GATEWAY_URL=ws://localhost:3100/\n")
        f.write(f"export SPACEBAR_GUILD_ID={guild_id}\n")
        f.write(f"export SPACEBAR_API_URL=http://localhost:3100/api/v9\n")
    return True

def is_running(profile_name):
    """Check if gateway_state.json has a live PID."""
    sf = os.path.join(profiles_dir, profile_name, 'gateway_state.json')
    if os.path.exists(sf):
        try:
            with open(sf) as f:
                state = json.load(f)
            if state.get('pid', 0) and is_pid_alive(state['pid']): return True
        except: pass
    return False

def launch_one(profile_name, config):
    """Start a single bot gateway silently (no console window)."""
    env = os.environ.copy()
    env.update(config)
    CREATE_NO_WINDOW = 0x08000000
    proc = subprocess.Popen(
        [hermes_venv, gateway_script, profile_name],
        env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    return proc.pid

# Main
launched = 0
skipped = 0
already = 0
created = 0
errors = []

for name in sorted(os.listdir(profiles_dir)):
    pd = os.path.join(profiles_dir, name)
    if not os.path.isdir(pd) or name in SKIP_PROFILES:
        continue

    token = find_token(pd)
    if not token:
        skipped += 1
        continue

    if is_running(name):
        print(f"⏭️  {name}: already running")
        already += 1
        continue

    if ensure_env(pd, token):
        print(f"📝 {name}: created .env.spacebar")
        created += 1

    # Build config from .env.spacebar
    config = DEFAULT_CONFIG.copy()
    env_sb = os.path.join(pd, '.env.spacebar')
    if os.path.exists(env_sb):
        with open(env_sb) as f:
            for line in f:
                line = line.strip()
                if line.startswith('export SPACEBAR_BOT_TOKEN'):
                    raw = line.split('=', 1)[1].strip().strip("'\" \t\r\n")
                    config['SPACEBAR_BOT_TOKEN'] = raw
                    config['DISCORD_BOT_TOKEN'] = raw
                elif line.startswith('export SPACEBAR_GATEWAY_URL'):
                    config['SPACEBAR_GATEWAY_URL'] = line.split('=', 1)[1].strip().strip("'\" \t\r\n")
                elif line.startswith('export SPACEBAR_GUILD_ID'):
                    config['SPACEBAR_GUILD_ID'] = line.split('=', 1)[1].strip().strip("'\" \t\r\n")
                elif line.startswith('export SPACEBAR_API_URL'):
                    config['SPACEBAR_API_URL'] = line.split('=', 1)[1].strip().strip("'\" \t\r\n")

    try:
        pid = launch_one(name, config)
        print(f"✅ {name}: launched (PID {pid})")
        launched += 1
    except Exception as e:
        print(f"❌ {name}: {e}")
        errors.append(f"{name}: {e}")

    time.sleep(0.3)

print(f"\n{'='*50}")
print(f"Summary:")
print(f"  Launched: {launched}")
print(f"  Already running: {already}")
print(f"  Skipped: {skipped}")
print(f"  .env.spacebar created: {created}")
print(f"  Errors: {len(errors)}")
if errors:
    for e in errors:
        print(f"    - {e}")
print(f"  Total: {launched + already}")
