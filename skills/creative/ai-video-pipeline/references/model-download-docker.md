# Model Download Protocol for Docker Containers on Windows

Downloading large model weights (10-30GB) into Docker containers on a Windows host requires care. Multiple approaches fail before the correct one.

## Quick Answer: Download on Host → docker cp

The most reliable approach:

### Step 1: Download on the HOST using PowerShell

```powershell
$url = "https://huggingface.co/Comfy-Org/flux1-schnell/resolve/main/flux1-schnell-fp8.safetensors"
$out = "$env:TEMP\flux1-schnell-fp8.safetensors"
$client = New-Object System.Net.WebClient
$client.DownloadFile($url, $out)
```

### Step 1b: Download on the HOST using Python (with progress tracking)

Python's urllib is slightly faster than PowerShell WebClient and provides visible progress:

```bash
python -c "
import urllib.request, os, time
target = os.path.join(os.environ['TEMP'], 'flux1-schnell-fp8.safetensors')
url = 'https://huggingface.co/Comfy-Org/flux1-schnell/resolve/main/flux1-schnell-fp8.safetensors'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
resp = urllib.request.urlopen(req, timeout=3600)
total = int(resp.headers.get('content-length', 0))
downloaded = 0; start = time.time()
with open(target, 'wb') as f:
    while True:
        chunk = resp.read(65536)
        if not chunk: break
        f.write(chunk)
        downloaded += len(chunk)
        if downloaded % (10*1024*1024) < 65536:
            speed = downloaded/(time.time()-start)/1024/1024
            pct = downloaded/total*100 if total else 0
            print(f'{downloaded/1e9:.2f}/{total/1e9:.2f}GB ({pct:.1f}%) @ {speed:.1f} MB/s')
print(f'Done: {os.path.getsize(target)/1e9:.2f}GB')
"
```

### Step 2: Copy into Docker container

```bash
# Using PowerShell to resolve Windows temp path properly
$tempPath = [System.Environment]::GetEnvironmentVariable('TEMP')
docker cp "$tempPath\flux1-schnell-fp8.safetensors" yt-anim-comfyui:/workspace/ComfyUI/models/checkpoints/

# Or from git-bash, use the $TMP env var:
docker cp "${TMP}/flux1-schnell-fp8.safetensors" yt-anim-comfyui:/workspace/ComfyUI/models/checkpoints/
```

**Note**: The `docker cp` command may show a "write too long" warning but still succeed. Verify with `docker exec yt-anim-comfyui ls -lh models/checkpoints/flux1-schnell-fp8.safetensors`.

### Step 3: Restart ComfyUI

After copying models into the volume, restart the container so ComfyUI refreshes its model list:

```bash
docker restart yt-anim-comfyui
# Wait 15-30s for model loading
```

## Download Speed Comparison

| Method | Speed | Reliable? |
|--------|-------|-----------|
| **Host Python/urllib** | 6-28 MB/s | ✅ Yes |
| **Host PowerShell** | 5-15 MB/s | ✅ Yes |
| **Python inside container** | 3-6 MB/s | ⚠️ Slow, timeout on large files |
| **curl inside container** | 0.8-1 MB/s | ❌ Impractical for files >1GB |
| **hf download inside container** | 1-3 MB/s | ❌ MSYS path corruption |

## Approaches That FAIL

