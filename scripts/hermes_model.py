#!/usr/bin/env python3
"""
Centralized Model Configuration — SINGLE SOURCE OF TRUTH
========================================================
All Hermes scripts, cron jobs, and tools import this module to get
their LLM provider configuration. Change ONE profile in
model_config.json to swap every script at once.

Usage:
    from hermes_model import get_config, get_api_key, active_profile

    cfg = get_config()              # active profile config dict
    key = get_api_key()             # API key from env var
    url = cfg['base_url']           # https://api.deepseek.com/v1
    model = cfg['model']            # deepseek-v4-flash
    chat = cfg['chat_model']        # deepseek-chat

    # Build auth header
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

To swap all models at once:
    Edit model_config.json → change "active_profile" to another profile name.
    No scripts need to change.
"""

import json, os
from pathlib import Path

CONFIG_PATH = Path(os.environ.get(
    "HERMES_MODEL_CONFIG",
    str(Path.home() / "AppData" / "Local" / "hermes" / "model_config.json")
))


def load():
    """Load the full model config JSON."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Model config not found at {CONFIG_PATH}. "
            f"Set HERMES_MODEL_CONFIG env var or create the file."
        )
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def active_profile():
    """Return the name of the active profile (e.g. 'deepseek')."""
    return load()["active_profile"]


def get_config(profile=None):
    """Return the config dict for the given profile (or active profile by default).

    Returns: {
        'provider': 'deepseek',
        'base_url': 'https://api.deepseek.com/v1',
        'api_key_env': 'DEEPSEEK_API_KEY',
        'model': 'deepseek-v4-flash',
        'chat_model': 'deepseek-chat',
        'reasoning_model': 'deepseek-reasoner',
        'description': 'DeepSeek API direct',
    }
    """
    data = load()
    if profile is None:
        profile = data["active_profile"]
    return data["profiles"][profile]


def get_api_key(profile=None):
    """Return the API key for the given profile from its env var."""
    cfg = get_config(profile)
    return os.environ.get(cfg["api_key_env"], "")


def api_headers(profile=None):
    """Return HTTP headers dict for API calls to the LLM provider."""
    key = get_api_key(profile)
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def list_profiles():
    """Return list of profile names with descriptions."""
    data = load()
    return [
        (name, p["description"])
        for name, p in data["profiles"].items()
    ]


def switch_to(profile_name):
    """Switch the active profile. Returns True on success."""
    data = load()
    if profile_name not in data["profiles"]:
        raise ValueError(
            f"Unknown profile '{profile_name}'. Available: {list(data['profiles'].keys())}"
        )
    data["active_profile"] = profile_name
    import datetime
    data["last_updated"] = datetime.datetime.now(
        datetime.timezone.utc
    ).isoformat()
    CONFIG_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return True


# Quick test when run directly
if __name__ == "__main__":
    print(f"Active profile: {active_profile()}")
    print(f"Base URL: {get_config()['base_url']}")
    print(f"Model: {get_config()['model']}")
    print(f"API key loaded: {'Yes' if get_api_key() else 'No'}")
    print(f"\nAvailable profiles:")
    for name, desc in list_profiles():
        marker = " ← ACTIVE" if name == active_profile() else ""
        print(f"  {name}: {desc}{marker}")
