# interpolator.py — Working Frame Interpolation

`interpolator.py` (repo root) is a self-contained interpolation pipeline with 3 backends, designed
for the "keyframes at 0.5fps → smooth 12fps/24fps" workflow.

## Architecture

```
keyframe_dir/ (PNG sequence @ low fps)
    → interpolator.py --method opencv|rife|minterpolate
    → output video @ target fps
```

## Backend Comparison

### OpenCV (default, recommended for speed)
- Optical flow via `cv2.DISOpticalFlow`
- **1.6s** to interpolate 5 keyframes → 97 frames (1920×1080)
- Quality: good for MS Paint style (simple shapes, flat colors)
- No extra dependencies beyond `opencv-python`
- Default method in `interpolator.py`

### RIFE-NCNN (premium quality)
- Neural frame interpolation via NCNN Vulkan
- **23s** for same workload (5→97 frames)
- Quality: best — handles complex motion and detail
- Requires: `pip install rife-ncnn-vulkan`
- Slower but significantly better for detailed scenes

### ffmpeg minterpolate (fast, OK quality)
- Built-in ffmpeg filter
- Fastest setup (no extra deps)
- Quality: acceptable for simple content
- Issues: timeline/cut detection can cause dropped frames at transitions

## Key Commands

```bash
# OpenCV interpolation (keyframe dir → 12fps video)
python interpolator.py \
    --input outputs/myvideo/frames/ \
    --output outputs/myvideo/interpolated.mp4 \
    --method opencv \
    --source-fps 0.5 \
    --target-fps 12

# RIFE interpolation
python interpolator.py \
    --input outputs/myvideo/frames/ \
    --output outputs/myvideo/interpolated.mp4 \
    --method rife \
    --source-fps 0.5 \
    --target-fps 12

# ffmpeg minterpolate
python interpolator.py \
    --input outputs/myvideo/frames/ \
    --output outputs/myvideo/interpolated.mp4 \
    --method minterpolate \
    --source-fps 0.5 \
    --target-fps 12
```

## Interpolation + Ken Burns Integration

For best results, apply Ken Burns zoom to the KEYFRAMES BEFORE interpolation,
so the zoom is part of the interpolated motion:

```bash
# 1. Generate keyframes (FLUX)
# 2. Apply Ken Burns to keyframes → video at 0.5fps
# 3. Interpolate 0.5fps → 12fps
python interpolator.py --input kenburns_output/ --output smooth.mp4 \
    --method opencv --source-fps 0.5 --target-fps 12
# 4. Mux audio + SRT
```

## Validation (2026-06-10)

Test: 5 keyframes at 1920×1080, 0.5fps, interpolated to 12fps (97 frames total)

| Backend | Time | Output | Notes |
|---------|------|--------|-------|
| OpenCV DIS flow | 1.6s | smooth 12fps video | Clean, no artifacts on simple content |
| RIFE-NCNN Vulkan | 23s | smoother video | Better motion, 15x slower |
