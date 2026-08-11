# Discord Gateway Launcher Pattern

When deploying Hermes agent profiles as Discord bots, the gateway launcher is **much simpler** than the Spacebar equivalent. No monkey-patching is needed — Hermes has native Discord support built in.

## Architecture

```
Profile config.yaml (~/AppData/Local/hermes/profiles/<name>/)
  └── discord: { require_mention: false, auto_thread: false }
Profile .env
  └── DISCORD_BOT_TOKEN=<real_discord_token>
       │
       ▼
discord-gateway.py (wraps `hermes gateway run --accept-hooks`)
       │
       ▼
Real Discord API (discord.com/v10)
```

## Single-Bot Launcher: `discord-gateway.py`

Full script at: `agent-fleet/scripts/discord-gateway.py` (Windows-compatible)

```python
import os, sys, time, signal, logging, subprocess
from pathlib import Path

HERMES_HOME = Path(os.path.expanduser("~/AppData/Local/hermes"))
VENV_PYTHON = HERMES_HOME / "hermes-agent" / "venv" / "Scripts" / "python.exe"
HERMES_CLI = HERMES_HOME / "hermes-agent" / "venv" / "Scripts" / "hermes.exe"
LOG_DIR = Path(os.path.expanduser("~/.hermes/logs"))

def read_bot_token(profile):
    env_file = HERMES_HOME / "profiles" / profile / ".env"
    if not env_file.exists():
        return ""
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("DISCORD_BOT_TOKEN=***            return line.split("=", 1)[1].strip("\"' ")
    return ""

def run_gateway(profile, logger):
    token = read_bot_token(profile)
    if not token:
        logger.error("No DISCORD_BOT_TOKEN found")
        return 1

    env = os.environ.copy()
    env["HERMES_HOME"] = str(HERMES_HOME)
    env["HERMES_PROFILE"] = profile
    env["DISCORD_BOT_TOKEN"] = token

    process = subprocess.Popen(
        [str(HERMES_CLI), "gateway", "run", "--accept-hooks"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )
    for line in iter(process.stdout.readline, b""):
        text = line.decode("utf-8", errors="replace").rstrip()
        if text:
            logger.info("[gateway] %s", text)
    process.wait()
    return process.returncode

# Auto-restart loop with exponential backoff (2s → 30s max)
backoff = 2.0
while not shutdown_requested:
    exit_code = run_gateway(profile, logger)
    time.sleep(backoff)
    backoff = min(backoff * 2.0, 30.0)
```

## Fleet Manager: `discord-fleet-manager.py`

Full script at: `agent-fleet/scripts/discord-fleet-manager.py`

Launches multiple bots as subprocesses:

```python
COUNCIL = ["chief-of-staff", "technology-lead", "growth-lead",
    "intelligence-lead", "treasury-lead", "counsel-lead",
    "compliance-lead", "portfolio-lead", "operations-lead"]

for profile in profiles:
    pythonw = Path(os.path.expanduser("~/AppData/Local/hermes/hermes-agent/venv/Scripts/pythonw.exe"))
    proc = subprocess.Popen([str(pythonw), str(GATEWAY), profile])
    processes[profile] = {"proc": proc, "backoff": 2.0}
    time.sleep(1.5)  # stagger to avoid rate limits
```

Key features:
- Uses `pythonw.exe` on Windows to suppress console windows (0 terminal popups)
- 30-second monitor loop checks PID status
- Auto-restarts crashed gateways with exponential backoff (2s → 30s)
- Graceful shutdown on SIGINT/SIGTERM/SIGBREAK
- Rotating log files at 10MB to `~/.hermes/logs/discord-fleet-manager.log`

## Usage

```bash
# Single bot:
python /path/to/discord-gateway.py chief-of-staff

# Full council:
python /path/to/discord-fleet-manager.py
```

## Key Differences from Spacebar Gateway

| Aspect | Spacebar (`spacebar-gateway.py`) | Discord (`discord-gateway.py`) |
|--------|----------------------------------|-------------------------------|
| discord.py patches | 15+ patches (auth, compress, identify, etc.) | None |
| API version | v9 (Spacebar cap) | v10 (current Discord) |
| Gateway URL | Monkey-patched to `wss://discy...` | Default `wss://gateway.discord.gg` |
| Auth header | Strip `Bot ` prefix | No change |
| Thread support | Broken | Full support |
| Lock file | Needs msvcrt.locking patch | No issue |
| Launch | Complex multi-PYTHONPATH | Simple `hermes gateway run` |
