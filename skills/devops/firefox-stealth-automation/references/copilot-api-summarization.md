# Copilot API as LLM Summarization Backend (Fallback)

**Updated 2026-05-30:** The primary LLM backend is now OpenCode Go API. Copilot falls to second priority.

## Priority Order (from `ingest-chatgpt-grok.sh` / `pim-pipeline.py`)

1. **OpenCode Go API** — reads `opencode-go.key` from `~/.local/share/opencode/auth.json`
2. **GitHub Copilot API** — uses `gh auth token` (40-char GitHub OAuth token)
3. **OpenRouter** — returns 401/402 (no credits), last resort

## Copilot API Details (when OpenCode Go is unavailable)

| Property | Value |
|----------|-------|
| Base URL | `https://api.githubcopilot.com` |
| Auth | `Bearer <gh-auth-token>` (40 char OAuth) |
| Models | `gpt-4o-mini`, `gpt-4o` (limited) |
| Cost | Included in Copilot subscription |
| Extra headers | `Editor-Version: vscode/1.95.0`, `Editor-Plugin-Version: copilot-chat/0.23.0` |

## Requirements

- `gh` CLI installed and authenticated (`gh auth login`)
- Active GitHub Copilot subscription

## How the PIM .env is written

```python
gh_token = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=10).stdout.strip()
oc_key = json.load(open(auth_path))["opencode-go"]["key"]  # from ~/.local/share/opencode/auth.json
llm_key = oc_key or gh_token  # OpenCode Go wins, Copilot falls back
llm_base = "https://opencode.ai/zen/go/v1"
```

## Copilot vs OpenCode Go API

| Factor | OpenCode Go | Copilot API |
|--------|------------|-------------|
| Cost | Included | Included in Copilot sub |
| Credits | Working | Working |
| Reliability | Tested | Fallback only |
| Models | deepseek-v4-flash, deepseek-v4-pro | gpt-4o-mini, gpt-4o |
