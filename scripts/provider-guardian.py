#!/usr/bin/env python3
"""provider-guardian.py — always-on heartbeat + self-heal for the LLM provider stack.

Checks every provider backend over plain HTTP (no LLM tokens consumed):

  - OmniRoute    :8080? no — http://localhost:20128/api/health/ping
  - CLIProxyAPI  : http://127.0.0.1:8317/v1/models  (Gemini / Grok / Kimi pool)
  - Ollama local : http://127.0.0.1:11434/api/tags  (ultimate emergency tier)

When a provider is down, the guardian restarts it via its scheduled task /
start command and waits for it to become healthy again. It only logs STATE
CHANGES (healthy -> down -> recovering -> healthy), never a steady heartbeat
tick, so logs stay quiet and no API tokens are burned.

Designed to run under the fleet watchdog (hermes-watchdog.py) as a supervised
process so it is itself auto-restarted on crash.
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Optional

HERMES_HOME = Path(os.path.expanduser("~/AppData/Local/hermes"))
LOG_PATH = HERMES_HOME / "logs" / "provider-guardian.log"
STATE_PATH = HERMES_HOME / "provider-guardian-state.json"

CHECK_INTERVAL_SECONDS = 30          # heartbeat cadence
RECOVERY_POLL_SECONDS = 5            # poll cadence while waiting on recovery
RECOVERY_TIMEOUT_SECONDS = 240       # how long to keep polling a restart
RECOVERY_COOLDOWN_SECONDS = 60       # min gap between restart attempts per svc
HEALTH_PING_TIMEOUT = 3              # per-request socket timeout

log = logging.getLogger("provider-guardian")


# ---------------------------------------------------------------------------
# Provider definitions
# ---------------------------------------------------------------------------

def _http_ok(url: str, *, token: Optional[str] = None, method: str = "GET") -> bool:
    """Cheap reachability probe. Returns True when the endpoint returns <500."""
    req = urllib.request.Request(url, method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=HEALTH_PING_TIMEOUT) as r:
            return r.status < 500
    except Exception:
        return False


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=HEALTH_PING_TIMEOUT):
            return True
    except Exception:
        return False


def _run_quiet(cmd: list[str]) -> None:
    try:
        subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as exc:  # pragma: no cover
        log.warning("spawn failed for %r: %s", cmd, exc)


class Service:
    name: str
    label: str

    def healthy(self) -> bool:  # pragma: no cover - overridden
        raise NotImplementedError

    def restart(self) -> bool:  # pragma: no cover - overridden
        raise NotImplementedError


class OmniRoute(Service):
    name = "omniroute"
    label = "OmniRoute (primary router)"

    def healthy(self) -> bool:
        return _port_open("127.0.0.1", 20128) and _http_ok(
            "http://localhost:20128/api/health/ping"
        )

    def restart(self) -> bool:
        # The scheduled task auto-starts OmniRoute (dev server) at logon.
        _run_quiet(["schtasks", "/run", "/tn", "OmniRoute_Server"])
        return True


class CLIProxyAPI(Service):
    name = "cliproxyapi"
    label = "CLIProxyAPI (Gemini/Grok/Kimi pool)"

    def healthy(self) -> bool:
        return _port_open("127.0.0.1", 8317) and _http_ok(
            "http://127.0.0.1:8317/v1/models", token="omniroute-local"
        )

    def restart(self) -> bool:
        _run_quiet(["schtasks", "/run", "/tn", "CLIProxyAPI_Server"])
        return True


class Ollama(Service):
    name = "ollama"
    label = "Ollama local (ultimate emergency tier)"

    def healthy(self) -> bool:
        return _port_open("127.0.0.1", 11434) and _http_ok(
            "http://127.0.0.1:11434/api/tags"
        )

    def restart(self) -> bool:
        # Ollama registers itself as a user/startup service; start the binary.
        exe = Path(os.path.expandvars(r"%LocalAppData%\Programs\Ollama\ollama.exe"))
        if not exe.exists():
            exe = Path(r"${USER_HOME}\AppData\Local\Programs\Ollama\ollama.exe")
        if exe.exists():
            _run_quiet([str(exe), "serve"])
        return True


SERVICES: list[Service] = [OmniRoute(), CLIProxyAPI(), Ollama()]


# ---------------------------------------------------------------------------
# Persistent state (change detection)
# ---------------------------------------------------------------------------

def _load_state() -> Dict[str, Dict]:
    try:
        if STATE_PATH.exists():
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_state(state: Dict[str, Dict]) -> None:
    try:
        STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    except Exception:
        pass


def _cooldown_ok(state: Dict[str, Dict], name: str) -> bool:
    ts = (state.get(name) or {}).get("last_restart_at", 0) or 0
    return (time.monotonic() - ts) >= RECOVERY_COOLDOWN_SECONDS


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def log_setup() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("provider-guardian")
    logger.setLevel(logging.INFO)
    fh = logging.handlers.RotatingFileHandler(
        LOG_PATH, maxBytes=5_242_880, backupCount=3)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(ch)


def main() -> None:
    log_setup()
    log.info("provider-guardian started (interval=%ss)", CHECK_INTERVAL_SECONDS)
    state = _load_state()

    while True:
        try:
            for svc in SERVICES:
                entry = state.setdefault(svc.name, {})
                was_healthy = bool(entry.get("healthy"))

                ok = svc.healthy()
                if ok and not was_healthy:
                    log.info("UP   %s — recovered", svc.label)
                elif not ok and was_healthy:
                    log.warning("DOWN %s — probing recovery", svc.label)
                entry["healthy"] = ok

                if not ok:
                    if _cooldown_ok(state, svc.name):
                        log.warning("RESTART %s", svc.label)
                        svc.restart()
                        entry["last_restart_at"] = time.monotonic()
                    # Wait/poll for recovery (bounded) so we don't spam restarts.
                    deadline = time.monotonic() + RECOVERY_TIMEOUT_SECONDS
                    while time.monotonic() < deadline:
                        time.sleep(RECOVERY_POLL_SECONDS)
                        if svc.healthy():
                            entry["healthy"] = True
                            log.info("UP   %s — recovered after restart", svc.label)
                            break
            _save_state(state)
        except Exception as exc:  # never die
            log.warning("guardian cycle error: %s", exc)
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("provider-guardian stopped")
        sys.exit(0)
