# FLUX Workflow Notes for ComfyUI

## Workflow Structure

The text-to-image workflow at `workflows/flux_text_to_image.json` is a simple FLUX.1-schnell pipeline:

```
CheckpointLoaderSimple → CLIPTextEncode (pos+neg) → EmptyLatentImage → KSampler → VAEDecode → SaveImage
```

All parameter values use `{{PLACEHOLDER}}` syntax for the pipeline's `render_template()` function.

## Parameters

| Placeholder | Type | Default | Notes |
|-------------|------|---------|-------|
| `{{MODEL_NAME}}` | string | flux1-schnell-fp8.safetensors | Exact checkpoint filename |
| `{{POSITIVE_PROMPT}}` | string | (from scene) | Style prefix + scene visual prompt |
| `{{NEGATIVE_PROMPT}}` | string | blurry, low quality, deformed... | Global negative prompt |
| `{{WIDTH}}` | string (int) | 1280 | Output width in pixels |
| `{{HEIGHT}}` | string (int) | 720 | Output height in pixels |
| `{{SEED}}` | string (int) | random | Deterministic generation |
| `{{STEPS}}` | string (int) | 20 | Inference steps (FLUX schnell: 1-4) |
| `{{CFG}}` | string (float) | 1.0 | Classifier-free guidance scale. **CRITICAL: MUST be 1.0 for FLUX.1-schnell** (not 3.5!) |

## KSampler Settings for FLUX

FLUX.1-schnell expects specific sampler settings:

| Setting | Value | Reason |
|---------|-------|--------|
| **sampler_name** | `euler` | FLUX was trained with Euler |
| **scheduler** | `simple` | matches FLUX's training schedule |
| **cfg** | 1.0 | **CRITICAL**: FLUX.1-schnell uses guidance-free architecture. CFG=3.5+ produces solid-color garbage. MUST be 1.0. |
| **denoise** | 1.0 | Standard for text-to-image |

## Steps vs Quality Tradeoff

| Steps | Quality | Speed (normalvram, RTX 3090) | Speed (lowvram, RTX 3090) |
|-------|---------|------------------------------|----------------------------|
| 4 | Good (schnell mode) | ~3-5 seconds | ~2-5 minutes |
| 8 | Better | ~6-10 seconds | ~4-8 minutes |
| 20 | Best | ~15-25 seconds | ~10-20 minutes |

FLUX.1-schnell is designed for 1-4 steps. For draft testing, use `--steps 4`.

## Model Discovery

To list available checkpoints from ComfyUI after models are loaded:

```bash
curl -s http://127.0.0.1:8188/object_info | python -c "
import json,sys
d=json.load(sys.stdin)
cps = d['CheckpointLoaderSimple']['input']['required']['ckpt_name'][0]
print('Available:')
for c in cps[:10]:
    print(f'  {c}')
print(f'  ...({len(cps)} total)')
"
```

## Workflow Template Replacement

The pipeline replaces `{{PLACEHOLDER}}` values in the workflow JSON at runtime. Example after replacement:

```json
{
  "5_KSAMPLER": {
    "class_type": "KSampler",
    "inputs": {
      "seed": "12345",
      "steps": "20",
      "cfg": "3.5",
      "sampler_name": "euler",
      "scheduler": "simple",
      "denoise": 1.0,
      "model": ["1_LOAD_FLUX", 0],
      "positive": ["2_CLIP_TEXT_ENCODE", 0],
      "negative": ["3_CLIP_TEXT_ENCODE_NEG", 0],
      "latent_image": ["4_EMPTY_LATENT", 0]
    }
  }
}
```

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| ComfyUI returns empty reply | Models still loading or container restart needed | `docker restart yt-anim-comfyui` and wait 30s |
| "model does not exist" | Wrong filename or model not in checkpoints/ | Check exact filename: `docker exec yt-anim-comfyui ls models/checkpoints/` |
| "class_type not found" | Wrong workflow format (editor format instead of API) | Export ComfyUI workflow via "Save (API Format)" |
| VRAM OOM | Too many steps or too high resolution | Reduce steps (--steps 4) or resolution (960x540) |
