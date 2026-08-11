# Gateway Router Integration Options — OmniRoute, Hermes-router, CLIProxyAPI, FreeLLMAPI, 9Router-v2

Five open-source AI gateways that provide free/cheap model access. OmniRoute is primary; the others plug into it as fallback tiers or automation pipelines.

## OmniRoute v3.8.49 (22,385★)

**GitHub:** `github.com/diegosouzapw/OmniRoute` — **Location:** `${USER_HOME}\OmniRoute\`
**Type:** TypeScript (Next.js) — local HTTP server on port 20128

| Feature | Value |
|---------|-------|
| Providers | 271 (90+ free tiers, ~1.4B free tokens/month) |
| Routing | 18 strategies: priority, cost-optimized, headroom, auto, fusion, etc. |
| Compression | RTK + Caveman (15-95% token savings) |
| Endpoint | `http://localhost:20128/v1` |

### .env Keys Configured
DEEPSEEK_API_KEY, KIMI_API_KEY, FAL_KEY from the operator's existing keys.

### Startup
```bash
bash ~/AppData/Local/hermes/scripts/hermes-stack.sh  # full stack
```
Or manually: `npm run dev` in the OmniRoute directory.

**Env fixes needed:** `OMNIROUTE_AUTO_FREE_FALLBACK_TO_FULL_POOL=true`, `NODE_ENV=development`
**Zombie cleanup:** Kill stale processes on 20128 before restarting.

## Hermes-router (the operator's own project)

**Location:** `${MY_REPOS}\Documents\github\Hermes-router` — **Port:** 8319
**Type:** Python Flask — single file router.py, Flask/Waitress server

Provides **both OpenAI and Anthropic API compatibility** — unlike OmniRoute which is OpenAI-only. Routes across Gemini, OpenRouter, Groq, SambaNova, Cerebras, Mistral, Cohere, Z.ai, Naga, NVIDIA NIM with automatic failover.

### .env
```bash
PORT=8319
HOST=127.0.0.1
PROXY_API_KEYS=omniroute-local
GEMINI_API_KEYS=...       # free tier, resets per minute
OPENROUTER_API_KEYS=...   # 50 free requests/day per key
```

### Start
```bash
cd ${MY_REPOS}/Documents/github/Hermes-router
pip install -r requirements.txt
python router.py
```

## CLIProxyAPI (43,968★)

**GitHub:** `github.com/router-for-me/CLIProxyAPI` — **Location:** `${USER_HOME}\CLIProxyAPI\`
**Type:** Go binary (62MB) — **Port:** 8317

Wraps Claude Code, Codex, Grok Build, Antigravity as OpenAI-compatible API. Free access to premium models by routing through CLI tools' free tiers.

### Config
```yaml
host: "127.0.0.1"; port: 8317; api-keys: ["omniroute-local"]
routing: strategy: "round-robin"
claude: disable-claude-cloak-mode: false
```

### OAuth Login (opens browser for each)
```
./cli-proxy-api.exe --antigravity-login
./cli-proxy-api.exe --claude-login
./cli-proxy-api.exe --codex-login
```

## FreeLLMAPI (16,544★)

**GitHub:** `github.com/tashfeenahmed/freellmapi` — **Location:** `${USER_HOME}\freellmapi\`
**Type:** Python — 28 free providers, ~4B tokens/month

## 9Router-v2 (Cloudflare + 2Captcha Automation)

**Location:** `${MY_REPOS}\Documents\github\9router-v2`
**Type:** Node.js Express + React

Built-in Playwright + 2Captcha automation for Cloudflare Workers AI account signup:
```
backend/src/automation/cloudflare_signup.py  (2392 lines)
```
Generates temp email → Camoufox signup → 2Captcha solve → extracts free API key. Outputs JSON: `{"status":"success","api_key":"...","account_id":"...","email":"..."}`

## Firefox CDP + Profile Cookies

Firefox with remote debugging on port 9239 using default profile (`<profile-id>.default-release-1`) provides saved cookies/logins for GitHub, Discord, Google, etc.

```bash
"/c/Program Files/Mozilla Firefox/firefox.exe" \
    --remote-debugging-port 9239 --no-remote \
    --profile "${USER_HOME}/AppData/Roaming/Mozilla/Firefox/Profiles/<profile-id>.default-release-1" --disable-gpu &
```

## Tier Cascade (All 47+1 Hermes Profiles)

| Tier | Source | Model ID | Cost | Quality |
|------|--------|----------|------|---------|
| 1st | OpenCode Zen | `oc/deepseek-v4-flash-free` | $0 | DeepSeek V4 Flash |
| 2nd | Together/SiliconFlow | `tllm/together_deepseek_v3` | $0 | DeepSeek V3 |
| 3rd | OmniRoute auto-free | `auto/coding:free` | $0 | Best free coding |
| 4th | Hermes-router (port 8319) | user's custom router | $0 | Gemini/OpenRouter/Groq |
| 5th | CLIProxyAPI (port 8317) | Antigravity/Codex | $0 | Free Claude/Codex |
| 6th | FreeLLMAPI | 28 free providers | $0 | ~4B tokens/mo |
| Last | DeepSeek paid API | deepseek-v4-flash | Pay | Only if ALL free exhausted |
| ⛔ NEVER | Kimi K3, Claude, GPT | manual switch | $Expensive | Never auto-routed |

## Batch Profile Migration

```python
from pathlib import Path
for d in Path("~/AppData/Local/hermes/profiles").expanduser().iterdir():
    if not d.is_dir(): continue
    c = d / "config.yaml"
    if not c.exists(): continue
    content = c.read_text()
    content = content.replace("old_url", "new_url")
    content = content.replace("old_model", "new_model")
    c.write_text(content)
```
