# IP-Adapter Setup for FLUX Character Consistency

## Overview

IP-Adapter provides character/visual consistency across multiple FLUX generations by injecting a reference image's visual features into each new prompt. For the v4 dense pipeline (100-180 shots), this means the protagonist looks the same in every scene.

## Two Approaches — Which Actually Works

### ❌ Standard IP-Adapter Nodes (DOES NOT WORK with FLUX)

The standard `IPAdapterModelLoader` + `IPAdapter` nodes (from `ComfyUI_IPAdapter_plus` by cubiq) CANNOT load FLUX-specific IP-Adapter models. Attempting to load the XLabs `ip_adapter.safetensors` (1GB) yields:

```
Exception: invalid IPAdapter model /workspace/ComfyUI/models/ipadapter/ip_adapter.safetensors
```

**Why**: cubiq/ComfyUI_IPAdapter_plus is in **maintenance mode** (last commit ~2025, 200 commits total, no updates in over a year). The `IPAdapterUnifiedLoader` preset options are limited to SD1.5/SDXL variants — there is NO FLUX preset. The `IPAdapterModelLoader` node (which bypasses the UnifiedLoader and loads any .safetensors from the ipadapter/ directory) also fails because the underlying attention patching code (`CrossAttentionPatch.py`, `IPAdapterPlus.py`) only handles SD1.5/SDXL cross-attention dimensions. FLUX uses a fundamentally different DiT architecture with double-block joint attention, which the standard IP-Adapter code cannot inject into.

To verify: check the installed version's capabilities
```bash
# List the presets available in IPAdapterUnifiedLoader
grep 'preset' /workspace/ComfyUI/custom_nodes/ComfyUI_IPAdapter_plus/IPAdapterPlus.py
# Should show only SD1.5/SDXL presets — no FLUX
# Also check git status for FLUX support
cd /workspace/ComfyUI/custom_nodes/ComfyUI_IPAdapter_plus && git log --oneline -3
# Last commit from ~2025 — repo is in maintenance mode
```

### ✅ XLabs-Specific Nodes (REQUIRED for FLUX)

FLUX IP-Adapter requires **two custom nodes not in the base ComfyUI install**:

| Node | Purpose | Status |
|------|---------|--------|
| `LoadFluxIPAdapter` | Loads IP-Adapter model + CLIP Vision encoder | ❌ Must install XLabs x-flux-comfyui |
| `ApplyFluxIPAdapter` | Injects IP-Adapter conditioning into FLUX UNet | ❌ Must install XLabs x-flux-comfyui |

Additional XLabs nodes needed: `XlabsSampler` (FLUX-specific sampler that handles the IP-Adapter conditioning).

Available without install: `UNETLoader`, `DualCLIPLoader`, `CLIPTextEncodeFlux`.

## XLabs Repo Status

