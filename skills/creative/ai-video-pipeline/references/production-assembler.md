# Production Assembler — No Ken Burns, Crossfade-Only Assembly

## When to Use

After FLUX images are generated for all scenes, use `production_assembler.py` to produce the final video with:
- **Crossfade transitions** between images within each scene (0.4s fade)
- **Crossfade transitions** between scenes (concatenated seamlessly)
- **No Ken Burns** — this is explicitly rejected by the user
- **No zoom/pan** — identical constraint
- **No slideshow effects** — professional cuts and dissolves only

This is the fallback when I2V video generation is unavailable (fal.ai balance exhausted, 14B model not downloaded, or VRAM constraints). It produces a 124s, 23MB video from 108 images across 30 scenes.

## Architecture

```
scripts/production_assembler.py
  ├── build_scene(scene_idx, images[], duration, output_dir)
  │   Each image gets (per_image + TRANSITION_DURATION) display time
  │   First image: fade out at end
  │   Middle images: fade in at start + fade out at end
  │   Last image: fade in at start only
  │   Single image: no transitions (just static)
  │   Output: scene clip via ffmpeg concat demuxer
  │
  ├── main(script_path, audio_path)
  │   1. Load script.json → get 30 scenes with timings
  │   2. For each scene: build_scene() with 3-5 images
  │   3. Concat all scene clips via demuxer → visuals.mp4
  │   4. Mux with TTS audio → sycamore-v2-prod.mp4
  └── Run: `python scripts/production_assembler.py`
```

## Key Parameters

```python
TRANSITION_DURATION = 0.4  # seconds for crossfade between images
per_image = available_time / num_images  # even split of scene time
```

## Image Timing Calculation

Each scene has `duration` seconds of TTS narration. If a scene has N images:
- Total transition time: (N-1) × 0.4s (the overlaps between images)
- Available display time: duration - total_transitions
- Per image display time: available_time / N
- Each middle image gets: per_image + 0.4s (overlap with neighbor)
- First/last image: per_image (fade out only / fade in only)

## FFmpeg Commands

**Single image with fade out:**
```
ffmpeg -y -loop 1 -i img.png -c:v libx264 -t 3.0s \
  -vf "fade=t=out:st=2.6:d=0.4" -pix_fmt yuv420p -preset fast -crf 18 clip.mp4
```

**Middle image with fade in + fade out:**
```
ffmpeg -y -loop 1 -i img.png -c:v libx264 -t 3.4s \
  -vf "fade=t=in:d=0.4,fade=t=out:st=3.0:d=0.4" -pix_fmt yuv420p -preset fast -crf 18 clip.mp4
```

**Scene concat (demuxer, NOT xfade):**
```
file 'clip1.mp4'
file 'clip2.mp4'
file 'clip3.mp4'
→ ffmpeg -y -f concat -safe 0 -i list.txt -c:v libx264 -preset fast -crf 18 scene.mp4
```

## Dependencies

- `pipeline_utils.estimate_scene_timings()` — computes per-scene timing from TTS duration
- `scene_assembler.get_clip_duration()` — ffprobe wrapper
- ffmpeg with libx264 support
- Each scene requires 3-5 FLUX images at 1920×1080

## Pitfalls

- **Duration mismatch**: If the sum of per-image display times doesn't match the scene duration, the assembler pads with a freeze frame on the last image. This is acceptable for ±0.5s errors but visible if >1s.
- **No audio per scene**: The assembler works on visuals-only clips. Audio is muxed globally at the final step, not per-scene. This ensures smooth audio without cuts.
- **No emphasis shots**: Unlike v5 assembly, the production assembler doesn't distinguish emphasis from normal shots. All images get equal treatment. Add text overlays in post-processing if emphasis is needed.
- **concat demuxer**: Always use `-f concat -safe 0 -i list.txt`. Never use `xfade` filter chains — the gyan.dev FFmpeg on Windows crashes on any chain >3 clips (exit code 4294967274).
