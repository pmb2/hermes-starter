# Provider Cost & Quality Comparison

## Image Generation — FLUX.1-schnell

### Replicate (Recommended for cloud)
| Model | Cost/image | 40-min video (170 imgs) | Speed |
|-------|-----------|------------------------|-------|
| black-forest-labs/flux-schnell | **$0.003** | **$0.51** | 2–5 sec |
| black-forest-labs/flux-dev | $0.025 | $4.25 | 5–10 sec |
| black-forest-labs/flux-1.1-pro | $0.04 | $6.80 | 3–8 sec |

### HuggingFace Inference (via Inference Providers)
- Free tier: $0.10/mo free credits
- PRO tier: $2.00/mo free credits
- Pay-as-you-go: same rates as underlying provider, no HF markup
- Serverless FLUX.1-dev: ~$0.0012/image (10 sec @ $0.00012/sec GPU)
- Note: HF-Inference (the old serverless API) is now mostly CPU-only. Use Inference Providers with Replicate/Fal as the backend.

### Fal AI
- Per-second GPU pricing starting at $1.89/hr for H100
- FLUX models typically $0.002–$0.005/image through their serverless API
- Not all models publicly listed on pricing page — check individual model pages

### Local ComfyUI (RTX 3090 24GB)
- **With free VRAM** (close browsers first): ~10–15 sec/image at 1024×1024, 4 steps
- **With saturated VRAM** (--lowvram): ~2–5 min/image, constant CPU ↔ GPU swapping
- **Cost:** $0 (electricity only)
- **VRAM needed:** ~8–10 GB for FLUX.1-schnell fp8 at 1024×1024

## TTS Voiceover

| Provider | Quality | Latency | Cost | API Endpoint |
|----------|---------|---------|------|-------------|
| Chatterbox (local Docker) | ★★★★★ | ~1 sec/10s audio | $0 | POST /audio/speech, {"model":"Chatterbox","input":"text","voice":"voice.wav","response_format":"wav"} |
| Fish Speech 2 (local Docker) | ★★★★ | ~0.5 sec/10s | $0 | POST /v1/tts |
| ElevenLabs | ★★★★★ | ~0.3 sec | ~$5/mo | OpenAI-compatible |
| OpenAI TTS | ★★★★ | ~0.3 sec | ~$0.015/1K chars | OpenAI-compatible |

## Script Generation (LLM)

| Provider | Quality | Cost | Notes |
|----------|---------|------|-------|
| OpenCode Go (deepseek-v4-flash) | ★★★★★ | Free tier | Fast, excellent for structured JSON output |
| OpenRouter (deepseek/deepseek-chat) | ★★★★ | ~$0.14/1M tokens | Good fallback |
| Ollama local (qwen2.5:72b) | ★★★ | $0 | ~2–5 tokens/sec on consumer GPU |

## Key Settings Reference

### FLUX.1-schnell
- **CFG:** `1.0` (MUST be 1.0 — never use SD defaults)
- **Steps:** `4` (distilled for 4-step; more doesn't help)
- **Sampler:** `euler`
- **Scheduler:** `simple`
- **Resolution:** `1024×1024` (native training resolution)
- **Model file:** `flux1-schnell-fp8.safetensors` (6.1 GB disk, 16.1 GB weights)

### Pipeline Config Template
```json
{
  "output_root": "outputs",
  "scene_count": 11,
  "resolution": "1280x720",
  "fps": 24,
  "script_provider": "any",
  "opencodego_model": "deepseek-v4-flash",
  "openrouter_fallback": "deepseek/deepseek-chat",
  "tts": "chatterbox",
  "chatterbox_url": "http://127.0.0.1:8004",
  "chatterbox_voice": "Alice.wav",
  "model": "flux1-schnell-fp8.safetensors",
  "steps": 20,
  "narration_style": "Professional documentary narrator tone with natural pacing.",
  "character_archetype": "A consistent character in a simple MS Paint illustration style, flat colors, white background, crude lines."
}
```