The actual repo is `XLabs-AI/x-flux-comfyui` (NOT `xlabs-ip-adapter` — that repo doesn't exist). **Caveat**: this repo's last commit was 2 years ago and it's in maintenance mode. Verify compatibility with your ComfyUI version before installing. GitHub clone from Docker may fail with "could not read Username for 'https://github.com'" — fall back to downloading the zip:

```bash
# Option A: git clone
docker exec yt-anim-comfyui bash -c "cd //workspace/ComfyUI/custom_nodes && \
  git clone https://github.com/XLabs-AI/x-flux-comfyui.git xlabs-ip-adapter && \
  pip install -r xlabs-ip-adapter/requirements.txt"
docker restart yt-anim-comfyui

# Option B (fallback if git asks for auth on public repo):
docker exec yt-anim-comfyui bash -c "curl -L https://github.com/XLabs-AI/x-flux-comfyui/archive/refs/heads/main.zip -o /tmp/xlabs.zip && \
  unzip /tmp/xlabs.zip -d //workspace/ComfyUI/custom_nodes/ && \
  mv //workspace/ComfyUI/custom_nodes/x-flux-comfyui-main //workspace/ComfyUI/custom_nodes/xlabs-ip-adapter && \
  pip install -r /workspace/ComfyUI/custom_nodes/xlabs-ip-adapter/requirements.txt"
docker restart yt-anim-comfyui
```
```

Verify installation:
```python
# After restart, check that nodes appear
curl -s http://127.0.0.1:8188/object_info | python -c "import sys,json; d=json.load(sys.stdin); [print(n) for n in sorted(d.keys()) if 'LoadFlux' in n or 'ApplyFlux' in n or 'Xlabs' in n]"
```

## Model Files Required

### IP-Adapter Model (~1GB)

| Source | Filename | Size | Auth Required | Works? |
|--------|----------|------|---------------|--------|
| `XLabs-AI/flux-ip-adapter-v2` | `ip_adapter.safetensors` | 1008 MB | ❌ No | ✅ Used in this session |
| `ostris/ip-adapter-flux` | `ip-adapter_flux_ip_adapter.safetensors` | ~460 MB | ✅ Yes (401 without auth) | Untested |
| `openai/clip-vit-large-patch14` | `model.safetensors` | 1631 MB | ⚠️ Requires HF_TOKEN (auth-gated) | May return stub files without auth |
| `laion/CLIP-ViT-H-14-laion2B-s32B-b79K` | `open_clip_pytorch_model.safetensors` | ~2.4GB | ✅ Open access | 404/not found at time of testing |
| `google/siglip-so400m-patch14-384` | `model.safetensors` | ~2.4GB | ✅ Open access | Alternative for XLabs workflows |

For auth-gated repos like OpenAI's CLIP, login via huggingface-cli first, then download:
```bash
docker exec yt-anim-comfyui huggingface-cli login --token YOUR_HF_TOKEN
docker exec yt-anim-comfyui python3 -c "
from huggingface_hub import hf_hub_download
import os
path = hf_hub_download(
    repo_id='openai/clip-vit-large-patch14',
    filename='model.safetensors',
    local_dir='/workspace/ComfyUI/models/clip-vit-large-patch14',
    local_dir_use_symlinks=False
)
print(f'Downloaded: {os.path.getsize(path)/1024/1024:.1f} MB')
"
```

**If auth fails**: Use the open-access SigLIP model (`google/siglip-so400m-patch14-384`) instead. Update the workflow JSON's `clip_name` widget accordingly.
```

### CLIP Vision Model (~1.6GB)

The XLabs workflow expects CLIP Vision at `clip-vit-large-patch14/model.safetensors`. Download one of these:

| Source | Filename | Size | Notes |
|--------|----------|------|-------|
| `openai/clip-vit-large-patch14` | `model.safetensors` | 1631 MB | ✅ Downloaded this session |
| `openai/clip-vit-large-patch14` | `model.safetensors` | 1631 MB | ⚠️ Requires HF_TOKEN (auth-gated) | May return stub files without auth |
| `laion/CLIP-ViT-H-14-laion2B-s32B-b79K` | `open_clip_pytorch_model.safetensors` | ~2.4GB | ✅ Open access | 404/not found at time of testing |
| `google/siglip-so400m-patch14-384` | `model.safetensors` | ~2.4GB | ✅ Open access | Alternative for XLabs workflows |

For auth-gated repos like OpenAI's CLIP, login via huggingface-cli first, then download:
```bash
docker exec yt-anim-comfyui huggingface-cli login --token YOUR_HF_TOKEN
docker exec yt-anim-comfyui python3 -c "
from huggingface_hub import hf_hub_download
import os
path = hf_hub_download(
    repo_id='openai/clip-vit-large-patch14',
    filename='model.safetensors',
    local_dir='/workspace/ComfyUI/models/clip-vit-large-patch14',
    local_dir_use_symlinks=False
)
print(f'Downloaded: {os.path.getsize(path)/1024/1024:.1f} MB')
"
```

**If auth fails**: Use the open-access SigLIP model (`google/siglip-so400m-patch14-384`) instead. Update the workflow JSON's `clip_name` widget accordingly.
```

### Which CLIP Name Does the Workflow Use?

The XLabs `ip_adapter_workflow.json` has `LoadFluxIPAdapter` with widget values:
```
['ip_adapter.safetensors', 'clip-vit-large-patch14/model.safetensors', 'CPU']
```

So the CLIP model path must be `clip-vit-large-patch14/model.safetensors` relative to ComfyUI's models directory.

## Workflow: Hybrid Approach (Recommended)

The XLabs workflow separately loads UNET + CLIP + VAE. But our working model (`flux1-schnell-fp8/AiAF/flux1-schnell-fp8.safetensors`) has everything baked in. The ideal hybrid:

```yaml
1_CHECKPOINT_LOADER: CheckpointLoaderSimple → MODEL, CLIP, VAE  (uses AiAF checkpoint)
9_LOAD_FLUX_IPADAPTER: LoadFluxIPAdapter → IPADAPTER              (XLabs node)
10_APPLY_IPADAPTER: ApplyFluxIPAdapter → MODEL                    (XLabs node, takes MODEL from checkpoint + IPADAPTER + reference IMAGE)
5_KSAMPLER: KSampler                                               (standard sampler)
```

BUT — this requires the XLabs custom nodes (`LoadFluxIPAdapter`, `ApplyFluxIPAdapter`) to be installed. Without them, the standard IP-Adapter nodes can't load FLUX models.

### Fallback: Prompt Engineering for Consistency

If XLabs nodes can't be installed, achieve partial consistency by:
1. Using the character description from script JSON in EVERY prompt
2. Fixing a seed range for each character's scenes
3. Including style guide prefix consistently
4. Post-selecting scenes where the character looks most consistent

## Character Reference Image Generation

```bash
# Generate a 1024x1024 character reference using the standard text-to-image workflow
docker cp <local_ref_image> yt-anim-comfyui://workspace/ComfyUI/input/character_ref.png
```

The reference should be:
- 1024x1024 (square, matches FLUX training)
- Simple background, character centered
- Full-body or 3/4 shot, neutral expression
- Same style as target scenes (MS Paint flat colors)

## File Locations after Setup

```
/workspace/ComfyUI/
├── models/
│   ├── ipadapter/
│   │   └── ip_adapter.safetensors          (1008 MB — XLabs, installed)
│   ├── clip-vit-large-patch14/
│   │   └── model.safetensors               (1631 MB — OpenAI CLIP, installed)
│   └── checkpoints/
│       ├── flux1-schnell-fp8/AiAF/
│       │   └── flux1-schnell-fp8.safetensors (17GB — working model)
│       └── flux1-schnell-fp8.safetensors     (11GB — UNet-only alternate)
├── custom_nodes/
│   └── xlabs-ip-adapter/                    (NEEDS INSTALL — git clone + pip)
└── input/
    └── character_ref.png                   (your reference image)
```

## Pitfalls

- **Standard IPAdapter nodes can't load FLUX models** — even when the model file appears in the node's dropdown. You must use XLabs-specific nodes.
- **huggingface_hub not wget/curl** — Auth-gated HF repos (ostris, h94) return 15-29 byte error pages via wget/curl. Use `hf_hub_download()` Python API instead.
- **CLIP Vision path matters** — The XLabs workflow expects `clip-vit-large-patch14/model.safetensors`, not a bare filename in clip_vision/.
- **Docker path escaping** — MSYS bash translates `/workspace` to `C:/Program Files/Git/workspace`. Use `//workspace` (double slash) or pipe commands via `python3 -c` to avoid path mangling.
