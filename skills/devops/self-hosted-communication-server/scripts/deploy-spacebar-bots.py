#!/usr/bin/env python3
"""
Spacebar Hermes Agent Deploy — register bot accounts, join guild, save tokens.
"""
import json, urllib.request, urllib.error, os, datetime

API = "http://localhost:3001/api/v9"  # or https://discy.your.domain/api/v9
GUILD_ID = "<discord-channel-id>"  # replace after creating guild

BOTS = {
    "agent1": {"pass": "pass1!", "email": "agent1@domain"},
    "agent2": {"pass": "pass2!", "email": "agent2@domain"},
}

def api(method, path, data=None, token=None):
    hdrs = {"Content-Type": "application/json"}
    if token: hdrs["Authorization"] = token
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(f"{API}{path}", data=body, headers=hdrs, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"_error": f"HTTP {e.code}", "_body": json.loads(e.read().decode())}

tokens = {}

# Step 1: Register or login each bot
for name, info in BOTS.items():
    r = api("POST", "/auth/register", {
        "username": name, "password": info["pass"],
        "consent": True, "date_of_birth": "1990-01-01",
        "email": info["email"]
    })
    if isinstance(r, dict) and "token" in r:
        token = r["token"]
    elif r.get("_error") == "HTTP 400" and "EMAIL_ALREADY_REGISTERED" in str(r):
        r2 = api("POST", "/auth/login", {"login": name, "password": info["pass"]})
        if isinstance(r2, dict) and "token" in r2:
            token = r2["token"]
        else:
            print(f"LOGIN FAIL: {name}")
            continue
    else:
        print(f"FAIL: {name}")
        continue
    tokens[name] = token
    print(f"  {name}: token len={len(token)}")

# Step 2: Join guild
for name, token in tokens.items():
    r = api("PUT", f"/guilds/{GUILD_ID}/members/@me", {}, token=token)
    guild = r.get("guild_id", "") if isinstance(r, dict) else ""
    print(f"  {name}: joined guild_id={guild[:20] if guild else '?'}")

# Step 3: Write shared env file
env_lines = [
    "# Spacebar Bot Tokens — Generated " + datetime.datetime.now().isoformat()[:19],
    f"# API: {API}",
    f"# Guild ID: {GUILD_ID}",
]
for name, token in tokens.items():
    env_lines.append(f"export SPACEBAR_BOT_{name.upper()}={token}")
env_path = "spacebar-bot-tokens.env"
with open(env_path, "w") as f:
    f.write("\n".join(env_lines) + "\n")
print(f"\nTokens written: {env_path}")

# Step 4: Per-profile .env.spacebar files
profile_base = os.path.expanduser("~/AppData/Local/hermes/profiles")
for name, token in tokens.items():
    profile_dir = os.path.join(profile_base, name)
    os.makedirs(profile_dir, exist_ok=True)
    env_lines = [
        "# Spacebar env for " + name,
        "export SPACEBAR_BOT_TOKEN=*** + token,
        "export SPACEBAR_API_URL=" + API,
        "export SPACEBAR_GATEWAY_URL=ws://localhost:3001/",
        "export SPACEBAR_GUILD_ID=" + GUILD_ID,
        "export SPACEBAR_CHANNEL=#team-channel",
    ]
    with open(os.path.join(profile_dir, ".env.spacebar"), "w") as f:
        f.write("\n".join(env_lines) + "\n")
    print(f"  Wrote {profile_dir}/.env.spacebar")
