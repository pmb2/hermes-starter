# v5 Flipbook Pipeline — Img2Img Visual Evolution

## Problem
v4 produced 108 static images at 1.4s each. User reported "too many images, flashing too quickly, they don't have relevance to one another." Shots within a scene were independently generated — no visual continuity between them.

## Solution: Img2Img Flipbook Evolution
Each shot visually flows from the previous one using FLUX img2img:

1. **Shot 1 per scene**: Standard text-to-image (`flux_dev_text_to_image.json`)
2. **Shot 2+**: img2img from previous shot's output (`flux_dev_img2img.json` with `denoise: 0.6`)
   - Previous image is `docker cp`'d into ComfyUI's `/workspace/ComfyUI/input/` 
   - `LoadImage` node reads it by filename
   - `VAEEncode` converts pixels to latent
   - `KSampler` at `denoise: 0.6` generates an evolution (60% new content, 40% preserved)
   - Result: same character, same location, camera/action evolves naturally

## Pacing
- 2 shots per scene (establishing + transition) instead of 3-5
- 2.5-4s per shot (longer = breathe)
- 15-25 scenes × 2 shots = 30-50 images total
- 80% static, 20% emphasis zoom (peak/hook openings only)

## Sequential Seeds Per Scene
Seeds are derived from scene index: `base_seed = scene_index * 1000`, then `seed = base_seed + shot_index`. This gives sequential seeds (1001, 1002, ...) within each scene, producing similar compositions from FLUX.

## Modular Pipeline Architecture
- `scripts/generate_script_v5.py` — Script with `emphasis` field
- `scripts/generate_tts_v5.py` — Standalone TTS
- `scripts/generate_flux_v5.py` — `FluxGenerator` class with `generate_t2i()` + `generate_i2i()`
- `scripts/assemble_v5.py` — Static default + emphasis zoom + text overlays
- `run_v5.py` — Orchestrator with git checkpoint between each stage

## Workflow
```yaml
workflows/flux_dev_img2img.json:
  1_LOAD_MODEL → model → 9_KSAMPLER
  4_DUAL_CLIP → 5_CLIP_TEXT_ENCODE → positive → 9_KSAMPLER
               → 6_CLIP_TEXT_ENCODE_NEG → negative → 9_KSAMPLER
  12_LOAD_IMAGE → image → 13_VAE_ENCODE → latent → 9_KSAMPLER
  9_KSAMPLER → 10_VAE_DECODE → 11_SAVE_IMAGE
```

Template variables: `{{MODEL_NAME}}`, `{{POSITIVE_PROMPT}}`, `{{NEGATIVE_PROMPT}}`, `{{WIDTH}}`, `{{HEIGHT}}`, `{{SEED}}`, `{{STEPS}}`, `{{CFG}}`, `{{DENOISE}}`, `{{INPUT_IMAGE}}`

## Legacy Script Format Compatibility

Old v3/v4 script JSONs (e.g., `sycamore-trailer-script.json`) may lack `index` keys on scene objects. The v5 pipeline's cause an error `KeyError: 'index'` at the FLUX generation step. Fix by adding indices before processing:

```python
for i, scene in enumerate(script["scenes"]):
    if "index" not in scene:
        scene["index"] = i + 1
```

Always add this compatibility shim when loading scripts from `outputs/` whose provenance is unknown.

## Script Subsampling for Pacing Control

When the user reports "too many images, flashing too quickly," the fix is to reduce shot count by keeping only **first + last shot of each scene**:

```python
for scene in script["scenes"]:
    shots = scene.get("shots", [])
    kept = []
    for j, shot in enumerate(shots):
        if j == 0 or j == len(shots) - 1:
            shot["emphasis"] = (scene.get("energy_level") in ("peak", "hook") and j == 0)
            kept.append(shot)
    scene["shots"] = kept
```

This transforms 108 shots → 60, shot duration from 1.4s → 2.5s. The establishing shot sets the scene; the transition shot advances the narrative. Used when the user wants "flipbook, storybook" pacing where each image breathes.

## Reversion Safety
Each pipeline stages commits via git. Revert any stage:
```bash
git log --oneline | head -5  # Find v5 commits
git revert <hash>             # Roll back one stage
```
