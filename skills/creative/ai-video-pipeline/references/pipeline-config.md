# Pipeline Configuration Reference

The `config/pipeline_v2.json` file externalizes all tunable pipeline parameters. No code changes needed to switch providers, models, or styles.

## Full Config

```json
{
  "output_root": "outputs",
  "channel_assets_root": "channel_assets",
  "channel": "main",
  "scene_count": 11,
  "resolution": "1280x720",
  "fps": 24,
  "script_provider": "any",
  "opencodego_url": "https://opencode.ai/zen/go/v1",
  "opencodego_model": "deepseek-v4-flash",
  "openrouter_model": "deepseek/deepseek-chat",
  "ollama_host": "http://127.0.0.1:11435",
  "ollama_model": "qwen2.5:72b-instruct-q4_K_M",
  "ollama_fallback_models": ["qwen2.5:14b"],
  "ollama_timeout": 900,
  "comfyui_url": "http://127.0.0.1:8188",
  "workflow": "workflows/flux_text_to_image.json",
  "model": "flux1-schnell-fp8.safetensors",
  "steps": 20,
  "narration_style": "Professional documentary narrator tone with natural pacing and clear educational phrasing.",
  "character_archetype": "A consistent character in a simple MS Paint illustration style, flat colors, white background, crude lines.",
  "tts": "chatterbox",
  "chatterbox_url": "http://127.0.0.1:8004",
  "chatterbox_voice": "Alice.wav"
}
```

## Key Fields

| Field | Description | Default |
|-------|-------------|---------|
| `script_provider` | Provider cascade: "any" (try all), "opencode-go", "openrouter", "ollama" | "any" |
| `opencodego_url` | OpenCodeGo API base URL | "https://opencode.ai/zen/go/v1" |
| `opencodego_model` | Model for script generation | "deepseek-v4-flash" |
| `model` | ComfyUI checkpoint filename | "flux1-schnell-fp8.safetensors" |
| `workflow` | ComfyUI workflow JSON path | "workflows/flux_text_to_image.json" |
| `steps` | FLUX inference steps | 20 |
| `narration_style` | Describes the narrator tone for script generation | Professional documentary... |
| `character_archetype` | Character description for visual consistency | MS Paint style businessman |
| `tts` | TTS engine | "chatterbox" |
| `chatterbox_url` | Chatterbox server URL | "http://127.0.0.1:8004" |
| `chatterbox_voice` | Voice name (must include .wav extension) | "Alice.wav" |

## Environment Variables

| Variable | Purpose | Source |
|----------|---------|--------|
| `OPENCODE_GO_API_KEY` | Auth for OpenCodeGo API | ~/.hermes/.env |
| `OPENROUTER_API_KEY` | Auth for OpenRouter fallback | ~/.hermes/.env |
| `COMFYUI_URL` | Override ComfyUI URL | optional |
| `OLLAMA_HOST` | Override Ollama URL | optional |
