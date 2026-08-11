"""Intelligence routing plugin — dual-tier workhorse/powerful model control.

Flags (prefix of message text, stripped before agent sees the prompt):
  --h / --hard   stick this chat/thread to powerful (YunWu gpt-5.6-sol)
  --s / --soft   stick this chat/thread to workhorse (DeepSeek class)

Without flags: keep sticky override if present; else auto-escalate hard tasks
for one turn only (silent). Subagents are NOT affected (delegation config).

Runtime model IDs always go through OmniRoute (localhost:20128).
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("hermes.plugin.intelligence_routing")

HERMES_HOME = Path.home() / "AppData" / "Local" / "hermes"
STATE_PATH = HERMES_HOME / "state" / "intelligence_routing_sticky.json"
LOG_PATH = HERMES_HOME / "logs" / "intelligence-routing.jsonl"

# OmniRoute combo aliases. hermes/workhorse -> OC Go -> DeepSeek -> Grok;
# hermes/powerful -> YunWu gpt-5.6-sol -> OC Go -> DeepSeek -> Grok.
WORKHORSE_MODEL = "hermes/workhorse"
POWERFUL_MODEL = "hermes/powerful"
PROVIDER = "custom:omniroute"
BASE_URL = "http://localhost:20128/v1"
API_KEY = "omniroute-local"
API_MODE = "chat_completions"

# Sticky flags at start of message (optional whitespace after)
_FLAG_RE = re.compile(
    r"^\s*(?P<flag>--h(?:ard)?|--s(?:oft)?)\b\s*",
    re.IGNORECASE,
)

# Auto-escalate heuristics (silent one-turn powerful)
_ESCALATE_KEYWORDS = re.compile(
    r"\b("
    r"architecture|threat\s*model|security\s*audit|red\s*team|"
    r"legal\s*strategy|production\s*incident|deep\s*review|"
    r"design\s*system|multi[- ]repo|roadmap\s*rewrite|"
    r"code\s*review\s*all|full\s*audit|incident\s*response|"
    r"refactor\s*the\s*entire|system[- ]wide\s*plan"
    r")\b",
    re.IGNORECASE,
)

# Explicit user request for strongest model (sticky not required — one turn)
_EXPLICIT_POWERFUL = re.compile(
    r"\b("
    r"use\s+(the\s+)?(strongest|most\s+powerful|best)\s+model|"
    r"use\s+(gpt[- ]?5\.6[- ]?sol|yunwu|sol\b)|"
    r"switch\s+to\s+(hard|powerful|sol)"
    r")\b",
    re.IGNORECASE,
)


def _override(model: str) -> Dict[str, str]:
    return {
        "model": model,
        "provider": PROVIDER,
        "api_key": API_KEY,
        "base_url": BASE_URL,
        "api_mode": API_MODE,
    }


def _session_key_from_event(event: Any, gateway: Any) -> Optional[str]:
    source = getattr(event, "source", None)
    if source is None:
        return None
    try:
        if gateway is not None and hasattr(gateway, "_session_key_for_source"):
            return gateway._session_key_for_source(source)  # noqa: SLF001
    except Exception as exc:
        logger.debug("session key via gateway failed: %s", exc)
    try:
        from gateway.session import build_session_key

        return build_session_key(
            source,
            group_sessions_per_user=True,
            thread_sessions_per_user=False,
            profile=getattr(source, "profile", None),
        )
    except Exception as exc:
        logger.debug("build_session_key failed: %s", exc)
        # Fallback composite
        parts = [
            str(getattr(source, "platform", "")),
            str(getattr(source, "chat_id", "")),
            str(getattr(source, "thread_id", "") or ""),
            str(getattr(source, "user_id", "") or ""),
        ]
        return ":".join(parts)


def _load_sticky() -> Dict[str, str]:
    try:
        if STATE_PATH.exists():
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items() if v in ("workhorse", "powerful")}
    except Exception as exc:
        logger.warning("sticky load failed: %s", exc)
    return {}


def _save_sticky(data: Dict[str, str]) -> None:
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    except Exception as exc:
        logger.warning("sticky save failed: %s", exc)


def _log_decision(payload: Dict[str, Any]) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(payload)
        payload.setdefault("ts", datetime.now(timezone.utc).isoformat())
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception as exc:
        logger.debug("decision log failed: %s", exc)


def _set_session_override(gateway: Any, session_key: str, model: str, *, one_turn: bool = False) -> None:
    """Apply in-memory session model override used by gateway agent creation."""
    if gateway is None or not session_key:
        return
    override = _override(model)

    # Preferred path: session state / legacy dicts
    try:
        if hasattr(gateway, "_session_state"):
            st = gateway._session_state(session_key)  # noqa: SLF001
            st.conversation.model_override = dict(override)
            if one_turn:
                # Snapshot previous was already sticky; one-turn restore after agent ends
                # Use pending one-turn restore dict if available
                if not hasattr(gateway, "_pending_one_turn_model_restores"):
                    gateway._pending_one_turn_model_restores = {}
                # Restore to workhorse after this turn unless sticky powerful
                sticky = _load_sticky().get(session_key)
                if sticky == "powerful":
                    # sticky powerful — no one-turn restore
                    pass
                else:
                    gateway._pending_one_turn_model_restores[session_key] = {
                        "had_override": True,
                        "override": _override(WORKHORSE_MODEL),
                    }
            elif hasattr(gateway, "_pending_one_turn_model_restores"):
                gateway._pending_one_turn_model_restores.pop(session_key, None)
    except Exception as exc:
        logger.debug("session_state override failed: %s", exc)

    # Legacy dict property path
    try:
        if not hasattr(gateway, "_session_model_overrides") or gateway._session_model_overrides is None:
            gateway._session_model_overrides = {}
        gateway._session_model_overrides[session_key] = dict(override)
    except Exception as exc:
        logger.debug("legacy override dict failed: %s", exc)

    # Persist non-secret parts for session continuity (async store best-effort)
    try:
        store = getattr(gateway, "async_session_store", None) or getattr(gateway, "session_store", None)
        if store is not None and hasattr(store, "set_model_override") and not one_turn:
            # sync or async — fire and forget for async
            result = store.set_model_override(session_key, {
                "model": override["model"],
                "provider": override["provider"],
                "base_url": override["base_url"],
            })
            # if coroutine, schedule
            import asyncio
            import inspect

            if inspect.iscoroutine(result):
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(result)
                except Exception:
                    pass
    except Exception as exc:
        logger.debug("persist override failed: %s", exc)


def _should_auto_escalate(text: str) -> bool:
    if not text:
        return False
    if _EXPLICIT_POWERFUL.search(text):
        return True
    if len(text) >= 1800 and _ESCALATE_KEYWORDS.search(text):
        return True
    if _ESCALATE_KEYWORDS.search(text) and len(text) >= 400:
        return True
    return False


def pre_gateway_dispatch(*, event: Any, gateway: Any = None, session_store: Any = None, **_kwargs: Any) -> Optional[Dict[str, Any]]:
    """Intercept inbound gateway messages for --h/--s and auto-tiering."""
    try:
        text = getattr(event, "text", None)
        if not isinstance(text, str) or not text.strip():
            return None

        # Ignore pure slash commands (let Hermes handle /model etc.)
        stripped = text.lstrip()
        if stripped.startswith("/") and not stripped.lower().startswith(("/h", "/s")):
            # still allow /h /s as aliases if someone types them
            pass

        session_key = _session_key_from_event(event, gateway)
        sticky = _load_sticky()
        flag_match = _FLAG_RE.match(text)
        new_text = text
        tier: Optional[str] = None
        reason = "inherit"
        one_turn = False

        if flag_match:
            flag = flag_match.group("flag").lower()
            new_text = text[flag_match.end() :]
            if not new_text.strip():
                # Flag-only message: still switch sticky, rewrite to a no-op acknowledge prompt
                # Better: skip LLM and silent — use skip would drop completely.
                # Keep a minimal invisible task so session switches without user-facing notice content.
                new_text = "(model tier updated; continue with previous task context if any.)"
            if flag.startswith("--h"):
                tier = "powerful"
                reason = "flag_hard"
                if session_key:
                    sticky[session_key] = "powerful"
                    _save_sticky(sticky)
            else:
                tier = "workhorse"
                reason = "flag_soft"
                if session_key:
                    sticky[session_key] = "workhorse"
                    _save_sticky(sticky)
        else:
            # Sticky session preference
            if session_key and sticky.get(session_key) == "powerful":
                tier = "powerful"
                reason = "sticky_powerful"
            elif session_key and sticky.get(session_key) == "workhorse":
                tier = "workhorse"
                reason = "sticky_workhorse"
            elif _should_auto_escalate(text):
                tier = "powerful"
                reason = "auto_escalate"
                one_turn = True
            else:
                tier = "workhorse"
                reason = "default_workhorse"

        model = POWERFUL_MODEL if tier == "powerful" else WORKHORSE_MODEL
        if session_key:
            _set_session_override(gateway, session_key, model, one_turn=one_turn)

        _log_decision(
            {
                "session_key": session_key,
                "tier": tier,
                "model": model,
                "reason": reason,
                "one_turn": one_turn,
                "platform": str(getattr(getattr(event, "source", None), "platform", "")),
                "chat_id": str(getattr(getattr(event, "source", None), "chat_id", "")),
                "thread_id": str(getattr(getattr(event, "source", None), "thread_id", "") or ""),
            }
        )

        if new_text != text:
            return {"action": "rewrite", "text": new_text}
        # Still return allow so other plugins can run; override already applied
        return {"action": "allow"}
    except Exception as exc:
        logger.exception("intelligence-routing hook failed: %s", exc)
        return None


def register(ctx: Any) -> None:
    ctx.register_hook("pre_gateway_dispatch", pre_gateway_dispatch)
    logger.info(
        "intelligence-routing plugin registered (workhorse=%s powerful=%s)",
        WORKHORSE_MODEL,
        POWERFUL_MODEL,
    )
