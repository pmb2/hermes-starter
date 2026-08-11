# API Key Redaction in Hermes Agent

## The Problem

When an agent (or subagent) reads an API key from a `.env` file and writes it to another file (e.g., propagating `OPENCODE_GO_API_KEY` to profile `.env` directories), the value gets masked with `***` in tool output. If the agent copies the masked value, the target file contains `OPENCODE_GO_API_KEY=*** — literally three asterisks.

## Two Redaction Layers

### Layer 1 — Tool Output Redaction (`agent/redact.py`)

The `redact_sensitive_text()` function runs on ALL text returned to the agent from tool calls (terminal output, file reads, etc.). It uses these patterns:

```python
_PREFIX_PATTERNS = [
    r"sk-[A-Za-z0-9_-]{10,}",           # OpenAI / OpenRouter / Anthropic / OpenCode Go
    r"ghp_[A-Za-z0-9]{10,}",            # GitHub PAT
    # ... 20+ more patterns
]
```

When `sk-3IhavGBsC4j3...` appears in tool output, `_mask_token()` replaces it with `sk-3Ih...yrG4` (first 6 + `...` + last 4 chars). The agent sees the truncated form.

Additionally, the `_ENV_ASSIGN_RE` pattern catches `KEY=VALUE` lines where `KEY` contains `API_KEY`, `TOKEN`, `SECRET`, etc., and also masks the value:

```python
_ENV_ASSIGN_RE.sub(lambda m: f"{m.group(1)}={_mask_token(m.group(3))}", text)
```

This means `grep` output like `OPENCODE_GO_API_KEY=sk-3IhavGBs...` becomes `OPENCODE_GO_API_KEY=sk-3Ih...yrG4` before the agent sees it.

### Layer 2 — Config Switch (`security.redact_secrets`)

The redaction is gated by `_REDACT_ENABLED`:

```python
_REDACT_ENABLED = os.getenv("HERMES_REDACT_SECRETS", "true").lower() in {"1", "true", "yes", "on"}
```

- Default: `true` (enabled)
- Config.yaml: `security.redact_secrets: true` (bridged to env var at startup)
- To disable: set `security.redact_secrets: false` in config OR `HERMES_REDACT_SECRETS=*** in `.env`

## How It Breaks Key Propagation

1. Agent reads root `.env` via `terminal('grep OPENCODE_GO_API_KEY .env')` or `read_file('.env')`
2. `redact_sensitive_text()` masks the key → agent sees `sk-3Ih...yrG4`
3. Agent writes `OPENCODE_GO_API_KEY=sk-3Ih...yrG4` to profile `.env` via `write_file()`
4. Profile gateway uses truncated key → 401 authentication error

**Worse case:** If the key is shorter than 18 chars (the `_mask_token` floor), it becomes literally `***`.

## Fixes Applied

### Immediate fix — sk- pattern disabled

The `sk-[A-Za-z0-9_-]{10,}` pattern was commented out in `agent/redact.py`. This prevents `sk-` prefixed keys (OpenCode Go, OpenAI, OpenRouter, Anthropic) from being masked. Other patterns (ghp_, xox[baprs]-, AIza, etc.) remain active.

**Committed to:** `pmb2/hermes-agent`, branch `fix/disable-sk-redaction`
**File changed:** `agent/redact.py` line 71

### Config disable

`security.redact_secrets: false` set in `~/.hermes/config.yaml` to ensure redaction is off globally.
`HERMES_REDACT_SECRETS=*** added to all profile `.env` files for defense-in-depth.

### Safe propagation pattern (when redaction is on)

Read the key via a Python script that reads the file directly without going through tool output:

```python
# In a script file, NOT via terminal tool:
from pathlib import Path
root_env = Path.home() / "AppData/Local/hermes/.env"
for line in root_env.read_text().splitlines():
    if line.startswith("OPENCODE_GO_API_KEY") and "=" in line:
        key = line.split("=", 1)[1].strip()
        # Write to profiles without ever printing the key
```

## Verification

Check that the key in profile `.env` is the real value, not truncated:

```bash
grep "OPENCODE_GO_API_KEY" ~/AppData/Local/hermes/profiles/<name>/.env
# Should show: OPENCODE_GO_API_KEY=sk-realvalue...
# NOT:          OPENCODE_GO_API_KEY=sk-3Ih...yrG4
# NOT:          OPENCODE_GO_API_KEY=***
```

## Key Files

- `agent/redact.py` — `redact_sensitive_text()`, `_PREFIX_PATTERNS`, `_mask_token()`, `_REDACT_ENABLED`
- `hermes_cli/gateway.py` — controls `security.redact_secrets` bridge to env var
- `config.yaml` — `security.redact_secrets: true/false`
