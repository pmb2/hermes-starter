# Codex config.toml Reference

Location: `~/.codex/config.toml` (Windows: `C:\Users\<user>\.codex\config.toml`)

## Key Sections

```toml
# Active model and reasoning effort
model = "gpt-5.4"
model_reasoning_effort = "high"
approvals_reviewer = "user"   # or "model"

# Marketplace sources for tools/plugins
[marketplaces]
[marketplaces.openai-bundled]
source_type = "local"
source = 'C:\Users\<user>\.codex\.tmp\bundled-marketplaces\openai-bundled'

[marketplaces.openai-primary-runtime]
source_type = "local"
source = 'C:\Users\<user>\.cache\codex-runtimes\...\plugins\openai-primary-runtime'

# External MCP servers Codex can call
[mcp_servers]
[mcp_servers.DOCKER]
command = 'docker.exe'
args = ['mcp', 'gateway', 'run', '--profile', 'default']

[mcp_servers.firefox-devtools]
command = 'cmd'  # Windows only
args = ['/c', 'npx', '-y', 'firefox-devtools-mcp', '--headless', '--viewport', '1280x720']

[mcp_servers.GIT-STARS]
command = 'python.exe'
args = ['-m', 'app.main']
cwd = 'E:/path/to/project'

# Custom model providers (gateways, proxy endpoints)
[model_providers]
[model_providers.model-gateway]
base_url = 'http://localhost:4001/v1'
env_key = 'LITELLM_MASTER_KEY'
name = 'Model Gateway (Local)'

[model_providers.model-gateway.models]
cloud-reasoner = { name = 'Cloud Reasoner (OpenRouter)' }
local-agent = { name = 'Local Qwen 35B' }
local-fast = { name = 'Local Qwen 14B' }

# Installed plugins
[plugins]
[plugins.'github@openai-curated']
enabled = true
[plugins.'browser@openai-bundled']
enabled = true

# Trusted project directories (Codex requires trust for disk access)
[projects]
[projects.'E:\\path\\to\\projects']
trust_level = 'trusted'

# Windows-specific
[windows]
sandbox = 'elevated'  # or 'none'

# Feature discovery / model migration notices
[notice]
[notice.model_migrations]
'gpt-5.3-codex' = 'gpt-5.4'  # model was auto-migrated

# TUI / model availability tracking
[tui]
[tui.model_availability_nux]
'gpt-5.5' = 4  # seen 4 times in NUX
```

## Model Override Flags

| Flag | Purpose | Example |
|------|---------|---------|
| `-m <model>` | Override model | `-m gpt-5.5` |
| `-c model=...` | Set model via config | `-c model=gpt-5.5` |
| `-c model_reasoning_effort=...` | Set reasoning level | `-c model_reasoning_effort="high"` |
| `-p <profile>` | Use a named config profile | - |

Multiple `-c` flags can be chained: `-c model=gpt-5.5 -c model_reasoning_effort="high"`

## Model Migration Tracking

When Codex auto-migrates a model, it records the mapping under `[notice.model_migrations]`. The old model name is no longer valid — try the new one. Example: `'gpt-5.3-codex' = 'gpt-5.4'` means `gpt-5.3-codex` was renamed to `gpt-5.4`.

## Health Check

```bash
# Quick check of active model + reasoning
cat ~/.codex/config.toml | grep -E '^(model|model_reasoning_effort)'

# Verify version
codex --version
```
