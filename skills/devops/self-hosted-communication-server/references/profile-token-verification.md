# Profile Token Verification — Fleet Audit Pattern

Before launching any gateway fleet, verify every profile's `DISCORD_BOT_TOKEN` is still valid against the running Spacebar instance. JWT tokens become invalid when:
- The Spacebar process restarts (new JWT key pair generated unless keys are persisted)
- Tokens were generated for a different Spacebar instance (different JWT secret)
- The user account was deleted/recreated

## Verification Script Pattern

```python
import json, urllib.request, os

profiles = ["chief-of-staff", "technology-lead", "growth-lead", ...]
base_url = "https://gc.your-domain.example/api/v9"
profile_base = "/path/to/hermes/profiles"

valid = []
invalid = []

for p in profiles:
    env_path = f"{profile_base}/{p}/.env"
    token = None
    try:
        with open(env_path) as f:
            for line in f:
                if line.startswith("DISCORD_BOT_TOKEN="):
                    token = line.strip().split("=", 1)[1]
                    break
    except FileNotFoundError:
        invalid.append((p, "no .env file"))
        continue

    if not token:
        invalid.append((p, "no DISCORD_BOT_TOKEN in .env"))
        continue

    try:
        req = urllib.request.Request(f"{base_url}/users/@me",
            headers={"Authorization": token})
        resp = urllib.request.urlopen(req, timeout=10)
        user = json.loads(resp.read())
        uid = user.get("id", "?")
        uname = user.get("username", "?")
        is_bot = user.get("bot", False)
        valid.append((p, uname, uid, is_bot))
    except urllib.error.HTTPError as e:
        invalid.append((p, f"HTTP {e.code}: {e.read().decode()[:80]}"))
    except Exception as e:
        invalid.append((p, str(e)[:80]))

print(f"Valid: {len(valid)}, Invalid: {len(invalid)}")
for p, uname, uid, bot in valid:
    print(f"  {p:25s} → {uname:20s} (id={uid[:15]}, bot={bot})")
for p, reason in invalid:
    print(f"  {p:25s} ✗ {reason}")
```

## Handling Expired Tokens

For profiles with expired tokens, either:
1. **Re-login** via `POST /auth/login` with known password to get fresh token
2. **Reset password** via DB if unknown: generate bcrypt hash, update `users.data.hash`

```python
# Fresh login
login = {"login": username, "password": password}
req = urllib.request.Request(f"{base_url}/auth/login",
    data=json.dumps(login).encode(),
    headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req, timeout=10)
fresh_token = json.loads(resp.read())["token"]

# Update .env
import re
with open(env_path) as f:
    content = f.read()
content = re.sub(r'^DISCORD_BOT_TOKEN=.*$',
    f'DISCORD_BOT_TOKEN={fresh_token}',
    content, flags=re.MULTILINE)
with open(env_path, 'w') as f:
    f.write(content)
```

## Before Launching Gateways

1. Run verification script against all target profiles
2. Refresh any expired tokens
3. Clear stale gateway state files:
   ```bash
   rm -f <profile>/gateway.pid <profile>/gateway_state.json
   rm -f <profile>/gateway.lock* <profile>/.gateway_state*
   ```
4. Launch each gateway with 30-60s stagger to avoid overwhelming Spacebar
5. Verify each gateway's state file shows `discord.state=connected`
