#!/usr/bin/env python3
"""Shared model identity for OmniRoute + Buzz fleet.

Single source of truth for which model the Buzz bridge / Desktop agents
present as. When the active model changes, avatars and display names update
so every connected bot shows the live provider/model at a glance.

Files:
  model_identity.json   — active model + catalog
  model_config.json     — hermes_model profiles (kept in sync on switch)
"""
from __future__ import annotations

import base64
import datetime as dt
import json
import os
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Any

HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / "AppData" / "Local" / "hermes")))
IDENTITY_PATH = Path(os.environ.get("HERMES_MODEL_IDENTITY", str(HERMES_HOME / "model_identity.json")))
MODEL_CONFIG_PATH = Path(os.environ.get("HERMES_MODEL_CONFIG", str(HERMES_HOME / "model_config.json")))
MANAGED_AGENTS = Path(
    os.environ.get(
        "BUZZ_MANAGED_AGENTS",
        str(Path.home() / "AppData" / "Roaming" / "xyz.block.buzz.app" / "agents" / "managed-agents.json"),
    )
)
STATE_PATH = HERMES_HOME / ".model_identity_state.json"

# Friendly short names for raw OmniRoute model IDs not in the catalog
_FALLBACK_LABELS = {
    "oc/deepseek-v4-flash-free": ("Workhorse", "WH", "#22C55E"),
    "deepseek/deepseek-v4-flash": ("DeepSeek", "DS", "#0EA5E9"),
    "ds/deepseek-v4-flash": ("DeepSeek", "DS", "#0EA5E9"),
    "opencode-go/deepseek-v4-flash": ("OpenCode", "OG", "#A855F7"),
    "gpt-5.6-sol": ("Powerful", "PWR", "#F59E0B"),
    "auto/coding": ("Auto", "AUTO", "#6366F1"),
    "auto/best-coding": ("Best", "BEST", "#EC4899"),
}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def load_identity() -> dict[str, Any]:
    if not IDENTITY_PATH.exists():
        raise FileNotFoundError(f"model_identity.json missing: {IDENTITY_PATH}")
    return json.loads(IDENTITY_PATH.read_text(encoding="utf-8"))


def save_identity(data: dict[str, Any]) -> None:
    data["last_updated"] = _now()
    IDENTITY_PATH.parent.mkdir(parents=True, exist_ok=True)
    IDENTITY_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def list_models() -> list[dict[str, Any]]:
    data = load_identity()
    return list(data.get("models", {}).values())


def get_active_key() -> str:
    data = load_identity()
    return data.get("active_model_key") or data.get("default_model_key") or "workhorse"


def get_model(key: str | None = None) -> dict[str, Any]:
    data = load_identity()
    key = key or get_active_key()
    models = data.get("models", {})
    if key not in models:
        # allow raw omniroute id
        for m in models.values():
            if m.get("omniroute_model") == key or m.get("key") == key:
                return dict(m)
        label, short, color = _FALLBACK_LABELS.get(key, (key.split("/")[-1][:12], "?", "#64748B"))
        return {
            "key": key,
            "label": label,
            "short": short,
            "color": color,
            "accent": color,
            "omniroute_model": key,
            "profile": None,
            "description": f"Raw OmniRoute model {key}",
            "tier": "raw",
        }
    return dict(models[key])


def resolve_for_agent(slug: str) -> dict[str, Any]:
    """Active model, with optional per-agent override from identity file."""
    data = load_identity()
    overrides = data.get("agent_overrides") or {}
    key = overrides.get(slug) or data.get("active_model_key") or data.get("default_model_key")
    return get_model(key)


def active_omniroute_model(slug: str | None = None) -> str:
    if slug:
        return resolve_for_agent(slug).get("omniroute_model") or "oc/deepseek-v4-flash-free"
    return get_model().get("omniroute_model") or "oc/deepseek-v4-flash-free"


def provider_label(model: dict[str, Any] | None = None) -> str:
    m = model or get_model()
    omni = m.get("omniroute_model") or ""
    if "/" in omni:
        return omni.split("/", 1)[0]
    if m.get("profile"):
        return str(m["profile"])
    return "omniroute"


def display_name_for(base_name: str, model: dict[str, Any] | None = None) -> str:
    data = load_identity()
    avatar_cfg = data.get("avatar") or {}
    if not avatar_cfg.get("include_model_in_display_name", True):
        return base_name
    m = model or get_model()
    tmpl = avatar_cfg.get("display_name_template") or "{name} · {short}"
    return tmpl.format(
        name=base_name,
        short=m.get("short") or "?",
        label=m.get("label") or "",
        model=m.get("omniroute_model") or "",
        provider=provider_label(m),
    )


