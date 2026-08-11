# Windows PID-Check Fleet Launcher

When launching 40+ Spacebar bot gateways on Windows, you need a script that:

1. Finds ALL profiles with bot tokens
2. Checks if each gateway is already running (using Windows PID check)
3. Creates `.env.spacebar` files for profiles that only have `.env` tokens
4. Launches missing gateways with 0.3s stagger
5. Reports total running vs launched

## Windows PID Check (ctypes)

`os.kill(pid, 0)` does NOT work on Windows for process-alive checks. Use `kernel32.OpenProcess` instead:

```python
import ctypes

kernel32 = ctypes.windll.kernel32

def is_pid_alive(pid):
    if not pid:
        return False
    # PROCESS_QUERY_INFORMATION = 0x0400
    handle = kernel32.OpenProcess(0x0400, False, pid)
    if not handle:
        return False
    kernel32.CloseHandle(handle)
    return True
```

## Finding Tokens in Profiles

Bot tokens can be stored in two files per profile:

1. `.env.spacebar` — contains `export SPACEBAR_BOT_TOKEN=<jwt>`
2. `.env` — contains `DISCORD_BOT_TOKEN=<jwt>` or `BOT_TOKEN=<jwt>` or `CLIENT_TOKEN=<jwt>`

Check both, preferring `.env.spacebar`:

```python
def find_token(profile_dir):
    # Check .env.spacebar first
    env_sb = os.path.join(profile_dir, '.env.spacebar')
    if os.path.exists(env_sb):
        with open(env_sb) as f:
            for line in f:
                line = line.strip()
                if 'SPACEBAR_BOT_TOKEN' in line:
                    tok = line.split('=', 1)[1].replace('export', '', 1).strip().strip("'\" \t\r\n")
                    if len(tok) > 10:
                        return tok
    # Fall back to .env
    env_file = os.path.join(profile_dir, '.env')
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                for prefix in ['SPACEBAR_BOT_TOKEN=', 'DISCORD_BOT_TOKEN=', 'BOT_TOKEN=', 'CLIENT_TOKEN=']:
                    if line.startswith(prefix):
                        tok = line[len(prefix):].strip().strip("'\" \t\r\n")
                        if len(tok) > 10:
                            return tok
    return None
```

## Auto-Creating .env.spacebar

When a profile has a token in `.env` but no `.env.spacebar`, create one:

```python
def ensure_env(profile_dir, token):
    env_sb = os.path.join(profile_dir, '.env.spacebar')
    if os.path.exists(env_sb):
        return False  # Already exists
    # Default guild ID
    guild_id = '<discord-channel-id>'
    # Try to read from config.yaml
    cfg = os.path.join(profile_dir, 'config.yaml')
    if os.path.exists(cfg):
        with open(cfg) as f:
            for line in f:
                if 'guild_id' in line or 'guildId' in line:
                    gid = line.split(':', 1)[1].strip()
                    if gid:
                        guild_id = gid
    with open(env_sb, 'w') as f:
        f.write(f"export SPACEBAR_BOT_TOKEN={token}\n")
        f.write(f"export SPACEBAR_GATEWAY_URL=ws://localhost:3100/\n")
        f.write(f"export SPACEBAR_GUILD_ID={guild_id}\n")
        f.write(f"export SPACEBAR_API_URL=http://localhost:3100/api/v9\n")
    return True
```

## Launching Gateways

Use `CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP` to suppress the console window and detach from the parent process:

```python
def launch_one(profile_name, config):
    hermes_venv = os.path.expanduser('~/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe')
    gateway_script = '${MY_REPOS}/Documents/github/agent-fleet/scripts/spacebar-gateway.py'
    
    env = os.environ.copy()
    env.update(config)
    
    CREATE_NO_WINDOW = 0x08000000
    proc = subprocess.Popen(
        [hermes_venv, gateway_script, profile_name],
        env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    return proc.pid
```

## Full Launcher Pattern (Reference)

See `relay-pool/launch-full-fleet.py` for the complete implementation. Key design:

- Scans ALL profile directories sorted alphabetically
- Skips non-bot profiles (`the operator`, `default`, `hermes-agent`)
- Uses `is_pid_alive()` via ctypes to avoid false-positive PID matches
- 0.3s stagger between launches to avoid overwhelming the gateway
- Reports: launched, already-running, skipped, errors

```bash
# Run:
cd ${MY_REPOS}/relay-pool
python launch-full-fleet.py
# Output:
# ✅ ai-agency: launched (PID 77168)
# ⏭️  chief-of-staff: already running
# ✅ data-lead: launched (PID 36096)
# ...
# Summary:
#   Launched: 1
#   Already running: 43
#   Skipped: 0
#   Total: 44
```
