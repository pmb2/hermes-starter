# Uniform Agent Configuration Pattern

When managing a fleet of 20+ agent profiles, apply a **uniform base config**
(identical model, provider, tools, memory settings) to all profiles, then
layer per-agent customizations on top. This prevents drift and makes fleet-wide
changes (provider switch, tool addition) a single script edit.

## The Pattern

### Base Config Template

```yaml
model:
  api_mode: chat_completions
  base_url: http://localhost:20128/v1
  api_key: omniroute-local
  default: oc/deepseek-v4-flash-free
  provider: custom:omniroute
fallback_providers:
  - model: deepseek-v4-flash-free
    provider: opencode-zen
  - model: google/gemma-4-31b-it:free
    provider: openrouter
agent:
  max_turns: 120
  tool_use_enforcement: true
memory:
  memory_enabled: true
  user_profile_enabled: true
  provider: mempalace
tools:
  - web
  - terminal
  - file
  - memory
  - session_search
  - delegation
  - cronjob
  - clarify
  - skills
  - todo
  - vision_analyze
  - execute_code
```

### The Apply Script

```python
BASE_CONFIG = { ... }  # the dict above
PROFILES_DIR = Path("profiles")

for profile_dir in PROFILES_DIR.iterdir():
    config_path = profile_dir / "config.yaml"
    old_config = yaml.safe_load(config_path.read_text())
    
    # Build new config from base
    new_config = dict(BASE_CONFIG)
    
    # Preserve per-agent customizations
    for key in ["discord", "mcp_servers", "skills", "mempalace_wings", 
                "onboarding", "plugins"]:
        if key in old_config:
            new_config[key] = old_config[key]
    
    yaml.dump(new_config, open(config_path, "w"), ...)
```

### What Gets Preserved Per-Agent

| Section | How Preserved | Why |
|---------|--------------|-----|
| `SOUL.md` | Not touched by script | Personality, role, expertise (unique per agent) |
| `.env` | Not touched | API keys, relay URL, channel UUIDs |
| `skills` | Copied from old config | Each agent needs different capabilities |
| `mcp_servers` | Copied from old config | Database access, browser, etc. |
| `mempalace_wings` | Copied from old config | Knowledge base access |
| `discord` | Copied from old config | Channel permissions |
| `onboarding` | Copied from old config | Session state |

### What Gets Overwritten

- `model` — provider, base_url, model name
- `fallback_providers` — fallback chain
- `agent` — max_turns, tool enforcement
- `memory` — provider, enabled state
- `tools` — available tool categories (12 standard tools)

### Verification

After applying, verify every config is valid YAML with required keys:

```python
for d in PROFILES_DIR.iterdir():
    cfg = yaml.safe_load((d / "config.yaml").read_text())
    assert "model" in cfg, f"{d.name}: missing model"
    assert "tools" in cfg, f"{d.name}: missing tools"
```

### When to Re-Apply

- Switching LLM providers (e.g. OmniRoute → direct OpenRouter)
- Adding/removing standard tools (e.g. adding `vision_analyze` fleet-wide)
- Changing memory provider or model tier
- After adding new profiles (they start with defaults, apply to standardize)

### Pitfalls

- **YAML formatting**: `yaml.dump()` with `default_flow_style=False` keeps the config human-editable. Skip `sort_keys=True` to preserve key ordering.
- **Empty skills list**: If `old_config["skills"]` is `None` or `[]`, Python's truthiness matters. Use `if key in old_config and old_config[key]:`.
- **SOUL.md still lives in profile dir**: The config only references skills by name. Each agent's `SOUL.md` is at `profiles/<name>/SOUL.md` — never accidentally overwrite it from the config script.
