# v4 Dense Scene Pipeline — Timestamp-Aware Video Assembly

## Overview

v4 is a denser, faster-paced evolution of the ai-video-pipeline. Instead of 8-15 scenes × 2-4 shots, v4 produces **25-35 scenes × 4-6 shots each** = 100-180 images for a 5-minute video, with **2-5s per shot**.

The key innovation is **timestamp-based image naming**: each generated image's filename encodes its exact start and end position on the video timeline, so the assembly step reads the filename to know precisely when to show each image and for how long.

## When to Use v4

- User says "the images are too static" or "not enough visual variety"
- User wants to turn a full script into a fast-paced trailer
- User explicitly requests timestamp-based naming for frame-accurate timing
- v3's 2-4 shots per scene isn't enough visual density (29 shots for 5min = ~10s/shot)

## Timestamp Naming Convention

```
s{scene:03d}_kf{shot:02d}_{start_ms:05d}_{end_ms:05d}.png
```

| Example File | Meaning |
|-------------|---------|
| `s001_kf01_00000_04000.png` | Scene 1, Shot 1 — plays from 0.00s to 4.00s |
| `s001_kf02_04000_08000.png` | Scene 1, Shot 2 — plays from 4.00s to 8.00s |
| `s002_kf01_15000_17500.png` | Scene 2, Shot 1 — plays from 15.00s to 17.50s |

- `start_ms`/`end_ms` are integer milliseconds (5 digits, zero-padded)
- These are extracted from the LLM-generated `timestamp_start`/`timestamp_end` fields per shot
- The assembly regex: `r"_(\d{5})_(\d{5})\."`
- Fallback: if timestamps aren't in the filename (legacy v3 images), fall back to `audio_dur / scene_count * shot_weight`

## Architecture vs v3

| Aspect | v3 | v4 |
|--------|----|----|
| Scenes | 8-15 | **25-35** |
| Shots per scene | 2-4 | **4-6** |
| Shot duration | 6-10s | **2-5s** |
| Total images (5min) | ~29 | **100-180** |
| Seconds per shot | ~10s | **~2.8s** |
| Timing source | Calculated from audio ÷ scenes | **Read from filename timestamps** |
| Ken Burns variety | Fixed zoom-in | **Emphasis-based: 20% zoom, 80% static** |
| Transition variety | fade only | **Energy-based: hook/peak/build/release→fade** |
| Scene metadata | narration + shots | + `energy_level` + `visual_direction` |

## Scene Data Model

```python
@dataclass
class Shot:
    prompt: str
    shot_description: str = ""
    duration_hint_sec: float = 3.0
    timestamp_start: float = 0.0
    timestamp_end: float = 4.0
    emphasis: bool = False  # If True, shot gets Ken Burns zoom + text overlay during assembly

@dataclass
class Scene:
    index: int
    narration: str
    shots: list[Shot]
    energy_level: str = "build"     # hook, build, peak, release, transition
    visual_direction: str = ""      # e.g. "Rapid establishing cuts, high energy"
```

## Two-Step Dry Run → Production Pattern

Step 1 — Generate the dense script JSON via LLM (no TTS/FLUX):
```bash
python create_video_v4.py --script-file scripts/my-script.md --trailer --dry-run
```
This saves to `outputs/<slug>/script.json`. Inspect for scene count (expect 25-35), shot count (expect 100+).

Step 2 — Full production with saved script (no LLM call):
```bash
python create_video_v4.py --script-json outputs/<slug>/script.json --tts chatterbox --subtitles
```

This pattern saves $0.01-0.02 per run on LLM costs and lets you iterate the video without re-running the breakdown.

## Prompt Template

File: `prompts/trailer_breakdown_v4_prompt.txt`

Key instructions to the LLM:
- "EXACTLY 25-35 scenes (no fewer, no more)"
- "Each scene has EXACTLY 4-6 shots"
- "Each shot duration_hint_sec: 2.0 to 5.0"
- Energy levels with timestamp boundaries: hook→build→peak→release→transition
- Each shot has `timestamp_start` and `timestamp_end` for precise timeline positioning
- Visual direction per scene for camera/mood consistency across shots

## Assembly Logic

1. **Parse timestamps from filenames** via `_ts_re = re.compile(r"_(\d{5})_(\d{5})\.")`
2. **Clip duration** = `(end_ms - start_ms) / 1000.0` (clamped to min 0.5s)
3. **Emphasis-based Ken Burns** — default is static (no zoom). Only shots with `emphasis: true` get zoom + text overlay:
   - Allocation heuristic: `peak` → first+last shot, `hook` → first shot, `build` → last shot (50% chance), `release`/`transition` → none
   - Result: ~20% emphasis zoom, 80% static. Prevents nauseating constant motion.
4. **Energy-based transitions** — scene-level xfade type derived from `energy_level`:
   ```python
   xfade_map = {"hook": "fade", "peak": "fade", "build": "fade", 
                "release": "fade", "transition": "fade"}
   ```
   (Current: all fade. Architecture supports adding "slide", "wipe", etc.)
5. **Fallback path** — when timestamps are absent from filenames (legacy v3 images):
   ```python
   so = scene.shots[shot_idx]
   w = so.duration_hint_sec / sum(s.duration_hint_sec for s in scene.shots)
   dur = max(0.5, (audio_dur / len(scenes)) * w)
   ```

## GPU Generation Budget

108 images × ~15s per image (RTX 3090, 4-step schnell, WDDM driver overhead) ≈ 27 minutes total generation time.

Plan for:
- First image: 30-60s (model loads into VRAM)
- Subsequent images: 12-18s each (partial model swap in/out)
- Total: ~25-30 minutes for a full 108-shot v4 build

Use `background=true` + `notify_on_complete=true` and pipe output to a file.

## Known Limitations

- The LLM doesn't always follow the exact shot count constraint (4-6 shots). Floor at 3 is not uncommon, especially for later scenes. The 100+ total target is usually met.
- FLUX generation is the bottleneck. At ~15s per image × 108 images, the user should be told upfront it'll take ~30 minutes.
- WDDM GPU driver can hang under sustained FLUX loads on Windows. If VRAM usage climbs to 23.9/24GB and stays there, ComfyUI starts dropping keepalive connections. Recovery: `docker restart yt-anim-comfyui`.