def base_avatar_url(slug: str) -> str:
    data = load_identity()
    tmpl = (data.get("avatar") or {}).get(
        "base_url_template",
        "https://raw.githubusercontent.com/pmb2/hermes-config/vps-hybrid/assets/avatars/{slug}.svg",
    )
    return tmpl.format(slug=slug)


def _ring_avatar_svg(slug: str, model: dict[str, Any]) -> str:
    """Build an SVG that wraps the agent's existing character art in a colored ring.

    The character art stays intact — only the ring color changes per model.
    Hover tooltip shows the active model name. The ring is the only visual change.
    """
    short = (model.get("short") or "?").upper()[:6]
    label = model.get("label") or short
    color = model.get("color") or "#22C55E"
    accent = model.get("accent") or color
    omni = model.get("omniroute_model") or ""

    safe_label = (
        label.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    safe_omni = (
        omni.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    safe_short = (
        short.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    # Load base character art (local PNG or SVG, or remote SVG)
    icon_href = ""
    local_dir = Path((load_identity().get("avatar") or {}).get("local_svg_dir") or "")
    for ext in (".png", ".svg"):
        p = local_dir / f"{slug}{ext}"
        if p.exists():
            raw = p.read_bytes()
            mime = "image/png" if ext == ".png" else "image/svg+xml"
            b64 = base64.b64encode(raw).decode("ascii")
            icon_href = f"data:{mime};base64,{b64}"
            break
    if not icon_href:
        icon_href = base_avatar_url(slug)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     width="256" height="256" viewBox="0 0 256 256">
  <title>{safe_label} · {safe_omni}</title>
  <defs>
    <clipPath id="clip">
      <circle cx="128" cy="128" r="118"/>
    </clipPath>
    <linearGradient id="ringGrad" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{color}"/>
      <stop offset="100%" stop-color="{accent}"/>
    </linearGradient>
    <filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="4" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <!-- Character art (clipped to circle) -->
  <g clip-path="url(#clip)">
    <image href="{icon_href}" x="10" y="10" width="236" height="236"
           preserveAspectRatio="xMidYMid meet"/>
  </g>

  <!-- Colored model ring -->
  <circle cx="128" cy="128" r="120" fill="none" stroke="url(#ringGrad)"
          stroke-width="7" filter="url(#glow)" opacity="0.95"/>

  <!-- Model label badge (bottom-right, small) -->
  <rect x="186" y="216" width="60" height="22" rx="8" fill="url(#ringGrad)" opacity="0.9"/>
  <text x="216" y="232" text-anchor="middle"
        font-family="Segoe UI, Inter, Arial, sans-serif"
        font-size="10" font-weight="700" fill="#0B1220">{safe_short}</text>

  <metadata>
    <model key="{model.get('key','')}" omniroute="{safe_omni}" provider="{provider_label(model)}" short="{safe_short}"/>
    <agent slug="{slug}"/>
  </metadata>
</svg>
"""


def avatar_data_uri(slug: str, model: dict[str, Any] | None = None) -> str:
    m = model or resolve_for_agent(slug)
    svg = _ring_avatar_svg(slug, m)
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def switch_model(key: str, *, sync_buzz: bool = True, sync_profile: bool = True) -> dict[str, Any]:
    """Set active model key, optionally sync model_config profile + Buzz Desktop agents."""
    data = load_identity()
    models = data.get("models") or {}
    if key not in models:
        # try match by omniroute id or short label
        for k, m in models.items():
            if key in (m.get("omniroute_model"), m.get("short"), m.get("label"), m.get("key")):
                key = k
                break
        else:
            raise ValueError(
                f"Unknown model '{key}'. Available: {', '.join(sorted(models.keys()))}"
            )

    model = dict(models[key])
    data["active_model_key"] = key
    data["last_resolved_model"] = model.get("omniroute_model")
    data["last_provider_label"] = provider_label(model)
    save_identity(data)

    profile_switched = None
    if sync_profile and model.get("profile"):
        profile_switched = _sync_model_config_profile(model["profile"])

    buzz_result = None
    if sync_buzz:
        buzz_result = sync_buzz_agents(model_key=key)

    STATE_PATH.write_text(
        json.dumps(
            {
                "active_model_key": key,
                "omniroute_model": model.get("omniroute_model"),
                "provider": provider_label(model),
                "profile": model.get("profile"),
                "updated_at": _now(),
                "profile_switched": profile_switched,
                "buzz": buzz_result,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "active_model_key": key,
        "model": model,
        "profile_switched": profile_switched,
        "buzz": buzz_result,
    }


def _sync_model_config_profile(profile_name: str) -> str | None:
    if not MODEL_CONFIG_PATH.exists():
        return None
    try:
        cfg = json.loads(MODEL_CONFIG_PATH.read_text(encoding="utf-8"))
        if profile_name not in (cfg.get("profiles") or {}):
            return None
        if cfg.get("active_profile") == profile_name:
            return profile_name
        cfg["active_profile"] = profile_name
        cfg["last_updated"] = _now()
        MODEL_CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return profile_name
    except Exception as e:
        print(f"warn: model_config sync failed: {e}", file=sys.stderr)
        return None


def sync_buzz_agents(model_key: str | None = None) -> dict[str, Any]:
    """Rewrite Buzz Desktop managed-agents.json so each non-builtin agent shows active model.

    Updates:
      - display_name  (Name · SHORT)
      - model / provider fields
      - avatar_url    (badged data URI SVG)
      - system_prompt suffix with live model line
    """
    if not MANAGED_AGENTS.exists():
        return {"ok": False, "error": f"missing {MANAGED_AGENTS}", "updated": 0}

    agents = json.loads(MANAGED_AGENTS.read_text(encoding="utf-8"))
    if not isinstance(agents, list):
        return {"ok": False, "error": "managed-agents.json is not a list", "updated": 0}

    # backup once per day
    bak = MANAGED_AGENTS.with_suffix(f".json.bak-modelid-{dt.date.today().isoformat()}")
    if not bak.exists():
        bak.write_text(MANAGED_AGENTS.read_text(encoding="utf-8"), encoding="utf-8")

    updated = 0
    skipped = 0
    for a in agents:
        if not isinstance(a, dict):
            continue
        slug = a.get("slug") or ""
        if not slug or str(slug).startswith("builtin"):
            skipped += 1
            continue
        if a.get("is_builtin"):
            skipped += 1
            continue

        # Per-agent override or fleet default
        model = resolve_for_agent(slug) if not model_key else get_model(model_key)

        # Keep the character name intact — only change the ring
        a["display_name"] = a.get("name") or a.get("display_name") or slug
        a["model"] = model.get("omniroute_model")
        a["provider"] = "omniroute"
        a["avatar_url"] = avatar_data_uri(slug, model)

        sp = a.get("system_prompt") or ""
        sp = re.sub(r"\n?\n?\[Active model:.*?\]\s*$", "", sp, flags=re.S).rstrip()
        footer = (
            f"\n\n[Active model: {model.get('label')} · "
            f"{model.get('omniroute_model')} via OmniRoute. "
            f"If asked which model you are, answer with that.]"
        )
        a["system_prompt"] = (sp + footer).strip()
        a["updated_at"] = _now()
        updated += 1

    MANAGED_AGENTS.write_text(json.dumps(agents, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "updated": updated,
        "skipped": skipped,
        "path": str(MANAGED_AGENTS),
        "active": get_active_key(),
        "omniroute_model": active_omniroute_model(),
    }


def override_agent(slug: str, model_key: str, *, sync_buzz: bool = True) -> dict[str, Any]:
    """Set a per-agent model override. Returns updated identity + sync result."""
    data = load_identity()
    models = data.get("models") or {}
    # Resolve model_key
    resolved = None
    if model_key in models:
        resolved = model_key
    else:
        for k, m in models.items():
            if model_key in (m.get("omniroute_model"), m.get("short"), m.get("label"), m.get("key")):
                resolved = k
                break
    if not resolved:
        raise ValueError(
            f"Unknown model '{model_key}'. Available: {', '.join(sorted(models.keys()))}"
        )
    overrides = dict(data.get("agent_overrides") or {})
    overrides[slug] = resolved
    data["agent_overrides"] = overrides
    save_identity(data)

    model = get_model(resolved)
    buzz_result = sync_buzz_agents() if sync_buzz else None
    return {"slug": slug, "model": model, "buzz": buzz_result}


def unset_override(slug: str, *, sync_buzz: bool = True) -> dict[str, Any]:
    """Remove a per-agent override."""
    data = load_identity()
    overrides = dict(data.get("agent_overrides") or {})
    overrides.pop(slug, None)
    data["agent_overrides"] = overrides
    save_identity(data)

    buzz_result = sync_buzz_agents() if sync_buzz else None
    return {"slug": slug, "active": get_active_key(), "buzz": buzz_result}


def status() -> dict[str, Any]:
    m = get_model()
    return {
        "active_model_key": get_active_key(),
        "label": m.get("label"),
        "short": m.get("short"),
        "omniroute_model": m.get("omniroute_model"),
        "provider": provider_label(m),
        "profile": m.get("profile"),
        "tier": m.get("tier"),
        "description": m.get("description"),
        "identity_path": str(IDENTITY_PATH),
        "managed_agents": str(MANAGED_AGENTS),
        "available": [
            {
                "key": x.get("key"),
                "label": x.get("label"),
                "short": x.get("short"),
                "omniroute_model": x.get("omniroute_model"),
                "tier": x.get("tier"),
            }
            for x in list_models()
        ],
    }


def _cli(argv: list[str]) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="model_identity", description="OmniRoute+Buzz model identity")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="Show active model + catalog")
    sub.add_parser("list", help="List switchable models")

    sp = sub.add_parser("switch", help="Switch active model for fleet")
    sp.add_argument("model", help="Model key, short, label, or omniroute id")
    sp.add_argument("--no-buzz", action="store_true", help="Do not rewrite managed-agents.json")
    sp.add_argument("--no-profile", action="store_true", help="Do not update model_config.json")

    sub.add_parser("sync-buzz", help="Re-apply current model to Buzz Desktop agents")

    # Per-agent overrides
    oa = sub.add_parser("override", help="Set per-agent model override")
    oa.add_argument("slug", help="Agent slug (e.g. dev-lead, qa-lead)")
    oa.add_argument("model", help="Model key, short, label, or omniroute id")
    oa.add_argument("--no-buzz", action="store_true", help="Skip Buzz Desktop sync")

    ua = sub.add_parser("unset-override", help="Remove per-agent override")
    ua.add_argument("slug", help="Agent slug")
    ua.add_argument("--no-buzz", action="store_true", help="Skip Buzz Desktop sync")

    sub.add_parser("overrides", help="List all per-agent overrides")

    ap = sub.add_parser("avatar", help="Print data URI avatar for a slug")
    ap.add_argument("slug")

    args = p.parse_args(argv)
    if args.cmd == "status":
        print(json.dumps(status(), indent=2))
        return 0
    if args.cmd == "list":
        for m in list_models():
            mark = " *" if m.get("key") == get_active_key() else ""
            print(
                f"{m.get('key'):14s}  {m.get('short'):4s}  {m.get('omniroute_model'):32s}  {m.get('label')}{mark}"
            )
        return 0
    if args.cmd == "switch":
        result = switch_model(
            args.model,
            sync_buzz=not args.no_buzz,
            sync_profile=not args.no_profile,
        )
        m = result["model"]
        print(
            f"Switched → {m.get('label')} ({m.get('omniroute_model')})  "
            f"short={m.get('short')} color={m.get('color')}"
        )
        if result.get("profile_switched"):
            print(f"model_config active_profile → {result['profile_switched']}")
        if result.get("buzz"):
            b = result["buzz"]
            print(f"Buzz agents updated: {b.get('updated')} (skipped {b.get('skipped')})")
        print("Restart Buzz Desktop if avatars don't refresh immediately.")
        return 0
    if args.cmd == "sync-buzz":
        print(json.dumps(sync_buzz_agents(), indent=2))
        return 0
    if args.cmd == "override":
        result = override_agent(args.slug, args.model, sync_buzz=not args.no_buzz)
        print(
            f"Agent {args.slug} → {result['model'].get('label')} "
            f"({result['model'].get('omniroute_model')})"
        )
        if result.get("buzz"):
            print(f"Buzz sync: {result['buzz'].get('updated')} agents updated")
        return 0
    if args.cmd == "unset-override":
        result = unset_override(args.slug, sync_buzz=not args.no_buzz)
        print(f"Agent {args.slug} override removed. Fleet default: {result['active']}")
        if result.get("buzz"):
            print(f"Buzz sync: {result['buzz'].get('updated')} agents updated")
        return 0
    if args.cmd == "overrides":
        data = load_identity()
        ov = data.get("agent_overrides") or {}
        if not ov:
            print("No per-agent overrides. All agents use fleet default: " + get_active_key())
        else:
            for slug, key in sorted(ov.items()):
                print(f"  {slug:25s} → {key}")
        return 0
    if args.cmd == "avatar":
        print(avatar_data_uri(args.slug)[:120] + "...")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
