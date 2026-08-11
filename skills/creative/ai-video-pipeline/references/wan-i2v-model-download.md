# Wan2.1 I2V Model Download & Setup

## Required Models (for local I2V via ComfyUI WanVideoWrapper)

All models from `Kijai/WanVideo_comfy` on HuggingFace:

| File | Size | Destination in ComfyUI | Purpose |
|------|------|----------------------|---------|
| `Wan2_1-I2V-14B-480P_fp8_e4m3fn.safetensors` | ~17GB | `diffusion_models/` | I2V diffusion model (fp8, fits RTX 3090 24GB) |
| `umt5-xxl-enc-bf16.safetensors` | 10.5GB | `text_encoders/` | T5 text encoder for prompt conditioning |
| `Wan2_1_VAE_bf16.safetensors` | 243MB | `vae/` | VAE for decoding latents to frames |

## Download Methods

### Method 1: `hf download` CLI (recommended)
```bash
docker exec yt-anim-comfyui bash -c '
export HF_TOKEN="${HF_TOKEN:-}"
hf download Kijai/WanVideo_comfy Wan2_1_VAE_bf16.safetensors \
  --local-dir /workspace/ComfyUI/models/vae

hf download Kijai/WanVideo_comfy umt5-xxl-enc-bf16.safetensors \
  --local-dir /workspace/ComfyUI/models/text_encoders

hf download Kijai/WanVideo_comfy Wan2_1-I2V-14B-480P_fp8_e4m3fn.safetensors \
  --local-dir /workspace/ComfyUI/models/diffusion_models
'
```

### Method 2: `curl` (more reliable for large files, shows progress)
```bash
HF_BASE="https://huggingface.co/Kijai/WanVideo_comfy/resolve/main"
docker exec yt-anim-comfyui bash -c "
curl -L -o /workspace/ComfyUI/models/vae/Wan2_1_VAE_bf16.safetensors \
  '$HF_BASE/Wan2_1_VAE_bf16.safetensors'
curl -L -o /workspace/ComfyUI/models/text_encoders/umt5-xxl-enc-bf16.safetensors \
  '$HF_BASE/umt5-xxl-enc-bf16.safetensors'
curl -L -o /workspace/ComfyUI/models/diffusion_models/Wan2_1-I2V-14B-480P_fp8_e4m3fn.safetensors \
  '$HF_BASE/Wan2_1-I2V-14B-480P_fp8_e4m3fn.safetensors'
"
```

### Download Speed / Time Estimates
- VAE (243MB): ~15s at 13MB/s
- T5 encoder (10.5GB): ~13 min at 13MB/s
- I2V model (17GB): ~22 min at 13MB/s

## I2V ComfyUI Workflow Structure

Key nodes (API format, use `WanVideoWrapper` custom nodes from `ComfyUI-WanVideoWrapper`):

1. **LoadImage** — load the FLUX-generated still image
2. **LoadWanVideoT5TextEncoder** — T5 encoder (`umt5-xxl-enc-bf16.safetensors`, dtype=bf16)
3. **WanVideoVAELoader** — VAE (`wanvideo/Wan2_1_VAE_bf16.safetensors`, dtype=bf16)
4. **WanVideoModelLoader** — I2V model (`Wan2_1-I2V-14B-480P_fp8_e4m3fn.safetensors`, dtype=fp16, attention=sdpa)
5. **CLIPVisionLoader** + **WanVideoClipVisionEncode** — CLIP vision conditioning (requires `clip_vision_h.safetensors` — already in ComfyUI)
6. **WanVideoTextEncode** — encode prompt + negative prompt via T5
7. **WanVideoImageToVideoEncode** — encode image for I2V (width=832, height=480, num_frames=81, noise_multiplier=0.03)
8. **WanVideoVRAMManagement** — autodetect VRAM settings
9. **WanVideoSampler** — sample (4 steps, cfg=1.0, dpm++_sde scheduler, euler sampler, fixed seed)
10. **WanVideoDecode** — decode latents to frames (no tiling for speed)
11. **VHS_VideoCombine** — combine to MP4 (frame_rate=16, format=video/h264-mp4)

## Pipeline Integration

The `scripts/pipeline_utils.py` `generate_i2v_video()` function:
1. Uploads the FLUX image to ComfyUI input dir
2. Fills the workflow template with model name, prompt, seed, and params
3. Submits via `requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": wf})`
4. Downloads the generated video from ComfyUI output directory via `docker cp`
5. Returns path to the saved MP4

## VRAM Considerations

- 14B fp8 model + T5 encoder + VAE + activations = ~22GB on RTX 3090 24GB
- In WDDM mode (Windows Docker), VRAM allocation is less controllable
- The `WanVideoBlockSwap` node can offload transformer blocks to CPU if needed
- If VRAM OOM occurs, reduce to 20-24 frames or lower resolution (624x480)
- The 1.3B I2V variant would fit easily but is NOT available in the Kijai repo — the smallest I2V model is 14B fp8

## WanVideoWrapper Custom Nodes

The Docker image includes `ComfyUI-WanVideoWrapper` with these I2V-relevant nodes:
- `Sha` (sic): WanVideoModelLoader, WanVideoVAELoader, WanVideoTextEncode
- WanVideoImageToVideoEncode, WanVideoSampler, WanVideoDecode
- WanVideoClipVisionEncode, WanVideoVRAMManagement, WanVideoBlockSwap
- WanVideoLoraSelect, WanVideoTorchCompileSettings

Example workflows in container at:
`/workspace/ComfyUI/custom_nodes/ComfyUI-WanVideoWrapper/example_workflows/`

Key references: `wanvideo_2_1_14B_I2V_example_03.json` (14B I2V), `wanvideo_1_3B_EchoShot_example.json` (1.3B T2V).
