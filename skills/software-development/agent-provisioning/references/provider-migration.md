# Provider Migration — Cross-Repo Sweep Pattern

## When to Use This

When the operator says "search for everything using [old provider] and replace with [new provider]." This means a COMPREHENSIVE sweep — not just the profile that's currently failing.

## Migration Workflow

### Step 1: Understand the Provider Stack

Before sweeping, know the architecture:

**Provider topology (this environment):**
- **Hermes profile configs** — `~/.hermes/profiles/<name>/config.yaml` — `model.provider` defines the inference provider per-agent
- **Agent-fleet configs** — `agent-fleet/teams/<team>/<name>/config.yaml` — `profile.provider` for ClawFleet-deployed agents
- **Agent-fleet fleet config** — `agent-fleet/config/<fleet>.yaml` — bulk agent definitions with inline model/provider
- **Main Hermes config** — `~/.hermes/config.yaml` — global `model.provider`, `fallback_providers`, and MCP server env vars
- **Cron jobs** — `cronjob list` — individual jobs can override model/provider per job
- **MCP server env vars** — in config.yaml, MCP servers like bizdev-agent, gpt-researcher, job-agent, personal-intelligence each have their own `OPENROUTER_MODEL`/`LLM_BASE_URL` env vars
- **Deployment templates** — `hermes-config/config/config.yaml` (golden template), `hermes-config/vps/config.yaml` (VPS template)
- **Application `.env` files** — `auto-resume/bizdev-agent/.env`, `auto-resume/job-agent/.env` — standalone app configs
- **Application `.env.example` files** — templates showing env var structure
- **Application code** — `auto-resume/*/app/agents/llm.py`, `ai-scientist-hermes/llm.py` — hardcoded base URLs and model names

### Step 2: Sweep Inventory

Search order (most to least impactful):

```bash
# 1. Hermes profile configs
grep -r "openrouter\|deepseek/deepseek-chat" ~/.hermes/profiles/*/config.yaml

# 2. Agent fleet configs
grep -r "openrouter\|deepseek/deepseek-chat" ${MY_REPOS}/agent-fleet/

# 3. Main config (MCP server env vars)
grep -rn "openrouter\|OPENROUTER" ~/.hermes/config.yaml

# 4. Cron jobs
cronjob list  # then check each job's model/provider fields

# 5. Deployment templates
grep -r "openrouter\|OPENROUTER\|deepseek/deepseek-chat" \
  ${MY_REPOS}/hermes-config/

# 6. App env files and code
grep -r "openrouter\|OPENROUTER" \
  ${MY_REPOS}/auto-resume/
grep -r "openrouter\|OPENROUTER" \
  ${MY_REPOS}/ai-scientist-hermes/
```

### Step 3: Replace — Order Matters

**Always do the profiles first**, then cron jobs, then everything else. The profiles control what model the agent actually uses on every turn — they're the most impactful.

**Profile config template (primary + fallback):**
```yaml
model:
  api_mode: chat_completions
  base_url: https://opencode.ai/zen/go/v1
  default: deepseek-v4-flash
  provider: opencode-go
fallback_model:
  provider: openrouter
  model: free
```

**Agent-fleet config template:**
```yaml
profile:
  name: <agent-name>
  codename: <codename>
  model: deepseek-v4-flash
  provider: opencode-go
  fallback:
    provider: openrouter
    model: free
```

**Cron job model pinning:**
```yaml
model:
  model: deepseek-v4-flash
  provider: opencode-go
```

### Step 4: Handle MCP Server Env Vars Separately

MCP server env vars (bizdev-agent OPENROUTER_MODEL, gpt-researcher OPENAI_BASE_URL, etc.) are consumed by those MCP server processes for THEIR OWN LLM calls — not by Hermes itself.

**Decision:**
- If the MCP server supports OpenAI-compatible APIs, replace the base URL with `https://opencode.ai/zen/go/v1`
- Keep the `OPENROUTER_API_KEY` as fallback (the MCP server needs it for its internal fallback logic)
- Add `LLM_BASE_URL: https://opencode.ai/zen/go/v1` as a new env var alongside the existing OpenRouter config
- Update `STRATEGIC_LLM` to use the new provider: `opencode-go/deepseek-v4-flash`
- Don't delete OpenRouter env vars — they serve as the fallback path

### Step 5: Handle Application Code References

For standalone apps (bizdev-agent, job-agent, ai-scientist):
- **Config files** (config.py, .env) — update to let the app know about the new provider
- **LLM client init** — the app creates its own OpenAI client with a base_url and api_key; update the base_url
- **Default model strings** — update hardcoded model names in function defaults
- **Order**: the smarter approach is to add the new provider config alongside the old one, not replacing it. The app can then be updated to try the new provider first and fall back to the old one.

### Step 6: Update Templates (.env.example)

The `.env.example` files serve as documentation for how to configure the app. Update them to show:
1. Primary provider config (new)
2. Fallback config (old, labeled as fallback)

### Step 7: Verify

After the migration:

```bash
# No remaining old provider refs in configs
grep -r "deepseek/deepseek-chat" ~/.hermes/config.yaml ~/.hermes/profiles/

# OpenCode Go API responds
curl https://opencode.ai/zen/go/v1/models

# Cron jobs use pinned model
cronjob list | grep -A5 "provider\|model"
```

### What NOT to Change

- **npm packages** — changing the npm dependency requires code changes in the app
- **Third-party code** that hardcodes a provider — let their maintainers decide
- **Data files** — only config and code files
- **Dockerfiles** that reference a provider — unless you're rebuilding them
- **Comment-only references** — informational, not operational

## Real Example: OpenRouter → OpenCode Go API Migration

Files touched in a real sweep (from session 2026-05-29):
- 6 Hermes profile configs
- 9 agent-fleet council profile configs
- 1 agent-fleet fleet config
- 5 pulse cron jobs
- 2 hermes-config deployment templates
- 2 MCP server sections in main config
- 2 .env.example files
- 2 ai-scientist Python files
