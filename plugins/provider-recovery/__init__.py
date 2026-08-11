"""Provider recovery plugin — silent self-heal for the LLM routing stack.

Goal: when a model call fails because the router/providers are down, the agent
should FIRST try to recover silently (restart OmniRoute, keep retrying — the
user just sees typing run longer). Only when that genuinely fails should a
SHORT, specific message be surfaced explaining exactly what is happening and
how it is being resolved (e.g. "Deepseek via Opencode go - failed. trying
again..", "switching to deepseek direct api").

This plugin hooks ``api_request_error`` (fired on every failed API request)
and:

1. Detects when the failure is against OmniRoute (base_url contains
   localhost:20128 or the model is routed through it).
2. Silently restarts OmniRoute via its scheduled task, debounced, and lets the
   agent's built-in retry loop recover the turn (no user-visible message on a
   transient blip).
3. On repeated/terminal failures, emits a single short, specific escalation
   status so the user knows exactly what failed and what is being tried next.

The emergency tiers (CLIProxyAPI pool + local Ollama) are handled by the
provider-guardian daemon and by ``fallback_providers`` in config.yaml; this
plugin does not burn tokens probing them.
"""
from __future__ import annotations

import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("hermes.plugin.provider_recovery")

HERMES_HOME = Path.home() / "AppData" / "Local" / "hermes"
STATE_PATH = HERMES_HOME / "state" / "provider_recovery_state.json"

OMNIROUTE_BASE_URLS = (
    "localhost:20128",
    "127.0.0.1:20128",
    "omniroute",
)
OMNIROUTE_KEYWORDS = ("omniroute", "hermes/workhorse", "hermes/powerful", "gpt-5.6-sol")

RESTART_DEBOUNCE_SECONDS = 90          # min gap between OmniRoute restart triggers
ESCALATE_AFTER_ERRORS = 3              # surface a message after this many consecutive omni errors
RECOVERY_PROBE_INTERVAL = 8            # seconds between silence + probe cycles
MAX_RECOVERY_WAIT_SECONDS = 180        # cap how long we stay silent waiting on recovery


def _load_state() -> Dict[str, Any]:
    try:
        if STATE_PATH.exists():
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception as exc:
        logger.debug("provider-recovery state load failed: %s", exc)
    return {}


def _save_state(data: Dict[str, Any]) -> None:
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    except Exception as exc:
        logger.debug("provider-recovery state save failed: %s", exc)


def _omniroute_down() -> bool:
    """Cheap port probe — no tokens, no HTTP body."""
    import socket
    try:
        with socket.create_connection(("127.0.0.1", 20128), timeout=3):
            return False
    except Exception:
        return True


def _restart_omniroute() -> None:
    """Quietly (re)start OmniRoute via its scheduled task."""
    try:
        subprocess.Popen(
            ["schtasks", "/run", "/tn", "OmniRoute_Server"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        logger.info("provider-recovery: triggered OmniRoute restart (silent)")
    except Exception as exc:
        logger.warning("provider-recovery: OmniRoute restart trigger failed: %s", exc)


def _is_omniroute_error(kwargs: Dict[str, Any]) -> bool:
    base_url = str(kwargs.get("base_url") or "").lower()
    model = str(kwargs.get("model") or "").lower()
    provider = str(kwargs.get("provider") or "").lower()
    err_text = str(kwargs.get("error") or {}).lower()
    combined = " ".join([base_url, model, provider, err_text])
    return any(k in combined for k in OMNIROUTE_KEYWORDS) or any(
        u in base_url for u in OMNIROUTE_BASE_URLS
    )


def _describe_target(kwargs: Dict[str, Any]) -> str:
    """Short human label for what is failing, e.g. 'Deepseek via Opencode go'."""
    model = str(kwargs.get("model") or "").strip()
    provider = str(kwargs.get("provider") or "").strip()
    model = model.replace("hermes/powerful", "GPT-5.6 Sol").replace(
        "hermes/workhorse", "DeepSeek"
    ).replace("deepseek-v4-flash", "DeepSeek").replace("gpt-5.6-sol", "GPT-5.6 Sol")
    provider = provider.replace("custom:omniroute", "OmniRoute").replace(
        "opencode-go", "Opencode go"
    ).replace("deepseek", "DeepSeek direct")
    if provider and provider not in model:
        return f"{model} via {provider}"
    return model or "the model"


def _emit_status(agent: Any, message: str) -> None:
    """Emit a status line through the agent's standard callback."""
    try:
        if agent is None:
            return
        emit = getattr(agent, "_emit_status", None)
        if callable(emit):
            emit(message)
            return
        # Fallback: some agent builds only wire status via _vprint(force=True).
        vp = getattr(agent, "_vprint", None)
        if callable(vp):
            vp(f"{message}", force=True)
    except Exception as exc:
        logger.debug("provider-recovery status emit failed: %s", exc)


def api_request_error(**kwargs: Any) -> None:
    """Hook: fired on every failed API request.

    Returns nothing (silent). When the failure is against OmniRoute we
    quietly restart it (debounced) and let the agent's retry loop recover —
    the user just sees typing run longer. Only after repeated failures do we
    surface ONE short, specific escalation line via the agent status path.
    """
    try:
        if not _is_omniroute_error(kwargs):
            return
        agent = kwargs.get("agent")
        state = _load_state()
        now = time.monotonic()
        last_restart = state.get("last_omniroute_restart_at", 0) or 0
        err_count = int(state.get("consecutive_omni_errors", 0) or 0) + 1
        state["consecutive_omni_errors"] = err_count
        state["last_omni_error_at"] = time.monotonic()
        state["last_error_summary"] = _describe_target(kwargs)

        if _omniroute_down():
            # Router is unreachable: restart silently (debounced), then reset
            # the escalation counter so a single restart isn't announced.
            if (now - last_restart) >= RESTART_DEBOUNCE_SECONDS:
                _restart_omniroute()
                state["last_omniroute_restart_at"] = now
                state["consecutive_omni_errors"] = 0
        elif err_count >= ESCALATE_AFTER_ERRORS:
            # OmniRoute is up but this specific target keeps failing: surface
            # one short, specific line so the user sees the resolution path.
            state["consecutive_omni_errors"] = 0
            target = _describe_target(kwargs)
            _emit_status(
                agent,
                f"⚠️ {target} is having issues — retrying, then switching "
                "models. please hold..",
            )

        _save_state(state)
    except Exception as exc:
        logger.warning("provider-recovery hook error: %s", exc)


def register(ctx: Any) -> None:
    ctx.register_hook("api_request_error", api_request_error)
    logger.info("provider-recovery plugin registered (silent OmniRoute self-heal)")
