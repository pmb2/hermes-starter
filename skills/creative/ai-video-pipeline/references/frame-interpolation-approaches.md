# Frame Interpolation Approaches for "On the Twos" Animation

Goal: Generate 12 images per second of video (animation "on the twos" at 24fps)
without generating every frame via FLUX.

## The Keyframe Strategy

Instead of 1,440 FLUX images for a 2-minute video, generate keyframes at
a lower rate and interpolate the in-between frames:

| Keyframe Rate | Keyframes (2 min) | Interpolated Frames | FLUX Time (15s each) | Interpolation Time |
|---------------|-------------------|--------------------|---------------------|-------------------|
| Every 2 sec (0.5fps) | 60 | 1,380 | 15 min | ~5 min |
| Every 5 sec (0.2fps) | 24 | 1,416 | 6 min | ~5 min |
| Every scene (~14 sec) | 9 | 1,431 | 2 min | ~5 min |

The sweet spot is probably 60 keyframes (1 every 2 seconds) — 15 minutes
of FLUX generation + 5 minutes of interpolation = 20 minutes total.
Down from 6 hours.

## Interpolation Options

### RIFE (Recommended — FOSS, best quality/speed tradeoff)
- GitHub: https://github.com/hzwer/ECCV2022-RIFE
- Requires: `pip install torch torchvision opencv-python` + pre-trained model weights
- Pipeline: `python inference_video.py --video input.mp4 --output output.mp4 --exp=2`
    - `--exp=2` doubles the frame rate (24fps → 48fps → subsample to keep 24fps with in-betweens)
- Speed: ~2-5 min per minute of video on RTX 3090
- Quality: Excellent for simple animation (MS Paint style). Struggles with complex motion.
- Integration: Can be called as a subprocess from the pipeline after frame generation

### FILM (Google Research)
- GitHub: https://github.com/google-research/frame-interpolation
- Higher quality than RIFE but slower (TensorFlow, ~5-10 min per min of video)
- Better for scenes with large motion or complex backgrounds
- Downside: heavier dependency (TF ecosystem)

### DAIN (Depth-Aware)
- GitHub: https://github.com/baowenbo/DAIN
- Slower than RIFE, similar quality
- Depth-aware — better for scenes with parallax motion
- Not recommended as first choice

## Implementation Plan (to be built)

1. After FLUX generates N keyframes (e.g., 60 for 2 min), save them as numbered PNGs
2. Run RIFE interpolation to generate the missing frames:
   ```
   python rife.py --input frames/ --output frames_full/ --exp 24
   ```
   (where `--exp 24` means interpolate each gap to 24 output frames)
3. Assemble the full frame sequence into a video with ffmpeg
4. Apply Ken Burns zoom per scene BEFORE interpolation (so zoom is smooth)
5. Mux audio and SRT as before

## Alternative: Video Generation Models

Instead of FLUX + interpolation, could use end-to-end video generation:
- **Stable Video Diffusion (SVD)** — short clips (2-4 sec), not great for 2+ min
- **AnimateDiff** — generates consistent animations but style-limited
- **LTX Video** — 240fps capable, but incoherent generation (the operator rejected this)
- **Wan 2.1** — video generation, could generate scene transitions

**Verdict:** FLUX keyframes + RIFE interpolation is the best path for now.
Generates style-consistent frames (FLUX) with smooth motion (RIFE).
