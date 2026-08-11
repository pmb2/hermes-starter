# Higgsfield Platform — Local + Cloud ComfyUI Video Generation

## Overview

The Higgsfield platform (`scripts/higgsfield.py`) transforms the local ComfyUI into a hybrid local+cloud generation service. It auto-routes between local GPU and fal.ai cloud based on VRAM pressure.

**Key file:** `scripts/higgsfield.py` (276 lines)
**Workflows dir:** `workflows/higgsfield/`
**Bootstrap:** `workflows/bootstrap.sh`

## Architecture

```
┌─ User Prompt ─────────────────────────────────────────────────┐
│  python scripts/higgsfield.py video --prompt "..." --workflow  │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │  should_route_to_    │
                   │  cloud()             │
                   │  (VRAM check)        │
                   └──────┬──────────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
    ┌─────────────────┐    ┌─────────────────────┐
    │ Local ComfyUI    │    │ fal.ai Cloud GPU     │
    │ (127.0.0.1:8188) │    │ (via fal-Connector)  │
    │ FLUX, SD, etc.   │    │ Wan2.1, AnimateDiff  │
    └─────────────────┘    └─────────────────────┘
```

## VRAM-Based Auto-Routing

- **Threshold**: 18GB used → routes to cloud
- `higgsfield.py vram` — check current VRAM usage
- `--cloud` / `--local` flags override auto-routing

## Modes

| Mode | Command | Description |
|------|---------|-------------|
| `video` | `higgsfield.py video -p "prompt" -w wan_t2v` | Text-to-video, image-to-video, AnimateDiff, Hunyuan |
| `character` | `higgsfield.py character -p "prompt" -r ref.jpg` | IP-Adapter + InstantID character consistency |
| `faceswap` | `higgsfield.py faceswap -i source.jpg` | Face swap via InstantID |
| `upscale` | `higgsfield.py upscale -i image.png` | Detail upscaling |
| `vram` | `higgsfield.py vram` | Check VRAM usage only |

## Workflow Templates

Workflow JSONs live in `workflows/higgsfield/` and must be in ComfyUI **API format** (export via Workflow → Save (API Format) or Export (API) in the UI).

Expected workflow files:
- `wan_text_to_video.json` — Text-to-video with Wan2.1
- `wan_image_to_video.json` — Image-to-video with Wan2.1
- `animatediff_video.json` — AnimateDiff video generation
- `hunyuan_video.json` — Hunyuan video generation
- `character_consistency.json` — IP-Adapter + InstantID
- `face_swap.json` — Face swap
- `upscale.json` — Image upscale

To generate workflows: Open ComfyUI → Build node graph → Save (API Format) → place in `workflows/higgsfield/`.

## Environment Variables

| Variable | Required | Source |
|----------|----------|--------|
| `FAL_KEY` | For cloud routing | fal.ai dashboard API key |
| `HF_TOKEN` | For auth-gated models | HuggingFace token |

Both are declared in `docker-compose.yml` as `${FAL_KEY:-}` / `${HF_TOKEN:-}` — they pass through from host env.

## Docker Setup

`workflows/bootstrap.sh` runs on container start and installs:
- `ComfyUI-fal-Connector` — Cloud GPU bridge to fal.ai
- `ComfyUI_InstantID` — Face identity preservation
- Python deps: `insightface`, `fal-client`

Add new custom nodes to `bootstrap.sh` as needed. Container must be restarted after bootstrap changes.

## Script API

```python
from scripts.higgsfield import generate_video, generate_character, face_swap, upscale

# Generate a video
result = generate_video("A cat walks across a keyboard", workflow="wan_t2v")

# Character-consistent generation
result = generate_character("A person in a grey hoodie", reference_image="ref.png")

# Check result
print(result["status"], result.get("outputs", []))
```

Each function returns `{"status": "completed"|"error"|"timeout", "outputs": [...], "error": "..."}`.

## Integration with Scene-Based Pipeline

When building a scene-based video that needs both images AND video clips:

1. **Static shots** — Use local FLUX (existing `generate_flux_v5.py` approach)
2. **Dynamic clips (money flow, cursor clicks, transitions)** — Use `higgsfield.py video --workflow wan_t2v` on fal.ai cloud
3. **Character shots** — Use `higgsfield.py character` with reference image for narrator consistency

The VRAM auto-router handles local-vs-cloud selection. For scenes where local GPU is handling FLUX images, video gen automatically routes to cloud.
