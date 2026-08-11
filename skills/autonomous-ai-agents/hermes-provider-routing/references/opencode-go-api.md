# OpenCode Go API Reference

**Base URL:** `https://opencode.ai/zen/go/v1`
**Auth:** `OPENCODE_GO_API_KEY` (OpenAI-compatible `sk-...` key)
**API Compatibility:** OpenAI chat completions format

## Available Models (16)

| Model ID | Type |
|----------|------|
| `deepseek-v4-flash` | Fast inference, primary default |
| `deepseek-v4-pro` | Higher quality, slower |
| `kimi-k2.6` | Moonshot Kimi |
| `kimi-k2.5` | Moonshot Kimi |
| `glm-5.1` | Z.AI GLM |
| `glm-5` | Z.AI GLM |
| `minimax-m2.7` | MiniMax |
| `minimax-m2.5` | MiniMax |
| `qwen3.7-max` | Alibaba Qwen |
| `qwen3.6-plus` | Alibaba Qwen |
| `qwen3.5-plus` | Alibaba Qwen |
| `mimo-v2.5-pro` | Mimo |
| `mimo-v2.5` | Mimo |
| `mimo-v2-pro` | Mimo |
| `mimo-v2-omni` | Mimo (multimodal) |
| `hy3-preview` | Preview |

## API Usage

```bash
# List models
curl -s https://opencode.ai/zen/go/v1/models

# Chat completion
curl -s -X POST https://opencode.ai/zen/go/v1/chat/completions \
  -H "Authorization: Bearer $OPENCODE_GO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"Hello"}]}'
```

## Hermes Config

```yaml
model:
  provider: opencode-go
  base_url: https://opencode.ai/zen/go/v1
  default: deepseek-v4-flash
  api_mode: chat_completions
```

## OpenCode CLI Integration

OpenCode uses OpenCode Go API as a built-in provider. Configured in `~/.local/share/opencode/auth.json`:

```json
{
  "opencode-go": {
    "type": "api",
    "key": "sk-..."
  }
}
```

The provider routes for `opencode-go/<model>` model names. OpenCode's own config at `~/.config/opencode/opencode.json` sets the default model to `opencode-go/deepseek-v4-flash`.
