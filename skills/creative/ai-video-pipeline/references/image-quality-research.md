# Image Quality & Character Consistency Research

## Current Setup
- **Model:** FLUX.1-schnell fp8 via ComfyUI Docker
- **Steps:** 4 (schnell design) or 20 (quality mode)
- **VRAM:** ~8-10GB at 1024x1024 on RTX 3090
- **Problems:** Low quality at 4 steps, no character consistency, can't render text

## Upgrade Path

### FLUX.1-dev fp8
- **Source:** `Comfy-Org/flux1-dev-fp8` (HuggingFace, ~7GB, gated — needs HF_TOKEN)
- **Alternative:** `Kijai/flux-fp8` (public community conversion)
- **Quality:** HIGH — significantly better detail, lighting, composition
- **Steps:** 20-50 (vs 4 for schnell)
- **VRAM:** ~12-16GB at 1024x1024 in fp8
- **Speed:** ~45-90s per image on RTX 3090
- **Text rendering:** Still unreliable — use Pillow overlay instead (see references/text-overlay.md)

### IP-Adapter for Character Consistency
- **ComfyUI Node:** `ComfyUI_IPAdapter_plus` by cubiq (6k stars, already installed in container)
- **Workflow:** `workflows/flux_ip_adapter.json`
- **How it works:** Reference image conditions generation via cross-attention. Provide one character reference PNG, all generations use that visual as a guide.
- **VRAM:** +2-3GB over base model
- **Consistency:** Good for style/appearance, less reliable for exact face identity
- **Setup:** Need to download IP-Adapter model weights + CLIP vision model

### IP-Adapter Model Setup
```bash
# Inside ComfyUI container or via docker exec:
# 1. Create ipadapter directory
mkdir -p /workspace/ComfyUI/models/ipadapter
# 2. Download IP-Adapter FLUX model (via huggingface_hub or curl)
curl -L -o /workspace/ComfyUI/models/ipadapter/ip-adapter-flux-dev.safetensors \
  https://huggingface.co/h94/IP-Adapter-Flux.1-dev/resolve/main/ip-adapter-flux-dev.safetensors
# 3. Download CLIP vision model
curl -L -o /workspace/ComfyUI/models/clip_vision/model.safetensors \
  [url needed]
```

### Character Reference Images
- Tool: `scripts/generate_character_ref.py`
- Creates reference PNG at `assets/characters/<name>-reference.png`
- Must be copied to ComfyUI input directory: `docker cp <file> <container>:/workspace/ComfyUI/input/`

## VRAM Management

On Windows WDDM with RTX 3090 (24GB), these processes hog GPU VRAM:
- MS Edge WebView2 (msedgewebview2.exe) — 1-3GB
- Discord (Discord.exe) — 500MB-1GB
- Chrome/Chromium — 1-4GB
- ChatGPT Desktop — 500MB-1GB
- Codex Desktop — 500MB-1GB
- RustDesk (rustdesk.exe) — 200-500MB
- PhoneExperienceHost — 200-500MB
- VLC — 200-500MB

**Kill command** (from git-bash/MSYS, use //F not /F):
```bash
taskkill //F //IM msedgewebview2.exe
taskkill //F //IM rustdesk.exe
taskkill //F //IM vlc.exe
taskkill //F //IM PhoneExperienceHost.exe
```

**Before running:** check VRAM: `nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader`
**Target:** >17GB free for `--normalvram`. If <10GB free, switch to `--lowvram` (2-5 min/frame) or use Replicate API.
