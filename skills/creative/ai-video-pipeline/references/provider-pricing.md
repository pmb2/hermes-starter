# Image Generation Provider Pricing (June 2026)

Costs for generating FLUX images via cloud APIs as an alternative to local ComfyUI.

## Replicate (Recommended — Simplest API)

| Model | Per Image | 40-min video (170 images) | 40-min video (80 images) |
|-------|-----------|--------------------------|--------------------------|
| **FLUX.1-schnell** | **$0.003** | **$0.51** | **$0.24** |
| FLUX.1-dev | $0.025 | $4.25 | $2.00 |
| FLUX 1.1 Pro | $0.04 | $6.80 | $3.20 |

**Key takeaway**: FLUX.1-schnell at $0.003/image is so cheap it's essentially free for video production. A 40-minute video costs about 50 cents.

### API Usage

```bash
# Requires REPLICATE_API_TOKEN
curl -s -X POST "https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions" \
  -H "Authorization: Bearer $REPLICATE_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "prompt": "MS Paint style, simple flat colors...",
      "num_inference_steps": 4,
      "guidance_scale": 1.0
    }
  }'
```

Python:
```python
import replicate
output = replicate.run(
    "black-forest-labs/flux-schnell",
    input={"prompt": prompt, "num_inference_steps": 4, "guidance_scale": 1.0}
)
# output is a list of image URLs
```

## HuggingFace Inference

**Free tier**: $0.10/month free credits
**PRO tier**: $2.00/month free credits ($9/mo subscription)

FLUX.1-dev via HF Inference: ~$0.0012/image (~10s @ $0.00012/s GPU compute)
Pay-as-you-go after credits exhausted — same rates as underlying provider, no HF markup.

FLUX.1-schnell requires accepting model terms on HuggingFace (gated: auto).
You must call `huggingface-cli login` with a token.

### API Usage

```python
from huggingface_hub import InferenceClient
client = InferenceClient(token="hf_...")

# FLUX.1-schnell (after accepting terms)
image = client.text_to_image(
    "MS Paint style, simple flat colors...",
    model="black-forest-labs/FLUX.1-schnell",
    num_inference_steps=4,
    guidance_scale=1.0
)
```

## Fal AI

FLUX models available but pricing not explicitly listed on their public page.
Typical FLUX pricing through HF Inference Providers routing: ~$0.002-$0.005/image.
GPU compute as low as $1.89/hr (H100) for custom deployments.

## Summary

| Provider | Cost/Image | Best For |
|----------|-----------|----------|
| Replicate | $0.003 | Simplest integration, no auth complexity |
| HuggingFace | ~$0.0012 | If already using HF ecosystem |
| Local (RTX 3090) | Free | If VRAM available (~4-6GB free needed) |

## Image Count for a 40-Min Video

With the Ken Burns approach (1 image per scene, zoom/pan animation):

| Scene Length | Scenes in 40 min | Images Needed | Cost (@$0.003) |
|---|---|---|---|
| 14 sec (current pace) | ~170 | 170 | **$0.51** |
| 30 sec (documentary) | ~80 | 80 | **$0.24** |
| 60 sec (in-depth) | ~40 | 40 | **$0.12** |
