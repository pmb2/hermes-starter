# Hyperframes Integration

Hyperframes (heygen-com/hyperframes, 27k+ stars) is an open-source HTML-to-MP4 rendering engine. Write HTML/CSS with animations (GSAP, CSS, Lottie, Three.js), render via headless Chrome + FFmpeg. Deterministic output — same input always produces same video.

**Purpose in pipeline**: Finishing pass over the FLUX-assembled video. Wraps the base MP4 with:
- Animated HTML/CSS text overlays (titles, scene labels, captions)
- GSAP fade/slide entrances for text elements
- Professional lower thirds on emphasis shots
- Kinetic captions synced to narration
- Shader transitions between scenes

## Installation

```bash
npm install -g hyperframes             # v0.6.95+
npx hyperframes --help
```

Requires Node.js 22+ and FFmpeg.

## Flow

```
v5 assembly output (video_final.mp4)
           ↓
    Hyperframes HTML composition wraps the video
           ↓
    npx hyperframes render → polished MP4
```

## Tested Commands

```bash
# Scaffold a project
cd outputs/hyperframes_work
npx hyperframes init my-video

# Preview in browser (live reload)
cd my-video && npm run dev

# Render to MP4
npm run render
# Output: renders/my-video_YYYY-MM-DD_HH-MM-SS.mp4
```

Full test run completed in 21s for a 22s test video on this machine.

## Composition Template

The HTML stage wraps the base video + text overlays with GSAP timings:

```html
<div id="stage" data-composition-id="trailer" data-start="0"
     data-width="1920" data-height="1080" data-duration="154">

  <!-- Base video from our pipeline -->
  <video data-start="0" data-duration="154" data-track-index="0"
         src="video_final.mp4" muted playsinline></video>

  <!-- Animated title overlay -->
  <h1 class="title" data-start="0.5" data-duration="4" data-track-index="1"
      style="position:absolute; top:80px; left:60px; font-family:sans-serif;
             color:white; font-size:48px; text-shadow:2px 2px 4px rgba(0,0,0,0.8);">
    Title Text
  </h1>

  <script src="https://cdn.jsdelivr.net/npm/gsap@3/dist/gsap.min.js"></script>
  <script>
    const tl = gsap.timeline({ paused: true });
    tl.from(".title", { opacity: 0, y: -30, duration: 0.8 }, 0.5);
    tl.to(".title", { opacity: 0, y: -30, duration: 0.5 }, 4.0);
    window.__timelines = window.__timelines || {};
    window.__timelines.trailer = tl;
  </script>
</div>
```

## Catalog Blocks

```bash
npx hyperframes add flash-through-white    # Shader transition
npx hyperframes add instagram-follow       # Social overlay
npx hyperframes add data-chart             # Animated chart
npx hyperframes add kinetic-captions       # Auto-synced captions
npx hyperframes add lower-third            # Professional lower thirds
npx hyperframes add progress-bar           # Timeline progress
```

## Integration into Pipeline

Add as a post-assembly step in `run_v5.py`:

```python
def hyperframes_finish(video_path, output_path):
    hf_dir = Path("outputs/hyperframes_temp")
    if hf_dir.exists(): shutil.rmtree(hf_dir)
    
    subprocess.run(["npx", "hyperframes", "init", str(hf_dir / "finish")],
                   capture_output=True, timeout=30)
    shutil.copy2(video_path, hf_dir / "finish" / "source.mp4")
    
    comp = hf_dir / "finish" / "src" / "index.html"
    comp.write_text(generate_composition_html("source.mp4"))
    
    subprocess.run(["npm", "run", "render"],
                   cwd=hf_dir / "finish", capture_output=True, timeout=300)
    
    result = list((hf_dir / "finish" / "out").glob("*.mp4"))
    if result:
        shutil.copy2(result[0], output_path)
```

## Benefits Over FFmpeg-Only

| Aspect | FFmpeg-only | + Hyperframes |
|--------|-------------|---------------|
| Text overlays | drawtext (limited, crashes on gyan.dev) | Full HTML/CSS typography |
| Animations | Ken Burns zoom only | GSAP, CSS keyframes, Lottie |
| Captions | SRT file only | Kinetic typography |
| Design control | None | Full CSS design system |
| Components | None | Catalog blocks |
