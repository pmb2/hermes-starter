# Wan2.1 I2V Local Pipeline

## Overview

Full local video generation pipeline using ComfyUI's WanVideoWrapper nodes + RTX 3090.
Replaces fal.ai cloud calls (which require balance) with local GPU inference.

## Model Files Required

Download all into the `comfyui-models` Docker volume:

| File | Size | Destination |
|------|------|-------------|
| `Wan2_1_VAE_bf16.safetensors` | 243MB | `vae/` |
| `umt5-xxl-enc-bf16.safetensors` | 11GB | `text_encoders/` |
| `Wan2_1-I2V-1_3B_fp16.safetensors` | 3GB | `diffusion_models/` |
| `clip_vision_h.safetensors` | 2GB | `clip_vision/` |

Source: `https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/<filename>`

## Workflow Node Architecture (API Format)

The I2V workflow at `workflows/wan_i2v_1_3B.json` uses 12 nodes:

```
LoadImage (input FLUX image)
  ├──→ WanVideoClipVisionEncode (CLIP vision conditioning)
  └──→ WanVideoImageToVideoEncode (I2V encoding)
       ├── WanVideoModelLoader (I2V model)
       ├── WanVideoVAELoader (VAE)
       ├── WanVideoTextEncode (prompt conditioning)
       ├── LoadWanVideoT5TextEncoder (T5 encoder)
       └── WanVideoSampler (dpm++_sde / euler)
            └── WanVideoDecode
                 └── VHS_VideoCombine (output MP4)
```

## Template Variables

The workflow JSON uses these template variables:
- `{{INPUT_IMAGE}}` — uploaded image filename
- `{{MODEL_NAME}}` — model in `diffusion_models/`
- `{{POSITIVE_PROMPT}}` — video description
- `{{WIDTH}}`, `{{HEIGHT}}` — output resolution (832x480 for 1.3B)
- `{{NUM_FRAMES}}` — 81 frames = ~5s at 16fps
- `{{STEPS}}`, `{{CFG}}`, `{{SEED}}` — sampler params

## ComfyUI Submission

The `pipeline_utils.py` flow:

1. Upload input image via `POST /upload/image` (multipart form)
2. Replace template vars in workflow JSON
3. Submit via `POST /prompt` with `{"prompt": workflow}`
4. Poll `GET /history/{prompt_id}` until completed
5. Retrieve video: `docker cp yt-anim-comfyui:/workspace/ComfyUI/output/<filename> <dest>`

Video files are found by searching `/workspace/ComfyUI/output/` for the filename prefix.

## Resolution Limits (RTX 3090 24GB)

| Model | Max Resolution | Max Frames | VRAM |
|-------|---------------|------------|------|
| 1.3B I2V | 832x480 | 81 | ~6-8GB |
| 1.3B I2V | 640x360 | 161 | ~10GB |
| 14B I2V fp8 | 832x480 | 81 | ~18-20GB (tight) |
| 14B I2V fp8 | 640x360 | 81 | ~14GB |

## No Ken Burns

The user explicitly rejects zoom-pan effects as "cheap slideshow quality."
All scene transitions must use actual generated video clips with speed ramping.
