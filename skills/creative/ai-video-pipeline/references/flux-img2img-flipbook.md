# FLUX Img2Img Flipbook Evolution

The flipbook technique creates visual continuity between shots within a scene. Instead of generating each shot independently (which produces disconnected images), each subsequent shot evolves from the previous one via FLUX img2img.

## Core Concept

```
Scene N:
  Shot 1: text-to-image (from prompt)
  Shot 2: img2img from Shot 1's output (denoise 0.6)
  Shot 3: img2img from Shot 2's output (denoise 0.6)
```

Each evolution preserves the character, composition, and lighting from the previous shot while incorporating the new prompt's action/camera change. Result: a natural flipbook feel where each frame flows into the next.

## Img2Img Workflow

File: `workflows/flux_dev_img2img.json`

```json
{
  "12_LOAD_IMAGE": {
    "class_type": "LoadImage",
    "inputs": { "image": "{{INPUT_IMAGE}}" }
  },
  "13_VAE_ENCODE": {
    "class_type": "VAEEncode",
    "inputs": {
      "pixels": ["12_LOAD_IMAGE", 0],
      "vae": ["1_LOAD_MODEL", 2]
    }
  },
  "9_KSAMPLER": {
    "class_type": "KSampler",
    "inputs": {
      "seed": "{{SEED}}",
      "steps": "{{STEPS}}",
      "cfg": 1.0,
      "denoise": "{{DENOISE}}",
      "model": ["1_LOAD_MODEL", 0],
      "positive": ["5_CLIP_TEXT_ENCODE", 0],
      "negative": ["6_CLIP_TEXT_ENCODE_NEG", 0],
      "latent_image": ["13_VAE_ENCODE", 0]
    }
  }
}
```

Key differences from text-to-image:
- **LoadImage** instead of EmptyLatentImage
- **VAEEncode** converts the loaded image to latent space
- **denoise: 0.6** — lower = more like the input, higher = more creative
- **KSampler.latent_image** connects to VAEEncode output

## Docker CP Pattern

ComfyUI's `LoadImage` reads from the container's `/workspace/ComfyUI/input/` directory by filename only. To feed a host-side image into img2img:

```python
def _copy_to_comfyui_input(self, src_path: Path) -> str:
    name = f"prev_{uuid.uuid4().hex[:8]}.png"
    subprocess.run(["docker", "cp", str(src_path.resolve()),
        f"yt-anim-comfyui:/workspace/ComfyUI/input/{name}"],
        capture_output=True, timeout=30)
    return name
```

## Sequential Seeds Per Scene

```python
base_seed = scene_index * 1000
for j, shot in enumerate(scene_shots):
    seed = base_seed + j
```

## Denoise Guide

| Denoise | Effect | Use Case |
|---------|--------|----------|
| 0.3 | Very subtle | Same angle, minor expression |
| 0.6 | Moderate | Camera shift, character moves |
| 0.8 | Significant | New action, new lighting |
| 1.0 | = text-to-image | No visual connection |