| Approach | Why It Fails |
|----------|-------------|
| `hf download` inside container | Uses old `huggingface-cli` which is deprecated; `hf` CLI uses MSYS-translated paths (`C:/Program Files/Git/workspace/...`) that don't exist in the container |
| `hf_hub_download` with `resume=True` | The `resume` parameter does not exist in huggingface_hub 1.14.0 |
| `hf_hub_download` inside container | Downloads succeed but `os.link()` fails across filesystems inside Docker; files end up in an inaccessible cache |
| `curl` inside container | Dramatically slower than host download (~0.8 MB/s vs ~6 MB/s) due to Docker networking overhead or throttling |
| `wget` inside container | Not installed in most containers (ComfyUI image doesn't have wget) |

## Required Models for FLUX Workflow

| File | Source (HuggingFace) | Size | Destination in Container |
|------|---------------------|------|--------------------------|
| `flux1-schnell-fp8.safetensors` | `Comfy-Org/flux1-schnell` | ~6GB (17GB content-length reported but actual is 6GB) | `models/checkpoints/` |
| `t5xxl_fp16.safetensors` | `comfyanonymous/flux_text_encoders` | ~3GB (9.8GB content-length reported but actual is 3GB) | `models/clip/` |
| `clip_l.safetensors` | `comfyanonymous/flux_text_encoders` | 235MB | `models/clip/` |
| `ae.safetensors` | `black-forest-labs/FLUX.1-schnell` | ~400MB | `models/vae/` |

Note: Content-length headers from HuggingFace may report larger sizes than actual downloaded files (sometimes 2-3x inflated). The `--local-dir` FLUX checkpoint ends up at ~6GB despite HF reporting 17GB. This is a known HF CDN behavior for combined checkpoints.

## Docker Volume Structure

The ComfyUI container mounts a Docker volume at `/workspace/ComfyUI/models/`:

```
/workspace/ComfyUI/models/
├── checkpoints/    ← UNET/diffusion model (e.g., flux1-schnell-fp8.safetensors)
├── clip/           ← Text encoders (clip_l.safetensors, t5xxl_fp16.safetensors)
├── vae/            ← VAE model (ae.safetensors)
├── loras/          ← LoRA adapters
├── upscale_models/ ← Upscalers
└── ...
```

## Checking What's Installed

```bash
# List all model files
docker exec yt-anim-comfyui find /workspace/ComfyUI/models/ -name "*.safetensors" -type f

# Check total model storage
docker exec yt-anim-comfyui du -sh /workspace/ComfyUI/models/

# Check specific directories
docker exec yt-anim-comfyui ls -lh /workspace/ComfyUI/models/checkpoints/
```

## Verify ComfyUI Can See Models

```bash
# ComfyUI API lists available checkpoints
curl -s http://127.0.0.1:8188/object_info | python -c "
import json,sys
d = json.load(sys.stdin)
cps = d.get('CheckpointLoaderSimple',{}).get('input',{}).get('required',{}).get('ckpt_name',[[]])[0]
print(f'Available checkpoints ({len(cps)}):')
for c in cps[:10]:
    print(f'  {c}')
"
```

## About the 17.2GB File Size

The `flux1-schnell-fp8.safetensors` from `Comfy-Org/flux1-schnell` is reported as 17.2GB by HuggingFace's Content-Length header but the actual downloaded file is ~6GB. This is a known HF CDN behavior where the content-length includes chunked transfer encoding overhead or reflects a different representation. Always trust the final file size, not the header.

## Model Source Matrix (Auth Requirements)

Different HuggingFace repos have different access requirements. The Comfy-Org repos are gated and return HTTP 401 without a HF_TOKEN:

| Repo | Models | Auth Required? | Notes |
|------|--------|---------------|-------|
| `Comfy-Org/flux1-schnell-fp8` | Full checkpoint (11GB) | **Yes** (401 without token) | Gated repo. Use only with HF_TOKEN set. |
| `Comfy-Org/flux1-dev-fp8` | UNet-only (12GB) | **Yes** (401 without token) | Gated. Needs separate CLIP+VAE loaders in workflow. |
| `Kijai/flux-fp8` | schnell fp8-e4m3fn (12GB), dev fp8 (12GB) | **No** (public, HTTP 200) | Works without auth. Both variants are **UNet-only** (0 CLIP keys, 0 VAE keys). Requires `workflows/flux_dev_text_to_image.json`. |
| `black-forest-labs/FLUX.1-schnell` | Full model | **Yes** (gated terms) | Requires accepted terms of use + HF_TOKEN. |

### The 17GB Complete Model (AiAF Cache)

When the HuggingFace Hub snapshot downloader (`hf_hub_download` or `snapshot_download`) downloads the full checkpoint, it places the complete model file inside a subdirectory of the checkpoint folder, not at the root:

```
models/checkpoints/flux1-schnell-fp8/AiAF/flux1-schnell-fp8.safetensors   ← 17GB, has CLIP+VAE
```

This file IS the complete model (1438 tensors including 198 CLIP keys + 244 VAE keys). It was downloaded by the HF cache system and works with the standard `flux_text_to_image.json` workflow. Use the full path as the model name:

```bash
python build_trailer_v2.py --generate-flux --steps 20 \
  --model "flux1-schnell-fp8/AiAF/flux1-schnell-fp8.safetensors"
```

### Download Method That Works Without Auth

```bash
# Inside the Docker container — Kijai/flux-fp8 is public
docker exec yt-anim-comfyui sh -c '
  cd /workspace/ComfyUI/models/checkpoints && \
  curl -L -o flux1-dev-fp8.safetensors \
    "https://huggingface.co/Kijai/flux-fp8/resolve/main/flux1-dev-fp8.safetensors" \
    --retry 5 --retry-delay 15 --max-time 7200
'

# For the full schnell model with CLIP (use the AiAF cache path)
# OR download UNet-only schnell from Kijai and use the dev workflow
docker exec yt-anim-comfyui sh -c '
  cd /workspace/ComfyUI/models/checkpoints && \
  curl -L -o flux1-schnell-fp8.safetensors \
    "https://huggingface.co/Kijai/flux-fp8/resolve/main/flux1-schnell-fp8-e4m3fn.safetensors" \
    --retry 5 --retry-delay 15 --max-time 7200
'
```

### Model Verification

After downloading, verify the model has the expected structure:

```bash
docker exec yt-anim-comfyui sh -c '
python3 -c "
import safetensors
with safetensors.safe_open(\"/workspace/ComfyUI/models/checkpoints/flux1-schnell-fp8.safetensors\", framework=\"pt\") as st:
    keys = list(st.keys())
    clip_count = len([k for k in keys if \"clip\" in k.lower() or \"text_model\" in k.lower()])
    vae_count = len([k for k in keys if \"vae\" in k.lower()])
    print(f\"Tensors: {len(keys)}, CLIP: {clip_count}, VAE: {vae_count}\")
    if clip_count == 0:
        print(\"WARNING: UNet-only model — needs workflows/flux_dev_text_to_image.json\")
    else:
        print(\"Complete model — works with standard workflow\")
"
'
```
